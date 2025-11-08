"""
角色独属被动技能系统（Passive Traits System）
处理角色固有的被动能力，不同于技能系统中的被动技能
包括：生命回复、吸血、反伤、暴击、闪避、额外收益等
"""

import logging
import random
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.battle_manager import Defender, Enemy, BattleManager

logger = logging.getLogger(__name__)


class PassiveTraitsManager:
    """角色被动特质管理器"""

    def __init__(self):
        pass

    def apply_passive_traits(self, unit, delta_time: float, battle_manager: 'BattleManager'):
        """
        应用角色的所有被动特质
        config格式：
        passive_traits:
          - type: hp_regen
            value: 5  # 每秒回复5点生命值
          - type: lifesteal
            value: 0.2  # 20%吸血
          - type: crit_rate
            value: 0.25  # 25%暴击率
        """
        if not hasattr(unit, 'config'):
            return

        passive_traits = unit.config.get('passive_traits', [])

        for trait in passive_traits:
            trait_type = trait.get('type')
            value = trait.get('value', 0)

            # 根据类型应用不同的被动特质
            if trait_type == 'hp_regen':
                self._apply_hp_regen(unit, value, delta_time)

            elif trait_type == 'shield_regen':
                self._apply_shield_regen(unit, value, delta_time)

            elif trait_type == 'mana_regen':
                self._apply_mana_regen(unit, value, delta_time)

            # 其他被动特质在不同的时机触发（攻击时、受击时等）
            # 这些不需要在update中处理

    def _apply_hp_regen(self, unit, regen_per_second: float, delta_time: float):
        """生命回复"""
        if unit.hp < unit.max_hp:
            heal_amount = regen_per_second * delta_time
            unit.hp = min(unit.hp + heal_amount, unit.max_hp)

    def _apply_shield_regen(self, unit, regen_per_second: float, delta_time: float):
        """护盾回复"""
        if not hasattr(unit, 'shield'):
            unit.shield = 0
            unit.max_shield = unit.max_hp * 0.3  # 护盾上限为最大生命值的30%

        if unit.shield < unit.max_shield:
            shield_regen = regen_per_second * delta_time
            unit.shield = min(unit.shield + shield_regen, unit.max_shield)

    def _apply_mana_regen(self, unit, regen_per_second: float, delta_time: float):
        """法力回复"""
        if not hasattr(unit, 'mana'):
            unit.mana = 100
            unit.max_mana = 100

        if unit.mana < unit.max_mana:
            mana_regen = regen_per_second * delta_time
            unit.mana = min(unit.mana + mana_regen, unit.max_mana)

    def on_attack(self, attacker, target, original_damage: int, battle_manager: 'BattleManager') -> int:
        """
        攻击时触发的被动特质
        返回：修改后的伤害值
        """
        if not hasattr(attacker, 'config'):
            return original_damage

        passive_traits = attacker.config.get('passive_traits', [])
        final_damage = original_damage

        for trait in passive_traits:
            trait_type = trait.get('type')
            value = trait.get('value', 0)

            if trait_type == 'lifesteal':
                # 攻击吸血
                heal = int(final_damage * value)
                if heal > 0:
                    attacker.hp = min(attacker.hp + heal, attacker.max_hp)
                    logger.debug(f"{attacker.name} 吸血回复 {heal} 生命值")

            elif trait_type == 'crit_rate':
                # 暴击率
                if random.random() < value:
                    crit_damage_multiplier = self._get_trait_value(attacker, 'crit_damage', 2.0)
                    final_damage = int(final_damage * crit_damage_multiplier)
                    logger.debug(f"{attacker.name} 触发暴击！伤害: {original_damage} -> {final_damage}")

            elif trait_type == 'true_damage':
                # 真实伤害（忽略防御）
                extra_true_damage = int(original_damage * value)
                final_damage += extra_true_damage
                logger.debug(f"{attacker.name} 造成额外真实伤害: {extra_true_damage}")

            elif trait_type == 'bonus_damage':
                # 额外伤害（百分比）
                extra_damage = int(original_damage * value)
                final_damage += extra_damage

            elif trait_type == 'execute':
                # 斩杀（对低血量敌人额外伤害）
                threshold = trait.get('threshold', 0.2)  # 默认血量低于20%
                if hasattr(target, 'hp') and hasattr(target, 'max_hp'):
                    hp_percent = target.hp / target.max_hp
                    if hp_percent < threshold:
                        execute_damage = int(original_damage * value)
                        final_damage += execute_damage
                        logger.debug(f"{attacker.name} 触发斩杀！额外伤害: {execute_damage}")

        return final_damage

    def on_take_damage(self, defender, attacker, original_damage: int, battle_manager: 'BattleManager') -> int:
        """
        受击时触发的被动特质
        返回：修改后的伤害值
        """
        if not hasattr(defender, 'config'):
            return original_damage

        passive_traits = defender.config.get('passive_traits', [])
        final_damage = original_damage

        for trait in passive_traits:
            trait_type = trait.get('type')
            value = trait.get('value', 0)

            if trait_type == 'evasion':
                # 闪避
                if random.random() < value:
                    logger.debug(f"{defender.name} 闪避了攻击！")
                    return 0

            elif trait_type == 'damage_reduction':
                # 伤害减免（百分比）
                reduction = int(final_damage * value)
                final_damage -= reduction

            elif trait_type == 'thorns':
                # 反伤（对攻击者造成伤害）
                thorn_damage = int(final_damage * value)
                if thorn_damage > 0:
                    attacker.take_damage(thorn_damage)
                    logger.debug(f"{defender.name} 反伤 {attacker.name} {thorn_damage} 伤害")

            elif trait_type == 'shield_block':
                # 护盾格挡
                if hasattr(defender, 'shield') and defender.shield > 0:
                    shield_absorbed = min(final_damage, int(defender.shield))
                    defender.shield -= shield_absorbed
                    final_damage -= shield_absorbed
                    logger.debug(f"{defender.name} 的护盾吸收了 {shield_absorbed} 伤害")

        return max(final_damage, 0)

    def on_kill(self, killer, victim, battle_manager: 'BattleManager'):
        """
        击杀时触发的被动特质
        """
        if not hasattr(killer, 'config'):
            return

        passive_traits = killer.config.get('passive_traits', [])

        for trait in passive_traits:
            trait_type = trait.get('type')
            value = trait.get('value', 0)

            if trait_type == 'bonus_gold':
                # 额外金币
                extra_gold = int(battle_manager.kill_reward * value)
                battle_manager.gold += extra_gold
                logger.debug(f"{killer.name} 获得额外金币: {extra_gold}")

            elif trait_type == 'heal_on_kill':
                # 击杀回血
                heal = int(killer.max_hp * value)
                killer.hp = min(killer.hp + heal, killer.max_hp)
                logger.debug(f"{killer.name} 击杀回血: {heal}")

            elif trait_type == 'cooldown_reduction_on_kill':
                # 击杀减CD
                if hasattr(killer, 'skills'):
                    cd_reduction = value  # 秒数
                    for skill in killer.skills:
                        if skill.cooldown_remaining > 0:
                            skill.cooldown_remaining = max(0, skill.cooldown_remaining - cd_reduction)
                    logger.debug(f"{killer.name} 击杀减少技能冷却: {cd_reduction}秒")

    def _get_trait_value(self, unit, trait_type: str, default: float) -> float:
        """获取某个被动特质的数值"""
        if not hasattr(unit, 'config'):
            return default

        passive_traits = unit.config.get('passive_traits', [])
        for trait in passive_traits:
            if trait.get('type') == trait_type:
                return trait.get('value', default)

        return default

    def get_stat_bonuses(self, unit) -> Dict[str, float]:
        """
        获取所有被动特质提供的属性加成
        返回格式：{'attack': 10, 'defense': 5, 'speed': 1.2, ...}
        """
        bonuses = {}

        if not hasattr(unit, 'config'):
            return bonuses

        passive_traits = unit.config.get('passive_traits', [])

        for trait in passive_traits:
            trait_type = trait.get('type')
            value = trait.get('value', 0)

            if trait_type == 'bonus_attack':
                bonuses['attack'] = bonuses.get('attack', 0) + value

            elif trait_type == 'bonus_defense':
                bonuses['defense'] = bonuses.get('defense', 0) + value

            elif trait_type == 'bonus_attack_speed':
                bonuses['attack_speed'] = bonuses.get('attack_speed', 1.0) * (1 + value)

            elif trait_type == 'bonus_move_speed':
                bonuses['move_speed'] = bonuses.get('move_speed', 1.0) * (1 + value)

            elif trait_type == 'bonus_hp':
                bonuses['hp'] = bonuses.get('hp', 0) + value

            elif trait_type == 'bonus_attack_range':
                bonuses['attack_range'] = bonuses.get('attack_range', 0) + value

        return bonuses

    def apply_stat_bonuses(self, unit):
        """应用被动特质的属性加成（在单位初始化时调用）"""
        bonuses = self.get_stat_bonuses(unit)

        if 'attack' in bonuses:
            unit.attack += int(bonuses['attack'])

        if 'defense' in bonuses:
            if not hasattr(unit, 'defense'):
                unit.defense = 0
            unit.defense += int(bonuses['defense'])

        if 'attack_speed' in bonuses:
            unit.attack_speed *= bonuses['attack_speed']
            unit.attack_interval = 1.0 / unit.attack_speed

        if 'move_speed' in bonuses and hasattr(unit, 'speed'):
            unit.speed *= bonuses['move_speed']

        if 'hp' in bonuses:
            hp_bonus = int(bonuses['hp'])
            unit.max_hp += hp_bonus
            unit.hp += hp_bonus

        if 'attack_range' in bonuses:
            unit.attack_range += int(bonuses['attack_range'])

        logger.debug(f"{unit.name} 应用被动特质属性加成: {bonuses}")
