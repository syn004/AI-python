import functools
from utils.logger import log_info, log_req, log_error, log_success


def monitor_tool(tool):
    """
    工具执行监控中间件
    """

    if hasattr(tool, '_run'):
        original_run = tool._run

        @functools.wraps(original_run)
        def run_wrapper(*args, **kwargs):
            tool_name = tool.name
            # 记录调用的参数
            params = kwargs if kwargs else args
            log_req(f"🔍 [Middleware] 正在调用工具: {tool_name} | 参数: {params}")

            try:
                result = original_run(*args, **kwargs)

                # 截取一部分结果防止日志爆炸
                result_str = str(result)
                if len(result_str) > 100:
                    result_str = result_str[:100] + "..."

                log_success(f" [Middleware] 工具 {tool_name} 执行成功 | 结果: {result_str}")

                if tool_name == "fill_context_for_report":
                    log_info("📝 [Middleware] 检测到报告模式，已标记上下文")

                return result
            except Exception as e:
                log_error(f"[Middleware] 工具 {tool_name} 执行失败: {e}")
                raise e

        tool._run = run_wrapper


    if hasattr(tool, '_arun'):
        original_arun = tool._arun

        @functools.wraps(original_arun)
        async def arun_wrapper(*args, **kwargs):
            tool_name = tool.name
            params = kwargs if kwargs else args
            log_req(f"🔍 [Middleware Async] 正在调用工具: {tool_name} | 参数: {params}")

            try:
                result = await original_arun(*args, **kwargs)

                result_str = str(result)
                if len(result_str) > 100:
                    result_str = result_str[:100] + "..."

                log_success(f" [Middleware Async] 工具 {tool_name} 执行成功 | 结果: {result_str}")
                return result
            except Exception as e:
                log_error(f" [Middleware Async] 工具 {tool_name} 失败: {e}")
                raise e

        tool._arun = arun_wrapper

    return tool


def log_before_model(func):
    """
    模型调用前置拦截
    """
    return func