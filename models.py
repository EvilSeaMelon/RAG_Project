from datetime import datetime
from sqlalchemy import String, Text, DateTime, func, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    # 抽取公共的创建时间和更新时间
    create_time: Mapped[datetime] = mapped_column(DateTime, insert_default=func.now(), default=func.now,
                                                  comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(DateTime, insert_default=func.now(), default=func.now,
                                                  onupdate=func.now(), comment="修改时间")


# 1. 客户表 (Customer)
class Customer(Base):
    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="客户ID")
    name: Mapped[str] = mapped_column(String(50), comment="客户姓名")
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, comment="手机号(作为查询入口)")
    customer_level: Mapped[str] = mapped_column(String(20), default="普通", comment="客户等级(普通/VIP)")


# 2. 客户订单/设备台账表 (OrderAsset)
# 记录用户买了什么，后续 RAG 精准检索说明书的依据
class OrderAsset(Base):
    __tablename__ = "order_asset"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="订单/资产ID")
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), comment="关联客户")
    product_category: Mapped[str] = mapped_column(String(50), comment="商品品类")
    product_model: Mapped[str] = mapped_column(String(100), comment="商品具体型号(如: 华为Mate60 Pro / 海尔XQG100)")
    purchase_date: Mapped[datetime] = mapped_column(DateTime, comment="购买日期")
    warranty_status: Mapped[str] = mapped_column(String(20), default="保内", comment="保修状态(保内/保外)")


# 3. 售后工单表 (WorkOrder)
# 记录用户的客诉问题和 RAG 客服给出的诊断结果
class WorkOrder(Base):
    __tablename__ = "work_order"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, comment="工单编号(如: WO-20260509-001)")
    asset_id: Mapped[int] = mapped_column(ForeignKey("order_asset.id"), comment="关联出故障的商品订单")
    issue_description: Mapped[str] = mapped_column(Text, comment="客户描述的故障现象")
    ai_diagnosis: Mapped[str] = mapped_column(Text, nullable=True, comment="RAG系统给出的智能诊断结果")
    status: Mapped[str] = mapped_column(String(20), default="待处理",comment="工单状态(待处理/AI已解答/人工介入/已完结)")


# 历史对话记录表
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="记录ID")
    session_id: Mapped[str] = mapped_column(String(50), index=True, comment="会话ID(这里直接用手机号)")
    role: Mapped[str] = mapped_column(String(20), comment="角色 (user 或 ai)")
    content: Mapped[str] = mapped_column(Text, comment="消息内容")