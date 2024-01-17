from typing import List

from pydantic import BaseModel


class EsTermInfo(BaseModel):
    general_text: str
    general_text_vector: List[float]
    source: str
    uri: str
    mtime: str
    extended_metadata: str
