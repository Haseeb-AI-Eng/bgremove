"""
Mock database module to simulate MongoDB operations for development
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
from bson import ObjectId
from threading import Lock

# Thread-safe in-memory storage
class MockDatabase:
    def __init__(self):
        self._lock = Lock()
        self._collections = {
            'users': {},
            'refresh_tokens': {},
            'api_keys': {}
        }
    
    def get_collection(self, name: str):
        """Get a collection by name"""
        with self._lock:
            if name not in self._collections:
                self._collections[name] = {}
            return MockCollection(self, name)


class MockCollection:
    def __init__(self, db: 'MockDatabase', name: str):
        self.db = db
        self.name = name
    
    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document matching the query"""
        with self.db._lock:
            for doc_id, doc in self.db._collections[self.name].items():
                if self._matches_query(doc, query):
                    return doc.copy()
        return None
    
    def find(self, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Find all documents matching the query"""
        with self.db._lock:
            results = []
            for doc_id, doc in self.db._collections[self.name].items():
                if query is None or self._matches_query(doc, query):
                    results.append(doc.copy())
            return results
    
    def insert_one(self, document: Dict[str, Any]):
        """Insert a single document"""
        with self.db._lock:
            doc_id = ObjectId()
            document['_id'] = doc_id
            self.db._collections[self.name][str(doc_id)] = document
            return MockInsertResult(doc_id)
    
    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> 'MockUpdateResult':
        """Update a single document"""
        with self.db._lock:
            for doc_id, doc in self.db._collections[self.name].items():
                if self._matches_query(doc, query):
                    # Apply updates
                    for op, values in update.items():
                        if op == '$set':
                            for key, value in values.items():
                                doc[key] = value
                        elif op == '$unset':
                            for key in values.keys():
                                if key in doc:
                                    del doc[key]
                    
                    return MockUpdateResult(1, 1)  # matched_count, modified_count
            return MockUpdateResult(0, 0)
    
    def delete_one(self, query: Dict[str, Any]) -> 'MockDeleteResult':
        """Delete a single document"""
        with self.db._lock:
            for doc_id, doc in list(self.db._collections[self.name].items()):
                if self._matches_query(doc, query):
                    del self.db._collections[self.name][doc_id]
                    return MockDeleteResult(1)
            return MockDeleteResult(0)
    
    def _matches_query(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """Check if a document matches the query"""
        for key, value in query.items():
            if key == '$and':
                for condition in value:
                    if not self._all_matches(doc, condition):
                        return False
                return True
            elif key == '$or':
                for condition in value:
                    if self._all_matches(doc, condition):
                        return True
                return False
            elif key == '$exists':
                return (key in doc) == value
            else:
                if key not in doc:
                    return False
                if isinstance(value, dict):
                    if '$gt' in value:
                        if doc[key] <= value['$gt']:
                            return False
                    elif '$lt' in value:
                        if doc[key] >= value['$lt']:
                            return False
                    elif '$gte' in value:
                        if doc[key] < value['$gte']:
                            return False
                    elif '$lte' in value:
                        if doc[key] > value['$lte']:
                            return False
                    elif '$ne' in value:
                        if doc[key] == value['$ne']:
                            return False
                    elif '$in' in value:
                        if doc[key] not in value['$in']:
                            return False
                    elif '$nin' in value:
                        if doc[key] in value['$nin']:
                            return False
                else:
                    if doc[key] != value:
                        return False
        return True
    
    def _all_matches(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """Helper to check if document matches a sub-query"""
        return self._matches_query(doc, query)


class MockInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class MockUpdateResult:
    def __init__(self, matched_count: int, modified_count: int):
        self.matched_count = matched_count
        self.modified_count = modified_count


class MockDeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


# Global instance
mock_db_instance = MockDatabase()


def get_mock_db():
    """Get the global mock database instance"""
    return mock_db_instance