"""
Cache Busting Middleware for FastAPI Application

This module adds cache-busting headers and endpoints to help with deployment issues
on hosting providers like Hostinger where caching can cause issues.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import tempfile
from datetime import datetime
import psutil  # Add this import for system monitoring
import gc

def add_cache_busting_headers(app: FastAPI):
    """Add cache-busting headers to all responses"""
    
    @app.middleware("http")
    async def cache_busting_middleware(request, call_next):
        response = await call_next(request)
        
        # Add cache-busting headers to prevent browser/cache issues
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["ETag"] = str(hash(datetime.now().isoformat()))
        
        return response

def add_cache_management_endpoints(app: FastAPI):
    """Add endpoints for cache management"""
    
    @app.post("/api/admin/clear-cache")
    async def clear_cache():
        """Clear application cache and temporary files"""
        try:
            cleared_items = []
            
            # Clear temporary files
            temp_dir = tempfile.gettempdir()
            for file in os.listdir(temp_dir):
                if "cloth_enhanc" in file.lower() or "tmp" in file.lower():
                    file_path = os.path.join(temp_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                            cleared_items.append(f"Temp file: {file_path}")
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                            cleared_items.append(f"Temp dir: {file_path}")
                    except Exception as e:
                        # Continue even if some files can't be deleted
                        continue
            
            # Clear Python cache
            for root, dirs, files in os.walk("."):
                for d in dirs:
                    if d == "__pycache__":
                        pycache_path = os.path.join(root, d)
                        try:
                            shutil.rmtree(pycache_path)
                            cleared_items.append(f"Python cache: {pycache_path}")
                        except Exception:
                            # Continue even if some cache dirs can't be deleted
                            pass
            
            # Force garbage collection
            gc.collect()
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Cache cleared successfully",
                    "cleared_items": cleared_items,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")
    
    @app.get("/api/admin/system-info")
    async def system_info():
        """Get system information for debugging"""
        try:
            info = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent if hasattr(psutil, 'disk_usage') else "N/A",
                "process_count": len(psutil.pids()),
                "python_version": __import__('sys').version,
                "current_directory": os.getcwd(),
                "memory_info": dict(psutil.Process().memory_info()._asdict()) if hasattr(psutil.Process().memory_info(), '_asdict') else "N/A"
            }
            return JSONResponse(status_code=200, content=info)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting system info: {str(e)}")

def setup_cache_management(app: FastAPI):
    """Setup all cache management functionality"""
    add_cache_busting_headers(app)
    add_cache_management_endpoints(app)