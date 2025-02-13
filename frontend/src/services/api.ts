import axios from 'axios';

const API_URL ='http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const analyzeSentiment = async (text: string) => {
  const response = await api.post('/sentiment', { text });
  return response.data;
};

export const login = async (email: string, password: string) => {
  const response = await api.post('/token', { username: email, password });
  return response.data;
};

export const register = async (email: string, password: string) => {
  const response = await api.post('/register', { email, password });
  return response.data;
};
