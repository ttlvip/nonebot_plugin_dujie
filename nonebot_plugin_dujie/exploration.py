"""
修仙游戏探索事件模块
作者: biupiaa
"""
import random

from nonebot import on_command
from nonebot.adapters.onebot.v11 import (Bot, MessageEvent)
from nonebot.typing import T_State

from .models import XiuxianEvent, XiuxianUser

# 探索事件库
EXPLORATION_EVENTS = [
    # 基础事件 - 适合所有等级的道友
    {
        "name": "灵药园",
        "description": "道友在深山中发现了一片灵药园，灵气充沛，药草芬芳。",
        "type": "收益",
        "condition": lambda u: True,
        "effect": lambda u: {"cultivation": 100, "karma": 20}
    },
    {
        "name": "小溪洗礼",
        "description": "道友在山间发现一条灵气充沛的小溪，在此修炼事半功倍。",
        "type": "收益",
        "condition": lambda u: True,
        "effect": lambda u: {"cultivation": 80, "karma": 10}
    },
    {
        "name": "流浪修士",
        "description": "道友遇到一位流浪修士，互相切磋武艺，获益良多。",
        "type": "收益",
        "condition": lambda u: True,
        "effect": lambda u: {"cultivation": 50, "karma": 5}
    },

    # 初级事件 - 筑基期以上可遇
    {
        "name": "古修士洞府",
        "description": "道友发现了一座古老的洞府，里面留有前人的修炼心得。",
        "type": "收益",
        "condition": lambda u: u.level >= 2,
        "effect": lambda u: {"cultivation": 200, "karma": 50}
    },
    {
        "name": "灵石矿脉",
        "description": "道友探索时发现了一条灵石矿脉，收获颇丰。",
        "type": "收益",
        "condition": lambda u: u.level >= 2,
        "effect": lambda u: {"cultivation": 180, "karma": 30}
    },
    {
        "name": "迷雾密林",
        "description": "道友在一片迷雾密林中迷失方向，消耗了不少精力。",
        "type": "损失",
        "condition": lambda u: u.level >= 2,
        "effect": lambda u: {"cultivation": -50, "karma": -10}
    },

    # 中级事件 - 金丹期以上可遇
    {
        "name": "域外天魔",
        "description": "道友遭遇域外天魔袭击，一番苦战后才勉强逃脱。",
        "type": "战斗",
        "condition": lambda u: u.level >= 3,
        "effect": lambda u: {"cultivation": -int(u.cultivation * 0.3), "karma": -50}
    },
    {
        "name": "天材地宝",
        "description": "道友有幸发现一株万年灵芝，服用后修为大涨。",
        "type": "收益",
        "condition": lambda u: u.level >= 3,
        "effect": lambda u: {"cultivation": 500, "karma": 100}
    },
    {
        "name": "丹药炼制",
        "description": "道友收集了各种灵材，成功炼制出一炉上品丹药。",
        "type": "收益",
        "condition": lambda u: u.level >= 3,
        "effect": lambda u: {"cultivation": 300, "karma": 80}
    },

    # 高级事件 - 元婴期以上可遇
    {
        "name": "上古遗迹",
        "description": "道友发现了一处上古修仙门派的遗迹，获得了不少传承。",
        "type": "收益",
        "condition": lambda u: u.level >= 4,
        "effect": lambda u: {"cultivation": 800, "karma": 200, "artifacts": "古修传承玉简"}
    },
    {
        "name": "灵脉争夺",
        "description": "道友发现一条上好的灵脉，却引来其他修士的觊觎，一番争斗后侥幸守住。",
        "type": "战斗",
        "condition": lambda u: u.level >= 4,
        "effect": lambda u: {"cultivation": 600, "karma": -100}
    },
    {
        "name": "神秘洞天",
        "description": "道友误入一处神秘洞天，时间流速不同，在里面修炼了数年。",
        "type": "收益",
        "condition": lambda u: u.level >= 4,
        "effect": lambda u: {"cultivation": 1000, "karma": 150}
    },

    # 特殊事件 - 化神期以上可遇
    {
        "name": "远古战场",
        "description": "道友踏入一处远古仙魔战场，残留的能量波动让人心惊胆战。",
        "type": "特殊",
        "condition": lambda u: u.level >= 5,
        "effect": lambda u: {"cultivation": 1500, "karma": 300, "artifacts": "破损的仙器碎片"}
    },
    {
        "name": "天劫余波",
        "description": "道友不幸被卷入他人渡劫的余波中，受到了不小的伤害。",
        "type": "损失",
        "condition": lambda u: u.level >= 5,
        "effect": lambda u: {"cultivation": -int(u.cultivation * 0.4), "karma": -200}
    },
    {
        "name": "秘境入口",
        "description": "道友发现了一处通往秘境的入口，在里面获得了大量修炼资源。",
        "type": "收益",
        "condition": lambda u: u.level >= 5,
        "effect": lambda u: {"cultivation": 2000, "karma": 500}
    },

    # 顶级事件 - 炼虚期以上可遇
    {
        "name": "飞升遗址",
        "description": "道友发现了一位成功飞升的前辈留下的遗址，获得了关于飞升的重要线索。",
        "type": "特殊",
        "condition": lambda u: u.level >= 6,
        "effect": lambda u: {"cultivation": 3000, "karma": 1000, "artifacts": "飞升玉简"}
    },
    {
        "name": "天外来客",
        "description": "道友遭遇天外来客，对方实力强大，几乎陨落。",
        "type": "危险",
        "condition": lambda u: u.level >= 6,
        "effect": lambda u: {"cultivation": -int(u.cultivation * 0.5), "karma": -500}
    },
    {
        "name": "悟道茶树",
        "description": "道友有幸发现传说中的悟道茶树，品尝后顿悟己道。",
        "type": "顿悟",
        "condition": lambda u: u.level >= 6,
        "effect": lambda u: {"cultivation": int(u.cultivation * 0.5), "karma": 800}
    },

    # 极限事件 - 合体期以上可遇
    {
        "name": "仙人洞府",
        "description": "道友有幸闯入一位飞升仙人留下的洞府，获得了无上传承。",
        "type": "机缘",
        "condition": lambda u: u.level >= 7,
        "effect": lambda u: {"cultivation": 5000, "karma": 2000, "artifacts": "仙人传承"}
    },
    {
        "name": "天道惩罚",
        "description": "道友不知何故触怒了天道，遭受天罚，差点魂飞魄散。",
        "type": "危险",
        "condition": lambda u: u.level >= 7,
        "effect": lambda u: {"cultivation": -int(u.cultivation * 0.7), "karma": -1000}
    }
]


