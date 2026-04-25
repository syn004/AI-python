from mcp.server.fastmcp import FastMCP

# 创建MCP服务器实例
mcp = FastMCP("McpServer")

@mcp.tool()
def add(a: int, b: int) -> int:
    """两数相加"""
    print(f"计算 {a} 加 {b}")
    return a + b


@mcp.tool()
def ride(a: int, b: int) -> int:
    """两数相乘"""
    print(f"计算 {a} 乘 {b}")
    return a * b


if __name__ == "__main__":
    # 运行服务器，使用 sse 协议
    mcp.run(transport='sse')