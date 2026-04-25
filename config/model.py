import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class Config:
    # 基础配置
    PORT = int(os.getenv("PORT", 3000))
    ENV = os.getenv("NODE_ENV", "development")

    # 阿里配置
    ALI_API_KEY = os.getenv("ALI_API_KEY")
    ALI_APP_KEY = os.getenv("ALI_APP_KEY")
    ALI_ACCESS_KEY_ID = os.getenv("ALI_ACCESS_KEY_ID")
    ALI_ACCESS_KEY_SECRET = os.getenv("ALI_ACCESS_KEY_SECRET")
    ALI_CHAT_MODEL_NAME=os.getenv("ALI_CHAT_MODEL_NAME")
    ALI_ASR_MODEL_NAME=os.getenv("ALI_ASR_MODEL_NAME")
    ALI_TEXT_VECTOR_MODEL_NAME=os.getenv("ALI_TEXT_VECTOR_MODEL_NAME")

    # API 地址
    ALI_API = {
        "CHECK_TOKEN": "https://nls-meta.cn-shanghai.aliyuncs.com/auth/v1/token",
        "CHART_API": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        "WSS": "wss://dashscope.aliyuncs.com/api-ws/v1/inference/",
        "TTS_URL": "https://nls-gateway.cn-shanghai.aliyuncs.com/stream/v1/tts",
    }

config = Config()