"""
道友请渡劫 - 修仙游戏插件
作者: biupiaa
"""

import random
import time

import nonebot
from nonebot import on_command
from nonebot.adapters.onebot.v11 import (Bot, GroupMessageEvent, Message,
                                         MessageEvent)
from nonebot.params import CommandArg
from nonebot.typing import T_State

from . import database
from .exploration import (EXPLORATION_EVENTS, apply_event_effect,
                          get_available_events)
from .models import PkRecord, Sect, XiuxianEvent, XiuxianUser
from . import cultivation, sect, pk, tribulation

# 获取驱动器
driver = nonebot.get_driver()

# 在启动时初始化数据库
@driver.on_startup
async def init_db():
    """初始化修仙游戏数据库"""
    await database.init_db()
    

# 插件配置
PLUGIN_NAME = "道友请渡劫"
PLUGIN_DESCRIPTION = "一个基于群聊的修仙游戏"
PLUGIN_USAGE = """
基础命令：
1. 开始修仙 - 创建角色
2. 查看状态 - 查看当前状态
3. 修炼 - 进行修炼
4. 探索 - 探索秘境
5. 渡劫 - 尝试突破境界
"""

# 境界定义
REALMS = {
    1: "练气期",
    2: "筑基期",
    3: "金丹期",
    4: "元婴期",
    5: "化神期",
    6: "炼虚期",
    7: "合体期",
    8: "大乘期"
}

# 灵根系数
ELEMENT_COEFFICIENTS = {
    "金": 0.3,
    "木": 0.2,
    "水": 0.25,
    "火": 0.25,
    "土": 0.15
}

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

# 修炼命令
cultivate = on_command("修炼", priority=5, block=True)

@cultivate.handle()
async def handle_cultivate(bot: Bot, event: MessageEvent, state: T_State):
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

# 渡劫命令
tribulation = on_command("渡劫", priority=5, block=True)

@tribulation.handle()
async def handle_tribulation(bot: Bot, event: MessageEvent, state: T_State):
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

# PK命令
pk_command = on_command("修仙PK", aliases={"修仙pk", "道友PK", "道友pk"}, priority=5, block=True)

@pk_command.handle()
async def handle_pk(bot: Bot, event: MessageEvent, state: T_State, args: Message = CommandArg()):
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

# 创建门派命令
create_sect = on_command("创建门派", priority=5, block=True)

@create_sect.handle()
async def handle_create_sect(bot: Bot, event: MessageEvent, state: T_State, args: Message = CommandArg()):
    user_id = str(event.user_id)
    
    # 获取用户数据
    user = await XiuxianUser.get_or_none(user_id=user_id)
    if not user:
        await create_sect.finish("道友还未创建角色，请先使用「开始修仙」命令！")
        return
    
    # 检查境界要求
    if user.level < 3:
        await create_sect.finish(f"道友境界不足，创建门派至少需要金丹期(3级)境界！当前境界：{user.get_realm_name()}")
        return
    
    # 检查是否已有门派
    if user.sect_id:
        await create_sect.finish("道友已经加入了门派，请先退出当前门派！")
        return
    
    # 获取门派名称
    sect_name = args.extract_plain_text().strip()
    if not sect_name:
        await create_sect.finish("请提供门派名称！格式：创建门派 [名称]")
        return
    
    # 检查门派名称是否已存在
    existing_sect = await Sect.get_or_none(name=sect_name)
    if existing_sect:
        await create_sect.finish(f"门派「{sect_name}」已存在！")
        return
    
    # 创建门派
    sect = await Sect.create(
        name=sect_name,
        leader_id=user_id,
        description=f"{sect_name}，一个新兴的修仙门派。",
        level=1,
        resources=100,
        elders=[]
    )
    
    # 更新用户门派信息
    user.sect_id = sect.id
    await user.save()
    
    # 记录事件
    await XiuxianEvent.create(
        user=user,
        event_type="门派",
        event_name=f"创建门派「{sect_name}」",
        exp_change=0,
        karma_change=50
    )
    
    await create_sect.finish(f"恭喜道友成功创建门派「{sect_name}」！\n你已成为该门派的掌门。")

# 门派信息命令
sect_info = on_command("门派信息", priority=5, block=True)

@sect_info.handle()
async def handle_sect_info(bot: Bot, event: MessageEvent, state: T_State):
    user_id = str(event.user_id)
    
    # 获取用户数据
    user = await XiuxianUser.get_or_none(user_id=user_id)
    if not user:
        await sect_info.finish("道友还未创建角色，请先使用「开始修仙」命令！")
        return
    
    # 检查是否有门派
    if not user.has_sect:
        await sect_info.finish("道友尚未加入任何门派！")
        return
    
    # 获取门派信息
    sect = await Sect.get_or_none(id=user.sect_id)
    if not sect:
        # 门派数据异常，重置用户门派信息
        user.leave_sect()
        await user.save()
        await sect_info.finish("未找到门派信息，已重置你的门派状态。")
        return
    
    # 获取门派成员
    members = await sect.get_members()
    member_count = len(members)
    
    # 获取门派总战力
    total_power = await sect.get_total_power()
    
    # 构建结果消息
    result = f"""===== 门派「{sect.name}」=====
门派等级: {sect.level}
掌门: {sect.leader_id}
成员数: {member_count}
门派资源: {sect.resources}
门派总战力: {total_power}

简介: {sect.description}

长老列表:
"""
    
    if sect.elders:
        for elder_id in sect.elders:
            result += f"- {elder_id}\n"
    else:
        result += "暂无长老\n"
    
    await sect_info.finish(result)

