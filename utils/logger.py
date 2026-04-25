import logging
import sys
import os
import json
import datetime
from fastapi import Request

# 创建 Logger
logger = logging.getLogger("Robot")
logger.setLevel(logging.INFO)

# 设置控制台输出格式
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    "%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# 定义日志目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "../logs")

# 如果目录不存在则创建
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)


def _get_log_file_path():
    """获取当日的日志文件路径 (yyyy-mm-dd.json)"""
    today = datetime.date.today().isoformat()
    return os.path.join(LOG_DIR, f"{today}.json")


def _append_to_file(entry: dict):
    """
    核心写入逻辑：读取旧日志 -> 追加新条目 -> 写入文件
    """
    file_path = _get_log_file_path()
    data = []

    # 读取现有日志
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
        except (json.JSONDecodeError, IOError):
            data = []

    if not isinstance(data, list):
        data = []

    # 追加新条目
    data.append(entry)

    # 写入文件
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error(f"日志写入文件失败: {e}")


def log_info(msg):
    logger.info(f"ℹ️ {msg}")


def log_success(msg):
    logger.info(f"✅ {msg}")


def log_req(msg):
    logger.info(f"📤 {msg}")


def log_error(msg):
    logger.error(f"❌ {msg}")


def write_log(log_type: str, req: Request, content: dict):
    """
    通用请求日志 (对应 log.js 的 writeLog)
    :param log_type: 日志类型 (如 'text_chat')
    :param req: FastAPI Request 对象
    :param content: 日志详情
    """
    try:
        user_agent = "unknown"
        ip = "unknown"

        # 兼容处理，防止 req 为 None
        if req:
            user_agent = req.headers.get("user-agent", "unknown")
            if req.client:
                ip = req.client.host

        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": log_type,
            "client": {
                "userAgent": user_agent,
                "ip": ip
            },
            "content": content
        }

        # 写入文件
        _append_to_file(entry)

    except Exception as e:
        logger.error(f"通用日志记录异常: {e}")


def write_voice_log(client_info: dict, content: dict):
    """
    语音对话专用日志
    :param client_info: 包含 userAgent 和 ip 的字典
    :param content: 包含 event, user_text, ai_response 等信息的字典
    """
    try:
        # 控制台简略输出
        user_text = content.get('user_speech_text', '')
        ai_text = content.get('ai_response', '')
        event = content.get('event', 'unknown')

        if user_text or ai_text:
            logger.info(f"📝 [LOG] Event:{event} | User:{user_text[:20]} | AI:{ai_text[:20]}...")

        # 文件详细记录
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": "realtime_voice_dialogue",
            "client": {
                "userAgent": client_info.get("userAgent", "unknown"),
                "ip": client_info.get("ip", "unknown")
            },
            "content": content
        }

        _append_to_file(entry)

    except Exception as e:
        logger.error(f"语音日志记录异常: {e}")