from typing import TypedDict

class AgentState(TypedDict):
    raw_user_prompt: str
    normalize_user_prompt: str
    extracted_keywords: list[str]
    target_q_count: int
    retrieve_chunk_count: int
    retrieve_chunk: list[dict]
    
