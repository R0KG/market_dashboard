import React, { useState } from 'react';
import axios from 'axios';

interface SentimentResult {
  text: string;
  sentiment: {
    compound: number;
    pos: number;
    neg: number;
    neu: number;
  };
  timestamp: string;
}

export function Dashboard() {
  const [text, setText] = useState('');
  const [results, setResults] = useState<SentimentResult[]>([]);
  const [error, setError] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const analyzeSentiment = async () => {
    if (!text.trim()) return;

    try {
      setIsAnalyzing(true);
      setError('');

      console.log('Sending text:', text);
      
      const response = await axios.post<SentimentResult>('http://localhost:8000/sentiment', { text });
      console.log('Received response:', response.data);
      
      setResults(prevResults => [response.data, ...prevResults]);
      setText('');
    } catch (err) {
      console.error('Error:', err);
      setError('Failed to analyze sentiment');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="dashboard-container">
      <div className="header">
        <h1>Sentiment Analysis Dashboard</h1>
      </div>

      <div className="input-section">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter text to analyze..."
          className="sentiment-input"
          disabled={isAnalyzing}
        />
        <button 
          onClick={analyzeSentiment}
          className="analyze-btn"
          disabled={!text.trim() || isAnalyzing}
        >
          {isAnalyzing ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="results-section">
        {results.map((result, index) => (
          <div key={index} className="result-card">
            <p className="text">{result.text}</p>
            <div className="sentiment-scores">
              <div className={`score ${result.sentiment.compound > 0 ? 'positive' : 'negative'}`}>
                Compound: {result.sentiment.compound.toFixed(2)}
              </div>
              <div className="score">Positive: {result.sentiment.pos.toFixed(2)}</div>
              <div className="score">Negative: {result.sentiment.neg.toFixed(2)}</div>
              <div className="score">Neutral: {result.sentiment.neu.toFixed(2)}</div>
            </div>
            <div className="timestamp">
              {new Date(result.timestamp).toLocaleString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
} 