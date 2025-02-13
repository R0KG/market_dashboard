from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_sentiment_positive():
    response = client.post("/sentiment", params={"text": "I love this stock!"})
    assert response.status_code == 200
    data = response.json()
    assert data["sentiment"]["compound"] > 0
    assert "id" in data  # Check if ID is returned

def test_sentiment_negative():  
    response = client.post("/sentiment", params={"text": "I hate this stock!"})
    assert response.status_code == 200
    data = response.json()
    assert data["sentiment"]["compound"] < 0
    assert "id" in data  # Check if ID is returned
    
def test_sentiment_neutral():
    response = client.post("/sentiment", params={"text": "This is a stock."})
    assert response.status_code == 200
    data = response.json()
    assert -0.1 <= data["sentiment"]["compound"] <= 0.1  # More realistic neutral check
    assert "id" in data  # Check if ID is returned

def test_get_sentiments():
    # First add a test sentiment
    client.post("/sentiment", params={"text": "Test sentiment"})
    
    # Then get all sentiments
    response = client.get("/sentiments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "id" in data[0]
        assert "text" in data[0]
        assert "sentiment" in data[0]
        assert "timestamp" in data[0]