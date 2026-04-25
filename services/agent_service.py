import os
from fastapi import UploadFile, BackgroundTasks
from rag.vector_store import VectorStoreService
from agent.agent_main import agent_app
from utils.logger import log_info, log_error


class AgentService:
    def __init__(self):
        # 初始化基础设施层
        self.vector_store = VectorStoreService()
        self.data_dir = "data"

        # 确保数据目录存在
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    async def chat_with_agent(self, query: str) -> str:
        """
        调用 Agent 智能体进行对话 (支持 RAG、工具调用等)
        """
        return await agent_app.chat_async(query)

    def build_knowledge_base(self):
        """
        触发底层向量库服务进行增量构建
        """
        return self.vector_store.build_knowledge_base()

    async def upload_file(self, file: UploadFile, kb_type: str, background_tasks: BackgroundTasks) -> dict:
        """
        文件上传并触发构建，返回详细的结果信息
        """
        try:
            target_dir = os.path.join(self.data_dir)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            # 读取文件内容
            contents = await file.read()

            # 检查文件重复
            duplicate_result = self._check_file_duplicate(file.filename, contents, target_dir)
            if duplicate_result['is_duplicate']:
                return {
                    "success": False,
                    "error": duplicate_result['error_message']
                }

            # 保存文件到本地
            file_path = os.path.join(target_dir, file.filename)
            with open(file_path, "wb") as f:
                f.write(contents)
            log_info(f"📄 文件 {file.filename} 已保存至 {file_path}")

            background_tasks.add_task(self.build_knowledge_base)

            return {
                "success": True,
                "message": f"文件 {file.filename} 上传成功，后台正在为您构建知识库..."
            }
            # # 构建知识库
            # build_result = self.build_knowledge_base()
            # if not build_result:
            #     return {
            #         "success": False,
            #         "error": "知识库构建失败"
            #     }
            #
            # return {
            #     "success": True,
            #     "message": f"文件 {file.filename} 上传成功并已添加到知识库"
            # }
        except Exception as e:
            error_msg = f"上传失败: {str(e)}"
            log_error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

    def _check_file_duplicate(self, file_name: str, file_content: bytes, target_dir: str) -> dict:
        """
        检查文件是否重复
        返回包含重复状态和错误信息的字典
        """
        # 检查文件名重复
        file_path = os.path.join(target_dir, file_name)
        if os.path.exists(file_path):
            error_msg = f"文件名重复: {file_name} 已存在"
            log_error(f"❌ {error_msg}")
            return {
                "is_duplicate": True,
                "error_message": error_msg
            }

        # 计算文件内容哈希
        import hashlib
        content_hash = hashlib.md5(file_content).hexdigest()

        # 检查内容重复（遍历现有文件）
        for root, dirs, files in os.walk(target_dir):
            for existing_file in files:
                existing_path = os.path.join(root, existing_file)
                try:
                    with open(existing_path, 'rb') as f:
                        existing_content = f.read()
                        existing_hash = hashlib.md5(existing_content).hexdigest()
                        if existing_hash == content_hash:
                            error_msg = f"内容重复: {file_name} 与 {existing_file} 内容相同"
                            log_error(f"❌ {error_msg}")
                            return {
                                "is_duplicate": True,
                                "error_message": error_msg
                            }
                except Exception as e:
                    continue

        return {
            "is_duplicate": False,
            "error_message": None
        }

# 单例导出
agent_service = AgentService()