"""
Configuration for Image Processing API
"""

import os

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

# Database Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "admin")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "users")

# API Configuration
API_TITLE = os.getenv("API_TITLE", "Image Processing API")
API_VERSION = os.getenv("API_VERSION", "1.0.0")

# File Upload Configuration
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB
ALLOWED_FORMATS = os.getenv("ALLOWED_FORMATS", "png,jpg,jpeg,bmp,webp").split(",")

# Processing Configuration
DEFAULT_COLOR_SHIFT = int(os.getenv("DEFAULT_COLOR_SHIFT", 60))
DEFAULT_BG_COLOR = os.getenv("DEFAULT_BG_COLOR", "FFFFFF")

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")

# Stripe Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")

# Frontend Configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://hintergrundentfernen.ai")

# Optional: FASHN AI Integration
FASHN_API_KEY = os.getenv("FASHN_API_KEY", None)
FASHN_API_URL = os.getenv("FASHN_API_URL", "https://api.fashn.ai/v1/run")

# Feature Flags
ENABLE_FASHN_INTEGRATION = os.getenv("ENABLE_FASHN_INTEGRATION", "false").lower() == "true"