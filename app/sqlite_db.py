import sqlite3
import json
from datetime import datetime
from typing import Optional
import hashlib
import os

class SQLiteDB:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database and create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                is_pro INTEGER DEFAULT 0,
                subscription_end TEXT,
                first_name TEXT,
                last_name TEXT,
                bio TEXT,
                profile_image TEXT
            )
        ''')
        
        # Create refresh_tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create api_keys table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                key TEXT NOT NULL UNIQUE,  -- This will be the hashed key
                key_prefix TEXT NOT NULL,
                name TEXT DEFAULT 'Default API Key',
                status TEXT DEFAULT 'active',
                permissions TEXT DEFAULT '["read", "write"]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used_at TEXT,
                expires_at TEXT,
                revoked_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_user(self, email: str):
        """Get user by email"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        
        if row:
            user_dict = {
                'id': row[0],
                'email': row[1],
                'hashed_password': row[2],
                'created_at': datetime.fromisoformat(row[3]) if isinstance(row[3], str) else row[3],
                'is_active': bool(row[4]),
                'is_pro': bool(row[5]),
                'subscription_end': datetime.fromisoformat(row[6]) if row[6] else None,
                'first_name': row[7],
                'last_name': row[8],
                'bio': row[9],
                'profile_image': row[10]
            }
            conn.close()
            return user_dict
        
        conn.close()
        return None
    
    def create_user(self, user_data: dict):
        """Create a new user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if user already exists
            cursor.execute('SELECT email FROM users WHERE email = ?', (user_data['email'],))
            if cursor.fetchone():
                conn.close()
                return None
            
            # Insert new user
            cursor.execute('''
                INSERT INTO users (
                    id, email, hashed_password, first_name, last_name
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                user_data['id'],
                user_data['email'],
                user_data['hashed_password'],
                user_data.get('first_name'),
                user_data.get('last_name')
            ))
            
            conn.commit()
            conn.close()
            return user_data
        except Exception as e:
            conn.close()
            raise e
    
    def update_user_subscription(self, email: str, is_pro: bool, subscription_end: datetime):
        """Update user subscription status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET is_pro = ?, subscription_end = ?
            WHERE email = ?
        ''', (int(is_pro), subscription_end.isoformat() if subscription_end else None, email))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    def update_user_profile(self, email: str, first_name: str = None, last_name: str = None, bio: str = None):
        """Update user profile information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if first_name is not None:
            updates.append("first_name = ?")
            params.append(first_name)
        if last_name is not None:
            updates.append("last_name = ?")
            params.append(last_name)
        if bio is not None:
            updates.append("bio = ?")
            params.append(bio)
        
        if updates:
            query = f"UPDATE users SET {', '.join(updates)} WHERE email = ?"
            params.append(email)
            
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
        return cursor.rowcount > 0
    
    def update_user_profile_image(self, email: str, profile_image_url: str):
        """Update user profile image"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET profile_image = ?
            WHERE email = ?
        ''', (profile_image_url, email))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    def store_refresh_token(self, user_id: str, refresh_token: str, expires_at: datetime):
        """Store a refresh token"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO refresh_tokens (user_id, token, expires_at)
            VALUES (?, ?, ?)
        ''', (user_id, refresh_token, expires_at.isoformat()))
        
        conn.commit()
        conn.close()
        return cursor.lastrowid
    
    def is_refresh_token_valid(self, refresh_token: str) -> bool:
        """Check if refresh token is valid and not expired"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 1 FROM refresh_tokens 
            WHERE token = ? AND is_active = 1 AND expires_at > ?
        ''', (refresh_token, datetime.utcnow().isoformat()))
        
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def invalidate_refresh_token(self, refresh_token: str):
        """Invalidate a refresh token"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE refresh_tokens 
            SET is_active = 0 
            WHERE token = ?
        ''', (refresh_token,))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    def create_api_key(self, api_key_data: dict):
        """Create a new API key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO api_keys (
                id, user_id, key, key_prefix, name, permissions
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            api_key_data['id'],
            api_key_data['user_id'],
            api_key_data['key'],  # This is the hashed key
            api_key_data['key_prefix'],
            api_key_data['name'],
            json.dumps(api_key_data['permissions'])
        ))
        
        conn.commit()
        conn.close()
        return api_key_data['id']
    
    def get_api_keys_for_user(self, user_id: str):
        """Get all API keys for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM api_keys WHERE user_id = ? AND status = 'active'
        ''', (user_id,))
        
        rows = cursor.fetchall()
        api_keys = []
        
        for row in rows:
            api_key = {
                'id': row[0],
                'user_id': row[1],
                'key': row[2],  # This is the hashed key
                'key_prefix': row[3],
                'name': row[4],
                'status': row[5],
                'permissions': json.loads(row[6]),
                'created_at': datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
                'last_used_at': datetime.fromisoformat(row[8]) if row[8] else None,
                'expires_at': datetime.fromisoformat(row[9]) if row[9] else None,
                'revoked_at': datetime.fromisoformat(row[10]) if row[10] else None
            }
            api_keys.append(api_key)
        
        conn.close()
        return api_keys
    
    def get_api_key_by_id(self, api_key_id: str, user_id: str):
        """Get a specific API key by ID for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM api_keys 
            WHERE id = ? AND user_id = ? AND status = 'active'
        ''', (api_key_id, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'key': row[2],
                'key_prefix': row[3],
                'name': row[4],
                'status': row[5],
                'permissions': json.loads(row[6]),
                'created_at': datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
                'last_used_at': datetime.fromisoformat(row[8]) if row[8] else None,
                'expires_at': datetime.fromisoformat(row[9]) if row[9] else None,
                'revoked_at': datetime.fromisoformat(row[10]) if row[10] else None
            }
        
        return None
    
    def revoke_api_key(self, api_key_id: str, user_id: str) -> bool:
        """Revoke an API key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE api_keys 
            SET status = 'revoked', revoked_at = ?
            WHERE id = ? AND user_id = ? AND status = 'active'
        ''', (datetime.utcnow().isoformat(), api_key_id, user_id))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    def delete_api_key(self, api_key_id: str, user_id: str) -> bool:
        """Delete an API key permanently"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM api_keys 
            WHERE id = ? AND user_id = ? AND status = 'active'
        ''', (api_key_id, user_id))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    def get_user_by_api_key(self, api_key: str):
        """Get user by API key"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First, find the API key record
        cursor.execute('''
            SELECT user_id FROM api_keys 
            WHERE key = ? AND status = 'active'
        ''', (api_key,))
        
        row = cursor.fetchone()
        if row:
            user_id = row[0]
            
            # Update last used timestamp
            cursor.execute('''
                UPDATE api_keys 
                SET last_used_at = ? 
                WHERE key = ?
            ''', (datetime.utcnow().isoformat(), api_key))
            
            # Get the user
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user_row = cursor.fetchone()
            
            if user_row:
                user_dict = {
                    'id': user_row[0],
                    'email': user_row[1],
                    'hashed_password': user_row[2],
                    'created_at': datetime.fromisoformat(user_row[3]) if isinstance(user_row[3], str) else user_row[3],
                    'is_active': bool(user_row[4]),
                    'is_pro': bool(user_row[5]),
                    'subscription_end': datetime.fromisoformat(user_row[6]) if user_row[6] else None,
                    'first_name': user_row[7],
                    'last_name': user_row[8],
                    'bio': user_row[9],
                    'profile_image': user_row[10]
                }
                
                conn.commit()
                conn.close()
                return user_dict
        
        conn.commit()
        conn.close()
        return None

# Create a global instance
sqlite_db = SQLiteDB()

def get_sqlite_db():
    """Get the SQLite database instance"""
    return sqlite_db