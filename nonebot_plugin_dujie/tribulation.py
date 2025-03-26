"""
渡劫系统实现
作者: biupiaa
"""

import random

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.typing import T_State

from .constants import REALMS
from .models import XiuxianUser

# 渡劫命令
tribulation = on_command("渡劫", priority=5, block=True)

@tribulation.handle()
async def handle_tribulation(bot: Bot, event: MessageEvent, state: T_State):
    """处理渡劫命令"""
    user_id = str(event.user_id)
    
    # 获取用户数据
    user = await XiuxianUser.get_or_none(user_id=user_id)
    if not user:
        await tribulation.finish("道友还未创建角色，请先使用「开始修仙」命令！")
        return
    
    current_level = user.level
    
    # 检查是否可以渡劫
    if current_level >= 8:
        await tribulation.finish("道友已经达到最高境界，无需渡劫！")
        return
    
    # 检查修为是否足够
    required_cultivation = (current_level + 1) * 1000
    if user.cultivation < required_cultivation:
        await tribulation.finish(f"道友修为不足，需要{required_cultivation}点修为才能渡劫！")
        return
    
    # 渡劫成功率计算
    success_rate = 0.8 - (current_level * 0.05)  # 境界越高，成功率越低
    success = random.random() < success_rate
    
    if success:
        user.level += 1
        user.cultivation -= required_cultivation
        event_name = f"渡劫成功，突破到{REALMS[user.level]}"
    else:
        user.cultivation -= int(required_cultivation * 0.5)  # 失败损失一半修为
        event_name = "渡劫失败"
    
    await user.save()
    
    # 记录事件
    await XiuxianEvent.create(
        user=user,
        event_type="渡劫",
        event_name=event_name,
        exp_change=-required_cultivation if success else -int(required_cultivation * 0.5),
        karma_change=50 if success else -30
    )
    
    if success:
        await tribulation.finish(f"恭喜道友渡劫成功，突破到{REALMS[user.level]}！")
    else:
        await tribulation.finish("渡劫失败，道友修为受损！") 