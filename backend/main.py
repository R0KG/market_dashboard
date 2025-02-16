from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from redis import Redis
import json
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import jwt
from passlib.context import CryptContext

app = FastAPI()
# Connect to Redis using the service name from docker-compose
redis_client = Redis(host='redis', port=6379, db=0, decode_responses=True)
vader_analyzer = SentimentIntensityAnalyzer()

# Auth settings
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis key patterns
USER_KEY = "user:{}"  # user:email
SENTIMENT_KEY = "sentiment:{}:{}"  # sentiment:user_id:text_hash
HISTORY_KEY = "history:{}"  # history:user_id

class UserCreate(BaseModel):
    email: str
    password: str

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        # Verify user exists in Redis
        if not redis_client.exists(USER_KEY.format(email)):
            raise credentials_exception
        return email
    except jwt.JWTError:
        raise credentials_exception

@app.post("/register")
async def register(user: UserCreate):
    user_key = USER_KEY.format(user.email)
    if redis_client.exists(user_key):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Store user data in Redis
    user_data = {
        "email": user.email,
        "password": get_password_hash(user.password),
        "created_at": datetime.now().isoformat()
    }
    redis_client.hmset(user_key, user_data)
    return {"message": "Registration successful"}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_key = USER_KEY.format(form_data.username)
    user_data = redis_client.hgetall(user_key)
    
    if not user_data or not verify_password(form_data.password, user_data.get("password", "")):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

def get_sentiment(text: str, user_id: str) -> dict:
    # Create unique key for this sentiment analysis
    sentiment_key = SENTIMENT_KEY.format(user_id, hash(text))
    
    # Check cache
    cached_result = redis_client.get(sentiment_key)
    if cached_result:
        return json.loads(cached_result)
    
    # Generate new sentiment
    vader_result = vader_analyzer.polarity_scores(text)
    
    result = {
        "text": text,
        "sentiment": {
            "compound": vader_result["compound"],
            "positive": vader_result["pos"],
            "negative": vader_result["neg"],
            "neutral": vader_result["neu"]
        },
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id
    }
    
    # Store sentiment result with expiration
    redis_client.setex(sentiment_key, 3600, json.dumps(result))
    
    # Add to user's history
    history_key = HISTORY_KEY.format(user_id)
    redis_client.lpush(history_key, json.dumps(result))
    redis_client.ltrim(history_key, 0, 99)  # Keep last 100 entries
    
    return result

@app.post("/sentiment")
async def analyze_sentiment(text: str, current_user: str = Depends(get_current_user)):
    try:
        sentiment = get_sentiment(text, current_user)
        return sentiment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sentiments")
async def get_sentiments(current_user: str = Depends(get_current_user)):
    try:
        history_key = HISTORY_KEY.format(current_user)
        history = redis_client.lrange(history_key, 0, -1)
        return [json.loads(item) for item in history]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")




