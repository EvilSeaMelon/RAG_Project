
from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory, RunnableLambda

import config_data as config
# 历史对话功能
from file_history_store import truncate_by_token
# 知识库功能
from vector_stores import VectorStoreService


def print_prompt(prompt):
    print("="*20)
    print(prompt.to_string())
    print("="*20)

    return prompt




class RagService(object):
    def __init__(self):

        # 模型
        self.chat_model = ChatTongyi(model=config.chat_model)

        # 检索向量服务类实例
        self.vector_service = VectorStoreService(
            DashScopeEmbeddings(model=config.embedding_model)
        )

        # ================== 新增：Query 重写，关键词提取链 ==================
        self.rewrite_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "你是一个电商售后知识库的检索专家。用户的客诉提问通常包含情绪发泄、口语化表达和冗余词汇。\n"
                           "请根据用户的原始提问，提取出最核心的【故障现象】和【部件名词】，并结合售后常识，适当补充一两个相关专业同义词（例如'漏雪种'可补充'漏氟','缺冷媒'）。\n"
                           "请去除所有无意义的停用词（如：怎么办、为什么、啊、昨天刚买的）。\n"
                           "【严格要求】：你必须仅返回一个合法的 JSON 对象，不要输出任何其他解释性文字。\n"
                           "JSON 格式如下：\n"
                           "{{\"search_query\": \"提取的关键词和同义词，用空格隔开\"}}"),
                ("user", "设备型号：{product_model}\n用户提问：{input}")
            ]
        )
        # query重写链：提示词 -> LLM -> JSON 解析
        self.rewrite_chain = self.rewrite_prompt | self.chat_model | JsonOutputParser()

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

        # 隐式地把“设备型号”拼接到用户的提问中去查向量库
        # ================== 新增query重写：在检索前重写Query ==================
        def format_for_retriever(value):
            original_issue = value.get("input", "")
            model = value.get("product_model", "")

            if not original_issue:
                return model

            try:
                # 1. 调用重写链，获取提取后的关键词
                rewrite_result = self.rewrite_chain.invoke({
                    "product_model": model,
                    "input": original_issue
                })

                # 2. 从 JSON 中提取字段
                search_keywords = rewrite_result.get("search_query", original_issue)

                print(f"\n[Query重写触发]")
                print(f"   原始提问: {original_issue}")
                print(f"   重写结果: {search_keywords}\n")

                # 3. 将设备型号与重写后的关键词拼接后返回
                return f"{model} {search_keywords}".strip()

            except Exception as e:
                # 如果 LLM 没有返回标准 JSON 或发生错误，退回原始查询方式
                print(f"Query重写失败，使用原query检索]: {e}")
                return f"{model} {original_issue}".strip()



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

        # conversation_chain = RunnableWithMessageHistory(
        #     chain,  # 被增强的原有chain
        #     get_history,  # 通过会话id获取FileChatMessageHistory类对象
        #     input_messages_key="input",  # 表示用户输入在模板中的占位符
        #     history_messages_key="history"  # 表示用户输入在模板中的占位符
        # )

        return chain

    # 热重载机制
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

