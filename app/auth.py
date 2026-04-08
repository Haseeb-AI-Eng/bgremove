from fastapi import HTTPException, status, Depends, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from bson import ObjectId
from dotenv import load_dotenv
import os
import secrets
import string
import uuid
import json

# Load environment variables
load_dotenv()

# Import vector DB and email service
try:
    from vector_db import vector_db
    VECTOR_DB_AVAILABLE = True
except ImportError:
    vector_db = None
    VECTOR_DB_AVAILABLE = False
    print("Vector DB not available")

try:
    from email_service import email_service
    EMAIL_SERVICE_AVAILABLE = True
except ImportError:
    email_service = None
    EMAIL_SERVICE_AVAILABLE = False
    print("Email service not available")

# Strict MongoDB requirement
try:
    from mongodb_db import get_mongodb_db
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    DB_NAME = os.getenv('DB_NAME', 'bgremove_db')
    db_instance = get_mongodb_db(MONGODB_URI, DB_NAME)
    DATABASE_TYPE = "mongodb"
    print(f"Connected to MongoDB successfully at {MONGODB_URI}")
except Exception as e:
    print(f"CRITICAL ERROR: Could not connect to MongoDB: {e}")
    DATABASE_TYPE = "sqlite" # Fallback
    try:
        from sqlite_db import sqlite_db
        print("Falling back to SQLite")
    except ImportError:
        print("SQLite fallback also failed")
        raise RuntimeError(f"Database connection failed: {e}")

# JWT configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# User models
class User(BaseModel):
    id: Optional[str] = None
    email: str
    password: str
    created_at: datetime = datetime.utcnow()
    is_active: bool = True
    is_verified: bool = False
    is_pro: bool = False
    subscription_end: Optional[datetime] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None

class UserInDB(User):
    hashed_password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Helper function to verify password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Helper function to hash password
def get_password_hash(password):
    return pwd_context.hash(password)

# Database access functions (Async)
async def get_user(email: str) -> Optional[UserInDB]:
    if DATABASE_TYPE == "mongodb":
        user_data = await db_instance.get_user(email)
        if user_data:
            return UserInDB(**user_data)
    elif DATABASE_TYPE == "sqlite":
        user_data = sqlite_db.get_user(email)
        if user_data:
            return UserInDB(
                id=user_data['id'],
                email=user_data['email'],
                password="",
                hashed_password=user_data['hashed_password'],
                created_at=user_data['created_at'],
                is_active=user_data['is_active'],
                is_verified=user_data.get('is_verified', False),
                is_pro=user_data['is_pro'],
                subscription_end=user_data['subscription_end'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                bio=user_data['bio'],
                profile_image=user_data['profile_image']
            )
    return None

async def create_user(user_data: UserRegister) -> UserInDB:
    if VECTOR_DB_AVAILABLE and vector_db:
        if vector_db.check_user_exists(user_data.email):
            raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_user = await get_user(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_data.password)
    user_id = str(uuid.uuid4())

    user_in_db = UserInDB(
        id=user_id,
        email=user_data.email,
        password="",
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=False,
        is_verified=False
    )

    if DATABASE_TYPE == "mongodb":
        user_doc = user_in_db.dict()
        user_doc['id'] = user_id
        await db_instance.create_user(user_doc)
    elif DATABASE_TYPE == "sqlite":
        user_data_dict = {
            'id': user_in_db.id,
            'email': user_in_db.email,
            'hashed_password': user_in_db.hashed_password,
            'first_name': user_in_db.first_name,
            'last_name': user_in_db.last_name,
            'is_active': int(user_in_db.is_active),
            'is_verified': int(user_in_db.is_verified)
        }
        sqlite_db.create_user(user_data_dict)

    if VECTOR_DB_AVAILABLE and vector_db:
        try:
            vector_db.add_user(user_id=user_id, email=user_data.email, user_data={"first_name": user_data.first_name or "", "last_name": user_data.last_name or ""})
        except Exception as e:
            print(f"Warning: Failed to add user to vector DB: {e}")

    token = await generate_verification_token(user_in_db.id)
    if EMAIL_SERVICE_AVAILABLE and email_service:
        try:
            email_service.send_verification_email(to_email=user_data.email, verification_token=token)
        except Exception as e:
            print(f"Warning: Failed to send verification email: {e}")

    return user_in_db

async def create_auth_response(user: UserInDB) -> Token:
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"sub": user.email}, expires_delta=refresh_token_expires)
    expires_at = datetime.utcnow() + refresh_token_expires
    await store_refresh_token(user.id, refresh_token, expires_at)
    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

