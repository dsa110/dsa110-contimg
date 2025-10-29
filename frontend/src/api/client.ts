/**
 * API client configuration for DSA-110 pipeline backend.
 */
import axios from 'axios';

// Use current origin when served from API at /ui, otherwise use localhost:8000
const API_BASE_URL = (typeof window !== 'undefined' && window.location.pathname.startsWith('/ui')) 
  ? window.location.origin 
  : 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,  // 30 seconds for conversion jobs
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.message);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }
    return Promise.reject(error);
  }
);

