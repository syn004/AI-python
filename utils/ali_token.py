import json
import time
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from config.model import config
from utils.logger import log_info, log_error

# 简单的内存缓存，避免频繁请求 Token
_token_cache = {
    "token": None,
    "expire_time": 0
}

def get_nls_token():
    """获取阿里云 NLS Token (带缓存)"""
    global _token_cache

    # 如果缓存有效（提前10秒刷新），直接返回
    if _token_cache["token"] and time.time() < _token_cache["expire_time"] - 10:
        return _token_cache["token"]

    try:
        # 初始化阿里云客户端
        client = AcsClient(
            config.ALI_ACCESS_KEY_ID,
            config.ALI_ACCESS_KEY_SECRET,
            "cn-shanghai"
        )

        request = CommonRequest()
        request.set_method('POST')
        request.set_domain('nls-meta.cn-shanghai.aliyuncs.com')
        request.set_version('2019-02-28')
        request.set_action_name('CreateToken')

        response = client.do_action_with_exception(request)
        response_json = json.loads(response)

        if 'Token' in response_json and 'Id' in response_json['Token']:
            token = response_json['Token']['Id']
            expire = response_json['Token']['ExpireTime']

            # 更新缓存
            _token_cache["token"] = token
            _token_cache["expire_time"] = expire

            log_info(f"NLS Token 刷新成功")
            return token
        else:
            raise Exception("Token响应格式异常")

    except Exception as e:
        log_error(f"获取 Token 失败: {e}")
        return None