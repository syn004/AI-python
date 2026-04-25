import os
import hashlib
import time
from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    TextLoader, DirectoryLoader, PyPDFLoader,
    UnstructuredWordDocumentLoader, UnstructuredPowerPointLoader
)
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_text_splitters import RecursiveCharacterTextSplitter
from model.factory import embed_model
from utils.logger import log_info, log_error, log_success


class VectorStoreService:
    def __init__(self):
        self.chroma_store_path = "./chroma_db"
        self.data_dir = "data"
        self.embeddings = embed_model
        self.vector_store = self._init_vector_store()

        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _init_vector_store(self):
        try:
            db = Chroma(
                persist_directory=self.chroma_store_path,
                embedding_function=self.embeddings
            )
            log_success(f"Chroma向量数据库加载成功: {self.chroma_store_path}")
            return db
        except Exception as e:
            log_error(f"Chroma初始化失败: {e}")
            return None

    def get_retriever(self, k=4):
        if not self.vector_store:
            raise Exception("向量库未初始化")
        return self.vector_store.as_retriever(search_kwargs={"k": k})

    def _calculate_file_hash(self, file_path: str):
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    def _get_db_state(self):
        if not self.vector_store:
            return set(), set()
        try:
            data = self.vector_store.get(include=['metadatas'])
            existing_hashes = set()
            existing_paths = set()
            for meta in data.get("metadatas", []):
                if meta:
                    if "file_hash" in meta: existing_hashes.add(meta["file_hash"])
                    if "source" in meta: existing_paths.add(os.path.abspath(meta["source"]))
            return existing_paths, existing_hashes
        except Exception as e:
            log_error(f"获取数据库状态失败: {e}")
            return set(), set()

    def build_knowledge_base(self):
        """增量构建核心逻辑"""
        try:
            log_info("🔄 开始增量构建...")
            existing_paths, existing_hashes = self._get_db_state()

            all_docs = []
            loaders = [
                ("**/*.txt", TextLoader, {"autodetect_encoding": True}),
                ("**/*.md", TextLoader, {"autodetect_encoding": True}),
                ("**/*.pdf", PyPDFLoader, {}),
                ("**/*.docx", UnstructuredWordDocumentLoader, {}),
                ("**/*.pptx", UnstructuredPowerPointLoader, {"mode": "elements"}),
            ]

            for pattern, loader_cls, kwargs in loaders:
                try:
                    loader = DirectoryLoader(self.data_dir, glob=pattern, loader_cls=loader_cls, loader_kwargs=kwargs,
                                             show_progress=False)
                    docs = loader.load()
                    all_docs.extend(docs)
                except Exception as e:
                    log_error(f"加载 {pattern} 失败: {e}")

            if not all_docs:
                log_error("目录下无文件")
                return "没有发现新内容"

            new_docs = []
            for doc in all_docs:
                source = doc.metadata.get("source", "")
                abs_path = os.path.abspath(source)
                file_hash = self._calculate_file_hash(abs_path)

                # 双重去重策略
                if abs_path in existing_paths: continue
                if file_hash and file_hash in existing_hashes: continue

                doc.metadata["file_hash"] = file_hash
                new_docs.append(doc)

            if not new_docs:
                log_success("没有发现新内容")
                return "没有发现新内容"

            # 切分与入库
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = splitter.split_documents(new_docs)
            splits = filter_complex_metadata(splits)

            batch_size = 10
            total = len(splits)
            log_info(f" 准备写入 {total} 个新片段...")

            for i in range(0, total, batch_size):
                batch = splits[i:i + batch_size]
                self.vector_store.add_documents(batch)
                log_info(f"---- 进度: {min(i + batch_size, total)}/{total}")
                time.sleep(0.5)

            log_success("增量构建完成")
            return True
        except Exception as e:
            log_error(f"构建失败: {e}")
            return False