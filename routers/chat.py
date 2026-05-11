import sys
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Customer, OrderAsset, WorkOrder, ChatHistory
import schemas

# 导入底层 RAG 引擎
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rag_engine'))
try:
    from rag_engine.rag import RagService
    rag_service = RagService()
    print("RAG 引擎装载完毕！")
except ImportError as e:
    print(f"RAG 引擎导入失败: {e}")
    rag_service = None

router = APIRouter(prefix="/api/chat", tags=["RAG"])


@router.post("/", response_model=schemas.ChatResponse)
async def handle_rag_chat(request: schemas.ChatRequest, db: AsyncSession = Depends(get_db)):
    if rag_service is None:
        raise HTTPException(status_code=500, detail="RAG 引擎未启动。")

    # 1. 查数据库：获取身份与设备信息
    customer = (await db.execute(select(Customer).where(Customer.phone == request.phone))).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="查无此人，请先注册。")

    asset = (await db.execute(select(OrderAsset).where(OrderAsset.customer_id == customer.id).order_by(
        OrderAsset.purchase_date.desc()))).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="该客户名下无设备。")

    # ==========================================
    # 🌟 2. 从 MySQL 拉取历史聊天记录并转化格式
    # ==========================================
    history_stmt = select(ChatHistory).where(ChatHistory.session_id == request.phone).order_by(ChatHistory.id.asc())
    history_records = (await db.execute(history_stmt)).scalars().all()

    langchain_history = []
    for record in history_records:
        if record.role == "user":
            langchain_history.append(HumanMessage(content=record.content))
        else:
            langchain_history.append(AIMessage(content=record.content))

    # 3. 将历史记录与其他参数一起组装给大模型
    rag_payload = {
        "input": request.issue,
        "customer_name": customer.name,
        "product_model": asset.product_model,
        "warranty_status": asset.warranty_status,
        "history": langchain_history  # 历史记录正式注入
    }

    # 4. 调用 RAG 处理链 (因为剥离了本地存储，不需要传 session_config 了)
    try:
        real_ai_reply = await run_in_threadpool(rag_service.chain.invoke, rag_payload)
    except Exception as e:
        print(f"RAG 引擎崩溃: {e}")
        raise HTTPException(status_code=500, detail=f"AI 推理异常: {e}")

    # ==========================================
    # 🌟 5. 持久化数据：把本轮对话存入 MySQL
    # ==========================================
    new_user_msg = ChatHistory(session_id=request.phone, role="user", content=request.issue)
    new_ai_msg = ChatHistory(session_id=request.phone, role="ai", content=real_ai_reply)
    db.add(new_user_msg)
    db.add(new_ai_msg)

    # 6. 生成售后工单
    wo_id = f"WO-{uuid.uuid4().hex[:8].upper()}"
    new_wo = WorkOrder(id=wo_id, asset_id=asset.id, issue_description=request.issue, ai_diagnosis=real_ai_reply,
                       status="AI已解答")
    db.add(new_wo)

    await db.commit()  # 一并提交对话和工单，保证事务一致性

    return schemas.ChatResponse(work_order_id=wo_id, asset_info=asset.product_model, ai_reply=real_ai_reply)

@router.post("/knowledge/upload")
async def upload_knowledge(doc: schemas.DocumentUpload):
    if rag_service is None:
        raise HTTPException(status_code=500, detail="RAG 引擎未启动。")
    try:
        upload_msg = await run_in_threadpool(rag_service.knowledge_base.upload_by_str, data=doc.text_data, filename=doc.filename)
        if "跳过" not in upload_msg:
            await run_in_threadpool(rag_service.reload_memory)
        return {"msg": upload_msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档解析失败: {str(e)}")