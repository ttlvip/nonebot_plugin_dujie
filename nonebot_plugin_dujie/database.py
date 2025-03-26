"""
数据库管理模块
作者: biupiaa
"""

import os
from typing import List, Tuple, Any

from nonebot.utils import is_coroutine_callable
from tortoise import Tortoise
from tortoise.connection import connections
from tortoise.models import Model as Model_

from .log import logger

# 存储所有模型和SQL脚本方法
SCRIPT_METHOD: List[Tuple[str, Any]] = []
MODELS: List[str] = []


class Model(Model_):
    """自动注册的模型基类"""
    
    def __init_subclass__(cls, **kwargs):
        """子类初始化时自动注册到MODELS列表"""
        MODELS.append(cls.__module__)
        
        # 检查是否有SQL脚本方法
        if func := getattr(cls, "_run_script", None):
            SCRIPT_METHOD.append((cls.__module__, func))


class DbUrlIsNone(Exception):
    """数据库连接地址为空异常"""
    pass


class DbConnectError(Exception):
    """数据库连接错误异常"""
    pass


async def init_db():
    """初始化数据库连接"""
    # 获取数据库URL
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise DbUrlIsNone("数据库配置为空，请在.env.dev中配置DB_URL...")
    
    try:
        # 初始化数据库连接
        await Tortoise.init(
            db_url=db_url,
            modules={"models": MODELS},
            timezone="Asia/Shanghai"
        )
        
        # 执行SQL脚本方法
        if SCRIPT_METHOD:
            db = Tortoise.get_connection("default")
            logger.debug(
                "即将运行SCRIPT_METHOD方法, 合计 "
                f"<u><y>{len(SCRIPT_METHOD)}</y></u> 个..."
            )
            sql_list = []
            
            for module, func in SCRIPT_METHOD:
                try:
                    sql = await func() if is_coroutine_callable(func) else func()
                    if sql:
                        sql_list += sql
                except Exception as e:
                    logger.debug(f"{module} 执行SCRIPT_METHOD方法出错...", e=e)
            
            for sql in sql_list:
                logger.debug(f"执行SQL: {sql}")
                try:
                    await db.execute_query_dict(sql)
                except Exception as e:
                    logger.debug(f"执行SQL: {sql} 错误...", e=e)
            
            if sql_list:
                logger.debug("SCRIPT_METHOD方法执行完毕!")
        
        # 生成数据库表
        await Tortoise.generate_schemas()
        logger.info("数据库加载成功!")
        
    except Exception as e:
        raise DbConnectError(f"数据库连接错误... e:{e}") from e


async def disconnect():
    """断开数据库连接"""
    await connections.close_all()


def get_db_url() -> str:
    """获取数据库URL"""
    return os.getenv("DB_URL", "sqlite://./data/db/xiuxian.db")


def get_db_type() -> str:
    """获取数据库类型"""
    db_url = get_db_url()
    if db_url.startswith("sqlite"):
        return "sqlite"
    elif db_url.startswith("mysql"):
        return "mysql"
    elif db_url.startswith("postgres"):
        return "postgresql"
    else:
        raise ValueError(f"不支持的数据库类型: {db_url}")

def register_db(app):
    """注册数据库到FastAPI应用"""
    register_tortoise(
        app,
        config=TORTOISE_ORM,
        generate_schemas=True,
        add_exception_handlers=True,
    ) 