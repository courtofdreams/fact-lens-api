from pymongo import MongoClient

class MongoDBService: 
    def __init__(self, uri, db_name, collection_name, ):
        self.mongo_client = MongoClient(uri)
        self.db = self.mongo_client[db_name]
        self.collection_name = collection_name

    def get_note_by_id(self, note_id ):
        return self.db[self.collection_name].find_one({"id": note_id})
    
    def insert_note(self, note):
        return self.db[self.collection_name].insert_one(note)
    
    def insert_notes(self, notes):
        return self.db[self.collection_name].insert_many(notes)
    
    def reset_database(self):
        self.db[self.collection_name].drop()
        self.db.create_collection(self.collection_name)
    
    def get_mongo_client(self):
        return self.mongo_client    
    
    def search(self,statement: str) -> list:
        results = self.db[self.collection_name].find(
            {"$text": {"$search": statement}}, {"id": 0}
        ).limit(5)
        
        if results.count() == 0:
            return "No relevant facts found"
        

        return "\n".join([str(doc) for doc in results]) or "No relevant facts found"