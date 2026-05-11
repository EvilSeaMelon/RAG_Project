import json
import os
from typing import Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, message_to_dict
import tiktoken


# --- 新增：Token 触发式动态滑动窗口截断工具 ---
def truncate_by_token(messages: Sequence[BaseMessage], max_tokens: int = 1500) -> list[BaseMessage]:
    """按 Token 阈值倒序截断历史记录，确保近期上下文优先"""
    if not messages:
        return []

    try:
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    selected_messages = []
    current_tokens = 0

    for msg in reversed(messages):
        text_content = str(msg.content) if msg.content else ""
        msg_tokens = len(encoding.encode(text_content))

        if current_tokens + msg_tokens > max_tokens:
            break

        selected_messages.append(msg)
        current_tokens += msg_tokens

    selected_messages.reverse()  # 恢复正常语序
    return selected_messages


# # ---------------------------------------------------
#
# class FileChatMessageHistory(BaseChatMessageHistory):
#     def __init__(self, session_id, storage_path):
#         self.session_id = session_id        # 会话id
#         self.storage_path = storage_path    # 不同会话id的存储文件，所在的文件夹路径
#         # 完整的文件路径
#         self.file_path = os.path.join(self.storage_path, self.session_id)
#
#         # 确保文件夹是存在的
#         os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
#
#
#     # 读取文件，将[dict]转换为[BaseMessage]输出
#     @property       # @property装饰器将messages方法变成成员属性用
#     def messages(self) -> list[BaseMessage]:
#         # 当前文件内： list[字典]
#         try:
#             with open(self.file_path, "r", encoding="utf-8") as f:
#                 messages_data = json.load(f)                # 返回值是list[dict,dict,...]
#                 return messages_from_dict(messages_data)    # 返回值是list[BaseMessage,BaseMessage,...]
#         except FileNotFoundError:
#             return []
#
#     # 加入新消息
#     def add_messages(self, messages_new: Sequence[BaseMessage]) -> None:
#         # Sequence序列 类似list、tuple
#         all_messages = list(self.messages)      # 已有的消息列表
#         all_messages.extend(messages_new)           # 新的和已有的融合成一个list
#
#         # 将数据同步写入到本地文件中
#         # 类对象写入文件 -> 一堆二进制
#         # 为了方便，可以将BaseMessage消息转为字典（借助json模块以json字符串写入文件）
#         # 官方message_to_dict：单个消息对象（BaseMessage类实例） -> 字典
#
#         # new_messages = []
#         # for message in all_messages:
#         #     d = message_to_dict(message)
#         #     new_messages.append(d)
#
#         new_messages = [message_to_dict(message) for message in all_messages]
#         # 将数据写入文件
#         with open(self.file_path, "w", encoding="utf-8") as f:
#             json.dump(new_messages, f)
#
#
#     def clear(self) -> None:
#         with open(self.file_path, "w", encoding="utf-8") as f:
#             json.dump([], f)
#
#
# def get_history(session_id):
#     # 1. 动态获取当前 file_history_store.py 所在的绝对目录 (也就是 backend 目录)
#     BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#
#     # 2. 拼接出绝对路径： /你的项目路径/backend/chat_history
#     history_path = os.path.join(BASE_DIR, "chat_history")
#
#     return FileChatMessageHistory(session_id, history_path)