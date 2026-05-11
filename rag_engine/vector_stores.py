from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
import config_data as config

class VectorStoreService(object):
    def __init__(self, embedding):
        self.embedding = embedding

        # 1. 初始化原有的 Chroma 向量数据库
        self.vector_store = Chroma(
            collection_name=config.collection_name,
            embedding_function=self.embedding,
            persist_directory=config.persist_directory,
        )

        # 2. 构建 BM25 内存索引 (用于关键字精准匹配)
        self.bm25_retriever = self._build_bm25()

        # 3. 加载 BGE 重排模型 (终极法官)
        # 首次运行会自动从 HuggingFace 下载模型权重
        self.cross_encoder = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        # 设定重排后只保留最核心的 3 段内容给大模型
        self.compressor = CrossEncoderReranker(model=self.cross_encoder, top_n=3)

    def _build_bm25(self):
        """
        内部方法：从 Chroma 数据库中提取所有文本，构建 BM25 索引。
        """
        # 从本地 Chroma 库中把所有存进去的数据“掏出来”
        db_data = self.vector_store.get()
        texts = db_data['documents']
        metadatas = db_data['metadatas']

        # 防护机制：如果数据库是空的，给一个默认的空检索器防止报错
        if not texts:
            return BM25Retriever.from_texts(["empty"])

        # 使用提取出的文本建立 BM25 检索器，设置召回数量为 5
        retriever = BM25Retriever.from_texts(texts, metadatas=metadatas)
        retriever.k = 5
        return retriever

    def reload_bm25(self):
        """
        对外暴露的方法：当用户上传新文件后，调用此方法热更新 BM25 内存。
        """
        self.bm25_retriever = self._build_bm25()

    def get_retriever(self):
        """
        返回最终装配好的“混合检索+重排”超级检索器
        """
        # 1. 配置向量检索器 (召回 5 条)
        vector_retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})

        # 防护机制：如果是空库，直接返回普通向量检索器
        if self.vector_store._collection.count() == 0:
            return vector_retriever

        # 2. 组装混合检索器 (EnsembleRetriever)
        # 将 BM25 和 向量检索 各分配 50% 的权重
        ensemble_retriever = EnsembleRetriever(
            retrievers=[self.bm25_retriever, vector_retriever],
            weights=[0.5, 0.5]
        )

        # 3. 组装重排检索器 (ContextualCompressionRetriever)
        # 将混合检索器捞回来的结果，送入 compressor (重排法官) 进行压缩和筛选
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.compressor,
            base_retriever=ensemble_retriever
        )

        return compression_retriever