async def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    user = await get_user(email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not verified yet.")
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def generate_verification_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    await store_verification_token(user_id, token, expires_at)
    return token

async def store_verification_token(user_id: str, token: str, expires_at: datetime):
    if DATABASE_TYPE == "mongodb":
        await db_instance.store_verification_token(user_id, token, expires_at)
    elif DATABASE_TYPE == "sqlite":
        sqlite_db.store_verification_token(user_id, token, expires_at)

async def verify_email_token(token: str) -> bool:
    if DATABASE_TYPE == "mongodb":
        return await db_instance.verify_email_token(token)
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.verify_email_token(token)

async def get_verification_token_for_user(email: str) -> Optional[str]:
    user = await get_user(email)
    if not user: return None
    if DATABASE_TYPE == "mongodb":
        token_doc = await db_instance.email_verification_tokens.find_one({"user_id": user.id, "is_active": True})
        return token_doc["token"] if token_doc else None
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.get_verification_token_for_user(user.id)

async def store_refresh_token(user_id: str, refresh_token: str, expires_at: datetime):
    if DATABASE_TYPE == "mongodb":
        await db_instance.store_refresh_token(user_id, refresh_token, expires_at)
    elif DATABASE_TYPE == "sqlite":
        sqlite_db.store_refresh_token(user_id, refresh_token, expires_at)

async def is_refresh_token_valid(refresh_token: str) -> bool:
    if DATABASE_TYPE == "mongodb":
        return await db_instance.is_refresh_token_valid(refresh_token)
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.is_refresh_token_valid(refresh_token)

async def invalidate_refresh_token(refresh_token: str):
    if DATABASE_TYPE == "mongodb":
        await db_instance.invalidate_refresh_token(refresh_token)
    elif DATABASE_TYPE == "sqlite":
        sqlite_db.invalidate_refresh_token(refresh_token)

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)) -> UserInDB:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access": raise credentials_exception
        email = payload.get("sub")
        if email is None: raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = await get_user(email=email)
    if user is None or not user.is_active or not user.is_verified: raise credentials_exception
    return user

async def update_user_subscription(email: str, is_pro: bool, subscription_end: datetime):
    if DATABASE_TYPE == "mongodb":
        return await db_instance.update_user_subscription(email, is_pro, subscription_end)
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.update_user_subscription(email, is_pro, subscription_end)

async def update_user_profile(email: str, first_name: Optional[str] = None, last_name: Optional[str] = None, bio: Optional[str] = None):
    if DATABASE_TYPE == "mongodb":
        return await db_instance.update_user_profile(email, first_name, last_name, bio)
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.update_user_profile(email, first_name, last_name, bio)

async def update_user_profile_image(email: str, profile_image_url: str):
    if DATABASE_TYPE == "mongodb":
        return await db_instance.update_user_profile_image(email, profile_image_url)
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.update_user_profile_image(email, profile_image_url)

# API Keys
class APIKey(BaseModel):
    id: Optional[str] = None
    user_id: str
    key: str
    key_prefix: str
    name: Optional[str] = "Default API Key"
    status: str = "active"
    permissions: Optional[list] = []
    created_at: datetime = datetime.utcnow()
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

def generate_api_key():
    alphabet = string.ascii_letters + string.digits
    key = ''.join(secrets.choice(alphabet) for _ in range(64))
    return key, key[:8]

def hash_api_key(api_key: str) -> str:
    return pwd_context.hash(api_key)

