"""
修炼系统实现
作者: biupiaa
"""

import random
import time

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.typing import T_State

from .constants import ELEMENT_COEFFICIENTS, REALMS
from .models import XiuxianUser, XiuxianEvent

# 修炼命令
cultivate = on_command("修炼", priority=5, block=True)

@cultivate.handle()
async def handle_cultivate(bot: Bot, event: MessageEvent, state: T_State):
    """处理修炼命令"""
    user_id = str(event.user_id)
    
    # 获取用户数据
    user = await XiuxianUser.get_or_none(user_id=user_id)
    if not user:
        await cultivate.finish("道友还未创建角色，请先使用「开始修仙」命令！")
        return
    
    current_time = time.time()
    
    # 检查修炼冷却时间（1小时）
    if current_time - user.last_cultivation_time < 3600:
        remaining_time = int(3600 - (current_time - user.last_cultivation_time))
        await cultivate.finish(f"道友需要休息片刻，{remaining_time}秒后可以继续修炼。")
        return
    
    # 计算本次修炼获得的修为
    base_exp = user.level * (1 + ELEMENT_COEFFICIENTS[user.element])
    # 添加随机波动
    exp_gain = int(base_exp * (1 + random.uniform(-0.2, 0.2)))
    
    # 更新用户数据
    user.cultivation += exp_gain
    user.last_cultivation_time = current_time
    
    # 检查是否可以突破
    next_level = user.level + 1
    if next_level in REALMS and user.cultivation >= next_level * 1000:
        user.level = next_level
        event_name = f"突破到{REALMS[next_level]}"
    else:
        event_name = "日常修炼"
    
    await user.save()
    
    # 记录事件
    await XiuxianEvent.create(
        user=user,
        event_type="修炼",
        event_name=event_name,
        exp_change=exp_gain,
        karma_change=0
    )
    
    await cultivate.finish(f"本次修炼获得{exp_gain}点修为。") 