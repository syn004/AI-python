import json
import asyncio
from typing import List
from langchain_core.tools import Tool
from mcp import ClientSession
from mcp.client.sse import sse_client
from utils.logger import log_info, log_error


class MCPToolAdapter:
    def __init__(self, sse_url: str):
        self.sse_url = sse_url
        self.session = None
        self._tools_ready = asyncio.Event()

    async def _keep_connection_alive(self):
        """后台常驻任务，保持 SSE 连接永不断开: mcp_server文件"""
        try:
            async with sse_client(url=self.sse_url) as streams:
                async with ClientSession(*streams) as session:
                    self.session = session
                    await session.initialize()
                    self._tools_ready.set()  # 标记连接成功
                    log_info("✅ MCP 服务器连接已就绪并保持常驻。")

                    # 挂起当前协程，让它永远不结束，从而保持连接不断
                    await asyncio.Future()
        except Exception as e:
            log_error(f"❌ MCP 连接断开或失败: {e}")

    async def connect_and_load_tools(self) -> List[Tool]:
        # 启动后台守护任务去连服务器
        asyncio.create_task(self._keep_connection_alive())

        # 最多等 5 秒
        try:
            await asyncio.wait_for(self._tools_ready.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            log_error("❌ MCP 服务器连接超时！")
            return []

        try:
            mcp_tools = await self.session.list_tools()
            log_info(f"发现 {len(mcp_tools.tools)} 个远程工具")

            langchain_tools = []
            for tool in mcp_tools.tools:
                # 把服务器传来的参数格式 (JSON Schema) 告诉大模型
                schema_str = json.dumps(tool.inputSchema, ensure_ascii=False)
                desc = f"{tool.description or tool.name}\n【重要要求】参数必须严格输出为 JSON 字典格式，Schema如下: {schema_str}"

                # 闭包生成执行函数
                def create_run_func(tool_name):
                    async def async_run(tool_input: str) -> str:
                        log_info(f"🌐 准备调用 MCP 工具: {tool_name}, 原始输入: {tool_input}")
                        try:
                            # 过滤大模型可能带有的多余反引号
                            clean_input = tool_input.strip()
                            if clean_input.startswith("`") and clean_input.endswith("`"):
                                clean_input = clean_input.strip("`")

                            # 强制解析为 JSON 字典
                            args = json.loads(clean_input)
                            if not isinstance(args, dict):
                                raise ValueError("解析结果不是字典")

                        except Exception:
                            # 让大模型看到错误后，自己反思并重试
                            error_msg = f"参数解析失败！你传入的是: '{tool_input}'。请严格按照 JSON 字典格式传入，例如: {{\"a\": 4, \"b\": 5}}"
                            log_error(error_msg)
                            return error_msg

                        log_info(f"🚀 正式发送请求到 MCP: {tool_name}, 参数: {args}")
                        result = await self.session.call_tool(tool_name, arguments=args)
                        return result.content[0].text

                    return async_run

                # 使用最基础的 Tool，接管全部参数处理
                lc_tool = Tool(
                    name=tool.name,
                    description=desc,
                    func=lambda x: "此工具仅支持异步环境执行",
                    coroutine=create_run_func(tool.name)
                )
                langchain_tools.append(lc_tool)

            return langchain_tools

        except Exception as e:
            log_error(f"❌ 获取 MCP 工具失败: {e}")
            return []