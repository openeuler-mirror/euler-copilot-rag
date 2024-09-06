from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    topk_sql: int = 5
    topk_answer: int = 5
    use_llm_enhancements: bool=False