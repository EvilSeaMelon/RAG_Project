from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Customer
import schemas

router = APIRouter(prefix="/api/customers", tags=["客户管理"])


@router.post("/", response_model=schemas.CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(customer_in: schemas.CustomerCreate, db: AsyncSession = Depends(get_db)):
    # 唯一性校验
    stmt = select(Customer).where(Customer.phone == customer_in.phone)
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该手机号已注册，请勿重复添加。")

    new_customer = Customer(**customer_in.model_dump())
    db.add(new_customer)
    await db.commit()
    await db.refresh(new_customer)
    return new_customer