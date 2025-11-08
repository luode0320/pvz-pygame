"""
技能系统 - 处理所有技能相关逻辑
包括：主动技能、被动技能、AOE技能、召唤技能、增益/减益效果
"""

import pygame
import logging
import math
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from core.battle_manager import Defender, Enemy, BattleManager

logger = logging.getLogger(__name__)


class SkillEffect:
    """技能效果（增益/减益）"""

    def __init__(self, effect_type: str, value: float, duration: float):
        """
        effect_type: 效果类型 (attack_boost, defense_boost, speed_boost, slow, stun, poison, etc.)
        value: 效果数值 (可以是百分比或绝对值)
        duration: 持续时间（秒）
        """
        self.effect_type = effect_type
        self.value = value
        self.duration = duration
        self.remaining_time = duration

    def update(self, delta_time: float) -> bool:
        """更新效果，返回是否还有效"""
        self.remaining_time -= delta_time
        return self.remaining_time > 0

    def apply_to_unit(self, unit):
        """应用效果到单位"""
        # === 增益效果 ===
        if self.effect_type == "attack_boost":
            # 攻击力提升（百分比）
            if not hasattr(unit, '_original_attack'):
                unit._original_attack = unit.attack
            unit.attack = int(unit._original_attack * (1 + self.value))

        elif self.effect_type == "defense_boost":
            # 防御提升（减少受到的伤害）
            if not hasattr(unit, '_defense_multiplier'):
                unit._defense_multiplier = 1.0
            unit._defense_multiplier = 1.0 - self.value

        elif self.effect_type == "speed_boost":
            # 攻速提升（只对防守方有效）
            if hasattr(unit, 'attack_speed') and not hasattr(unit, '_original_attack_speed'):
                unit._original_attack_speed = unit.attack_speed
                unit.attack_speed = unit._original_attack_speed * (1 + self.value)
                unit.attack_interval = 1.0 / unit.attack_speed

        elif self.effect_type == "movement_speed_boost":
            # 移速提升（百分比）
            if hasattr(unit, 'speed') and not hasattr(unit, '_original_move_speed'):
                unit._original_move_speed = unit.speed
            if hasattr(unit, 'speed'):
                unit.speed = unit._original_move_speed * (1 + self.value)

        elif self.effect_type == "invulnerable":
            # 无敌（免疫所有伤害）
            unit.is_invulnerable = True

        elif self.effect_type == "invisible":
            # 隐身（敌人无法选中）
            unit.is_invisible = True

        # === 减益效果 ===
        elif self.effect_type == "slow":
            # 减速（对敌人有效）
            if hasattr(unit, 'speed') and not hasattr(unit, '_original_speed'):
                unit._original_speed = unit.speed
            if hasattr(unit, 'speed'):
                unit.speed = unit._original_speed * (1 - self.value)

        elif self.effect_type == "stun":
            # 眩晕（停止移动和攻击）
            unit.is_stunned = True

        elif self.effect_type == "root":
            # 定身（无法移动，但可以攻击）
            unit.is_rooted = True

        elif self.effect_type == "silence":
            # 沉默（无法使用技能）
            unit.is_silenced = True

        elif self.effect_type == "disarm":
            # 缴械（无法普通攻击）
            unit.is_disarmed = True

        elif self.effect_type == "blind":
            # 致盲（降低命中率）
            if not hasattr(unit, '_miss_chance'):
                unit._miss_chance = 0
            unit._miss_chance = self.value  # value为miss概率，如0.5=50%miss

        elif self.effect_type == "fear":
            # 恐惧（失去控制，随机移动）
            unit.is_feared = True
            if hasattr(unit, 'speed'):
                unit.fear_direction = 1 if unit.x % 2 == 0 else -1  # 随机方向

        elif self.effect_type == "taunt":
            # 嘲讽（强制攻击施法者）
            unit.is_taunted = True
            if hasattr(self, 'caster'):
                unit.taunt_target = self.caster

        elif self.effect_type == "knockback":
            # 击退（瞬间位移）
            unit.is_knocked_back = True
            unit.knockback_distance = self.value  # value为击退距离
            unit.knockback_speed = 200  # 击退速度

        elif self.effect_type == "knockup":
            # 击飞（无法行动，特殊状态）
            unit.is_airborne = True
            unit.knockup_height = self.value  # value为击飞高度（用于渲染）

        # === 持续伤害效果 ===
        elif self.effect_type == "poison":
            # 中毒（持续伤害）
            if not hasattr(unit, '_poison_damage'):
                unit._poison_damage = 0
            unit._poison_damage = self.value

        elif self.effect_type == "burn":
            # 燃烧（持续伤害，通常伤害更高）
            if not hasattr(unit, '_burn_damage'):
                unit._burn_damage = 0
            unit._burn_damage = self.value

        elif self.effect_type == "bleed":
            # 流血（持续伤害，移动时伤害加倍）
            if not hasattr(unit, '_bleed_damage'):
                unit._bleed_damage = 0
            unit._bleed_damage = self.value

    def remove_from_unit(self, unit):
        """从单位移除效果"""
        # === 增益效果移除 ===
        if self.effect_type == "attack_boost":
            if hasattr(unit, '_original_attack'):
                unit.attack = unit._original_attack
                delattr(unit, '_original_attack')

        elif self.effect_type == "defense_boost":
            if hasattr(unit, '_defense_multiplier'):
                unit._defense_multiplier = 1.0

        elif self.effect_type == "speed_boost":
            if hasattr(unit, '_original_attack_speed'):
                unit.attack_speed = unit._original_attack_speed
                unit.attack_interval = 1.0 / unit.attack_speed
                delattr(unit, '_original_attack_speed')

        elif self.effect_type == "movement_speed_boost":
            if hasattr(unit, '_original_move_speed'):
                unit.speed = unit._original_move_speed
                delattr(unit, '_original_move_speed')

        elif self.effect_type == "invulnerable":
            unit.is_invulnerable = False

        elif self.effect_type == "invisible":
            unit.is_invisible = False

        # === 减益效果移除 ===
        elif self.effect_type == "slow":
            if hasattr(unit, '_original_speed'):
                unit.speed = unit._original_speed
                delattr(unit, '_original_speed')

        elif self.effect_type == "stun":
            unit.is_stunned = False

        elif self.effect_type == "root":
            unit.is_rooted = False

        elif self.effect_type == "silence":
            unit.is_silenced = False

        elif self.effect_type == "disarm":
            unit.is_disarmed = False

        elif self.effect_type == "blind":
            if hasattr(unit, '_miss_chance'):
                unit._miss_chance = 0

        elif self.effect_type == "fear":
            unit.is_feared = False
            if hasattr(unit, 'fear_direction'):
                delattr(unit, 'fear_direction')

        elif self.effect_type == "taunt":
            unit.is_taunted = False
            if hasattr(unit, 'taunt_target'):
                delattr(unit, 'taunt_target')

        elif self.effect_type == "knockback":
            unit.is_knocked_back = False
            if hasattr(unit, 'knockback_distance'):
                delattr(unit, 'knockback_distance')
            if hasattr(unit, 'knockback_speed'):
                delattr(unit, 'knockback_speed')

        elif self.effect_type == "knockup":
            unit.is_airborne = False
            if hasattr(unit, 'knockup_height'):
                delattr(unit, 'knockup_height')

        # === 持续伤害效果移除 ===
        elif self.effect_type == "poison":
            if hasattr(unit, '_poison_damage'):
                unit._poison_damage = 0

        elif self.effect_type == "burn":
            if hasattr(unit, '_burn_damage'):
                unit._burn_damage = 0

        elif self.effect_type == "bleed":
            if hasattr(unit, '_bleed_damage'):
                unit._bleed_damage = 0


