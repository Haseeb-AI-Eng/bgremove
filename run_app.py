#!/usr/bin/env python3
"""
Script to run the application with fallback to mock database if MongoDB is not available
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if we can connect to MongoDB, if not, warn the user
try:
    from pymongo import MongoClient
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=1000)  # 1 second timeout
    client.admin.command('ping')
    print("+ Connected to MongoDB successfully")
    client.close()
except Exception as e:
    print(f"- Could not connect to MongoDB: {e}")
    print("Using mock database for development. Data will not persist between runs.")
    print("To use a real database, install MongoDB or set up MongoDB Atlas.")

# Run the main application
if __name__ == "__main__":
    import sys
    import os
    # Add the app directory to the Python path so imports work correctly
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

    import uvicorn
    from main import app
    uvicorn.run(app, host="0.0.0.0", port=8000)