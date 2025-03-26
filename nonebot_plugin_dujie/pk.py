"""
PK系统实现
作者: biupiaa
"""

import random

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageEvent
from nonebot.params import CommandArg
from nonebot.typing import T_State

from .models import XiuxianUser, XiuxianEvent, PkRecord

# PK命令
pk_command = on_command("修仙PK", aliases={"修仙pk", "道友PK", "道友pk"}, priority=5, block=True)

@pk_command.handle()
async def handle_pk(bot: Bot, event: MessageEvent, state: T_State, args: Message = CommandArg()):
    """处理PK命令"""
    user_id = str(event.user_id)
    
    # 确保用户在群组中
    if not isinstance(event, GroupMessageEvent):
        await pk_command.finish("修仙PK只能在群聊中使用！")
        return
    
    group_id = str(event.group_id)
    
    # 获取挑战者信息
    challenger = await XiuxianUser.get_or_none(user_id=user_id)
    if not challenger:
        await pk_command.finish("道友还未创建角色，请先使用「开始修仙」命令！")
        return
    
    # 解析目标ID
    target_id = args.extract_plain_text().strip()
    if not target_id:
        await pk_command.finish("请指定要挑战的道友QQ号！格式：修仙PK [QQ号]")
        return
    
    # 确保目标不是自己
    if target_id == user_id:
        await pk_command.finish("道友不能挑战自己！")
        return
    
    # 获取目标用户信息
    defender = await XiuxianUser.get_or_none(user_id=target_id)
    if not defender:
        await pk_command.finish("目标道友尚未踏上修仙之路！")
        return
    
    # 计算战斗力
    challenger_power = await challenger.get_combat_power()
    defender_power = await defender.get_combat_power()
    
    # 计算胜率
    win_rate = 0.5 + (challenger_power - defender_power) / (challenger_power + defender_power) * 0.3
    win_rate = max(0.2, min(0.8, win_rate))  # 保证胜率在20%-80%之间
    
    # 随机决定胜负
    challenger_wins = random.random() < win_rate
    
    # 战斗结果
    winner_id = challenger.user_id if challenger_wins else defender.user_id
    loser_id = defender.user_id if challenger_wins else challenger.user_id
    
    # 奖惩计算
    exp_reward = int(min(challenger.level, defender.level) * 100)
    karma_change = 20
    
    # 更新胜者数据
    winner = challenger if challenger_wins else defender
    winner.cultivation += exp_reward
    winner.karma += karma_change
    await winner.save()
    
    # 更新败者数据
    loser = defender if challenger_wins else challenger
    loser.karma -= karma_change
    await loser.save()
    
    # 记录PK结果
    await PkRecord.create(
        challenger_id=challenger.user_id,
        defender_id=defender.user_id,
        winner_id=winner_id,
        challenger_sect_id=challenger.sect_id,
        defender_sect_id=defender.sect_id,
        is_sect_pk=False,
        exp_reward=exp_reward,
        karma_change=karma_change
    )
    
    # 记录事件
    await XiuxianEvent.create(
        user=winner,
        event_type="PK胜利",
        event_name=f"击败{loser.user_id}",
        exp_change=exp_reward,
        karma_change=karma_change
    )
    
    await XiuxianEvent.create(
        user=loser,
        event_type="PK失败",
        event_name=f"被{winner.user_id}击败",
        exp_change=0,
        karma_change=-karma_change
    )
    
    # 构建结果消息
    if challenger_wins:
        result_msg = f"🔥 激烈的修仙对决！\n\n{challenger.user_id}（{challenger.get_realm_name()}） VS {defender.user_id}（{defender.get_realm_name()}）\n\n{challenger.user_id} 获胜！\n获得修为 {exp_reward} 点\n获得功德 {karma_change} 点"
    else:
        result_msg = f"🔥 激烈的修仙对决！\n\n{challenger.user_id}（{challenger.get_realm_name()}） VS {defender.user_id}（{defender.get_realm_name()}）\n\n{defender.user_id} 获胜！\n获得修为 {exp_reward} 点\n获得功德 {karma_change} 点"
    
    await pk_command.finish(result_msg)

