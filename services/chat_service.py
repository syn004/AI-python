import json
import asyncio
import httpx
import websockets
import time
from fastapi import WebSocket, WebSocketDisconnect
from config.model import config
from utils.logger import log_info, log_req, log_error, write_voice_log
from utils.ali_token import get_nls_token
from agent.agent_main import agent_app



async def chat_with_model(messages: list, model: str = config.ALI_CHAT_MODEL_NAME):
    """
    纯 LLM 对话 (用于 chat_api 的简单闲聊，不走 Agent)
    """
    log_req(f"调用模型: {model}, 消息数: {len(messages)}")
    headers = {"Authorization": f"Bearer {config.ALI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "input": {"messages": messages}, "parameters": {"result_format": "message"}}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(config.ALI_API["CHART_API"], json=payload, headers=headers, timeout=30.0)
            return resp.json()
        except Exception as e:
            log_error(f"LLM 请求失败: {e}")
            raise e
# 声音记忆，聊天记忆，面容记忆，会员手机号，员工     科大讯飞语音兼容

async def synthesize_speech(text: str):
    """TTS 语音合成"""
    log_req(f"请求 TTS 合成: {text[:10]}...")
    token = get_nls_token()
    if not token: return None
    payload = {
        "appkey": config.ALI_APP_KEY, "token": token, "text": text,
        "voice": "xiaobei", "format": "mp3", "sample_rate": 16000, "volume": 80
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(config.ALI_API["TTS_URL"], json=payload,
                                     headers={"Content-Type": "application/json"})
            if resp.status_code == 200 and resp.headers.get("content-type") == "audio/mpeg":
                return resp.content
            return None
        except Exception as e:
            log_error(f"TTS 异常: {e}")
            return None


async def handle_auto_chat(query: str, ws: WebSocket, client_info: dict, history: list):
    """
    语音对话处理主流程
    """
    try:
        log_info(f"🎤 语音提问: {query}")

        # 机器人现在可以查知识库、查天气、写报告了
        assistant_text = await agent_app.chat_async(query)

        # 记录语音日志
        write_voice_log(client_info, {
            "event": "conversation",
            "user_speech_text": query,
            "ai_response": assistant_text
        })

        # 发送文字回复
        await ws.send_text(json.dumps({"type": "ai_text", "text": assistant_text}))

        # 合成语音并发送
        audio_data = await synthesize_speech(assistant_text)
        if audio_data:
            await ws.send_bytes(audio_data)

    except Exception as e:
        log_error(f"自动对话流程异常: {e}")
        error_msg = "系统繁忙，请稍后再试。"
        await ws.send_text(json.dumps({"type": "ai_text", "text": error_msg}))


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 主入口"""
    await websocket.accept()

    client_info = {
        "ip": websocket.client.host,
        "userAgent": websocket.headers.get("user-agent", "unknown")
    }
    log_info(f"WebSocket连接: {client_info['ip']}")

    ali_ws = None
    current_task_id = ""
    session_text = ""
    last_intermediate_text = ""
    is_wake_word_mode = False
    current_history = []

    async def listen_to_ali_asr():
        nonlocal session_text, last_intermediate_text
        try:
            async for message in ali_ws:
                msg = json.loads(message)
                event = msg.get("header", {}).get("event")

                if event == "result-generated":
                    sentence = msg.get("payload", {}).get("output", {}).get("sentence", {})
                    text = sentence.get("text", "")
                    is_final = sentence.get("is_final", False)
                    last_intermediate_text = text

                    if is_wake_word_mode:
                        if "小仁" in text:
                            log_info("检测到唤醒词！")
                            await websocket.send_text(json.dumps({"type": "wake_success"}))
                            wake_text = "我在，请说"

                            write_voice_log(client_info, {"event": "wake_word_detected", "trigger_word": text,
                                                          "ai_response": wake_text})

                            audio = await synthesize_speech(wake_text)
                            if audio:
                                await websocket.send_bytes(audio)

                            await websocket.send_text(
                                json.dumps({"type": "ai_text", "text": wake_text, "isWakeUp": True}))
                            await ali_ws.close()
                            return
                    else:
                        await websocket.send_text(json.dumps({"type": "asr_text", "text": text, "isFinal": is_final}))
                        if is_final:
                            session_text += text
                            last_intermediate_text = ""

                elif event == "task-finished":
                    if is_wake_word_mode: return
                    final_text = session_text or last_intermediate_text
                    if final_text.strip():
                        await websocket.send_text(json.dumps({"type": "user_text", "text": final_text}))
                        # 调用 Agent 对话
                        await handle_auto_chat(final_text, websocket, client_info, current_history)
                    else:
                        await websocket.send_text(json.dumps({"type": "no_voice"}))
                    await ali_ws.close()
                    return

        except Exception as e:
            log_error(f"阿里 ASR 监听异常: {e}")

    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                if ali_ws:
                    await ali_ws.send(message["bytes"])
            elif "text" in message and message["text"]:
                try:
                    cmd = json.loads(message["text"])
                    if cmd.get("type") == "start_asr":
                        session_text = ""
                        last_intermediate_text = ""
                        current_task_id = cmd.get("taskId", str(int(time.time())))
                        is_wake_word_mode = (cmd.get("mode") == "wake_word")
                        current_history = cmd.get("history", [])

                        ali_ws = await websockets.connect(config.ALI_API["WSS"], additional_headers={
                            "Authorization": f"bearer {config.ALI_API_KEY}"})

                        start_payload = {
                            "header": {"action": "run-task", "task_id": current_task_id, "streaming": "duplex"},
                            "payload": {"task_group": "audio", "task": "asr", "function": "recognition",
                                        "model": config.ALI_ASR_MODEL_NAME,
                                        "parameters": {"sample_rate": 16000, "format": "pcm"}, "input": {}}
                        }
                        await ali_ws.send(json.dumps(start_payload))
                        asyncio.create_task(listen_to_ali_asr())

                    elif cmd.get("type") == "stop_asr":
                        if ali_ws:
                            await ali_ws.send(json.dumps(
                                {"header": {"action": "finish-task", "task_id": current_task_id, "streaming": "duplex"},
                                 "payload": {"input": {}}}))
                        else:
                            if not is_wake_word_mode: await websocket.send_text(json.dumps({"type": "no_voice"}))
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        log_info("前端断开连接")
        if ali_ws: await ali_ws.close()
    except Exception as e:
        log_error(f"WebSocket 主流程错误: {e}")