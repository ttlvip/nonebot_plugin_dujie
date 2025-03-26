"""
道友请渡劫 - 修仙模拟器
作者: biupiaa
"""

from pathlib import Path

from nonebot import get_driver
from nonebot.plugin import PluginMetadata

from .constants import ELEMENT_COEFFICIENTS, REALMS
from .cultivation import cultivate
from .database import init_db

# 插件元数据
__plugin_meta__ = PluginMetadata(
    name="道友请渡劫",
    description="一个修仙模拟器插件",
    usage="""基础命令：
    创建角色 - 开始你的修仙之旅
    修炼 - 提升修为
    渡劫 - 突破境界
    门派相关 - 创建/加入/退出/查看门派
    PK - 与其他道友切磋
    探索 - 探索机缘""",
    type="application",
    homepage="https://github.com/yourusername/nonebot_plugin_dujie",
    supported_adapters={"~onebot.v11"},
)

from .exploration import apply_event_effect, get_available_events

from .pk import sect_pk, pk_command
from .sect import appoint_elder, leave_sect, join_sect, sect_info, create_sect

# 获取插件目录
dir_ = Path(__file__).parent

# 初始化数据库
driver = get_driver()
driver.on_startup(init_db)

# 导入子模块
from . import cultivation, sect, pk, tribulation

import random
import time

from nonebot import on_command
from nonebot.adapters.onebot.v11 import (Bot, GroupMessageEvent, Message,
                                         MessageEvent)
from nonebot.params import CommandArg
from nonebot.typing import T_State

from .models import PkRecord, Sect, XiuxianEvent, XiuxianUser

# 创建角色命令
create_char = on_command("开始修仙", priority=5, block=True)

@create_char.handle()
async def handle_create_char(bot: Bot, event: MessageEvent, state: T_State):
    """处理创建角色命令"""
    user_id = str(event.user_id)
    
    # 检查用户是否已存在
    user = await XiuxianUser.get_or_none(user_id=user_id)
    if user:
        await create_char.finish("道友已经创建过角色了！")
        return
    
    # 随机分配灵根
    element = random.choice(list(ELEMENT_COEFFICIENTS.keys()))
    
    # 创建用户
    user = await XiuxianUser.create(
        user_id=user_id,
        level=1,
        exp=0,
        element=element,
        cultivation=0,
        karma=0,
        artifacts=[],
        last_cultivation_time=0
    )
    
    # 记录事件
    await XiuxianEvent.create(
        user=user,
        event_type="创建角色",
        event_name="踏上修仙之路",
        exp_change=0,
        karma_change=0
    )
    
    await create_char.finish(f"恭喜道友踏上修仙之路！\n你的灵根是：{element}\n当前境界：练气期")

# 查看状态命令
check_status = on_command("查看状态", priority=5, block=True)

@check_status.handle()
async def handle_check_status(bot: Bot, event: MessageEvent, state: T_State):
    """处理查看状态命令"""
    user_id = str(event.user_id)
    
    # 获取用户数据
    user = await XiuxianUser.get_or_none(user_id=user_id)
    if not user:
        await check_status.finish("道友还未创建角色，请先使用「开始修仙」命令！")
        return
    
    # 获取最近事件
    recent_events = await XiuxianEvent.filter(user=user).order_by('-created_at').limit(3)
    event_history = "\n".join([f"- {event.event_type}: {event.event_name}" for event in recent_events])
    
    status_msg = f"""
道友当前状态：
境界：{user.get_realm_name()}
修为：{user.cultivation}
灵根：{user.element}
功德：{user.karma}
法宝：{', '.join(user.artifacts) if user.artifacts else '无'}

最近事件：
{event_history}
"""
    await check_status.finish(status_msg)