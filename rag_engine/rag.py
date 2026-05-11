
from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory, RunnableLambda

import config_data as config
from file_history_store import get_history, truncate_by_token
from vector_stores import VectorStoreService
from knowledge_base import KnowledgeBaseService


def print_prompt(prompt):
    print("="*20)
    print(prompt.to_string())
    print("="*20)

    return prompt




class RagService(object):
    def __init__(self):

        # 检索向量服务类实例
        self.vector_service = VectorStoreService(
            DashScopeEmbeddings(model=config.embedding_model)
        )

        # 挂载知识库服务
        self.knowledge_base = KnowledgeBaseService()

        # 提示词模板实例
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", "你是电商售后智能专家。\n"
                           "【当前客户状态】姓名：{customer_name} | 故障设备：{product_model} | 保修状态：{warranty_status}\n\n"
                           "【系统指令】请严格基于以下产品参考资料回答问题：\n{context}\n\n"
                           "【纪律规则】：\n"
                           "1. 你可以运用常识对资料进行合理推断，但无法得出答案时请如实回答。\n"
                           "2. 如果设备处于【保外】，请务必在回答末尾客气地提示客户可能产生检测或维修费用。\n\n"
                           "以下是用户的历史对话记录："),
                MessagesPlaceholder("history"),
                ("user", "请回答提问：{input}")
            ]
        )

        # 模型
        self.chat_model = ChatTongyi(model=config.chat_model)

        # 将链条方法变成属性
        self.chain = self.__get_chain()

    def __get_chain(self):
        """获取最终执行链"""

        retriever = self.vector_service.get_retriever()

        # [document] -> str
        def retriever_format(docs):
            formatted = ""
            for doc in docs:
                formatted += f"文档片段：{doc.page_content}\n文档元数据：{doc.metadata}\n\n"

            return formatted

        # 加入历史对话增强后的chain只能传入dict，但是retriever需要str，所以加函数转换
        # 隐式地把“设备型号”拼接到用户的提问中去查向量库
        def format_for_retriever(value):
            issue = value.get("input", "")
            model = value.get("product_model", "")
            return f"{model} {issue}".strip()



        # chain本身传入人造字典，加强历史对话chain后输入又为dict，所以会变成input中包着{"input":...,"histore":...}
        def format_for_prompt(value):
            new_value = {}
            original_input = value["input"]
            new_value["input"] = original_input.get("input", "")
            new_value["customer_name"] = original_input.get("customer_name", "尊贵的客户")
            new_value["product_model"] = original_input.get("product_model", "未知设备")
            new_value["warranty_status"] = original_input.get("warranty_status", "未知状态")
            new_value["context"] = value["context"]
            # 触发 Token 滑动窗口，对拿到的全量历史进行动态截断 (预设 1500 Tokens)
            new_value["history"] = truncate_by_token(original_input["history"], max_tokens=1500)
            return new_value

        chain = (
                {"input": RunnablePassthrough(),
                 "context": RunnableLambda(format_for_retriever) | retriever | retriever_format}
                | RunnableLambda(format_for_prompt)
                | self.prompt_template
                | print_prompt
                | self.chat_model
                | StrOutputParser()
        )

        conversation_chain = RunnableWithMessageHistory(
            chain,  # 被增强的原有chain
            get_history,  # 通过会话id获取FileChatMessageHistory类对象
            input_messages_key="input",  # 表示用户输入在模板中的占位符
            history_messages_key="history"  # 表示用户输入在模板中的占位符
        )

        return chain

    #【本次新增的核心代码】：热重载机制
    def reload_memory(self):
        """
        热重载机制：当有新知识入库时被调用
        1. 刷新底层 BM25 内存索引
        2. 重新把新的检索器装配到大模型链条上
        """
        print("监测到新知识入库，正在热重载 BM25 内存索引和链条...")
        self.vector_service.reload_bm25()
        self.chain = self.__get_chain()
        print("热重载完成")

if __name__ == '__main__':

    # RunnableWithMessageHistory增强chain后必须传入dict格式
    r = RagService().chain.invoke({"input":"我身高160cm，体重50kg，白皮肤，怎么穿衣服"}, config.session_config)
    print(r)