# 门派PK命令
sect_pk = on_command("门派战", aliases={"门派pk", "门派PK"}, priority=5, block=True)

@sect_pk.handle()
async def handle_sect_pk(bot: Bot, event: MessageEvent, state: T_State, args: Message = CommandArg()):
    """处理门派战命令"""
    user_id = str(event.user_id)
    
    # 确保用户在群组中
    if not isinstance(event, GroupMessageEvent):
        await sect_pk.finish("门派战只能在群聊中使用！")
        return
    
    # 获取用户数据
    user = await XiuxianUser.get_or_none(user_id=user_id)
    if not user:
        await sect_pk.finish("道友还未创建角色，请先使用「开始修仙」命令！")
        return
    
    # 检查是否有门派
    if not user.has_sect:
        await sect_pk.finish("道友尚未加入任何门派！")
        return
    
    # 获取自己的门派信息
    own_sect = await Sect.get_or_none(id=user.sect_id)
    if not own_sect:
        # 门派数据异常，重置用户门派信息
        user.leave_sect()
        await user.save()
        await sect_pk.finish("未找到门派信息，已重置你的门派状态。")
        return
    
    # 检查是否为掌门或长老
    if own_sect.leader_id != user_id and user_id not in own_sect.elders:
        await sect_pk.finish("只有掌门或长老才能发起门派战！")
        return
    
    # 获取目标门派名称
    target_sect_name = args.extract_plain_text().strip()
    if not target_sect_name:
        await sect_pk.finish("请提供要挑战的门派名称！格式：门派战 [门派名称]")
        return
    
    # 检查目标门派是否存在
    target_sect = await Sect.get_or_none(name=target_sect_name)
    if not target_sect:
        await sect_pk.finish(f"未找到门派「{target_sect_name}」！")
        return
    
    # 确保不是与自己的门派战斗
    if target_sect.id == own_sect.id:
        await sect_pk.finish("不能与自己的门派战斗！")
        return
    
    # 计算战斗力
    own_power = await own_sect.get_total_power()
    target_power = await target_sect.get_total_power()
    
    # 计算胜率
    win_rate = 0.5 + (own_power - target_power) / (own_power + target_power) * 0.3
    win_rate = max(0.2, min(0.8, win_rate))  # 保证胜率在20%-80%之间
    
    # 随机决定胜负
    own_sect_wins = random.random() < win_rate
    
    # 计算奖惩
    resource_reward = random.randint(50, 100)
    
    # 更新胜者和败者门派资源
    if own_sect_wins:
        own_sect.resources += resource_reward
        target_sect.resources = max(0, target_sect.resources - resource_reward)
        winner_sect = own_sect
        loser_sect = target_sect
    else:
        target_sect.resources += resource_reward
        own_sect.resources = max(0, own_sect.resources - resource_reward)
        winner_sect = target_sect
        loser_sect = own_sect
    
    await own_sect.save()
    await target_sect.save()
    
    # 记录PK结果
    await PkRecord.create(
        challenger_id=user_id,
        defender_id="system",  # 门派战没有具体防守者
        winner_id="system",
        challenger_sect_id=own_sect.id,
        defender_sect_id=target_sect.id,
        is_sect_pk=True,
        exp_reward=0,
        karma_change=0
    )
    
    # 构建结果消息
    result_msg = f"""⚔️ 激烈的门派对决！
我方: {own_sect.name} (总战力: {own_power})
对方: {target_sect.name} (总战力: {target_power})

结果: {'我方获胜' if own_sect_wins else '对方获胜'}！
{'我方' if own_sect_wins else '对方'}获得资源 {resource_reward} 点
"""
    
    await sect_pk.finish(result_msg) 