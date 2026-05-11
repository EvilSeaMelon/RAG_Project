import os

# 1. 动态获取当前 config_data.py 所在的绝对目录 (也就是你的 backend 目录)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. 将 md5.txt 和 chroma_db 拼接到当前目录下
md5_path = os.path.join(BASE_DIR, "md5.txt")
persist_directory = os.path.join(BASE_DIR, "chroma_db") #表文件存放路径


# Chroma
collection_name = "rag"           #表名


# spliter
chunk_size = 1000         # 分段的最大字符数
chunk_overlap = 100       # 分段之间允许重叠字符数
separators = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
max_split_char_number = 1000        #文本分割阈值


# vector_store
similarity_threshold = 1    # 检索返回匹配的文档数量
embedding_model = "text-embedding-v4"
chat_model = "qwen3-max"
session_config = {
        "configurable": {
            "session_id": "user_001",
        }
    }