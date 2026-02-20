"""
Vector Database Service using ChromaDB for user storage and duplicate prevention
"""

import os
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    logger.warning("ChromaDB not installed. Falling back to file-based vector storage.")
    CHROMADB_AVAILABLE = False


class VectorDBService:
    """Service for storing and querying user data in a vector database"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the vector database
        
        Args:
            db_path: Path to store the vector database (for persistent storage)
        """
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "vector_db")
        self.collection_name = "users"
        self.client = None
        self.collection = None
        self._initialized = False
        
        # Initialize ChromaDB if available
        if CHROMADB_AVAILABLE:
            self._initialize_chromadb()
        else:
            self._initialize_file_based_db()
    
    def _initialize_chromadb(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Use persistent storage
            self.client = chromadb.PersistentClient(path=self.db_path)
            
            # Get or create collection
            # Using cosine similarity for email/user matching
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            self._initialized = True
            logger.info("ChromaDB initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self._initialize_file_based_db()
    
    def _initialize_file_based_db(self):
        """Initialize a simple file-based vector storage as fallback"""
        import json
        
        self.db_file = os.path.join(self.db_path, "users_vector.json")
        os.makedirs(self.db_path, exist_ok=True)
        
        # Load existing data or initialize empty
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r') as f:
                    self.file_db = json.load(f)
            except:
                self.file_db = {"users": []}
        else:
            self.file_db = {"users": []}
            self._save_file_db()
        
        self._initialized = True
        logger.info("File-based vector DB initialized")
    
    def _save_file_db(self):
        """Save file-based database to disk"""
        import json
        try:
            with open(self.db_file, 'w') as f:
                json.dump(self.file_db, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save file DB: {e}")
    
    def _create_user_embedding(self, email: str, user_data: Dict[str, Any]) -> List[float]:
        """
        Create a simple embedding for user data
        In production, you might want to use a more sophisticated embedding model
        
        Args:
            email: User's email
            user_data: Additional user data
            
        Returns:
            List of floats representing the embedding vector
        """
        # Create a hash-based embedding (simple but effective for exact matching)
        # In production with ChromaDB, you could use sentence transformers or similar
        combined = f"{email}:{user_data.get('first_name', '')}:{user_data.get('last_name', '')}"
        hash_bytes = hashlib.sha256(combined.encode()).digest()
        
        # Convert to a 256-dimensional vector (one byte per dimension, normalized)
        embedding = [b / 255.0 for b in hash_bytes]
        
        return embedding
    
    def add_user(self, user_id: str, email: str, user_data: Dict[str, Any]) -> bool:
        """
        Add a user to the vector database
        
        Args:
            user_id: Unique user ID
            email: User's email
            user_data: Additional user data (first_name, last_name, etc.)
            
        Returns:
            bool: True if user was added successfully
        """
        if not self._initialized:
            logger.error("Vector DB not initialized")
            return False
        
        try:
            # Create embedding
            embedding = self._create_user_embedding(email, user_data)
            
            # Prepare metadata
            metadata = {
                "user_id": user_id,
                "email": email,
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "created_at": datetime.utcnow().isoformat(),
                "is_active": "true"
            }
            
            if CHROMADB_AVAILABLE and self.collection:
                # Add to ChromaDB
                self.collection.add(
                    ids=[user_id],
                    embeddings=[embedding],
                    metadatas=[metadata]
                )
            else:
                # Add to file-based DB
                self.file_db["users"].append({
                    "id": user_id,
                    "email": email,
                    "metadata": metadata,
                    "embedding": embedding
                })
                self._save_file_db()
            
            logger.info(f"User {user_id} added to vector DB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add user to vector DB: {e}")
            return False
    
    def check_user_exists(self, email: str) -> bool:
        """
        Check if a user with the given email already exists
        
        Args:
            email: Email to check
            
        Returns:
            bool: True if user exists, False otherwise
        """
        if not self._initialized:
            logger.error("Vector DB not initialized")
            return False
        
        try:
            if CHROMADB_AVAILABLE and self.collection:
                # Create embedding for the email
                embedding = self._create_user_embedding(email, {})
                
                # Query for similar emails
                results = self.collection.query(
                    query_embeddings=[embedding],
                    n_results=1,
                    where={"email": email}
                )
                
                # If we got results, user exists
                return len(results.get("ids", [[]])[0]) > 0
            else:
                # Check file-based DB
                for user in self.file_db["users"]:
                    if user["email"] == email and user["metadata"].get("is_active") == "true":
                        return True
                return False
                
        except Exception as e:
            logger.error(f"Failed to check user existence: {e}")
            return False
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user data by ID
        
        Args:
            user_id: User's unique ID
            
        Returns:
            Dict with user data or None if not found
        """
        if not self._initialized:
            return None
        
        try:
            if CHROMADB_AVAILABLE and self.collection:
                results = self.collection.get(ids=[user_id])
                
                if results and results.get("metadatas"):
                    return results["metadatas"][0]
            else:
                for user in self.file_db["users"]:
                    if user["id"] == user_id:
                        return user["metadata"]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
    
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update user data
        
        Args:
            user_id: User's unique ID
            update_data: Data to update
            
        Returns:
            bool: True if update was successful
        """
        if not self._initialized:
            return False
        
        try:
            if CHROMADB_AVAILABLE and self.collection:
                # Get existing metadata
                existing = self.get_user_by_id(user_id)
                if not existing:
                    return False
                
                # Update metadata
                updated_metadata = {**existing, **update_data}
                
                # ChromaDB doesn't support direct metadata update, so we need to delete and re-add
                self.collection.delete(ids=[user_id])
                
                # Create new embedding with updated data
                embedding = self._create_user_embedding(
                    updated_metadata["email"],
                    updated_metadata
                )
                
                self.collection.add(
                    ids=[user_id],
                    embeddings=[embedding],
                    metadatas=[updated_metadata]
                )
            else:
                # Update file-based DB
                for i, user in enumerate(self.file_db["users"]):
                    if user["id"] == user_id:
                        self.file_db["users"][i]["metadata"].update(update_data)
                        self._save_file_db()
                        return True
                return False
            
            logger.info(f"User {user_id} updated in vector DB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            return False
    
    def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate a user (soft delete)
        
        Args:
            user_id: User's unique ID
            
        Returns:
            bool: True if deactivation was successful
        """
        return self.update_user(user_id, {"is_active": "false"})
    
    def get_all_users_count(self) -> int:
        """Get total number of users"""
        if not self._initialized:
            return 0
        
        try:
            if CHROMADB_AVAILABLE and self.collection:
                return self.collection.count()
            else:
                return len(self.file_db["users"])
        except:
            return 0


# Global vector DB instance
vector_db = VectorDBService()
