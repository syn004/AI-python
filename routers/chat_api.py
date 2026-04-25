from fastapi import APIRouter, HTTPException, Request
from services.chat_service import chat_with_model, synthesize_speech
from fastapi.responses import Response
from utils.logger import write_log, log_req, log_error
from utils.models import ChatRequest, TTSRequest

router = APIRouter(prefix="/robot/ali")

@router.post("/chat")
async def chat_endpoint(req: ChatRequest, request: Request):
    """
    简单文本对话接口 (不走 Agent，纯 LLM)
    """
    try:
        # 转换为 dict
        msgs = [m.model_dump() for m in req.messages]

        result = await chat_with_model(msgs, req.model)

        # 简化返回结构
        simplified_data = {
            "content": "",
            "role": "assistant"
        }

        if "output" in result and "choices" in result["output"]:
            choice = result["output"]["choices"][0]
            if "message" in choice:
                simplified_data["content"] = choice["message"].get("content", "")
                simplified_data["role"] = choice["message"].get("role", "assistant")

        # 提取 Token 信息
        usage = result.get("usage", {})
        tokens = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }

        # 获取用户最后一条消息
        last_user_message = msgs[-1] if len(msgs) > 0 else None
        user_query = last_user_message["content"] if last_user_message else "unknown"

        # 写入日志
        # write_log("text_chat", request, {
        #     "user_query": user_query,
        #     "ai_response": simplified_data["content"],
        #     "tokens": tokens
        # })

        return {"code": 200, "data": simplified_data}

    except Exception as e:
        log_error(f"Chat API Error: {e}")
        return {"code": 500, "data": {"err_msg": str(e)}}


@router.post("/voice/tts")
async def tts_endpoint(req: TTSRequest, request: Request):
    """
    文本转语音接口
    """
    try:
        log_req(f"收到 TTS 请求: {req.text[:20]}...")

        audio_content = await synthesize_speech(req.text)
        if not audio_content:
            raise HTTPException(status_code=500, detail="合成失败")

        # # 写入日志
        # write_log("voice_tts_only", request, {
        #     "text_to_speech": req.text
        # })

        return Response(content=audio_content, media_type="audio/wav")

    except Exception as e:
        log_error(f"TTS API Error: {e}")
        return {"code": 500, "data": {"err_msg": str(e)}}