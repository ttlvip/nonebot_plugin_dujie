"""
数据库管理模块
作者: biupiaa
"""

import os

from dotenv import load_dotenv
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

# 加载环境变量
load_dotenv(".env.dev")  # 优先加载开发环境配置
load_dotenv(".env")      # 加载默认配置

# 数据库配置
DB_URL = os.getenv("DB_URL", "sqlite://./data/db/xiuxian.db")

# 数据库模型定义
TORTOISE_ORM = {
    "connections": {"default": DB_URL},
    "apps": {
        "models": {
            "models": ["zhenxun.plugins.xiuxian.models"],
            "default_connection": "default",
        }
    }
}

async def init_db():
    """初始化数据库"""
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()

def get_db_url() -> str:
    """获取数据库URL"""
    return DB_URL

def get_db_type() -> str:
    """获取数据库类型"""
    if DB_URL.startswith("sqlite"):
        return "sqlite"
    elif DB_URL.startswith("mysql"):
        return "mysql"
    elif DB_URL.startswith("postgres"):
        return "postgresql"
    else:
        raise ValueError(f"不支持的数据库类型: {DB_URL}")

def register_db(app):
    """注册数据库到FastAPI应用"""
    register_tortoise(
        app,
        config=TORTOISE_ORM,
        generate_schemas=True,
        add_exception_handlers=True,
    ) 