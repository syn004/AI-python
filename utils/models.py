from pydantic import BaseModel
from typing import List, Optional
from config.model import config

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = config.ALI_CHAT_MODEL_NAME
    stream: Optional[bool] = False

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"

class AgentChatRequest(BaseModel):
        query: str