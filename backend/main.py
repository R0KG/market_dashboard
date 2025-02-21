from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize VADER sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

class TextInput(BaseModel):
    text: str

@app.post("/sentiment")
async def analyze_sentiment(input: TextInput):
    try:
        logger.info(f"Analyzing text: {input.text}")
        
        # Get sentiment scores
        sentiment_scores = analyzer.polarity_scores(input.text)
        
        # Create response
        result = {
            "text": input.text,
            "sentiment": {
                "compound": sentiment_scores["compound"],
                "pos": sentiment_scores["pos"],
                "neg": sentiment_scores["neg"],
                "neu": sentiment_scores["neu"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Analysis result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


