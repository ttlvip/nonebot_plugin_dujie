"""
门派系统实现
作者: biupiaa
"""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.params import CommandArg
from nonebot.typing import T_State

from .models import XiuxianUser, XiuxianEvent, Sect

# 创建门派命令
create_sect = on_command("创建门派", priority=5, block=True)

@create_sect.handle()
async def handle_create_sect(bot: Bot, event: MessageEvent, state: T_State, args: str = CommandArg()):
    """处理创建门派命令"""
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
    """处理查看门派信息命令"""
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
async def handle_join_sect(bot: Bot, event: MessageEvent, state: T_State, args: str = CommandArg()):
    """处理加入门派命令"""
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
    """处理退出门派命令"""
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
async def handle_appoint_elder(bot: Bot, event: MessageEvent, state: T_State, args: str = CommandArg()):
    """处理任命长老命令"""
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