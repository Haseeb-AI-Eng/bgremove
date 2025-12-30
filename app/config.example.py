"""
Configuration example for Image Processing API
Copy this file to config.py and modify as needed
"""

import os

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

# API Configuration
API_TITLE = os.getenv("API_TITLE", "Image Processing API")
API_VERSION = os.getenv("API_VERSION", "1.0.0")

# File Upload Configuration
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB
ALLOWED_FORMATS = os.getenv("ALLOWED_FORMATS", "png,jpg,jpeg,bmp,webp").split(",")

# Processing Configuration
DEFAULT_COLOR_SHIFT = int(os.getenv("DEFAULT_COLOR_SHIFT", 60))
DEFAULT_BG_COLOR = os.getenv("DEFAULT_BG_COLOR", "FFFFFF")

# Optional: FASHN AI Integration
FASHN_API_KEY = os.getenv("FASHN_API_KEY", None)
FASHN_API_URL = os.getenv("FASHN_API_URL", "https://api.fashn.ai/v1/run")

# Feature Flags
ENABLE_FASHN_INTEGRATION = os.getenv("ENABLE_FASHN_INTEGRATION", "false").lower() == "true"
