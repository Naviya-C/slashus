from langchain_core.prompts import ChatPromptTemplate

RAG_PROMPT = ChatPromptTemplate.from_template(
"""
You are a helpful Sinhala educational assistant.

Answer ONLY using the provided context.

If the answer cannot be found in the context, say:

"මා ලබාගත් දත්ත තුළ මෙම ප්‍රශ්නයට පිළිතුරක් නොමැත."

Context:
{context}

Question:
{question}

Answer:
"""
)