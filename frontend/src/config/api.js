// API configuration for development and production
const API_CONFIG = {
  // In production, use the actual backend URL
  // In development, use relative path (Vite proxy will handle it)
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 30000,
};

export default API_CONFIG;