class Skill(ABC):
    """技能基类"""

    def __init__(self, skill_config: dict):
        self.skill_id = skill_config.get('skill_id', 'unknown')
        self.name = skill_config.get('name', '未知技能')
        self.description = skill_config.get('description', '')
        self.skill_type = skill_config.get('type', 'active')  # active, passive, auto
        self.cooldown = skill_config.get('cooldown', 5.0)
        self.cooldown_remaining = 0

        # 技能参数
        self.damage = skill_config.get('damage', 0)
        self.range = skill_config.get('range', 100)
        self.aoe_radius = skill_config.get('aoe_radius', 0)  # AOE范围，0表示单体
        self.target_type = skill_config.get('target_type', 'enemy')  # enemy, ally, self, all
        self.max_targets = skill_config.get('max_targets', 1)  # 最大目标数

        # 效果列表
        effects_config = skill_config.get('effects', [])
        self.effects: List[Dict] = effects_config

        # 动画和特效
        self.animation_duration = skill_config.get('animation_duration', 0.3)
        self.particle_effect = skill_config.get('particle_effect', None)

        # 被动技能触发条件
        self.trigger_condition = skill_config.get('trigger_condition', None)  # on_attack, on_hit, on_low_hp, etc.
        self.trigger_chance = skill_config.get('trigger_chance', 1.0)  # 触发概率

        # 技能攻击类型（melee近战 或 ranged远程）
        self.attack_type = skill_config.get('attack_type', 'instant')  # instant（瞬发）, melee（近战）, ranged（远程）
        self.projectile_config = skill_config.get('projectile', {})  # 远程技能的弹道配置

        # 前提条件系统（Prerequisite System）
        prerequisites_config = skill_config.get('prerequisites', {})
        self.prerequisites = {
            # 施法者条件
            'caster_min_hp_percent': prerequisites_config.get('caster_min_hp_percent', 0),  # 施法者最低血量百分比
            'caster_max_hp_percent': prerequisites_config.get('caster_max_hp_percent', 1.0),  # 施法者最高血量百分比
            'caster_has_effects': prerequisites_config.get('caster_has_effects', []),  # 施法者必须有的效果
            'caster_not_has_effects': prerequisites_config.get('caster_not_has_effects', []),  # 施法者不能有的效果

            # 目标条件
            'target_states': prerequisites_config.get('target_states', []),  # 目标必须处于的状态（如airborne, stunned）
            'target_not_states': prerequisites_config.get('target_not_states', []),  # 目标不能处于的状态
            'target_min_hp_percent': prerequisites_config.get('target_min_hp_percent', 0),  # 目标最低血量百分比
            'target_max_hp_percent': prerequisites_config.get('target_max_hp_percent', 1.0),  # 目标最高血量百分比
            'target_has_effects': prerequisites_config.get('target_has_effects', []),  # 目标必须有的效果
            'target_not_has_effects': prerequisites_config.get('target_not_has_effects', []),  # 目标不能有的效果

            # 环境条件
            'min_nearby_enemies': prerequisites_config.get('min_nearby_enemies', 0),  # 附近最少敌人数
            'min_nearby_allies': prerequisites_config.get('min_nearby_allies', 0),  # 附近最少友军数
        }

    def update(self, delta_time: float):
        """更新技能冷却"""
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= delta_time

    def can_use(self, caster=None, target=None, battle_manager=None) -> bool:
        """检查技能是否可用（包括冷却和前提条件）"""
        # 检查冷却
        if self.cooldown_remaining > 0:
            return False

        # 检查前提条件
        if caster and not self._check_prerequisites(caster, target, battle_manager):
            return False

        return True

    def _check_prerequisites(self, caster, target, battle_manager) -> bool:
        """检查前提条件是否满足"""
        prereq = self.prerequisites

        # === 检查施法者条件 ===
        if caster:
            # 检查施法者血量百分比
            hp_percent = caster.hp / caster.max_hp
            if hp_percent < prereq['caster_min_hp_percent'] or hp_percent > prereq['caster_max_hp_percent']:
                return False

            # 检查施法者必须有的效果
            if prereq['caster_has_effects']:
                caster_effect_types = [e.effect_type for e in getattr(caster, 'active_effects', [])]
                for required_effect in prereq['caster_has_effects']:
                    if required_effect not in caster_effect_types:
                        return False

            # 检查施法者不能有的效果
            if prereq['caster_not_has_effects']:
                caster_effect_types = [e.effect_type for e in getattr(caster, 'active_effects', [])]
                for forbidden_effect in prereq['caster_not_has_effects']:
                    if forbidden_effect in caster_effect_types:
                        return False

        # === 检查目标条件 ===
        if target:
            # 检查目标必须处于的状态
            if prereq['target_states']:
                for required_state in prereq['target_states']:
                    state_attr = f'is_{required_state}'
                    if not getattr(target, state_attr, False):
                        return False

            # 检查目标不能处于的状态
            if prereq['target_not_states']:
                for forbidden_state in prereq['target_not_states']:
                    state_attr = f'is_{forbidden_state}'
                    if getattr(target, state_attr, False):
                        return False

            # 检查目标血量百分比
            if hasattr(target, 'hp') and hasattr(target, 'max_hp'):
                hp_percent = target.hp / target.max_hp
                if hp_percent < prereq['target_min_hp_percent'] or hp_percent > prereq['target_max_hp_percent']:
                    return False

            # 检查目标必须有的效果
            if prereq['target_has_effects']:
                target_effect_types = [e.effect_type for e in getattr(target, 'active_effects', [])]
                for required_effect in prereq['target_has_effects']:
                    if required_effect not in target_effect_types:
                        return False

            # 检查目标不能有的效果
            if prereq['target_not_has_effects']:
                target_effect_types = [e.effect_type for e in getattr(target, 'active_effects', [])]
                for forbidden_effect in prereq['target_not_has_effects']:
                    if forbidden_effect in target_effect_types:
                        return False

        # === 检查环境条件 ===
        if battle_manager and caster:
            # 检查附近敌人数量
            if prereq['min_nearby_enemies'] > 0:
                caster_pos = self._get_unit_position(caster, battle_manager)
                if caster_pos:
                    enemies = battle_manager.enemies if hasattr(caster, 'grid_x') else battle_manager.defenders
                    nearby_count = 0
                    for enemy in enemies:
                        enemy_pos = self._get_unit_position(enemy, battle_manager)
                        if enemy_pos:
                            distance = math.sqrt((caster_pos[0] - enemy_pos[0])**2 + (caster_pos[1] - enemy_pos[1])**2)
                            if distance <= self.range:
                                nearby_count += 1
                    if nearby_count < prereq['min_nearby_enemies']:
                        return False

            # 检查附近友军数量
            if prereq['min_nearby_allies'] > 0:
                caster_pos = self._get_unit_position(caster, battle_manager)
                if caster_pos:
                    allies = battle_manager.defenders if hasattr(caster, 'grid_x') else battle_manager.enemies
                    nearby_count = 0
                    for ally in allies:
                        if ally == caster:
                            continue
                        ally_pos = self._get_unit_position(ally, battle_manager)
                        if ally_pos:
                            distance = math.sqrt((caster_pos[0] - ally_pos[0])**2 + (caster_pos[1] - ally_pos[1])**2)
                            if distance <= self.range:
                                nearby_count += 1
                    if nearby_count < prereq['min_nearby_allies']:
                        return False

        return True

    def start_cooldown(self):
        """开始冷却"""
        self.cooldown_remaining = self.cooldown

    @abstractmethod
    def use(self, caster, targets: List, battle_manager: 'BattleManager') -> bool:
        """使用技能，返回是否成功"""
        pass

    def find_targets(self, caster, all_units: List, battle_manager: 'BattleManager') -> List:
        """查找技能目标"""
        targets = []
        caster_pos = self._get_unit_position(caster, battle_manager)

        if caster_pos is None:
            return targets

        for unit in all_units:
            if not self._is_valid_target(unit, caster):
                continue

            unit_pos = self._get_unit_position(unit, battle_manager)
            if unit_pos is None:
                continue

            distance = math.sqrt((caster_pos[0] - unit_pos[0])**2 + (caster_pos[1] - unit_pos[1])**2)

            if distance <= self.range:
                targets.append((unit, distance))

        # 按距离排序，取最近的目标
        targets.sort(key=lambda x: x[1])
        targets = [t[0] for t in targets[:self.max_targets]]

        return targets

    def _is_valid_target(self, unit, caster) -> bool:
        """检查是否是有效目标"""
        if not unit.is_alive():
            return False

        if self.target_type == 'enemy':
            # 如果施法者是防守方，目标应该是敌人
            return type(unit).__name__ != type(caster).__name__
        elif self.target_type == 'ally':
            # 同类单位
            return type(unit).__name__ == type(caster).__name__
        elif self.target_type == 'self':
            return unit == caster
        elif self.target_type == 'all':
            return True

        return False

    def _get_unit_position(self, unit, battle_manager: 'BattleManager') -> Optional[Tuple[int, int]]:
        """获取单位的屏幕坐标"""
        if hasattr(unit, 'get_screen_pos'):
            if hasattr(unit, 'grid_x'):  # Defender
                return unit.get_screen_pos(battle_manager.grid_start_x, battle_manager.grid_start_y, battle_manager.cell_size)
            else:  # Enemy
                return unit.get_screen_pos(battle_manager.grid_start_y, battle_manager.cell_size)
        return None

    def _apply_effects(self, target, caster):
        """应用技能效果到目标"""
        for effect_config in self.effects:
            effect = SkillEffect(
                effect_config.get('type'),
                effect_config.get('value', 0),
                effect_config.get('duration', 3.0)
            )

            # 添加效果到目标
            if not hasattr(target, 'active_effects'):
                target.active_effects = []
            target.active_effects.append(effect)
            effect.apply_to_unit(target)

            logger.debug(f"{self.name} 对 {target.name} 施加效果: {effect.effect_type}")


