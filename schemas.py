
"""数据校验层"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date
from typing import List, Optional


# ==========================
# 1. 客户相关 Schemas
# ==========================
class CustomerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="客户姓名")
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="11位手机号")


class CustomerCreate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    id: int
    customer_level: str
    create_time: datetime

    model_config = ConfigDict(from_attributes=True)  # 允许从 SQLAlchemy 模型解析


# ==========================
# 2. 订单资产相关 Schemas
# ==========================
class OrderAssetBase(BaseModel):
    product_category: str = Field(..., description="品类，如：家电、3C")
    product_model: str = Field(..., description="具体型号，如：美的空调KFR-35")


class OrderAssetCreate(OrderAssetBase):
    phone: str = Field(..., description="通过手机号绑定客户订单")
    purchase_date: date = Field(..., description="购买日期")


class OrderAssetResponse(OrderAssetBase):
    id: int
    warranty_status: str

    model_config = ConfigDict(from_attributes=True)


# ==========================
# 3. 联合查询响应 Schema
# ==========================
class CustomerDetailResponse(BaseModel):
    customer: CustomerResponse
    assets: List[OrderAssetResponse]


# ==========================
# 4. RAG 智能问答 Schemas
# ==========================
class ChatRequest(BaseModel):
    phone: str = Field(..., description="客户手机号(提取上下文必备)")
    issue: str = Field(..., min_length=2, description="故障描述")


class ChatResponse(BaseModel):
    work_order_id: str = Field(..., description="工单号")
    asset_info: str = Field(..., description="隐式提取的设备信息")
    ai_reply: str = Field(..., description="AI生成的解决方案")


# ==========================
# 5. 后台管理与数据看板 Schemas
# ==========================
class KPIData(BaseModel):
    total_customers: int
    total_assets: int
    pending_orders: int
    ai_resolved_rate: str


class WorkOrderResponse(BaseModel):
    id: str
    asset_id: int
    issue_description: str
    ai_diagnosis: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class WorkOrderUpdate(BaseModel):
    status: str

# ==========================
# 6. RAG 知识库管理 Schemas
# ==========================
class DocumentUpload(BaseModel):
    text_data: str = Field(..., description="文本文件的具体内容")
    filename: str = Field(..., description="文件名，如: 华为Mate60说明书.txt")