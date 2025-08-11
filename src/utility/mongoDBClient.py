from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from typing import Any, Dict, List, Optional
from threading import Lock

# mongoDBClient.py
class MongoDBClient:
    # def __init__(self, uri: str, db_name: str):
    #     self.client: MongoClient = MongoClient(uri)
    #     self.db: Database = self.client[db_name]

    _instance = None
    _lock = Lock()

    def __new__(cls, uri, db_name):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MongoDBClient, cls).__new__(cls)
                    cls._instance.client = MongoClient(uri)
                    cls._instance.db = cls._instance.client[db_name]
        return cls._instance

    def get_collection(self, collection_name: str) -> Collection:
        return self.db[collection_name]

    # mongo.insert_one("users", {"name": "Alice", "email": "alice@example.com"})
    def insert_one(self, collection_name: str, data: Dict[str, Any]) -> str:
        collection = self.get_collection(collection_name)
        result = collection.insert_one(data)
        return str(result)

    def insert_many(self, collection_name: str, data: List[Dict[str, Any]]) -> List[str]:
        collection = self.get_collection(collection_name)
        result = collection.insert_many(data)
        return [str(id) for id in result.inserted_ids]

    def find_one(self, collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        collection = self.get_collection(collection_name)
        return collection.find_one(query)

    def find_many(self, collection_name: str, query: Dict[str, Any] = {}) -> List[Dict[str, Any]]:
        collection = self.get_collection(collection_name)
        return list(collection.find(query))

    def update_one(self, collection_name: str, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        collection = self.get_collection(collection_name)
        result = collection.update_one(query, {'$set': update})
        return result.modified_count

    def delete_one(self, collection_name: str, query: Dict[str, Any]) -> int:
        collection = self.get_collection(collection_name)
        result = collection.delete_one(query)
        return result.deleted_count

    def close(self):
        self.client.close()

