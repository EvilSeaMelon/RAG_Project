"""
知识向量库，主要功能：存放文档数据到知识向量库
"""
import hashlib
import os
from datetime import datetime
import config_data as config
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker

"""
3个md5功能函数
"""
def get_string_md5(input_str, encoding='utf-8'):
    """将传入的字符串转换为md5"""

    # 将input_str先转换为字节数组
    str_bytes = input_str.encode(encoding=encoding)

    # 创建md5对象
    md5_obj = hashlib.md5()  # 得到md5对象
    md5_obj.update(str_bytes)  # 更新内容（传入即将要转换的字节数组）
    md5 = md5_obj.hexdigest()  # 得到md5的十六进制字符串

    return md5

def check_md5(md5):
    """
    检查传入的md5是否已经被处理过了
    False(md5未处理过)  True(已经处理过，已有记录）
    """
    if not os.path.exists(config.md5_path):
        # if进入表示文件不存在，那肯定没有处理过这个md5了，创建md5.txt
        open(config.md5_path, 'w', encoding='utf-8').close()
        return False
    else:
        for line in open(config.md5_path, 'r', encoding='utf-8').readlines():
            line = line.strip()  # 处理字符串前后的空格和回车
            if line == md5:
                return True  # 已处理过

        return False

def save_md5(md5):
    """将传入的md5字符串，记录到文件内保存"""
    with open(config.md5_path, 'a', encoding="utf-8") as f:
        f.write(md5 + '\n')


# 存放数据文档数据到知识向量库
class KnowledgeBaseService(object):
    def __init__(self):
        # 如果文件夹不存在则创建，如果存在则跳过
        os.makedirs(config.persist_directory, exist_ok=True)

        # 把 Embedding 提取出来，供底层切分和 Chroma 库共同使用
        self.embeddings = DashScopeEmbeddings(model=config.embedding_model)

        self.chroma = Chroma(
            collection_name=config.collection_name,  # 当前向量存储起个名字，类似数据库的表名称
            embedding_function=self.embeddings,
            persist_directory=config.persist_directory  # 指定数据存放的文件夹
        )  # 向量存储的实例 Chroma向量库对象 (27)

        # SemanticChunker 语义切分器
        self.spliter = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type="percentile"  # 寻找相邻句子相似度的断崖进行切分
        )

        # self.spliter = RecursiveCharacterTextSplitter(
        #     chunk_size=config.chunk_size,       # 分割后的文本段最大长度
        #     chunk_overlap=config.chunk_overlap, # 连续文本段之间的字符重叠数量
        #     separators=config.separators,       # 自然段落划分的符号
        #     length_function=len,                # 使用Python自带的len函数做长度统计的依据
        # )     # 文本分割器的对象 (25)

    def upload_by_str(self,  data: str, filename):
        """将传入的字符串，进行向量化，存入向量数据库中"""
        # 1、先得到传入字符串的md5值,并判断是否重复
        md5 = get_string_md5(data)

        if check_md5(md5):
            return "[跳过]内容已经存在知识库中"

        # 判断是否分割,比max_split_char_number大才分割,不然直接外面包列表，格式相同好操作
        if len(data) > config.max_split_char_number:
            # 👇SemanticChunker 切出来也是 List[str]
            knowledge_chunks: list[str] = self.spliter.split_text(data)
            print(f"💡 语义切分完成：长文本被智能切分成了 {len(knowledge_chunks)} 个独立语义块！")
        else:
            knowledge_chunks = [data]

        # 2、内容加载到向量库
        # 元数据
        metadata = {
            "source": filename,
            "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "operator": "旋哥",
        }

        self.chroma.add_texts(
            knowledge_chunks,   # list \ tuple
            metadatas=[metadata for _ in knowledge_chunks],
        )

        # 3、
        save_md5(md5)

        return "[成功]内容已经成功载入向量库"


if __name__ == '__main__':
    service = KnowledgeBaseService()
    r = service.upload_by_str("吴其旋", "test")
    print(r)
