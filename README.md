# Background Change & Watermark Removal Service

This project provides a web service for background removal, watermark removal, and enhanced image processing. It includes a FastAPI backend and a modern frontend built with Vite and React.

## Features
- Background removal and replacement
- Watermark removal (for authenticated users)
- Human parsing, pose estimation, and image refinement
- User authentication (JWT-based)
- RESTful API endpoints
- Frontend for easy image upload and processing

## Project Structure
```
bgremove/
  app/                # FastAPI backend
    main.py           # Main API entrypoint
    auth.py           # Authentication logic
    ...
  frontend/           # React frontend (Vite)
    src/
      ...
```

## Setup

### Backend
1. Install Python 3.9+ and pip.
2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r app/requirements.txt
   ```
4. Run the backend:
   ```
   cd app
   uvicorn main:app --reload
   ```

### Frontend
1. Install Node.js (v16+ recommended).
2. Install dependencies:
   ```
   cd frontend
   npm install
   ```
3. Start the frontend dev server:
   ```
   npm run dev
   ```

## Usage
- Access the frontend at `http://localhost:5173` (default Vite port).
- Use the provided UI to upload images and process them.
- Register/login to access watermark removal and premium features.

## API Endpoints
- `POST /api/public-change-background` — Public background change
- `POST /api/watermark-removal` — Watermark removal (requires authentication)
- ... (see app/main.py for more)

## Environment Variables
Copy `app/config.example.py` to `app/config.py` and set your secrets and configuration.

## License
MIT

## Author
Your Name Here
