from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from config.model import config
import os

# 设置 DashScope API Key
os.environ["DASHSCOPE_API_KEY"] = config.ALI_API_KEY

class ChatModelFactory:
    def generator(self):
        return ChatTongyi(model_name=config.ALI_CHAT_MODEL_NAME, temperature=0.1)

class EmbeddingsFactory:
    def generator(self):
        return DashScopeEmbeddings(model=config.ALI_TEXT_VECTOR_MODEL_NAME)

# 单例模式导出
chat_model = ChatModelFactory().generator()
embed_model = EmbeddingsFactory().generator()