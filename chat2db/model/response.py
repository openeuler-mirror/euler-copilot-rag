from pydantic import BaseModel
class ResponseData(BaseModel):
    code: int
    message: str
    result: dict