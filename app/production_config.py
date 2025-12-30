"""
Production Configuration for Cloth Enhancement App

This configuration addresses common deployment issues with hosting providers like Hostinger
"""

import os
from typing import List, Optional

class ProductionConfig:
    # Server configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    
    # CORS configuration for production
    ALLOWED_ORIGINS = [
        "https://hintergrundentfernen.ai",  # Replace with your actual domain
        "https://www.hintergrundentfernen.ai",
        "http://localhost:3000",  # For local frontend development
        "http://localhost:5173",  # Another common dev port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # Add your actual production domain
    CUSTOM_DOMAIN = os.getenv("CUSTOM_DOMAIN", "hintergrundentfernen.ai")
    if CUSTOM_DOMAIN:
        ALLOWED_ORIGINS.extend([
            f"https://{CUSTOM_DOMAIN}",
            f"https://www.{CUSTOM_DOMAIN}",
            f"http://{CUSTOM_DOMAIN}",
            f"http://www.{CUSTOM_DOMAIN}",
        ])
    
    # Database configuration
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    DB_NAME = os.getenv("DB_NAME", "cloth_enhancement")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "users")
    
    # File upload configuration
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    UPLOAD_DIRECTORY = os.getenv("UPLOAD_DIR", "uploads")
    OUTPUT_DIRECTORY = os.getenv("OUTPUT_DIR", "output")
    
    # Cache configuration
    ENABLE_CACHE_BUSTING = True
    CACHE_MAX_AGE = 0  # No caching for API responses
    
    # Security headers
    SECURITY_HEADERS = {
        "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
    }
    
    # API configuration
    API_PREFIX = "/api"
    API_VERSION = "v1"
    
    # Stripe configuration
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    # Frontend URL for redirects
    FRONTEND_URL = os.getenv("FRONTEND_URL", "https://hintergrundentfernen.ai")
    
    @classmethod
    def get_cors_config(cls):
        """Get CORS configuration for FastAPI"""
        return {
            "allow_origins": cls.ALLOWED_ORIGINS,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
            "allow_origin_regex": r"https?://.*\.?yourdomain\.com(/.*)?" if "yourdomain.com" in cls.CUSTOM_DOMAIN else None,
        }

# Hostinger-specific configurations
class HostingerConfig(ProductionConfig):
    """Specific configurations for Hostinger hosting"""
    
    # Hostinger often requires specific settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 80))  # Hostinger might use port 80
    
    # Additional security headers for Hostinger
    HOSTINGER_SECURITY_HEADERS = {
        **ProductionConfig.SECURITY_HEADERS,
        "X-Forwarded-Proto": "https",
        "X-Forwarded-For": "*",
    }
    
    # Specific CORS settings that work well with Hostinger
    HOSTINGER_CORS_ORIGINS = [
        "https://hintergrundentfernen.ai",  # Replace with your domain
        "https://www.hintergrundentfernen.ai",
        "https://hintergrundentfernen.h.filescdn.ru",  # Common Hostinger CDN
    ]
    
    @classmethod
    def get_hostinger_cors_config(cls):
        """Get CORS configuration optimized for Hostinger"""
        base_config = cls.get_cors_config()
        # Add Hostinger-specific settings
        base_config["allow_origins"].extend(cls.HOSTINGER_CORS_ORIGINS)
        return base_config

# Get the active configuration
def get_config():
    """Get the appropriate configuration based on environment"""
    env = os.getenv("ENVIRONMENT", "production").lower()
    
    if "hostinger" in env or "production" in env:
        return HostingerConfig
    else:
        return ProductionConfig

# Example usage for your main.py:
def configure_app(app):
    """Configure the FastAPI app with production settings"""
    from fastapi.middleware.cors import CORSMiddleware
    import os
    
    config = get_config()
    
    # Add CORS middleware with production settings
    cors_config = config.get_hostinger_cors_config() if "hostinger" in os.getenv("ENVIRONMENT", "").lower() else config.get_cors_config()
    
    app.add_middleware(
        CORSMiddleware,
        **cors_config
    )
    
    # Add security headers middleware
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        
        # Add security and cache-busting headers
        for header, value in config.SECURITY_HEADERS.items():
            if header == "Cache-Control":
                response.headers["Cache-Control"] = value
            elif header == "Pragma":
                response.headers["Pragma"] = value
            elif header == "Expires":
                response.headers["Expires"] = value
        
        # Add Hostinger-specific headers if applicable
        if hasattr(config, 'HOSTINGER_SECURITY_HEADERS'):
            for header, value in config.HOSTINGER_SECURITY_HEADERS.items():
                if header not in ["Cache-Control", "Pragma", "Expires"]:
                    response.headers[header] = str(value)
        
        return response
    
    return app