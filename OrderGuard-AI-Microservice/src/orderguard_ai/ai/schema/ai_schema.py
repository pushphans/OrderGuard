from pydantic import BaseModel
from pydantic import Field


class AiChatRequestModel(BaseModel):
    message : str = Field(..., min_length=1, max_length=500)


class AiChatResponseModel(BaseModel):
    message : str
    steps : list[str]
