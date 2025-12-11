from fastapi import FastAPI
from fastapi import HTTPException
from KnowledgeGraphService import KnowledgeGraphService
from MongoDBService import MongoDBService
from FactCheckAgent import FactCheckAgent
import uvicorn
from settings import settings
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
"http://localhost:5173",  # Example allowed origin
]

app.add_middleware(
CORSMiddleware,
allow_origins=origins,
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)

databaseName = "community-note-mongo"
collectionName = "community"
mongodbUri = settings.MONGO_DB_URI
mongo_service = MongoDBService(mongodbUri, databaseName, collectionName)
model = "gpt-4-turbo"
temperature = 0
kg_service = KnowledgeGraphService(temperature,model)
agent = FactCheckAgent(kg_service=kg_service,mongo_service=mongo_service,temperature=temperature,model_name=model)

# Root endpoint (GET request)
@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

# Endpoint with a path parameter (GET request)
@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}

# Endpoint with a query parameter (GET request)
@app.get("/search")
def search_items(query: str = None):
    return {"query": query}


@app.get('/facts/{twitter_id}')
def get_facts(twitter_id: str):
    """
    API endpoint to retrieve facts for a given Twitter ID.
    """
    try:
        # Query the knowledge graph for facts related to the Twitter ID
        final_answer = agent.invoke(twitter_id)
        return final_answer
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=e.__str__(),
        )
        
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8050, reload=True, env_file=".env")      