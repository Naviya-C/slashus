from typing import TypedDict, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from config.qdrant_client import get_qdrant_client


class AgentState(TypedDict):
    raw_user_prompt: str
    normalize_user_prompt: str
    extracted_keywords: List[str]
    target_q_count: int
    retrieve_chunk_count: int
    retrieve_chunk: List[dict]
    
class ParsedQuerySchema(BaseModel):
    """
    This function extracts below 3 things from the user prompt.
    
    Purpose:
        - Convert English, Singlish --> Sinhala Unicord.
        - Extract keywords from the user prompt
        - extract question count user need.
    """
    
    normalized_user_prompt: str = Field(
                                        description = "The input converted or transliterated completely into native Sinhala script."
                                        )
    extractedt_keywords: dict = Field(
                                        description = "The data from textbooks and other educational pdfs, therefore extract chapter, titles, page numbers, source name as a dict format."
                                        )
    target_q_count: int = Field(
                                "The integer N representing how many questions to generate."
                                )
    
    
def prompt_parsing_node(state: AgentState) -> Dict[str, Any]:
    
    systemInstruction = """
        You are an advanced Sri Lankan NLP agent. Process the user prompt:
        1. If input is Singlish (e.g., 'prashna 5k danna'), transliterate to native Sinhala ('ප්‍රශ්න 5ක් දෙන්න').
        2. If input is English, translate it to native Sinhala.
        3. The data from textbooks and other educational pdfs, therefore extract chapter, titles, page numbers, source names from user prompt."
        4. Detect 'N'—the number of questions requested. Default to 5 if unspecified.
    """
    
    llm = ChatGoogleGenerativeAI(
        model = "gemini-2.5-flash",
        temperature = 0.2,
        max_tokens = None,
        timeout = 300,
        max_retries = 3,
        system_instruction = systemInstruction
    )
        
    structured_llm = llm.with_structured_output(ParsedQuerySchema)
    
    userInput = state['raw_user_prompt']
    
    outputParse = structured_llm.invoke(userInput)
    
    return {
        "normalized_user_prompt": outputParse.normalized_user_prompt,
        "extractedt_keywords": outputParse.extractedt_keywords,
        "target_q_count": outputParse.target_q_count
    }
    
     
def qdrant_retrieval_node(state: dict) -> Dict[str, Any]:
    client = get_qdrant_client()
    n_questions = state["target_q_count"]
    final_limit = n_questions * 3
    prefetch_limit = final_limit * 4          # fusion needs depth to work with
    keywords = state.get("extracted_keywords") or []

    dense_vector = dense_encoder.encode(state["normalized_query"])
    sparse_vector = sparse_encoder.encode(state["normalized_query"])  # same vocab as index time

    prefetch = [
        models.Prefetch(query=dense_vector, using="text-dense", limit=prefetch_limit),
        models.Prefetch(query=sparse_vector, using="text-sparse", limit=prefetch_limit),
    ]

    if keywords:
        prefetch.append(
            models.Prefetch(
                query=sparse_vector,
                using="text-sparse",
                filter=models.Filter(
                    should=[
                        models.FieldCondition(key="text", match=models.MatchText(text=kw))
                        for kw in keywords
                    ]
                ),
                limit=prefetch_limit,
            )
        )

    try:
        response = client.query_points(
            collection_name="sinhala_pdf_chunks",
            prefetch=prefetch,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=final_limit,
            with_payload=True,
        )
    except Exception as e:
        logger.exception("qdrant hybrid search failed")
        return {"retrieved_chunks": [], "retrieval_error": str(e)}

    return {
        "retrieved_chunks": [
            {"id": p.id, "text": p.payload.get("text", ""), "rrf_score": p.score}
            for p in response.points
        ],
        "retrieval_error": None,
    }
    
    