class DamageSkill(Skill):
    """伤害技能"""

    def use(self, caster, targets: List, battle_manager: 'BattleManager') -> bool:
        """造成伤害"""
        if not self.can_use(caster, None, battle_manager):
            return False

        # 如果没有指定目标，自动查找
        if not targets:
            all_units = battle_manager.enemies if hasattr(caster, 'grid_x') else battle_manager.defenders
            targets = self.find_targets(caster, all_units, battle_manager)

        if not targets:
            return False

        # 如果是远程技能，发射弹道
        if self.attack_type == 'ranged' and hasattr(battle_manager, 'projectile_manager'):
            for target in targets:
                # 创建技能弹道配置
                projectile_config = self.projectile_config.copy()
                projectile_config['damage'] = self.damage
                projectile_config['on_hit_effects'] = self.effects  # 将技能效果传递给弹道
                projectile_config['skill_name'] = self.name  # 用于日志

                # 创建弹道
                battle_manager.projectile_manager.create_projectile(
                    caster, target, projectile_config, battle_manager
                )
                logger.debug(f"{caster.name} 使用技能 {self.name} 向 {target.name} 发射弹道")

        else:
            # 瞬发技能或近战技能：直接造成伤害
            for target in targets:
                damage = self.damage

                # 应用防御减免
                if hasattr(target, '_defense_multiplier'):
                    damage = int(damage * target._defense_multiplier)

                target.take_damage(damage)
                logger.debug(f"{caster.name} 使用 {self.name} 对 {target.name} 造成 {damage} 伤害")

                # 应用附加效果
                self._apply_effects(target, caster)

                # 创建伤害特效
                if self.particle_effect:
                    battle_manager.create_particle_effect(self.particle_effect, target)

        self.start_cooldown()
        return True


