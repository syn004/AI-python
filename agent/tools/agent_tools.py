import requests
import json
import urllib3
from langchain_core.tools import tool
from rag.rag_service import rag_service
from utils.logger import log_info, log_error

# 屏蔽警告，以防万一内网有拦截(中国气象局内网内置拦截器)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GAODE_API_KEY = "83a4debc611c63ed9c357dc9d596a1d7" # 5000次/月


@tool
def rag_summarize(query: str) -> str:
    """查询本地知识库"""
    log_info(f"🛠️ 调用工具 [rag_summarize]: {query}")
    return rag_service.rag_summarize(query)


@tool
def get_weather(city: str) -> str:
    """
    获取指定中国城市的天气情况。
    """
    try:
        # 清洗大模型传入的 JSON
        if city.strip().startswith("{") and city.strip().endswith("}"):
            city_dict = json.loads(city)
            city = city_dict.get("city", city)
    except Exception:
        pass

    city = city.strip(" \"'")

    # 高德 IP 自动静默定位
    if city.lower() in ["", "auto", "这里", "当前位置", "本地", "不知道"]:
        log_info("用户未指明城市，正在触发高德 IP 自动定位...")
        try:
            ip_url = f"https://restapi.amap.com/v3/ip?key={GAODE_API_KEY}"
            ip_resp = requests.get(ip_url, timeout=5, verify=False).json()

            # 高德如果定位不到（比如你在某些极端内网环境），city 可能是空数组 []
            if str(ip_resp.get("status")) == "1" and isinstance(ip_resp.get("city"), str) and ip_resp.get("city"):
                city = ip_resp.get("city")
                log_info(f"自动定位成功，当前网络城市为：{city}")
            else:
                city = "北京市" # 防火墙阻断或内网时的终极兜底
                log_info("IP定位未获取到精确城市，降级使用兜底城市: 北京市")
        except Exception as e:
            log_error(f"高德IP定位异常: {e}")
            city = "北京市"

    clean_city = city.replace("市", "").replace("县", "").replace("区", "")
    log_info(f"正在通过 高德地图节点 查询 {clean_city} 的天气...")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        # 高德地理编码 API
        geo_url = f"https://restapi.amap.com/v3/geocode/geo?address={clean_city}&key={GAODE_API_KEY}"
        geo_resp = requests.get(geo_url, headers=headers, timeout=5, verify=False)
        geo_data = geo_resp.json()

        if str(geo_data.get("status")) != "1" or not geo_data.get("geocodes"):
            return f"高德地图未能找到 '{clean_city}' 的位置信息，请检查城市名称。"

        adcode = geo_data["geocodes"][0]["adcode"]
        formatted_address = geo_data["geocodes"][0]["formatted_address"]

        # 高德天气 API 获取实况数据
        weather_url = f"https://restapi.amap.com/v3/weather/weatherInfo?city={adcode}&key={GAODE_API_KEY}&extensions=base"
        weather_resp = requests.get(weather_url, headers=headers, timeout=5, verify=False)
        weather_data = weather_resp.json()

        if str(weather_data.get("status")) == "1" and weather_data.get("lives"):
            live = weather_data["lives"][0]

            weather_str = (
                f"📍 **{formatted_address}** 实时天气\n"
                f"🌤️ 天气：{live.get('weather', '未知')}\n"
                f"🌡️ 温度：{live.get('temperature', 'N/A')}℃\n"
                f"💨 风向风力：{live.get('winddirection', '未知')}风 {live.get('windpower', '0')}级\n"
                f"💧 湿度：{live.get('humidity', 'N/A')}%"
            )
            log_info(f"天气查询成功:\n{weather_str}")
            return weather_str
        else:
            return f"高德天气查询失败，返回信息：{weather_data.get('info')}"

    except Exception as e:
        log_error(f"高德天气接口异常: {e}")
        return f"网络或解析异常，无法获取天气: {str(e)}"


@tool
def fill_context_for_report(topic: str) -> str:
    """控制流工具"""
    return "报告模式已激活"


# 工具列表
tool_list = [rag_summarize, get_weather, fill_context_for_report]