async def create_api_key_for_user(user_id: str, key_name: str = "Default API Key"):
    api_key, key_prefix = generate_api_key()
    hashed_key = hash_api_key(api_key)
    api_key_doc = {"id": str(uuid.uuid4()), "user_id": user_id, "key": hashed_key, "key_prefix": key_prefix, "name": key_name, "status": "active", "permissions": ["read", "write"]}
    if DATABASE_TYPE == "mongodb":
        api_key_id = await db_instance.create_api_key(api_key_doc)
    elif DATABASE_TYPE == "sqlite":
        api_key_id = sqlite_db.create_api_key(api_key_doc)
    return api_key, api_key_id

async def get_api_keys_for_user(user_id: str):
    if DATABASE_TYPE == "mongodb":
        keys = await db_instance.get_api_keys_for_user(user_id)
        return [APIKey(**key) for key in keys]
    elif DATABASE_TYPE == "sqlite":
        return [APIKey(**key) for key in sqlite_db.get_api_keys_for_user(user_id)]

async def get_api_key_by_id(api_key_id: str, user_id: str) -> Optional[APIKey]:
    if DATABASE_TYPE == "mongodb":
        key_doc = await db_instance.get_api_key_by_id(api_key_id, user_id)
        return APIKey(**key_doc) if key_doc else None
    elif DATABASE_TYPE == "sqlite":
        key_doc = sqlite_db.get_api_key_by_id(api_key_id, user_id)
        return APIKey(**key_doc) if key_doc else None

async def revoke_api_key(api_key_id: str, user_id: str) -> bool:
    if DATABASE_TYPE == "mongodb":
        return await db_instance.revoke_api_key(api_key_id, user_id)
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.revoke_api_key(api_key_id, user_id)

async def delete_api_key(api_key_id: str, user_id: str) -> bool:
    if DATABASE_TYPE == "mongodb":
        return await db_instance.delete_api_key(api_key_id, user_id)
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.delete_api_key(api_key_id, user_id)

async def get_user_by_api_key(api_key: str) -> Optional[UserInDB]:
    if DATABASE_TYPE == "mongodb":
        all_keys = await db_instance.api_keys.find({"status": "active"}).to_list(length=1000)
        for key_doc in all_keys:
            if pwd_context.verify(api_key, key_doc["key"]):
                await db_instance.api_keys.update_one({"id": key_doc["id"]}, {"$set": {"last_used_at": datetime.utcnow()}})
                user_data = await db_instance.get_user_by_id(key_doc["user_id"])
                return UserInDB(**user_data) if user_data else None
    elif DATABASE_TYPE == "sqlite":
        user_data = sqlite_db.get_user_by_api_key(api_key)
        if user_data: return UserInDB(**user_data, password="")
    return None

async def validate_api_key(api_key: str) -> bool:
    if DATABASE_TYPE == "mongodb":
        all_keys = await db_instance.api_keys.find({"status": "active"}).to_list(length=1000)
        for key_doc in all_keys:
            if pwd_context.verify(api_key, key_doc["key"]):
                await db_instance.api_keys.update_one({"id": key_doc["id"]}, {"$set": {"last_used_at": datetime.utcnow()}})
                return True
    elif DATABASE_TYPE == "sqlite":
        import sqlite3
        try:
            conn = sqlite3.connect(sqlite_db.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id, key FROM api_keys WHERE status = "active"')
            for row in cursor.fetchall():
                if pwd_context.verify(api_key, row[1]):
                    cursor.execute('UPDATE api_keys SET last_used_at = ? WHERE id = ?', (datetime.utcnow().isoformat(), row[0]))
                    conn.commit()
                    return True
        finally:
            conn.close()
    return False

async def require_api_key(request: Request) -> UserInDB:
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if not api_key: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key is required", headers={"WWW-Authenticate": "API-Key"})
    user = await get_user_by_api_key(api_key)
    if not user: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired API key", headers={"WWW-Authenticate": "API-Key"})
    return user

async def get_current_user_or_api_key(request: Request) -> UserInDB:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") == "access" and (email := payload.get("sub")):
                if user := await get_user(email=email): return user
        except jwt.PyJWTError: pass
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if api_key and (user := await get_user_by_api_key(api_key)): return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})