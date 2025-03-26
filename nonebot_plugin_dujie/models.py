"""
修仙游戏数据模型
作者: biupiaa
"""

from tortoise import fields
from .database import Model


class XiuxianUser(Model):
    """修仙用户模型"""
    id = fields.IntField(pk=True)
    user_id = fields.CharField(max_length=20, unique=True)  # QQ号
    level = fields.IntField(default=1)  # 境界等级
    exp = fields.IntField(default=0)  # 经验值
    element = fields.CharField(max_length=10)  # 灵根
    cultivation = fields.IntField(default=0)  # 修为
    karma = fields.IntField(default=0)  # 功德
    artifacts = fields.JSONField(default=list)  # 法宝列表
    last_cultivation_time = fields.FloatField(default=0)  # 上次修炼时间
    sect_id = fields.IntField(default=0, null=True)  # 门派ID，0表示无门派
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "xiuxian_users"
        table_description = "修仙用户数据表"

    def __str__(self):
        return f"用户{self.user_id} - {self.get_realm_name()}"

    def get_realm_name(self) -> str:
        """获取境界名称"""
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
        return REALMS.get(self.level, "未知境界")

    async def get_combat_power(self) -> int:
        """获取战斗力"""
        # 基础战力 = 修为 + 境界加成 + 灵根加成 + 法宝加成
        base_power = self.cultivation
        level_bonus = self.level * 500
        element_bonus = {
            "金": 300,
            "木": 200,
            "水": 250,
            "火": 350,
            "土": 150
        }.get(self.element, 0)
        
        # 处理法宝列表
        artifact_list = self.artifacts if isinstance(self.artifacts, list) else []
        artifact_bonus = len(artifact_list) * 200
        
        return base_power + level_bonus + element_bonus + artifact_bonus
    
    @property
    def has_sect(self) -> bool:
        """是否加入门派"""
        return self.sect_id is not None and self.sect_id > 0
    
    def leave_sect(self):
        """离开门派"""
        self.sect_id = 0  # 使用0代替None


class XiuxianEvent(Model):
    """修仙事件记录模型"""
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.XiuxianUser', related_name='events')
    event_type = fields.CharField(max_length=20)  # 事件类型：修炼、探索、渡劫等
    event_name = fields.CharField(max_length=50)  # 事件名称
    exp_change = fields.IntField(default=0)  # 经验变化
    karma_change = fields.IntField(default=0)  # 功德变化
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "xiuxian_events"
        table_description = "修仙事件记录表"

    def __str__(self):
        return f"{self.user.user_id}的{self.event_type}事件 - {self.event_name}"


class Sect(Model):
    """门派模型"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50, unique=True)  # 门派名称
    leader_id = fields.CharField(max_length=20)  # 掌门ID
    description = fields.TextField(default="")  # 门派介绍
    level = fields.IntField(default=1)  # 门派等级
    resources = fields.IntField(default=0)  # 门派资源
    elders = fields.JSONField(default=list)  # 长老列表
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "xiuxian_sects"
        table_description = "修仙门派表"

    def __str__(self):
        return f"门派: {self.name} (等级: {self.level})"

    async def get_members(self):
        """获取所有成员"""
        return await XiuxianUser.filter(sect_id=self.id)
    
    async def get_total_power(self):
        """计算门派总战力"""
        members = await self.get_members()
        total_power = 0
        for member in members:
            total_power += await member.get_combat_power()
        return total_power
        
    def add_elder(self, elder_id):
        """添加长老
        
        Args:
            elder_id: 长老ID
        """
        elder_list = self.elders if isinstance(self.elders, list) else []
        if elder_id not in elder_list:
            elder_list.append(elder_id)
            self.elders = elder_list
            
    def remove_elder(self, elder_id):
        """移除长老
        
        Args:
            elder_id: 长老ID
        """
        elder_list = self.elders if isinstance(self.elders, list) else []
        if elder_id in elder_list:
            elder_list.remove(elder_id)
            self.elders = elder_list


class PkRecord(Model):
    """PK记录模型"""
    id = fields.IntField(pk=True)
    challenger_id = fields.CharField(max_length=20)  # 挑战者ID
    defender_id = fields.CharField(max_length=20)  # 防守者ID
    winner_id = fields.CharField(max_length=20)  # 获胜者ID
    challenger_sect_id = fields.IntField(null=True)  # 挑战者门派ID
    defender_sect_id = fields.IntField(null=True)  # 防守者门派ID
    is_sect_pk = fields.BooleanField(default=False)  # 是否为门派PK
    exp_reward = fields.IntField(default=0)  # 经验奖励
    karma_change = fields.IntField(default=0)  # 功德变化
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "xiuxian_pk_records"
        table_description = "修仙PK记录表"

    def __str__(self):
        if self.is_sect_pk:
            return f"门派战: {self.challenger_sect_id} vs {self.defender_sect_id}"
        else:
            return f"个人战: {self.challenger_id} vs {self.defender_id}" 