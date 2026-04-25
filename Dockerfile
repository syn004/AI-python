# 使用官方 Python 3.11 镜像
FROM python:3.11.8-slim

# 安装系统级依赖（针对 RAG、PDF 解析和 unstructured 库极其重要）
RUN apt-get update && apt-get install -y \
    libmagic-dev \
    poppler-utils \
    tesseract-ocr \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_VERSION=0.9.28 sh
ENV PATH="/root/.local/bin:${PATH}"

# 设置工作目录
WORKDIR /app

# 复制依赖定义文件
COPY pyproject.toml uv.lock ./

# 使用 uv 安装系统级依赖 (不创建虚拟环境，直接安装到容器系统 Python 中)
RUN uv sync --no-dev

# 复制项目所有代码
COPY . .