class AOESkill(Skill):
    """范围伤害技能"""

    def use(self, caster, targets: List, battle_manager: 'BattleManager') -> bool:
        """范围伤害"""
        if not self.can_use(caster, None, battle_manager):
            return False

        # AOE技能需要一个中心点目标
        if not targets:
            all_units = battle_manager.enemies if hasattr(caster, 'grid_x') else battle_manager.defenders
            targets = self.find_targets(caster, all_units, battle_manager)

        if not targets:
            return False

        center_target = targets[0]

        # 如果是远程AOE技能，发射弹道
        if self.attack_type == 'ranged' and hasattr(battle_manager, 'projectile_manager'):
            # 创建AOE技能弹道配置
            projectile_config = self.projectile_config.copy()
            projectile_config['damage'] = self.damage
            projectile_config['splash_radius'] = self.aoe_radius  # AOE范围
            projectile_config['on_hit_effects'] = self.effects  # 将技能效果传递给弹道
            projectile_config['skill_name'] = self.name

            # 创建弹道
            battle_manager.projectile_manager.create_projectile(
                caster, center_target, projectile_config, battle_manager
            )
            logger.debug(f"{caster.name} 使用AOE技能 {self.name} 向 {center_target.name} 发射弹道")

        else:
            # 瞬发AOE技能：直接造成范围伤害
            center_pos = self._get_unit_position(center_target, battle_manager)

            if center_pos is None:
                return False

            # 查找范围内的所有单位
            all_units = battle_manager.enemies if hasattr(caster, 'grid_x') else battle_manager.defenders
            affected_units = []

            for unit in all_units:
                if not self._is_valid_target(unit, caster):
                    continue

                unit_pos = self._get_unit_position(unit, battle_manager)
                if unit_pos is None:
                    continue

                distance = math.sqrt((center_pos[0] - unit_pos[0])**2 + (center_pos[1] - unit_pos[1])**2)

                if distance <= self.aoe_radius:
                    affected_units.append(unit)

            # 对范围内所有单位造成伤害
            for unit in affected_units:
                damage = self.damage

                # 应用防御减免
                if hasattr(unit, '_defense_multiplier'):
                    damage = int(damage * unit._defense_multiplier)

                unit.take_damage(damage)
                logger.debug(f"{caster.name} 使用 {self.name} (AOE) 对 {unit.name} 造成 {damage} 伤害")

                # 应用附加效果
                self._apply_effects(unit, caster)

            # 创建AOE特效
            if self.particle_effect and affected_units:
                battle_manager.create_aoe_effect(self.particle_effect, center_pos, self.aoe_radius)

        self.start_cooldown()
        return True


class HealSkill(Skill):
    """治疗技能"""

    def use(self, caster, targets: List, battle_manager: 'BattleManager') -> bool:
        """治疗"""
        if not self.can_use(caster, None, battle_manager):
            return False

        # 查找需要治疗的友军
        if not targets:
            all_allies = battle_manager.defenders if hasattr(caster, 'grid_x') else battle_manager.enemies
            # 优先治疗血量最低的
            injured_allies = [unit for unit in all_allies if unit.is_alive() and unit.hp < unit.max_hp]
            injured_allies.sort(key=lambda x: x.hp / x.max_hp)
            targets = injured_allies[:self.max_targets]

        if not targets:
            return False

        for target in targets:
            heal_amount = self.damage  # 使用damage字段表示治疗量
            target.hp = min(target.hp + heal_amount, target.max_hp)
            logger.debug(f"{caster.name} 使用 {self.name} 治疗 {target.name} {heal_amount} 生命值")

            # 应用附加效果
            self._apply_effects(target, caster)

        self.start_cooldown()
        return True


class SummonSkill(Skill):
    """召唤技能"""

    def __init__(self, skill_config: dict):
        super().__init__(skill_config)
        self.summon_character_id = skill_config.get('summon_character_id', None)
        self.summon_count = skill_config.get('summon_count', 1)
        self.summon_duration = skill_config.get('summon_duration', 0)  # 0表示永久

    def use(self, caster, targets: List, battle_manager: 'BattleManager') -> bool:
        """召唤单位"""
        if not self.can_use(caster, None, battle_manager):
            return False

        if not self.summon_character_id:
            return False

        # 获取召唤物配置
        summon_config = battle_manager.config_loader.characters.get(self.summon_character_id)
        if not summon_config:
            logger.warning(f"找不到召唤物配置: {self.summon_character_id}")
            return False

        # 在施法者附近召唤单位
        if hasattr(caster, 'grid_x'):  # 防守方召唤
            from core.battle_manager import Defender

            # 在施法者周围找空位
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue

                    grid_x = caster.grid_x + dx
                    grid_y = caster.grid_y + dy

                    if (0 <= grid_x < battle_manager.grid_cols and
                        0 <= grid_y < battle_manager.grid_rows and
                        battle_manager.grid[grid_y][grid_x] is None):

                        # 创建召唤物
                        summon = Defender(summon_config, grid_x, grid_y, battle_manager.cell_size)
                        summon.is_summoned = True
                        if self.summon_duration > 0:
                            summon.summon_timer = self.summon_duration

                        battle_manager.defenders.append(summon)
                        battle_manager.grid[grid_y][grid_x] = summon

                        logger.info(f"{caster.name} 召唤了 {summon.name} 在 ({grid_x}, {grid_y})")
                        break

        self.start_cooldown()
        return True


class BuffSkill(Skill):
    """增益技能"""

    def use(self, caster, targets: List, battle_manager: 'BattleManager') -> bool:
        """施加增益"""
        if not self.can_use(caster, None, battle_manager):
            return False

        # 查找友军
        if not targets:
            all_allies = battle_manager.defenders if hasattr(caster, 'grid_x') else battle_manager.enemies
            targets = self.find_targets(caster, all_allies, battle_manager)

        if not targets:
            # 如果没有其他目标，对自己施加
            targets = [caster]

        for target in targets:
            # 应用增益效果
            self._apply_effects(target, caster)
            logger.debug(f"{caster.name} 对 {target.name} 施加增益: {self.name}")

        self.start_cooldown()
        return True


class DebuffSkill(Skill):
    """减益技能"""

    def use(self, caster, targets: List, battle_manager: 'BattleManager') -> bool:
        """施加减益"""
        if not self.can_use(caster, None, battle_manager):
            return False

        # 查找敌人
        if not targets:
            all_enemies = battle_manager.enemies if hasattr(caster, 'grid_x') else battle_manager.defenders
            targets = self.find_targets(caster, all_enemies, battle_manager)

        if not targets:
            return False

        for target in targets:
            # 应用减益效果
            self._apply_effects(target, caster)
            logger.debug(f"{caster.name} 对 {target.name} 施加减益: {self.name}")

        self.start_cooldown()
        return True