# 加入门派命令
join_sect = on_command("加入门派", priority=5, block=True)

@join_sect.handle()
async def handle_join_sect(bot: Bot, event: MessageEvent, state: T_State, args: Message = CommandArg()):
    user_id = str(event.user_id)
    
    # 获取用户数据
    user = await XiuxianUser.get_or_none(user_id=user_id)
    if not user:
        await join_sect.finish("道友还未创建角色，请先使用「开始修仙」命令！")
        return
    
    # 检查是否已有门派
    if user.sect_id:
        await join_sect.finish("道友已经加入了门派，请先退出当前门派！")
        return
    
    # 获取门派名称
    sect_name = args.extract_plain_text().strip()
    if not sect_name:
        await join_sect.finish("请提供门派名称！格式：加入门派 [名称]")
        return
    
    # 查找门派
    sect = await Sect.get_or_none(name=sect_name)
    if not sect:
        await join_sect.finish(f"未找到门派「{sect_name}」！")
        return
    
    # 更新用户门派信息
    user.sect_id = sect.id
    await user.save()
    
    # 记录事件
    await XiuxianEvent.create(
        user=user,
        event_type="门派",
        event_name=f"加入门派「{sect_name}」",
        exp_change=0,
        karma_change=0
    )
    
    await join_sect.finish(f"恭喜道友成功加入门派「{sect_name}」！")

# 退出门派命令
leave_sect = on_command("退出门派", priority=5, block=True)

@leave_sect.handle()
async def handle_leave_sect(bot: Bot, event: MessageEvent, state: T_State):
    user_id = str(event.user_id)
    
    # 获取用户数据
    user = await XiuxianUser.get_or_none(user_id=user_id)
    if not user:
        await leave_sect.finish("道友还未创建角色，请先使用「开始修仙」命令！")
        return
    
    # 检查是否有门派
    if not user.has_sect:
        await leave_sect.finish("道友尚未加入任何门派！")
        return
    
    # 获取门派信息
    sect = await Sect.get_or_none(id=user.sect_id)
    if not sect:
        # 门派数据异常，重置用户门派信息
        user.leave_sect()
        await user.save()
        await leave_sect.finish("未找到门派信息，已重置你的门派状态。")
        return
    
    # 检查是否为掌门
    if sect.leader_id == user_id:
        await leave_sect.finish("作为掌门，你不能直接退出门派。请先转让掌门职位或解散门派！")
        return
    
    # 获取门派名称
    sect_name = sect.name
    
    # 如果是长老，从长老列表中移除
    if user_id in sect.elders:
        sect.remove_elder(user_id)
        await sect.save()
    
    # 更新用户门派信息
    user.leave_sect()
    await user.save()
    
    # 记录事件
    await XiuxianEvent.create(
        user=user,
        event_type="门派",
        event_name=f"退出门派「{sect_name}」",
        exp_change=0,
        karma_change=0
    )
    
    await leave_sect.finish(f"道友已退出门派「{sect_name}」。")

# 任命长老命令
appoint_elder = on_command("任命长老", priority=5, block=True)

@appoint_elder.handle()
async def handle_appoint_elder(bot: Bot, event: MessageEvent, state: T_State, args: Message = CommandArg()):
    user_id = str(event.user_id)
    
    # 获取用户数据
    user = await XiuxianUser.get_or_none(user_id=user_id)
    if not user:
        await appoint_elder.finish("道友还未创建角色，请先使用「开始修仙」命令！")
        return
    
    # 检查是否有门派
    if not user.has_sect:
        await appoint_elder.finish("道友尚未加入任何门派！")
        return
    
    # 获取门派信息
    sect = await Sect.get_or_none(id=user.sect_id)
    if not sect:
        # 门派数据异常，重置用户门派信息
        user.leave_sect()
        await user.save()
        await appoint_elder.finish("未找到门派信息，已重置你的门派状态。")
        return
    
    # 检查是否为掌门
    if sect.leader_id != user_id:
        await appoint_elder.finish("只有掌门才能任命长老！")
        return
    
    # 获取目标用户ID
    target_id = args.extract_plain_text().strip()
    if not target_id:
        await appoint_elder.finish("请提供要任命的道友QQ号！格式：任命长老 [QQ号]")
        return
    
    # 检查目标用户是否存在
    target_user = await XiuxianUser.get_or_none(user_id=target_id)
    if not target_user:
        await appoint_elder.finish("目标道友尚未踏上修仙之路！")
        return
    
    # 检查目标用户是否在同一门派
    if target_user.sect_id != user.sect_id:
        await appoint_elder.finish("目标道友不在本门派中！")
        return
    
    # 使用Sect类的helper方法添加长老
    sect.add_elder(target_id)
    await sect.save()
    
    # 记录事件
    await XiuxianEvent.create(
        user=user,
        event_type="门派",
        event_name=f"任命{target_id}为长老",
        exp_change=0,
        karma_change=0
    )
    
    await appoint_elder.finish(f"已成功任命道友 {target_id} 为门派长老！")

# 门派PK命令
sect_pk = on_command("门派战", aliases={"门派pk", "门派PK"}, priority=5, block=True)

@sect_pk.handle()
async def handle_sect_pk(bot: Bot, event: MessageEvent, state: T_State, args: Message = CommandArg()):
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