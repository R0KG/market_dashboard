import React from 'react';



interface SentimentResult {
  text: string;
  sentiment: {
    compound: number;
    positive: number;
    negative: number;
    neutral: number;
  };
  timestamp: string;
}



export function Dashboard() {
  const [] 



  return (
    <div>
      <h1>Sentiment Analysis Dashboard</h1>
      <p>Welcome to the sentiment analysis dashboard</p>
    </div>
  );
} 