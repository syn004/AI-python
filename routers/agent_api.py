from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, BackgroundTasks
from services.agent_service import agent_service
from utils.logger import write_log, log_req
from utils.models import ChatRequest

router = APIRouter(prefix="/robot/agent")


@router.post("/chat")
async def agent_chat_endpoint(req: ChatRequest, request: Request):
    """
    智能体对话接口
    """
    try:
        # 校验消息
        if not req.messages or len(req.messages) == 0:
            raise Exception("消息列表不能为空")

        # 获取用户最后发送的一条内容
        query = req.messages[-1].content
        log_req(f"收到 Agent 请求: {query}")

        answer = await agent_service.chat_with_agent(query)

        # 记录日志
        # write_log("agent_chat", request, {
        #     "query": query,
        #     "answer": answer
        # })
        log_req(f"Agent 回复: {answer}")

        return {"code": 200, "data": {"content": answer, "role": "assistant"}}
    except Exception as e:
        return {"code": 500, "data": {"err_msg": str(e)}}


@router.post("/rebuild")
async def rebuild_knowledge_base():
    """触发知识库增量重建"""
    result = agent_service.build_knowledge_base()
    log_req(f"构建结果: {result}")

    # 统一返回格式
    return {"code": 200, "message": str(result)}


@router.post("/upload")
async def upload_file_endpoint(file: UploadFile = File(...), kb_type: str = Form("product"), background_tasks: BackgroundTasks = BackgroundTasks()):
    """上传文件"""
    try:
        log_req(f"收到文件: {file.filename}, 类型: {kb_type}")
        result = await agent_service.upload_file(file, kb_type, background_tasks)
        if result['success']:
            return {
                "code": 200,
                "message": result['message']
            }
        else:
            return {
                "code": 400,
                "message": result['error']
            }
    except Exception as e:
        return {"code": 500, "data": {"message": str(e)}}