from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models import Base
from routers import customer, order, chat, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("系统启动")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("系统就绪")
    yield
    print("系统关闭：正在安全释放 MySQL 连接池")
    await engine.dispose()

app = FastAPI(
    title="电商智能售后系统",
    version="1.0.0",
    description="基于 FastAPI + SQLAlchemy 2.0 的结构化与非结构化问答网关",
    lifespan=lifespan
)

# 标准跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载模块化路由
app.include_router(customer.router)
app.include_router(order.router)
app.include_router(chat.router)
app.include_router(admin.router)

if __name__ == "__main__":
    import uvicorn
    # 使用模块路径启动，这是生产环境的标准做法
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)