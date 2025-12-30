from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from typing import Optional
from pydantic import BaseModel
from bson import ObjectId
from dotenv import load_dotenv
import os
import secrets
import string
import uuid
from fastapi import Request

# Load environment variables
load_dotenv()

# Try to connect to MongoDB, fall back to SQLite if unavailable
try:
    from pymongo import MongoClient
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    DB_NAME = os.getenv('DB_NAME', 'admin')
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=1000)  # 1 second timeout
    db = client[DB_NAME]  # Using configured database name
    # Test the connection
    client.admin.command('ping')
    print("Connected to MongoDB successfully")
    DATABASE_TYPE = "mongodb"
except Exception as e:
    print(f"Could not connect to MongoDB: {e}")
    print("Falling back to SQLite database...")
    from sqlite_db import get_sqlite_db
    sqlite_db = get_sqlite_db()
    DATABASE_TYPE = "sqlite"
    client = None

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

# Helper function to find user by email
def get_user(email: str) -> Optional[UserInDB]:
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            user_data = db.users.find_one({"email": email})
            if user_data:
                return UserInDB(**user_data, id=str(user_data["_id"]))
    elif DATABASE_TYPE == "sqlite":
        user_data = sqlite_db.get_user(email)
        if user_data:
            # Convert SQLite user data to UserInDB format
            return UserInDB(
                id=user_data['id'],
                email=user_data['email'],
                password="",  # Not stored in DB
                hashed_password=user_data['hashed_password'],
                created_at=user_data['created_at'],
                is_active=user_data['is_active'],
                is_pro=user_data['is_pro'],
                subscription_end=user_data['subscription_end'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                bio=user_data['bio'],
                profile_image=user_data['profile_image']
            )
    return None

# Helper function to create user
def create_user(user_data: UserRegister) -> UserInDB:
    existing_user = get_user(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_data.password)
    user_id = str(ObjectId()) if client is not None else str(uuid.uuid4())

    user_in_db = UserInDB(
        id=user_id,
        email=user_data.email,
        password="",  # Not storing plain password
        hashed_password=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )

    # Insert the user and get the inserted ID
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            result = db.users.insert_one(user_in_db.dict(exclude={'id'}))
            user_in_db.id = str(result.inserted_id)
        else:  # Using mock database
            users_collection = db('users')
            result = users_collection.insert_one(user_in_db.dict(exclude={'id'}))
            user_in_db.id = str(result.inserted_id)
    elif DATABASE_TYPE == "sqlite":
        # Prepare data for SQLite
        user_data_dict = {
            'id': user_in_db.id,
            'email': user_in_db.email,
            'hashed_password': user_in_db.hashed_password,
            'first_name': user_in_db.first_name,
            'last_name': user_in_db.last_name
        }
        result = sqlite_db.create_user(user_data_dict)
        if not result:
            raise HTTPException(status_code=400, detail="Email already registered")

    return user_in_db

# Create authentication response with tokens
def create_auth_response(user: UserInDB) -> Token:
    """Create authentication response with access and refresh tokens"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(
        data={"sub": user.email},
        expires_delta=refresh_token_expires
    )

    # Store refresh token in database
    expires_at = datetime.utcnow() + refresh_token_expires
    store_refresh_token(user.id, refresh_token, expires_at)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

# Helper function to authenticate user
def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    user = get_user(email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

# JWT token creation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Store refresh tokens in database
def store_refresh_token(user_id: str, refresh_token: str, expires_at: datetime):
    """Store refresh token in database"""
    token_data = {
        "user_id": user_id,
        "token": refresh_token,
        "expires_at": expires_at,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            result = db.refresh_tokens.insert_one(token_data)
            return result.inserted_id
        else:  # Using mock database
            refresh_tokens_collection = db('refresh_tokens')
            result = refresh_tokens_collection.insert_one(token_data)
            return result.inserted_id
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.store_refresh_token(user_id, refresh_token, expires_at)

def is_refresh_token_valid(refresh_token: str) -> bool:
    """Check if refresh token is valid and not expired"""
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            token_doc = db.refresh_tokens.find_one({
                "token": refresh_token,
                "is_active": True,
                "expires_at": {"$gt": datetime.utcnow()}
            })
        else:  # Using mock database
            refresh_tokens_collection = db('refresh_tokens')
            token_doc = refresh_tokens_collection.find_one({
                "token": refresh_token,
                "is_active": True,
                "expires_at": {"$gt": datetime.utcnow()}
            })
        return token_doc is not None
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.is_refresh_token_valid(refresh_token)

def invalidate_refresh_token(refresh_token: str):
    """Invalidate refresh token when used or on logout"""
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            result = db.refresh_tokens.update_one(
                {"token": refresh_token},
                {"$set": {"is_active": False}}
            )
        else:  # Using mock database
            refresh_tokens_collection = db('refresh_tokens')
            result = refresh_tokens_collection.update_one(
                {"token": refresh_token},
                {"$set": {"is_active": False}}
            )
        return result.modified_count > 0
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.invalidate_refresh_token(refresh_token)

# Get current user from token
def get_current_user(token: str = Depends(security)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        if token_type != "access":
            raise credentials_exception

        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = get_user(email=email)
    if user is None:
        raise credentials_exception
    return user

# Update user subscription status
def update_user_subscription(email: str, is_pro: bool, subscription_end: datetime):
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            result = db.users.update_one(
                {"email": email},
                {"$set": {
                    "is_pro": is_pro,
                    "subscription_end": subscription_end
                }}
            )
        else:  # Using mock database
            users_collection = db('users')
            result = users_collection.update_one(
                {"email": email},
                {"$set": {
                    "is_pro": is_pro,
                    "subscription_end": subscription_end
                }}
            )
        return result.modified_count > 0
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.update_user_subscription(email, is_pro, subscription_end)

# Update user profile
def update_user_profile(email: str, first_name: Optional[str] = None, last_name: Optional[str] = None, bio: Optional[str] = None):
    if DATABASE_TYPE == "mongodb":
        update_data = {}
        if first_name is not None:
            update_data["first_name"] = first_name
        if last_name is not None:
            update_data["last_name"] = last_name
        if bio is not None:
            update_data["bio"] = bio

        if client is not None:  # Using real MongoDB
            result = db.users.update_one(
                {"email": email},
                {"$set": update_data}
            )
        else:  # Using mock database
            users_collection = db('users')
            result = users_collection.update_one(
                {"email": email},
                {"$set": update_data}
            )
        return result.modified_count > 0
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.update_user_profile(email, first_name, last_name, bio)

# Update user profile image
def update_user_profile_image(email: str, profile_image_url: str):
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            result = db.users.update_one(
                {"email": email},
                {"$set": {"profile_image": profile_image_url}}
            )
        else:  # Using mock database
            users_collection = db('users')
            result = users_collection.update_one(
                {"email": email},
                {"$set": {"profile_image": profile_image_url}}
            )
        return result.modified_count > 0
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.update_user_profile_image(email, profile_image_url)


# API Key models
class APIKey(BaseModel):
    id: Optional[str] = None
    user_id: str
    key: str  # This will be the actual API key (hashed)
    key_prefix: str  # First few characters for display
    name: Optional[str] = "Default API Key"
    status: str = "active"  # active, revoked
    permissions: Optional[list] = []
    created_at: datetime = datetime.utcnow()
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

# API Key functions
def generate_api_key():
    """Generate a random API key"""
    alphabet = string.ascii_letters + string.digits
    # Generate a 64 character API key for better security
    key = ''.join(secrets.choice(alphabet) for _ in range(64))
    # Return the key and its prefix for display purposes
    return key, key[:8]  # First 8 chars as prefix

def hash_api_key(api_key: str) -> str:
    """Hash the API key for secure storage"""
    return pwd_context.hash(api_key)

def create_api_key_for_user(user_id: str, key_name: str = "Default API Key"):
    """Create a new API key for a user"""
    api_key, key_prefix = generate_api_key()
    hashed_key = hash_api_key(api_key)

    # Create API key document
    api_key_doc = {
        "user_id": user_id,
        "key": hashed_key,
        "key_prefix": key_prefix,
        "name": key_name,
        "status": "active",
        "permissions": ["read", "write"],  # Default permissions
        "created_at": datetime.utcnow(),
        "last_used_at": None,
        "expires_at": None
    }

    # Insert the API key
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            result = db.api_keys.insert_one(api_key_doc)
            api_key_id = str(result.inserted_id)
        else:  # Using mock database
            api_keys_collection = db('api_keys')
            result = api_keys_collection.insert_one(api_key_doc)
            api_key_id = str(result.inserted_id)
    elif DATABASE_TYPE == "sqlite":
        api_key_doc["id"] = str(uuid.uuid4())
        api_key_id = sqlite_db.create_api_key(api_key_doc)

    # Return the unhashed key to the user (only once)
    return api_key, api_key_id

def get_api_keys_for_user(user_id: str):
    """Get all API keys for a user"""
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            api_keys = list(db.api_keys.find({"user_id": user_id}))
        else:  # Using mock database
            api_keys_collection = db('api_keys')
            api_keys = api_keys_collection.find({"user_id": user_id})
        return [APIKey(**key, id=str(key["_id"])) for key in api_keys]
    elif DATABASE_TYPE == "sqlite":
        api_keys = sqlite_db.get_api_keys_for_user(user_id)
        result = []
        for key in api_keys:
            result.append(APIKey(
                id=key['id'],
                user_id=key['user_id'],
                key=key['key'],  # This is the hashed key
                key_prefix=key['key_prefix'],
                name=key['name'],
                status=key['status'],
                permissions=key['permissions'],
                created_at=key['created_at'],
                last_used_at=key['last_used_at'],
                expires_at=key['expires_at']
            ))
        return result

def get_api_key_by_id(api_key_id: str, user_id: str) -> Optional[APIKey]:
    """Get a specific API key by ID for a user"""
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            key_doc = db.api_keys.find_one({"_id": ObjectId(api_key_id), "user_id": user_id})
        else:  # Using mock database
            api_keys_collection = db('api_keys')
            key_doc = api_keys_collection.find_one({"_id": ObjectId(api_key_id), "user_id": user_id})
        if key_doc:
            return APIKey(**key_doc, id=str(key_doc["_id"]))
    elif DATABASE_TYPE == "sqlite":
        key_doc = sqlite_db.get_api_key_by_id(api_key_id, user_id)
        if key_doc:
            return APIKey(
                id=key_doc['id'],
                user_id=key_doc['user_id'],
                key=key_doc['key'],  # This is the hashed key
                key_prefix=key_doc['key_prefix'],
                name=key_doc['name'],
                status=key_doc['status'],
                permissions=key_doc['permissions'],
                created_at=key_doc['created_at'],
                last_used_at=key_doc['last_used_at'],
                expires_at=key_doc['expires_at']
            )
    return None

def revoke_api_key(api_key_id: str, user_id: str) -> bool:
    """Revoke an API key"""
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            result = db.api_keys.update_one(
                {"_id": ObjectId(api_key_id), "user_id": user_id},
                {"$set": {"status": "revoked", "revoked_at": datetime.utcnow()}}
            )
        else:  # Using mock database
            api_keys_collection = db('api_keys')
            result = api_keys_collection.update_one(
                {"_id": ObjectId(api_key_id), "user_id": user_id},
                {"$set": {"status": "revoked", "revoked_at": datetime.utcnow()}}
            )
        return result.modified_count > 0
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.revoke_api_key(api_key_id, user_id)

def delete_api_key(api_key_id: str, user_id: str) -> bool:
    """Delete an API key permanently"""
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            result = db.api_keys.delete_one(
                {"_id": ObjectId(api_key_id), "user_id": user_id}
            )
        else:  # Using mock database
            api_keys_collection = db('api_keys')
            result = api_keys_collection.delete_one(
                {"_id": ObjectId(api_key_id), "user_id": user_id}
            )
        return result.deleted_count > 0
    elif DATABASE_TYPE == "sqlite":
        return sqlite_db.delete_api_key(api_key_id, user_id)

def get_user_by_api_key(api_key: str) -> Optional[UserInDB]:
    """Get user by API key"""
    if DATABASE_TYPE == "mongodb":
        # First, verify the API key
        if client is not None:  # Using real MongoDB
            api_key_doc = db.api_keys.find_one({"key": {"$exists": True}})
            all_keys = db.api_keys.find({"status": "active"})
        else:  # Using mock database
            api_keys_collection = db('api_keys')
            api_key_doc = api_keys_collection.find_one({"key": {"$exists": True}})
            all_keys = api_keys_collection.find({"status": "active"})

        found_key = None
        for key_doc in all_keys:
            if pwd_context.verify(api_key, key_doc["key"]):
                found_key = key_doc
                break

        if found_key:
            # Update last used timestamp
            if client is not None:  # Using real MongoDB
                db.api_keys.update_one(
                    {"_id": found_key["_id"]},
                    {"$set": {"last_used_at": datetime.utcnow()}}
                )

                # Get the user
                user_doc = db.users.find_one({"_id": ObjectId(found_key["user_id"])})
            else:  # Using mock database
                api_keys_collection.update_one(
                    {"_id": found_key["_id"]},
                    {"$set": {"last_used_at": datetime.utcnow()}}
                )

                # Get the user
                users_collection = db('users')
                user_doc = users_collection.find_one({"_id": ObjectId(found_key["user_id"])})

            if user_doc:
                return UserInDB(**user_doc, id=str(user_doc["_id"]))

        return None
    elif DATABASE_TYPE == "sqlite":
        # For SQLite, we'll use the dedicated method
        user_data = sqlite_db.get_user_by_api_key(api_key)
        if user_data:
            return UserInDB(
                id=user_data['id'],
                email=user_data['email'],
                password="",  # Not stored in DB
                hashed_password=user_data['hashed_password'],
                created_at=user_data['created_at'],
                is_active=user_data['is_active'],
                is_pro=user_data['is_pro'],
                subscription_end=user_data['subscription_end'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                bio=user_data['bio'],
                profile_image=user_data['profile_image']
            )
        return None

def validate_api_key(api_key: str) -> bool:
    """Validate if API key exists and is active"""
    if DATABASE_TYPE == "mongodb":
        if client is not None:  # Using real MongoDB
            all_keys = db.api_keys.find({"status": "active"})
        else:  # Using mock database
            api_keys_collection = db('api_keys')
            all_keys = api_keys_collection.find({"status": "active"})

        for key_doc in all_keys:
            if pwd_context.verify(api_key, key_doc["key"]):
                # Update last used timestamp
                if client is not None:  # Using real MongoDB
                    db.api_keys.update_one(
                        {"_id": key_doc["_id"]},
                        {"$set": {"last_used_at": datetime.utcnow()}}
                    )
                else:  # Using mock database
                    api_keys_collection.update_one(
                        {"_id": key_doc["_id"]},
                        {"$set": {"last_used_at": datetime.utcnow()}}
                    )
                return True
        return False
    elif DATABASE_TYPE == "sqlite":
        # For SQLite, we need to verify the key directly
        try:
            conn = sqlite3.connect(sqlite_db.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT id FROM api_keys WHERE status = "active"')
            rows = cursor.fetchall()

            for row in rows:
                api_key_id = row[0]
                cursor.execute('SELECT key FROM api_keys WHERE id = ?', (api_key_id,))
                stored_key = cursor.fetchone()
                if stored_key and pwd_context.verify(api_key, stored_key[0]):
                    # Update last used timestamp
                    cursor.execute('''
                        UPDATE api_keys
                        SET last_used_at = ?
                        WHERE id = ?
                    ''', (datetime.utcnow().isoformat(), api_key_id))
                    conn.commit()
                    conn.close()
                    return True

            conn.close()
            return False
        except Exception as e:
            print(f"Error validating API key: {e}")
            return False


# API Key validation middleware
async def require_api_key(request: Request) -> UserInDB:
    """
    Middleware that requires a valid API key (either in header or query param)
    """
    # Check for API key in header
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        # Check in query parameter
        api_key = request.query_params.get("api_key")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "API-Key"},
        )

    user = get_user_by_api_key(api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "API-Key"},
        )

    return user

# Dependency function to get current user supporting both JWT and API key
async def get_current_user_or_api_key(request: Request) -> UserInDB:
    """
    Get current user supporting both JWT tokens and API keys
    """
    # First check for Authorization header (JWT token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            token_type = payload.get("type")
            if token_type != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            email = payload.get("sub")
            if email:
                user = get_user(email=email)
                if user:
                    return user
        except jwt.PyJWTError:
            pass  # Continue to check API key

    # If JWT authentication failed, check for API key
    # Check in header
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        # Check in query parameter
        api_key = request.query_params.get("api_key")

    if api_key:
        user = get_user_by_api_key(api_key)
        if user:
            return user

    # If neither JWT nor API key worked, raise exception
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )