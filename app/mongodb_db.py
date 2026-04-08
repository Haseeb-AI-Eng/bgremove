import motor.motor_asyncio
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid
import os

class MongoDB:
    def __init__(self, connection_url: str = "mongodb://localhost:27017/", db_name: str = "bgremove_db"):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(connection_url)
        self.db = self.client[db_name]
        self.users = self.db["users"]
        self.refresh_tokens = self.db["refresh_tokens"]
        self.api_keys = self.db["api_keys"]
        self.email_verification_tokens = self.db["email_verification_tokens"]

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        return await self.users.find_one({"id": user_id})

    async def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        user = await self.users.find_one({"email": email})
        if user:
            # Convert _id to id if necessary, or just use the stored id
            return user
        return None

    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user = await self.users.find_one({"email": user_data["email"]})
            if existing_user:
                return None
            
            # Set default values if not present
            user_data.setdefault("created_at", datetime.now(timezone.utc))
            user_data.setdefault("is_active", True)
            user_data.setdefault("is_verified", False)
            user_data.setdefault("is_pro", False)
            
            await self.users.insert_one(user_data)
            return user_data
        except Exception as e:
            print(f"Error creating user in MongoDB: {e}")
            raise e

    async def update_user_subscription(self, email: str, is_pro: bool, subscription_end: Optional[datetime]) -> bool:
        """Update user subscription status"""
        result = await self.users.update_one(
            {"email": email},
            {"$set": {"is_pro": is_pro, "subscription_end": subscription_end}}
        )
        return result.modified_count > 0

    async def update_user_profile(self, email: str, first_name: Optional[str] = None, last_name: Optional[str] = None, bio: Optional[str] = None) -> bool:
        """Update user profile information"""
        updates = {}
        if first_name is not None: updates["first_name"] = first_name
        if last_name is not None: updates["last_name"] = last_name
        if bio is not None: updates["bio"] = bio
        
        if not updates:
            return False
            
        result = await self.users.update_one({"email": email}, {"$set": updates})
        return result.modified_count > 0

    async def update_user_profile_image(self, email: str, profile_image_url: str) -> bool:
        """Update user profile image"""
        result = await self.users.update_one(
            {"email": email},
            {"$set": {"profile_image": profile_image_url}}
        )
        return result.modified_count > 0

    async def store_refresh_token(self, user_id: str, token: str, expires_at: datetime):
        """Store a refresh token"""
        await self.refresh_tokens.insert_one({
            "user_id": user_id,
            "token": token,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
            "is_active": True
        })

    async def is_refresh_token_valid(self, token: str) -> bool:
        """Check if refresh token is valid and not expired"""
        token_doc = await self.refresh_tokens.find_one({
            "token": token,
            "is_active": True,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        return token_doc is not None

    async def invalidate_refresh_token(self, token: str) -> bool:
        """Invalidate a refresh token"""
        result = await self.refresh_tokens.update_one(
            {"token": token},
            {"$set": {"is_active": False}}
        )
        return result.modified_count > 0

    async def store_verification_token(self, user_id: str, token: str, expires_at: datetime):
        """Save an email verification token"""
        await self.email_verification_tokens.insert_one({
            "user_id": user_id,
            "token": token,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
            "is_active": True
        })

    async def verify_email_token(self, token: str) -> bool:
        """Consume a verification token and activate the associated user."""
        token_doc = await self.email_verification_tokens.find_one({
            "token": token,
            "is_active": True,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        
        if not token_doc:
            return False
            
        user_id = token_doc["user_id"]
        
        # Mark token inactive and user verified/active
        await self.email_verification_tokens.update_one({"token": token}, {"$set": {"is_active": False}})
        await self.users.update_one({"id": user_id}, {"$set": {"is_verified": True, "is_active": True}})
        
        return True

    async def create_api_key(self, api_key_data: Dict[str, Any]):
        """Create a new API key"""
        # Ensure permissions is a list
        if "permissions" in api_key_data and isinstance(api_key_data["permissions"], str):
            api_key_data["permissions"] = json.loads(api_key_data["permissions"])
            
        api_key_data["created_at"] = datetime.now(timezone.utc)
        api_key_data["status"] = "active"
        
        await self.api_keys.insert_one(api_key_data)
        return api_key_data["id"]

    async def get_api_keys_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all API keys for a user"""
        cursor = self.api_keys.find({"user_id": user_id, "status": "active"})
        return await cursor.to_list(length=100)

    async def get_api_key_by_id(self, api_key_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific API key by ID for a user"""
        return await self.api_keys.find_one({"id": api_key_id, "user_id": user_id, "status": "active"})

    async def revoke_api_key(self, api_key_id: str, user_id: str) -> bool:
        """Revoke an API key"""
        result = await self.api_keys.update_one(
            {"id": api_key_id, "user_id": user_id, "status": "active"},
            {"$set": {"status": "revoked", "revoked_at": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    async def delete_api_key(self, api_key_id: str, user_id: str) -> bool:
        """Delete an API key permanently"""
        result = await self.api_keys.delete_one({"id": api_key_id, "user_id": user_id})
        return result.deleted_count > 0

    async def get_user_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get user by API key"""
        key_doc = await self.api_keys.find_one({"key": api_key, "status": "active"})
        if key_doc:
            user_id = key_doc["user_id"]
            
            # Update last used timestamp
            await self.api_keys.update_one(
                {"key": api_key},
                {"$set": {"last_used_at": datetime.now(timezone.utc)}}
            )
            
            # Get the user
            return await self.users.find_one({"id": user_id})
        return None

# Global instance for initialization
_mongodb_instance: Optional[MongoDB] = None

def get_mongodb_db(connection_url: str = "mongodb://localhost:27017/", db_name: str = "bgremove_db"):
    global _mongodb_instance
    if _mongodb_instance is None:
        _mongodb_instance = MongoDB(connection_url, db_name)
    return _mongodb_instance
