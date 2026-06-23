from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv()

_client = None

def embedd_model_client():
    
    global _client 
    
    if _client is None:
        _client = genai.Client(
                    api_key = os.getenv("GEMINI_API_KEY")
                )
        
        return _client
    
    else:
        return _client
