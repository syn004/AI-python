from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from model.factory import chat_model
from agent.tools.agent_tools import tool_list
from agent.middleware import monitor_tool
from utils.logger import log_info, log_error
from agent.tools.mcp_adapter import MCPToolAdapter


class AgentMain:
    def __init__(self):
        self.mcp_adapter = None
        self.llm = chat_model

        # 加载本地工具
        self.local_tools = [monitor_tool(t) for t in tool_list]
        # 初始状态下，总工具箱只包含本地工具
        self.tools = self.local_tools.copy()

        # 加载提示词
        system_prompt = """
                你是一个智能助手。尽可能回答以下问题。你可以使用以下工具：

                {tools}

                使用格式如下：

                Question: 你必须回答的输入问题
                Thought: 你应该总是思考该做什么
                Action: 必须是 [{tool_names}] 中的一个
                Action Input: 工具的输入参数 (⚠️ 如果有多个参数，必须严格使用 JSON 字典格式，如 {{"a": 1, "b": 2}})
                Observation: 工具执行的结果
                ... (Thought/Action/Action Input/Observation 可以重复 N 次)
                Thought: 我现在知道最终答案了
                Final Answer: 对原始输入问题的最终回答

                Begin!

                Question: {input}
                Thought:{agent_scratchpad}
                """
        self.prompt = ChatPromptTemplate.from_template(system_prompt)

        # 初始化 Agent 和 执行器
        self._build_agent_executor()

    def _build_agent_executor(self):
        """
        内部方法：根据当前的 tools 列表重新构建 Agent。
        分离出这个方法是为了后续可以动态热加载 MCP 工具。
        """
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)

        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5  # 防止死循环
        )

    async def async_init_mcp(self, sse_url: str = "http://localhost:8000/sse"):
        """
        异步挂载 MCP 外部工具
        """
        try:
            log_info(f"正在尝试连接 MCP 服务器: {sse_url}")
            self.mcp_adapter = MCPToolAdapter(sse_url)
            remote_tools = await self.mcp_adapter.connect_and_load_tools()

            if remote_tools:
                # 将远程工具应用本地中间件后，追加到总工具箱中
                self.tools.extend([monitor_tool(t) for t in remote_tools])

                # 工具列表更新后，必须重新构建 Agent
                self._build_agent_executor()
                log_info(f" 成功将 {len(remote_tools)} 个 MCP 远程工具挂载到 Agent！")
        except Exception as e:
            log_error(f" MCP 初始化失败，将仅使用本地工具: {e}")

    def chat(self, query: str):
        """同步执行"""
        try:
            log_info(f"Agent 收到请求: {query}")
            result = self.agent_executor.invoke({"input": query})
            return result["output"]
        except Exception as e:
            log_error(f"Agent 思考出错: {e}")
            return f"Agent 思考出错: {str(e)}"

    async def chat_async(self, query: str):
        """异步执行"""
        try:
            log_info(f"Agent (Async) 收到请求: {query}")
            result = await self.agent_executor.ainvoke({"input": query})
            return result["output"]
        except Exception as e:
            log_error(f"Agent 思考出错: {e}")
            return f"Agent 思考出错: {str(e)}"


# 单例导出
agent_app = AgentMain()