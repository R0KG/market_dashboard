from fastapi import FastAPI
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime
import json
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import FastAPI, BackgroundTasks
from transformers import pipeline
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import redis
import json
from typing import List, Optional
import torch




class Base(DeclarativeBase):
    pass

app = FastAPI()
analyzer = SentimentIntensityAnalyzer()
SQLALCHEMY_DATABASE_URL = "postgresql://sentiment_user:sentiment_password@localhost:5432/sentiment_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




vader_analyzer = SentimentIntensityAnalyzer()
hf_analyzer = pipeline("sentiment-analysis", model="finiteautomata/bertweet-base-sentiment-analysis")

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


redis_client = redis.Redis(host="localhost", port=6379, db=0,decode_responses=True)
CACHE_TTL = 3600


        
class SentimentRequest(Base):
    texts: List[str]
    use_cache: bool = True

async def analyze_with_transformers(text: str) -> dict:
    results = hf_analyzer(text)
    return {
        "label": results[0]["label"],
        "score": float(results[0]["score"])
    }
def get_combined_sentiment(text: str,cache_key: Optional[str] = None) -> dict:
    
    if cache_key and redis_client.exists(cache_key):
        return json.loads(redis_client.get(cache_key))
    
    vader_result = analyzer.polarity_scores(text)
    transformers_result = hf_analyzer(text)[0]
    
    result = {
        "text": text,
        "vader":
            {
                "compound": vader_result["compound"],
                "positive": vader_result["pos"],
                "negative": vader_result["neg"],
                "neutral": vader_result["neu"]
            },
        "huggingface":
            {
                "label": transformers_result["label"],
                "score": float(transformers_result["score"])
            },
            "combined_score": (vader_result["compound"] + (1 if transformers_result["label"] == "POS" else -1)) / 2
    }
    if cache_key:
        redis_client.setex(cache_key,CACHE_TTL,json.dumps(result))
    return result


      

class User(Base):
    __tablename__ = "users"
    id = Column(Integer,primary_key=True,index=True)
    email = Column(String,unique=True,index=True)
    hashed_password = Column(String)
    is_active = Column(bool,default=True)
    

class SentimentRecord(Base):
    __tablename__ = "sentiments"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True)
    compound = Column(Float)
    positive = Column(Float)
    negative = Column(Float)
    neutral = Column(Float)
    hf_label = Column(String)
    hf_score = Column(Float)
    combined_score = Column(Float)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)


def get_current_user(email : str):
    db = SessionLocal()
    try:
        user = db.query(User).filer(email == User.email).first()
        raise HTTPException(status_code=400, detail="Not found")
        return user
    finally:
        db.close()

        

@app.post("/sentiment")
async def analyze_sentiment(
    text: str,
    use_cache :bool = True,
    current_user: User = Depends(get_current_user)
    ):
    cache_key = f"sentiment:{hash(text)}" if use_cache else None
    
    sentiment = get_combined_sentiment(text,cache_key=cache_key)
    
    db = SessionLocal()
    db_record = SentimentRecord(
        text=text,
        compound=sentiment["vader"]["compound"],
        positive=sentiment["vader"]["positive"],
        negative=sentiment["vader"]["negative"],
        neutral=sentiment["vader"]["neutral"],
        hf_label=sentiment["huggingface"]["label"],
        hf_score=sentiment["huggingface"]["score"],
        combined_score=sentiment["combined_score"],
        user_id=current_user.id
    )
    try:
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        sentiment["id"] = db_record.id
    
    finally:
        db.close()
    
    return sentiment

@app.get("/sentiments")
async def get_sentiments():
    db = SessionLocal()
    try:
        records = db.query(SentimentRecord).all()
        
        return [
            {
                "id": record.id,
                "text": record.text,
                "sentiment": {
                    "compound": record.compound,
                    "positive": record.positive,
                    "negative": record.negative,
                    "neutral": record.neutral
                },
                "timestamp": record.created_at
            } for record in records
        ]
    finally:
        db.close()
        
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
  db = SessionLocal()
  try:
      user = db.query(User).filter(User.email == form_data.email).first()
      if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
      access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
      access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
      return {"access_token": access_token, "token_type": "bearer"}
  finally:
      db.close()

@app.post("/batch-sentiment")
async def batch_sentiment(
    request: SentimentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    results = []
    for text in request.texts:
        cache_key = f"sentiment:{hash(text)}" if request.use_cache else None
        sentiment = get_combined_sentiment(text,cache_key=cache_key)
        results.append(sentiment)
        background_tasks.add_task(store_sentiment_records,request.texts,sentiment,current_user.id)
    return results

async def store_sentiment_records(text : str,sentiment: dict,user_id: int):
    db = SessionLocal()
    db_record = SentimentRecord(
        text=text,
        compound=sentiment["vader"]["compound"],
        positive=sentiment["vader"]["positive"],
        negative=sentiment["vader"]["negative"],
        neutral=sentiment["vader"]["neutral"],
        hf_label=sentiment["huggingface"]["label"],
        hf_score=sentiment["huggingface"]["score"],
        combined_score=sentiment["combined_score"],
        user_id=user_id
    )
    try:
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        return db_record
    finally:
        db.close()

@app.post("/register")
async def register(email: str, password: str):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        hashed_password = get_password_hash(password)
        user = User(email=email, hashed_password=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"message": "User registered successfully"}
    finally:
        db.close()
    
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt




