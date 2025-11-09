"""
战斗管理器 - 负责游戏玩法核心逻辑
包括：卡片系统、网格系统、单位管理、波次控制、战斗逻辑
"""

import pygame
import logging
import time
from typing import List, Dict, Optional, Tuple
from core.skill_system import SkillManager
from core.projectile_system import ProjectileManager
from core.passive_traits_system import PassiveTraitsManager

logger = logging.getLogger(__name__)


class Defender:
    """防守单位（玩家放置的角色）"""

    def __init__(self, character_config: dict, grid_x: int, grid_y: int, cell_size: int = 80, skill_manager: Optional[SkillManager] = None, battle_manager = None):
        self.character_id = character_config.get('character_id', 'unknown')
        self.name = character_config.get('name', '未知角色')
        self.config = character_config
        self.battle_manager = battle_manager  # 保存战斗管理器引用

        # 网格位置
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.cell_size = cell_size  # 保存cell_size用于距离计算

        # 属性
        stats = character_config.get('stats', {})
        self.max_hp = stats.get('hp', 100)
        self.hp = self.max_hp
        self.attack = stats.get('attack', 10)
        self.attack_range = stats.get('attack_range', 200)
        self.attack_speed = stats.get('attack_speed', 1.0)

        # 攻击类型和弹道配置
        self.attack_type = character_config.get('attack_type', 'melee')  # melee（近战）或 ranged（远程）
        self.projectile_config = character_config.get('projectile', {})  # 远程攻击的弹道配置

        # 攻击计时
        self.attack_cooldown = 0
        self.attack_interval = 1.0 / self.attack_speed

        # 目标
        self.target: Optional['Enemy'] = None

        # 动画状态
        self.animation_state = "idle"
        self.animation_time = 0

        # 技能系统
        self.skills: List = []
        self.active_effects: List = []

        # 控制状态
        self.is_stunned = False  # 眩晕
        self.is_rooted = False  # 定身
        self.is_silenced = False  # 沉默
        self.is_disarmed = False  # 缴械
        self.is_feared = False  # 恐惧
        self.is_taunted = False  # 嘲讽
        self.is_airborne = False  # 击飞
        self.is_knocked_back = False  # 击退

        # 特殊状态
        self.is_invulnerable = False  # 无敌
        self.is_invisible = False  # 隐身
        self.is_summoned = False  # 是否是召唤物
        self.summon_timer = 0  # 召唤物存活时间

        # 加载技能
        if skill_manager:
            self.skills = skill_manager.load_skills_for_character(character_config)

        # 应用被动特质的属性加成
        passive_traits_manager = PassiveTraitsManager()
        passive_traits_manager.apply_stat_bonuses(self)

    def get_screen_pos(self, grid_start_x: int, grid_start_y: int, cell_size: int) -> Tuple[int, int]:
        """获取屏幕坐标"""
        x = grid_start_x + self.grid_x * cell_size + cell_size // 2
        y = grid_start_y + self.grid_y * cell_size + cell_size // 2
        return x, y

    def update(self, delta_time: float, enemies: List['Enemy'], skill_manager: Optional[SkillManager] = None, battle_manager = None, projectile_manager = None):
        """更新防守单位"""
        # 更新召唤物计时器
        if self.is_summoned and self.summon_timer > 0:
            self.summon_timer -= delta_time
            if self.summon_timer <= 0:
                self.hp = 0  # 时间到，消失
                return

        # 更新技能效果
        if skill_manager:
            skill_manager.update_unit_effects(self, delta_time)

        # 应用被动特质（如生命回复）
        if battle_manager and hasattr(battle_manager, 'passive_traits_manager'):
            battle_manager.passive_traits_manager.apply_passive_traits(self, delta_time, battle_manager)

        # 如果被眩晕或击飞，无法行动
        if self.is_stunned or self.is_airborne:
            return

        # 更新技能冷却
        for skill in self.skills:
            skill.update(delta_time)

        # 更新攻击冷却
        if self.attack_cooldown > 0:
            self.attack_cooldown -= delta_time

        # 更新动画时间
        self.animation_time += delta_time

        # 查找目标（如果被嘲讽，强制攻击嘲讽目标）
        if self.is_taunted and hasattr(self, 'taunt_target'):
            if self.taunt_target and self.taunt_target.is_alive():
                self.target = self.taunt_target
            else:
                self.target = None
        elif self.target is None or not self.target.is_alive():
            # 隐身的敌人不能被选中
            visible_enemies = [e for e in enemies if not getattr(e, 'is_invisible', False)]
            if visible_enemies:
                self.find_target(visible_enemies)

        # 自动施放技能（除非被沉默）
        if skill_manager and battle_manager and not self.is_silenced:
            skill_manager.auto_cast_skills(self, battle_manager)

        # 攻击目标（除非被缴械）
        if self.target and self.attack_cooldown <= 0 and not self.is_disarmed:
            distance = abs(self.target.x - self.grid_x * self.cell_size)
            if distance <= self.attack_range:
                self.attack_target(projectile_manager, battle_manager)
                self.attack_cooldown = self.attack_interval
                self.animation_state = "attack"
                self.animation_time = 0

                # 触发攻击时的被动技能
                if skill_manager and battle_manager:
                    skill_manager.trigger_passive_skill(self, 'on_attack', battle_manager)
            else:
                self.target = None
                self.animation_state = "idle"

        # 重置动画
        if self.animation_state == "attack" and self.animation_time > 0.5:
            self.animation_state = "idle"

    def find_target(self, enemies: List['Enemy']):
        """查找攻击目标（最近的敌人）"""
        closest = None
        closest_distance = float('inf')

        for enemy in enemies:
            if enemy.is_alive() and enemy.lane == self.grid_y:
                distance = abs(enemy.x - self.grid_x * self.cell_size)
                if distance < closest_distance and distance <= self.attack_range:
                    closest = enemy
                    closest_distance = distance

        self.target = closest

    def attack_target(self, projectile_manager=None, battle_manager=None):
        """攻击目标"""
        if self.target and self.target.is_alive():
            if self.attack_type == 'ranged' and projectile_manager and battle_manager:
                # 远程攻击：发射弹道
                projectile_config = self.projectile_config.copy()
                projectile_config['damage'] = self.attack
                projectile_manager.create_projectile(self, self.target, projectile_config, battle_manager)
                logger.debug(f"{self.name} 向 {self.target.name} 发射弹道")
            else:
                # 近战攻击：直接造成伤害
                self.target.take_damage(self.attack)
                logger.debug(f"{self.name} 攻击 {self.target.name}，造成 {self.attack} 伤害")

    def take_damage(self, damage: int, is_crit: bool = False):
        """受到伤害"""
        # 无敌状态免疫所有伤害
        if getattr(self, 'is_invulnerable', False):
            return

        # 应用防御减免
        if hasattr(self, '_defense_multiplier'):
            damage = int(damage * self._defense_multiplier)

        self.hp -= damage
        if self.hp < 0:
            self.hp = 0

        # 显示伤害数字和音效
        if self.battle_manager and hasattr(self.battle_manager, 'hit_feedback'):
            # 获取屏幕坐标
            x, y = self.get_screen_pos(
                self.battle_manager.grid_start_x,
                self.battle_manager.grid_start_y,
                self.battle_manager.cell_size
            )

            # 显示伤害数字
            self.battle_manager.hit_feedback.show_damage(x, y, damage, is_crit)

            # 播放受击音效
            if hasattr(self.battle_manager, 'sound_system'):
                from core.sound_system import SoundPresets
                self.battle_manager.sound_system.play_sound(SoundPresets.ATTACK_HIT, volume=0.5)

    def is_alive(self) -> bool:
        return self.hp > 0

    def render(self, screen: pygame.Surface, font, grid_start_x: int, grid_start_y: int, cell_size: int):
        """渲染防守单位"""
        x, y = self.get_screen_pos(grid_start_x, grid_start_y, cell_size)

        # 绘制角色圆形（简化版）
        if self.animation_state == "attack":
            color = (255, 200, 100)  # 攻击时黄色
        else:
            color = (100, 200, 255)  # 空闲时蓝色

        pygame.draw.circle(screen, color, (x, y), cell_size // 3)
        pygame.draw.circle(screen, (255, 255, 255), (x, y), cell_size // 3, 2)

        # 绘制名字
        name_text = font.render(self.name[:2], True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(x, y))
        screen.blit(name_text, name_rect)

        # 绘制血条
        bar_width = cell_size
        bar_height = 5
        bar_x = x - bar_width // 2
        bar_y = y - cell_size // 2 - 10

        # 血条背景
        pygame.draw.rect(screen, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        # 血条前景
        hp_ratio = self.hp / self.max_hp
        pygame.draw.rect(screen, (0, 255, 0), (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))


class Enemy:
    """敌人单位"""

    def __init__(self, character_config: dict, lane: int, screen_width: int,
                 health_multiplier: float = 1.0, attack_interval: float = 2.0,
                 default_speed: int = 20, block_distance: int = 50, skill_manager: Optional[SkillManager] = None, battle_manager = None):
        self.character_id = character_config.get('character_id', 'unknown')
        self.name = character_config.get('name', '未知敌人')
        self.config = character_config
        self.battle_manager = battle_manager  # 保存战斗管理器引用

        # 位置（从右边进入）
        self.lane = lane
        self.x = screen_width + 50  # 从屏幕右侧开始

        # 属性
        stats = character_config.get('stats', {})
        self.max_hp = int(stats.get('hp', 100) * health_multiplier)
        self.hp = self.max_hp
        self.attack = stats.get('attack', 10)
        self.speed = stats.get('speed', default_speed)  # 从配置读取默认速度
        if self.speed == 0:  # 如果配置为0，使用默认速度
            self.speed = default_speed

        # 攻击类型和弹道配置
        self.attack_type = character_config.get('attack_type', 'melee')  # melee（近战）或 ranged（远程）
        self.projectile_config = character_config.get('projectile', {})  # 远程攻击的弹道配置

        # 攻击计时（从配置读取）
        self.attack_cooldown = 0
        self.attack_interval = attack_interval

        # 阻挡距离（从配置读取）
        self.block_distance = block_distance

        # 状态
        self.blocked_by: Optional[Defender] = None

        # 技能系统
        self.skills: List = []
        self.active_effects: List = []

        # 控制状态
        self.is_stunned = False  # 眩晕
        self.is_rooted = False  # 定身
        self.is_silenced = False  # 沉默
        self.is_disarmed = False  # 缴械
        self.is_feared = False  # 恐惧
        self.is_taunted = False  # 嘲讽
        self.is_airborne = False  # 击飞
        self.is_knocked_back = False  # 击退

        # 特殊状态
        self.is_invulnerable = False  # 无敌
        self.is_invisible = False  # 隐身
        self.is_boss = character_config.get('is_boss', False)  # Boss标记

        # 加载技能
        if skill_manager:
            self.skills = skill_manager.load_skills_for_character(character_config)

        # 应用被动特质的属性加成
        passive_traits_manager = PassiveTraitsManager()
        passive_traits_manager.apply_stat_bonuses(self)

    def update(self, delta_time: float, defenders: List[Defender], grid_start_x: int, cell_size: int, skill_manager: Optional[SkillManager] = None, battle_manager = None, projectile_manager = None):
        """更新敌人"""
        # 更新技能效果
        if skill_manager:
            skill_manager.update_unit_effects(self, delta_time)

        # 应用被动特质（如生命回复）
        if battle_manager and hasattr(battle_manager, 'passive_traits_manager'):
            battle_manager.passive_traits_manager.apply_passive_traits(self, delta_time, battle_manager)

        # 如果被眩晕或击飞，无法行动
        if self.is_stunned or self.is_airborne:
            return

        # 更新技能冷却
        for skill in self.skills:
            skill.update(delta_time)

        # 更新攻击冷却
        if self.attack_cooldown > 0:
            self.attack_cooldown -= delta_time

        # 自动施放技能（除非被沉默）
        if skill_manager and battle_manager and not self.is_silenced:
            skill_manager.auto_cast_skills(self, battle_manager)

        # 检查是否被阻挡（隐身的defender不能阻挡）
        self.blocked_by = None
        for defender in defenders:
            if defender.grid_y == self.lane and defender.is_alive() and not getattr(defender, 'is_invisible', False):
                defender_x = grid_start_x + defender.grid_x * cell_size + cell_size // 2
                if abs(self.x - defender_x) < self.block_distance:
                    self.blocked_by = defender
                    break

        # 如果被阻挡，攻击防守单位（除非被缴械）
        if self.blocked_by:
            if self.attack_cooldown <= 0 and not self.is_disarmed:
                if self.attack_type == 'ranged' and projectile_manager and battle_manager:
                    # 远程攻击：发射弹道
                    projectile_config = self.projectile_config.copy()
                    projectile_config['damage'] = self.attack
                    projectile_manager.create_projectile(self, self.blocked_by, projectile_config, battle_manager)
                    logger.debug(f"{self.name} 向 {self.blocked_by.name} 发射弹道")
                else:
                    # 近战攻击：直接造成伤害
                    self.blocked_by.take_damage(self.attack)
                    logger.debug(f"{self.name} 攻击 {self.blocked_by.name}，造成 {self.attack} 伤害")

                self.attack_cooldown = self.attack_interval

                # 触发攻击时的被动技能
                if skill_manager and battle_manager:
                    skill_manager.trigger_passive_skill(self, 'on_attack', battle_manager)
        else:
            # 移动逻辑
            if self.is_feared:
                # 恐惧状态：随机移动
                fear_direction = getattr(self, 'fear_direction', 1)
                self.x += self.speed * delta_time * fear_direction
            elif not self.is_rooted:
                # 正常前进（除非被定身）
                self.x -= self.speed * delta_time

    def take_damage(self, damage: int, is_crit: bool = False):
        """受到伤害"""
        # 无敌状态免疫所有伤害
        if getattr(self, 'is_invulnerable', False):
            return

        # 应用防御减免
        if hasattr(self, '_defense_multiplier'):
            damage = int(damage * self._defense_multiplier)

        self.hp -= damage
        if self.hp < 0:
            self.hp = 0

        # 显示伤害数字和音效
        if self.battle_manager and hasattr(self.battle_manager, 'hit_feedback'):
            # 获取Y坐标（Enemy直接有x, y属性）
            y_pos = getattr(self, 'y', 0)
            if y_pos == 0:
                # 如果没有y坐标，根据lane计算
                if hasattr(self.battle_manager, 'grid_start_y') and hasattr(self.battle_manager, 'cell_size'):
                    y_pos = self.battle_manager.grid_start_y + self.lane * self.battle_manager.cell_size + self.battle_manager.cell_size // 2

            # 显示伤害数字
            self.battle_manager.hit_feedback.show_damage(self.x, y_pos, damage, is_crit)

            # 创建命中粒子效果
            self.battle_manager.hit_feedback.create_hit_particles(self.x, y_pos, count=5)

            # 播放受击音效
            if hasattr(self.battle_manager, 'sound_system'):
                from core.sound_system import SoundPresets
                self.battle_manager.sound_system.play_sound(SoundPresets.ATTACK_HIT, volume=0.6)

    def is_alive(self) -> bool:
        return self.hp > 0

    def reached_base(self, base_x: int) -> bool:
        """是否到达基地"""
        return self.x <= base_x

    def get_screen_pos(self, grid_start_y: int, cell_size: int) -> Tuple[int, int]:
        """获取屏幕坐标"""
        y = grid_start_y + self.lane * cell_size + cell_size // 2
        return int(self.x), y

    def render(self, screen: pygame.Surface, font, grid_start_y: int, cell_size: int):
        """渲染敌人"""
        x, y = self.get_screen_pos(grid_start_y, cell_size)

        # 绘制敌人方形（简化版）
        size = cell_size // 3
        color = (255, 100, 100)  # 红色

        rect = pygame.Rect(x - size, y - size, size * 2, size * 2)
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2)

        # 绘制名字
        name_text = font.render(self.name[:2], True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(x, y))
        screen.blit(name_text, name_rect)

        # 绘制血条
        bar_width = size * 2
        bar_height = 5
        bar_x = x - bar_width // 2
        bar_y = y - size - 10

        # 血条背景
        pygame.draw.rect(screen, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        # 血条前景
        hp_ratio = self.hp / self.max_hp
        pygame.draw.rect(screen, (0, 255, 0), (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))


class BattleManager:
    """
    战斗管理器
    管理整个战斗流程：卡片、网格、单位、波次、资源
    """

    def __init__(self, config_loader, level_config: dict, settings: dict):
        self.config_loader = config_loader
        self.level_config = level_config
        self.settings = settings

        # 技能管理器
        self.skill_manager = SkillManager()

        # 弹道管理器
        self.projectile_manager = ProjectileManager()

        # 被动特质管理器
        self.passive_traits_manager = PassiveTraitsManager()

        # Boss管理器
        from core.boss_system import BossManager
        self.boss_manager = BossManager()

        # 音效系统
        from core.sound_system import get_sound_system
        self.sound_system = get_sound_system(settings)

        # 打击感反馈系统
        from core.hit_feedback_system import get_hit_feedback_system
        self.hit_feedback = get_hit_feedback_system()

        # 三级配置fallback：关卡配置 -> 全局配置 -> 硬编码默认值
        def get_config_value(level_key: str, global_section: str, config_key: str, default_value):
            """
            三级配置读取
            1. 优先从关卡配置读取
            2. 其次从全局配置读取
            3. 最后使用硬编码默认值
            """
            # 尝试从关卡配置读取
            level_section = level_config.get(level_key, {})
            if config_key in level_section:
                return level_section[config_key]

            # 尝试从全局配置读取
            global_config = settings.get('gameplay', {}).get(global_section, {})
            if config_key in global_config:
                return global_config[config_key]

            # 使用默认值
            return default_value

        # 战场网格配置（关卡可覆盖）
        self.grid_rows = get_config_value('battlefield', 'battlefield', 'grid_rows', 5)
        self.grid_cols = get_config_value('battlefield', 'battlefield', 'grid_cols', 9)
        self.cell_size = get_config_value('battlefield', 'battlefield', 'cell_size', 80)
        self.grid_start_x = get_config_value('battlefield', 'battlefield', 'grid_start_x', 100)
        self.grid_start_y = get_config_value('battlefield', 'battlefield', 'grid_start_y', 150)

        # 基地配置
        base_config = level_config.get('base', {})
        self.base_x = self.grid_start_x
        self.base_hp = base_config.get('initial_hp', 1000)
        self.base_max_hp = base_config.get('max_hp', 1000)

        # 经济系统配置（关卡可覆盖）
        self.gold = get_config_value('economy', 'economy', 'initial_gold', 200)
        self.gold_generation_rate = get_config_value('economy', 'economy', 'gold_generation_rate', 25)
        self.kill_reward = get_config_value('economy', 'economy', 'kill_reward', 25)
        self.gold_timer = 0

        # 战斗系统配置（关卡可覆盖）
        self.card_cooldown = get_config_value('battle_system', 'battle_system', 'card_cooldown', 5.0)
        self.enemy_attack_interval = get_config_value('battle_system', 'battle_system', 'enemy_attack_interval', 2.0)
        self.base_damage_multiplier = get_config_value('battle_system', 'battle_system', 'base_damage_multiplier', 10)
        self.block_distance = get_config_value('battle_system', 'battle_system', 'block_distance', 50)
        self.default_enemy_speed = get_config_value('battle_system', 'battle_system', 'default_enemy_speed', 20)

        # 卡片槽（可用角色）
        self.card_slots: List[dict] = []
        self.selected_card_index: Optional[int] = None

        # 网格占用情况
        self.grid: List[List[Optional[Defender]]] = [[None for _ in range(self.grid_cols)] for _ in range(self.grid_rows)]

        # 单位列表
        self.defenders: List[Defender] = []
        self.enemies: List[Enemy] = []

        # 波次管理
        self.waves = level_config.get('waves', [])
        self.current_wave_index = 0
        self.battle_time = 0
        self.all_waves_spawned = False

        # 游戏状态
        self.game_over = False
        self.victory = False

        # 玩家选择的角色列表（将由main.py设置）
        self.selected_characters: List[str] = []

        # 注意：不在这里初始化卡片槽，等待设置selected_characters后再初始化

        logger.info("战斗管理器初始化完成")

    def _init_card_slots(self):
        """初始化卡片槽（使用玩家选择的角色）"""
        if not self.selected_characters:
            logger.warning("未选择任何角色，加载所有防守方角色")
            # 如果没有选择角色，加载所有防守方角色
            for char_id, char_config in self.config_loader.characters.items():
                if char_config.get('type') == 'defender':
                    self.selected_characters.append(char_id)

        # 根据选择的角色创建卡片槽
        for char_id in self.selected_characters:
            char_config = self.config_loader.characters.get(char_id)
            if char_config:
                self.card_slots.append({
                    'character_id': char_id,
                    'name': char_config.get('name', char_id),
                    'cost': char_config.get('cost', 100),
                    'config': char_config,
                    'cooldown': 0,
                    'cooldown_max': self.card_cooldown  # 从配置读取
                })

        logger.info(f"加载了 {len(self.card_slots)} 个角色卡片")

    def update(self, delta_time: float, screen_width: int):
        """更新战斗状态"""
        if self.game_over:
            return

        self.battle_time += delta_time

        # 更新资源生成
        self.gold_timer += delta_time
        if self.gold_timer >= 1.0:
            self.gold += self.gold_generation_rate
            self.gold_timer = 0

        # 更新卡片冷却
        for card in self.card_slots:
            if card['cooldown'] > 0:
                card['cooldown'] -= delta_time

        # 生成波次
        self._spawn_waves(screen_width)

        # 更新弹道
        self.projectile_manager.update(delta_time)

        # 更新Boss系统
        self.boss_manager.update(delta_time)

        # 更新打击感反馈
        self.hit_feedback.update(delta_time)

        # 更新防守单位
        for defender in self.defenders[:]:
            defender.update(delta_time, self.enemies, self.skill_manager, self, self.projectile_manager)
            if not defender.is_alive():
                # 播放死亡音效和特效
                from core.sound_system import SoundPresets
                self.sound_system.play_sound(SoundPresets.UNIT_DEATH, volume=0.6)

                # 获取屏幕坐标
                x, y = defender.get_screen_pos(self.grid_start_x, self.grid_start_y, self.cell_size)
                self.hit_feedback.create_explosion_particles(x, y, count=15)

                self.defenders.remove(defender)
                self.grid[defender.grid_y][defender.grid_x] = None

        # 更新敌人
        for enemy in self.enemies[:]:
            enemy.update(delta_time, self.defenders, self.grid_start_x, self.cell_size, self.skill_manager, self, self.projectile_manager)

            # 检查是否死亡
            if not enemy.is_alive():
                # 播放死亡音效和特效
                from core.sound_system import SoundPresets

                # 判断是否是Boss
                if getattr(enemy, 'is_boss', False):
                    self.sound_system.play_sound(SoundPresets.BOSS_DEATH, volume=0.9)
                    # Boss死亡特效更强
                    y_pos = self.grid_start_y + enemy.lane * self.cell_size + self.cell_size // 2
                    self.hit_feedback.create_explosion_particles(enemy.x, y_pos, count=40)
                    self.hit_feedback.trigger_screen_shake(intensity=25, duration=0.6)
                else:
                    self.sound_system.play_sound(SoundPresets.UNIT_DEATH, volume=0.5)
                    y_pos = self.grid_start_y + enemy.lane * self.cell_size + self.cell_size // 2
                    self.hit_feedback.create_explosion_particles(enemy.x, y_pos, count=10)

                self.enemies.remove(enemy)
                self.gold += self.kill_reward  # 击杀奖励（从配置读取）

            # 检查是否到达基地
            elif enemy.reached_base(self.base_x):
                damage = enemy.attack * self.base_damage_multiplier
                self.base_hp -= damage
                self.enemies.remove(enemy)
                logger.info(f"敌人突破！基地受到 {damage} 伤害")

        # 检查胜利/失败
        self._check_game_over()

    def _spawn_waves(self, screen_width: int):
        """生成敌人波次"""
        if self.all_waves_spawned:
            return

        for i, wave in enumerate(self.waves[self.current_wave_index:], self.current_wave_index):
            wave_time = wave.get('time', 0)

            if self.battle_time >= wave_time:
                # 生成这一波敌人
                enemies_config = wave.get('enemies', [])
                for enemy_group in enemies_config:
                    char_id = enemy_group.get('character')
                    count = enemy_group.get('count', 1)
                    health_mult = enemy_group.get('health_multiplier', 1.0)
                    is_boss = enemy_group.get('is_boss', False)  # 标记为Boss

                    # 获取角色配置（如果是Boss，从bosses目录读取）
                    if is_boss:
                        # 尝试从config_loader的bosses字典获取
                        char_config = self.config_loader.get_boss_config(char_id) if hasattr(self.config_loader, 'get_boss_config') else None
                        if not char_config:
                            logger.warning(f"找不到Boss配置: {char_id}")
                            continue
                    else:
                        char_config = self.config_loader.characters.get(char_id)

                    if char_config:
                        for j in range(count):
                            lane = j % self.grid_rows  # 随机分配行
                            enemy = Enemy(
                                char_config, lane, screen_width,
                                health_mult,
                                self.enemy_attack_interval,
                                self.default_enemy_speed,
                                self.block_distance,
                                self.skill_manager,
                                self  # 传递battle_manager引用
                            )
                            self.enemies.append(enemy)

                            # 如果是Boss，创建BossUnit包装
                            if is_boss:
                                boss_unit = self.boss_manager.create_boss(char_config, enemy, self)
                                logger.info(f"生成Boss: {boss_unit.boss_name}")

                                # 播放Boss出现音效和特效
                                from core.sound_system import SoundPresets
                                self.sound_system.play_sound(SoundPresets.BOSS_APPEAR, volume=0.9)
                                self.hit_feedback.trigger_screen_shake(intensity=20, duration=0.5)

                logger.info(f"生成波次 {i + 1}")
                self.current_wave_index = i + 1

                if self.current_wave_index >= len(self.waves):
                    self.all_waves_spawned = True
                    break

    def _check_game_over(self):
        """检查游戏结束条件"""
        # 失败：基地血量为0
        if self.base_hp <= 0:
            if not self.game_over:  # 只在第一次触发时播放
                from core.sound_system import SoundPresets
                self.sound_system.play_sound(SoundPresets.DEFEAT, volume=0.8)
                self.hit_feedback.trigger_screen_shake(intensity=30, duration=1.0)

            self.game_over = True
            self.victory = False
            logger.info("游戏失败：基地被摧毁")

        # 胜利：所有波次生成且所有敌人被消灭
        if self.all_waves_spawned and len(self.enemies) == 0:
            if not self.game_over:  # 只在第一次触发时播放
                from core.sound_system import SoundPresets
                self.sound_system.play_sound(SoundPresets.VICTORY, volume=0.8)

            self.game_over = True
            self.victory = True
            logger.info("游戏胜利：击退所有敌人")

    def place_defender(self, grid_x: int, grid_y: int) -> bool:
        """放置防守单位"""
        # 检查是否选择了卡片
        if self.selected_card_index is None:
            return False

        card = self.card_slots[self.selected_card_index]

        # 检查金币是否足够
        if self.gold < card['cost']:
            logger.debug("金币不足")
            return False

        # 检查冷却
        if card['cooldown'] > 0:
            logger.debug("卡片冷却中")
            return False

        # 检查网格是否可用
        if grid_x < 0 or grid_x >= self.grid_cols or grid_y < 0 or grid_y >= self.grid_rows:
            return False

        if self.grid[grid_y][grid_x] is not None:
            logger.debug("该位置已有单位")
            return False

        # 创建防守单位
        defender = Defender(card['config'], grid_x, grid_y, self.cell_size, self.skill_manager, self)
        self.defenders.append(defender)
        self.grid[grid_y][grid_x] = defender

        # 扣除金币，设置冷却
        self.gold -= card['cost']
        card['cooldown'] = card['cooldown_max']

        logger.info(f"放置 {defender.name} 在 ({grid_x}, {grid_y})")
        return True

    def render(self, screen: pygame.Surface, fonts: dict):
        """渲染战斗界面"""
        # 绘制网格
        self._render_grid(screen)

        # 绘制防守单位
        for defender in self.defenders:
            defender.render(screen, fonts['small'], self.grid_start_x, self.grid_start_y, self.cell_size)

        # 绘制敌人
        for enemy in self.enemies:
            enemy.render(screen, fonts['small'], self.grid_start_y, self.cell_size)

        # 绘制弹道
        self.projectile_manager.render(screen)

        # 绘制打击感反馈效果（伤害数字、粒子等）
        self.hit_feedback.render(screen)

        # 绘制卡片槽
        self._render_card_slots(screen, fonts)

        # 绘制UI信息
        self._render_ui(screen, fonts)

    def _render_grid(self, screen: pygame.Surface):
        """渲染网格"""
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                x = self.grid_start_x + col * self.cell_size
                y = self.grid_start_y + row * self.cell_size

                # 绘制网格线
                color = (60, 80, 60) if (row + col) % 2 == 0 else (50, 70, 50)
                pygame.draw.rect(screen, color, (x, y, self.cell_size, self.cell_size))
                pygame.draw.rect(screen, (80, 100, 80), (x, y, self.cell_size, self.cell_size), 1)

    def _render_card_slots(self, screen: pygame.Surface, fonts: dict):
        """渲染卡片槽（参考植物大战僵尸，在顶部显示）"""
        card_width = 80
        card_height = 100
        card_spacing = 10
        start_x = 250  # 从左边留出空间显示资源信息
        start_y = 20  # 顶部20像素开始

        for i, card in enumerate(self.card_slots):
            x = start_x + i * (card_width + card_spacing)
            y = start_y

            # 判断是否可用
            can_afford = self.gold >= card['cost']
            is_ready = card['cooldown'] <= 0
            is_selected = i == self.selected_card_index

            # 绘制卡片背景
            if is_selected:
                color = (100, 150, 255)
            elif can_afford and is_ready:
                color = (80, 120, 80)
            else:
                color = (60, 60, 60)

            pygame.draw.rect(screen, color, (x, y, card_width, card_height))
            pygame.draw.rect(screen, (200, 200, 200), (x, y, card_width, card_height), 2)

            # 绘制角色名
            name_text = fonts['small'].render(card['name'][:4], True, (255, 255, 255))
            name_rect = name_text.get_rect(center=(x + card_width // 2, y + 30))
            screen.blit(name_text, name_rect)

            # 绘制费用
            cost_text = fonts['small'].render(f"{card['cost']}", True, (255, 200, 50))
            cost_rect = cost_text.get_rect(center=(x + card_width // 2, y + 60))
            screen.blit(cost_text, cost_rect)

            # 绘制冷却
            if card['cooldown'] > 0:
                cooldown_text = fonts['small'].render(f"{card['cooldown']:.1f}s", True, (255, 100, 100))
                cooldown_rect = cooldown_text.get_rect(center=(x + card_width // 2, y + 85))
                screen.blit(cooldown_text, cooldown_rect)

    def _render_ui(self, screen: pygame.Surface, fonts: dict):
        """渲染UI信息（调整布局避免重叠）"""
        # 基地血量 - 紧凑显示在左上角
        hp_text = fonts['small'].render(f"基地: {max(0, self.base_hp)}/{self.base_max_hp}", True, (255, 100, 100))
        screen.blit(hp_text, (20, 30))

        # 金币 - 在基地血量下方
        gold_text = fonts['small'].render(f"金币: {self.gold}", True, (255, 200, 50))
        screen.blit(gold_text, (20, 65))

        # 金币生成提示 - 在金币下方
        gold_gen_text = fonts['small'].render(f"+{self.gold_generation_rate}/秒", True, (180, 150, 50))
        screen.blit(gold_gen_text, (20, 95))

        # 波次信息 - 右上角，避开菜单按钮
        wave_text = fonts['small'].render(
            f"波次: {self.current_wave_index}/{len(self.waves)}",
            True,
            (200, 200, 200)
        )
        screen.blit(wave_text, (screen.get_width() - 200, 30))

        # 敌人数量 - 在波次下方
        enemy_text = fonts['small'].render(
            f"敌人: {len(self.enemies)}",
            True,
            (255, 150, 150)
        )
        screen.blit(enemy_text, (screen.get_width() - 200, 55))

    def create_particle_effect(self, effect_type: str, target):
        """
        创建粒子特效（占位方法，将在打击感反馈系统中实现）

        参数:
            effect_type: 特效类型
            target: 目标单位
        """
        # TODO: 在打击感反馈系统中实现
        pass

    def create_aoe_effect(self, effect_type: str, center_pos: Tuple[int, int], radius: float):
        """
        创建范围特效（占位方法，将在打击感反馈系统中实现）

        参数:
            effect_type: 特效类型
            center_pos: 中心位置
            radius: 范围半径
        """
        # TODO: 在打击感反馈系统中实现
        pass

    def handle_click(self, mouse_x: int, mouse_y: int, screen_height: int):
        """处理鼠标点击"""
        # 检查是否点击卡片槽（顶部位置）
        card_width = 80
        card_height = 100
        card_spacing = 10
        start_x = 250  # 与渲染保持一致
        start_y = 20  # 与渲染保持一致

        for i, card in enumerate(self.card_slots):
            x = start_x + i * (card_width + card_spacing)
            y = start_y

            if x <= mouse_x <= x + card_width and y <= mouse_y <= y + card_height:
                # 检查是否可选
                if self.gold >= card['cost'] and card['cooldown'] <= 0:
                    self.selected_card_index = i if self.selected_card_index != i else None
                    logger.debug(f"选择卡片: {card['name']}")
                return

        # 检查是否点击网格
        if self.selected_card_index is not None:
            grid_x = (mouse_x - self.grid_start_x) // self.cell_size
            grid_y = (mouse_y - self.grid_start_y) // self.cell_size

            if 0 <= grid_x < self.grid_cols and 0 <= grid_y < self.grid_rows:
                if self.place_defender(grid_x, grid_y):
                    self.selected_card_index = None  # 放置后取消选择
