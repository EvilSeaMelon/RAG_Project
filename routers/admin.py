from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from database import get_db
from models import Customer, OrderAsset, WorkOrder
import schemas
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/api/admin", tags=["后台管理员控制台"])


# 1. 获取真实的数据看板 KPI
@router.get("/kpi", response_model=schemas.KPIData)
async def get_kpi_data(db: AsyncSession = Depends(get_db)):
    # 统计总客户数和总资产数
    total_customers = await db.scalar(select(func.count(Customer.id))) or 0
    total_assets = await db.scalar(select(func.count(OrderAsset.id))) or 0

    # 统计非“AI已解答”和非“已完结”的待办工单
    pending_orders = await db.scalar(
        select(func.count(WorkOrder.id))
        .where(WorkOrder.status.not_in(['AI已解答', '已完结']))
    ) or 0

    # 计算 AI 解决率
    total_orders = await db.scalar(select(func.count(WorkOrder.id))) or 0
    ai_resolved = await db.scalar(
        select(func.count(WorkOrder.id)).where(WorkOrder.status == 'AI已解答')
    ) or 0

    rate = "0%"
    if total_orders > 0:
        rate = f"{(ai_resolved / total_orders) * 100:.1f}%"

    return schemas.KPIData(
        total_customers=total_customers,
        total_assets=total_assets,
        pending_orders=pending_orders,
        ai_resolved_rate=rate
    )


# 2. 获取所有的真实工单列表
@router.get("/work-orders", response_model=list[schemas.WorkOrderResponse])
async def get_all_work_orders(db: AsyncSession = Depends(get_db)):
    # 按照工单ID倒序，最新的在前面
    stmt = select(WorkOrder).order_by(WorkOrder.id.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


# 3. 管理员修改工单状态
@router.put("/work-orders/{wo_id}")
async def update_work_order_status(wo_id: str, payload: schemas.WorkOrderUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(WorkOrder).where(WorkOrder.id == wo_id)
    wo = (await db.execute(stmt)).scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")

    wo.status = payload.status
    await db.commit()
    return {"msg": "状态更新成功"}


# ==========================================
# Customer 表 CRUD
# ==========================================

# 获取全量客户列表 (Read)
@router.get("/customers", response_model=list[schemas.CustomerResponse])
async def get_all_customers(db: AsyncSession = Depends(get_db)):
    stmt = select(Customer).order_by(Customer.id.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


# ==========================
# 2. 客户表 (Customer) CRUD
# ==========================
@router.get("/customers", response_model=list[schemas.CustomerResponse])
async def get_all_customers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).order_by(Customer.id.desc()))
    return result.scalars().all()

@router.put("/customers/{c_id}")
async def update_customer(c_id: int, payload: schemas.CustomerCreate, db: AsyncSession = Depends(get_db)):
    cust = (await db.execute(select(Customer).where(Customer.id == c_id))).scalar_one_or_none()
    if not cust: raise HTTPException(404, "客户不存在")
    cust.name, cust.phone = payload.name, payload.phone
    await db.commit()
    return {"msg": "ok"}

@router.delete("/customers/{c_id}")
async def delete_customer(c_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(delete(Customer).where(Customer.id == c_id))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "该客户名下有设备或工单，无法删除！")
    return {"msg": "ok"}

# ==========================
# 3. 设备资产 (OrderAsset) CRUD
# ==========================
@router.get("/assets", response_model=list[schemas.OrderAssetResponse])
async def get_all_assets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OrderAsset).order_by(OrderAsset.id.desc()))
    return result.scalars().all()

@router.put("/assets/{a_id}")
async def update_asset(a_id: int, payload: schemas.OrderAssetBase, db: AsyncSession = Depends(get_db)):
    asset = (await db.execute(select(OrderAsset).where(OrderAsset.id == a_id))).scalar_one_or_none()
    if not asset: raise HTTPException(404, "资产不存在")
    asset.product_category = payload.product_category
    asset.product_model = payload.product_model
    await db.commit()
    return {"msg": "ok"}

@router.delete("/assets/{a_id}")
async def delete_asset(a_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(delete(OrderAsset).where(OrderAsset.id == a_id))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "该设备有关联工单记录，无法删除！")
    return {"msg": "ok"}

# ==========================
# 4. 售后工单 (WorkOrder) CRUD
# ==========================
@router.get("/work-orders", response_model=list[schemas.WorkOrderResponse])
async def get_all_work_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkOrder).order_by(WorkOrder.id.desc()))
    return result.scalars().all()

@router.put("/work-orders/{wo_id}")
async def update_work_order(wo_id: str, payload: schemas.WorkOrderUpdate, db: AsyncSession = Depends(get_db)):
    wo = (await db.execute(select(WorkOrder).where(WorkOrder.id == wo_id))).scalar_one_or_none()
    if not wo: raise HTTPException(404, "工单不存在")
    wo.status = payload.status
    await db.commit()
    return {"msg": "ok"}

@router.delete("/work-orders/{wo_id}")
async def delete_work_order(wo_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(WorkOrder).where(WorkOrder.id == wo_id))
    await db.commit()
    return {"msg": "ok"}