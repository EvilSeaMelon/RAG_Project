from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Customer, OrderAsset
import schemas

router = APIRouter(prefix="/api/orders", tags=["资产订单管理"])


@router.post("/", response_model=schemas.OrderAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order_in: schemas.OrderAssetCreate, db: AsyncSession = Depends(get_db)):
    # 查客户是否存在
    stmt = select(Customer).where(Customer.phone == order_in.phone)
    customer = (await db.execute(stmt)).scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=404, detail="未找到对应的客户，请先注册。")

    new_asset = OrderAsset(
        customer_id=customer.id,
        product_category=order_in.product_category,
        product_model=order_in.product_model,
        purchase_date=order_in.purchase_date
    )
    db.add(new_asset)
    await db.commit()
    await db.refresh(new_asset)
    return new_asset


@router.get("/{phone}", response_model=schemas.CustomerDetailResponse)
async def get_customer_assets(phone: str, db: AsyncSession = Depends(get_db)):
    # 联合查询客户档案及其所有资产
    stmt = select(Customer).where(Customer.phone == phone)
    customer = (await db.execute(stmt)).scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="该客户不存在")

    asset_stmt = select(OrderAsset).where(OrderAsset.customer_id == customer.id)
    assets = (await db.execute(asset_stmt)).scalars().all()

    return schemas.CustomerDetailResponse(customer=customer, assets=assets)