# 随机获取可用事件
def get_available_events(user):
    """获取可用事件列表
    
    Args:
        user: 修仙用户对象
        
    Returns:
        可用事件列表
    """
    return [e for e in EXPLORATION_EVENTS if e["condition"](user)]


# 处理文字效果描述
def get_effect_desc(effects):
    """生成效果描述文字
    
    Args:
        effects: 效果字典
        
    Returns:
        效果描述文字列表
    """
    effect_desc = []
    for key, value in effects.items():
        if key == "cultivation":
            effect_desc.append(f"修为{'增加' if value > 0 else '减少'}{abs(value)}点")
        elif key == "karma":
            effect_desc.append(f"功德{'增加' if value > 0 else '减少'}{abs(value)}点")
        elif key == "artifacts":
            effect_desc.append(f"获得法宝：{value}")
    return effect_desc


# 探索命令
explore = on_command("探索", priority=5, block=True)


@explore.handle()
async def handle_explore(bot: Bot, event: MessageEvent, state: T_State):
    """处理探索命令"""
    user_id = str(event.user_id)

    # 获取用户数据
    user = await XiuxianUser.get_or_none(user_id=user_id)
    if not user:
        await explore.finish("道友还未创建角色，请先使用「开始修仙」命令！")
        return

    # 从探索模块获取可用事件
    available_events = get_available_events(user)
    if not available_events:
        await explore.finish("道友暂时没有遇到任何机缘。")
        return

    # 随机选择一个事件
    selected_event = random.choice(available_events)

    # 应用事件效果
    result = await apply_event_effect(user, selected_event)

    # 记录事件
    await XiuxianEvent.create(
        user=user,
        event_type="探索",
        event_name=result["name"],
        exp_change=0,  # 修为变化已在apply_event_effect中处理
        karma_change=0  # 功德变化已在apply_event_effect中处理
    )

    # 构建结果消息
    result_msg = f"""【{result['name']}】
{result['description']}

事件结果:
"""
    for effect in result['effects']:
        result_msg += f"- {effect}\n"

    await explore.finish(result_msg)


# 应用事件效果到用户
async def apply_event_effect(user, event):
    """应用事件效果到用户
    
    Args:
        user: 修仙用户对象
        event: 事件数据
        
    Returns:
        事件效果描述
    """
    effects = event["effect"](user)

    # 处理基础属性
    for key, value in effects.items():
        if key in ["cultivation", "karma"]:
            current_value = getattr(user, key)
            setattr(user, key, max(0, current_value + value))
        elif key == "artifacts" and value:
            if not isinstance(user.artifacts, list):
                user.artifacts = []
            user.artifacts.append(value)

    await user.save()

    # 返回效果描述
    return {
        "name": event["name"],
        "description": event["description"],
        "effects": get_effect_desc(effects)
    }
