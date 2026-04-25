from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from model.factory import chat_model
from rag.vector_store import VectorStoreService


class RagSummarizeService:
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.llm = chat_model

    def rag_summarize(self, query: str) -> str:
        """
        检索生成流程
        """
        try:
            retriever = self.vector_store.get_retriever(k=4)

            # 定义 RAG 提示词
            template = """你是智能业务助手。请基于以下【参考资料】回答用户问题。
            如果资料不足，请说明不知道，不要编造。

            【参考资料】：
            {context}

            用户问题: {question}
            """
            prompt = ChatPromptTemplate.from_template(template)

            def format_docs(docs):
                return "\n\n".join(doc.page_content for doc in docs)

            rag_chain = (
                    {"context": retriever | format_docs, "question": RunnablePassthrough()}
                    | prompt
                    | self.llm
                    | StrOutputParser()
            )

            # 执行链
            return rag_chain.invoke(query)

        except Exception as e:
            return f"检索服务暂时不可用: {str(e)}"


rag_service = RagSummarizeService()