class SkillManager:
    """技能管理器"""

    def __init__(self):
        self.skill_classes = {
            'damage': DamageSkill,
            'aoe': AOESkill,
            'heal': HealSkill,
            'summon': SummonSkill,
            'buff': BuffSkill,
            'debuff': DebuffSkill
        }

    def create_skill(self, skill_config: dict) -> Optional[Skill]:
        """根据配置创建技能"""
        skill_class_type = skill_config.get('class', 'damage')
        skill_class = self.skill_classes.get(skill_class_type)

        if skill_class:
            return skill_class(skill_config)
        else:
            logger.warning(f"未知的技能类型: {skill_class_type}")
            return None

    def load_skills_for_character(self, character_config: dict) -> List[Skill]:
        """为角色加载技能"""
        skills = []
        skills_config = character_config.get('skills', [])

        for skill_config in skills_config:
            skill = self.create_skill(skill_config)
            if skill:
                skills.append(skill)

        return skills

    def update_unit_effects(self, unit, delta_time: float):
        """更新单位身上的效果"""
        if not hasattr(unit, 'active_effects'):
            unit.active_effects = []
            return

        # 更新所有效果
        effects_to_remove = []
        for effect in unit.active_effects:
            if not effect.update(delta_time):
                effects_to_remove.append(effect)

        # 移除过期效果
        for effect in effects_to_remove:
            effect.remove_from_unit(unit)
            unit.active_effects.remove(effect)

        # 应用持续伤害效果
        total_dot_damage = 0

        # 毒伤
        if hasattr(unit, '_poison_damage') and unit._poison_damage > 0:
            total_dot_damage += unit._poison_damage

        # 燃烧伤害
        if hasattr(unit, '_burn_damage') and unit._burn_damage > 0:
            total_dot_damage += unit._burn_damage

        # 流血伤害（移动时伤害加倍）
        if hasattr(unit, '_bleed_damage') and unit._bleed_damage > 0:
            bleed_dmg = unit._bleed_damage
            # 如果单位在移动（敌人），伤害加倍
            if hasattr(unit, 'speed') and unit.speed > 0 and not getattr(unit, 'blocked_by', None):
                bleed_dmg *= 2
            total_dot_damage += bleed_dmg

        # 应用总持续伤害
        if total_dot_damage > 0:
            unit.take_damage(int(total_dot_damage * delta_time))

    def trigger_passive_skill(self, unit, condition: str, battle_manager: 'BattleManager'):
        """触发被动技能"""
        if not hasattr(unit, 'skills'):
            return

        import random
        for skill in unit.skills:
            if (skill.skill_type == 'passive' and
                skill.trigger_condition == condition and
                random.random() < skill.trigger_chance):

                skill.use(unit, [], battle_manager)

    def auto_cast_skills(self, unit, battle_manager: 'BattleManager'):
        """自动施放技能"""
        if not hasattr(unit, 'skills'):
            return

        for skill in unit.skills:
            if skill.skill_type == 'auto' and skill.can_use(caster=unit, battle_manager=battle_manager):
                skill.use(unit, [], battle_manager)
