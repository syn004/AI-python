import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from config.model import config
from utils.logger import log_success
from routers import chat_api, agent_api
from services.chat_service import websocket_endpoint
from agent.agent_main import agent_app
from utils.logger import log_info
import os

# 创建 FastAPI 应用
app = FastAPI(title="Python-Robot")

# 配置 CORS (允许跨域)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 HTTP 路由
app.include_router(chat_api.router)
app.include_router(agent_api.router)

# 注册 WebSocket 路由, 注意：/ 会让nginx服务器失去方向。
@app.websocket("/ws")
async def ws_handler(websocket: WebSocket):
    await websocket_endpoint(websocket)

# 健康站点
@app.get("/health")
async def health():
    return {"status": "ok", "message": "Python-Robot is running"}

# 在应用启动时，异步连接 MCP 服务器
@app.on_event("startup")
async def startup_event():
    log_info("🚀 正在启动服务，准备挂载外部 MCP 工具...")
    # 连接到MCP 服务器, 避免docker容器内部找 8000 端口
    mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse")
    await agent_app.async_init_mcp(sse_url=mcp_url)


if __name__ == "__main__":
    log_success(f"🚀🚀🚀 启动 Python 机器人服务，端口: {config.PORT}")
    # 启动服务器
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.PORT,
        reload=(config.ENV == "development") # 开发模式下开启热重载
    )