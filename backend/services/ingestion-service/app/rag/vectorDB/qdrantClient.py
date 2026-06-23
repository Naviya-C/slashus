from qdrant_client import QdrantClient
import os
from dotenv import load_dotenv

load_dotenv()

_client = None

def qdrant_client():
     
    global _client 
    
    if _client is None:
        _client = QdrantClient(
            url = os.getenv("QDRANT_CLUSTER_ENDPOINT"),
            api_key = os.getenv("QDRANT_CLUSTER_API"),
            timeout = 120
        )

        return _client
    
    else:
        return _client
