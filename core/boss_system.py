"""
Boss战系统 - Boss Battle System
处理Boss单位的特殊逻辑：多阶段战斗、特殊机制、奖励系统
"""

import logging
import random
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.battle_manager import Enemy, BattleManager

logger = logging.getLogger(__name__)


class BossPhase:
    """Boss战斗阶段"""

    def __init__(self, phase_config: dict, phase_number: int):
        """
        初始化Boss阶段

        phase_config格式:
        {
            "hp_threshold": 1.0,  # 进入此阶段的血量百分比
            "hp_min": 0.7,  # 离开此阶段的血量百分比
            "skills": [...],  # 此阶段可用的技能列表
            "buffs": [...],  # 此阶段的增益效果
            "on_enter_effects": [...],  # 进入阶段时的特效
            "summon_minions": {...}  # 召唤小怪配置
        }
        """
        self.phase_number = phase_number
        self.hp_threshold = phase_config.get('hp_threshold', 1.0)
        self.hp_min = phase_config.get('hp_min', 0.0)
        self.skill_ids = [s.get('skill_id') if isinstance(s, dict) else s
                         for s in phase_config.get('skills', [])]
        self.buffs = phase_config.get('buffs', [])
        self.on_enter_effects = phase_config.get('on_enter_effects', [])
        self.summon_config = phase_config.get('summon_minions', None)

        # 特殊行为
        self.damage_multiplier = phase_config.get('damage_multiplier', 1.0)
        self.defense_multiplier = phase_config.get('defense_multiplier', 1.0)
        self.speed_multiplier = phase_config.get('speed_multiplier', 1.0)

    def is_in_phase(self, hp_percent: float) -> bool:
        """检查当前血量是否处于此阶段"""
        return self.hp_min <= hp_percent <= self.hp_threshold


class BossUnit:
    """
    Boss单位包装器
    为普通Enemy单位添加Boss特性
    """

    def __init__(self, enemy: 'Enemy', boss_config: dict, battle_manager: 'BattleManager'):
        """
        初始化Boss单位

        参数:
            enemy: 基础Enemy单位
            boss_config: Boss配置数据
            battle_manager: 战斗管理器引用
        """
        self.enemy = enemy
        self.config = boss_config
        self.battle_manager = battle_manager

        # Boss基本信息
        self.boss_id = boss_config.get('boss_id', 'unknown')
        self.boss_name = boss_config.get('name', 'Unknown Boss')
        self.is_boss = True

        # 阶段系统
        self.phases: List[BossPhase] = []
        phases_config = boss_config.get('phases', [])
        for idx, phase_config in enumerate(phases_config):
            self.phases.append(BossPhase(phase_config, idx + 1))

        self.current_phase_index = 0
        self.phase_changed_this_frame = False

        # 特殊机制
        self.special_mechanics = boss_config.get('special_mechanics', [])
        self.immunities = self._parse_immunities()

        # 狂暴机制
        self.enrage_config = self._find_mechanic('enrage')
        self.enrage_timer = 0
        self.is_enraged = False

        # 召唤机制
        self.summon_cooldowns = {}  # {phase_number: cooldown_remaining}

        # 奖励配置
        self.rewards = boss_config.get('rewards', {})

        # Boss UI相关
        self.show_health_bar = True
        self.health_bar_offset_y = -50  # 血条显示在Boss上方

        # 标记enemy为Boss
        enemy.is_boss = True
        enemy.boss_unit = self

        # 应用初始阶段
        if self.phases:
            self._enter_phase(0)

        logger.info(f"Boss '{self.boss_name}' 已创建，共 {len(self.phases)} 个阶段")

    def _parse_immunities(self) -> List[str]:
        """解析免疫效果列表"""
        for mechanic in self.special_mechanics:
            if mechanic.get('type') == 'immunity':
                return mechanic.get('immune_to', [])
        return []

    def _find_mechanic(self, mechanic_type: str) -> Optional[dict]:
        """查找特定类型的特殊机制"""
        for mechanic in self.special_mechanics:
            if mechanic.get('type') == mechanic_type:
                return mechanic
        return None

    def update(self, delta_time: float):
        """更新Boss逻辑"""
        if not self.enemy.is_alive():
            return

        # 重置阶段变更标志
        self.phase_changed_this_frame = False

        # 检查阶段转换
        self._check_phase_transition()

        # 更新狂暴计时器
        if self.enrage_config and not self.is_enraged:
            self.enrage_timer += delta_time
            enrage_time = self.enrage_config.get('time', 300)
            if self.enrage_timer >= enrage_time:
                self._trigger_enrage()

        # 更新召唤冷却
        for phase_num in list(self.summon_cooldowns.keys()):
            self.summon_cooldowns[phase_num] -= delta_time
            if self.summon_cooldowns[phase_num] <= 0:
                del self.summon_cooldowns[phase_num]

        # 处理当前阶段的召唤
        if self.phases and self.current_phase_index < len(self.phases):
            current_phase = self.phases[self.current_phase_index]
            if current_phase.summon_config:
                self._handle_phase_summon(current_phase)

    def _check_phase_transition(self):
        """检查并处理阶段转换"""
        if not self.phases:
            return

        hp_percent = self.enemy.hp / self.enemy.max_hp

        # 向后检查是否需要进入下一阶段
        for i in range(self.current_phase_index + 1, len(self.phases)):
            phase = self.phases[i]
            if hp_percent <= phase.hp_threshold:
                self._enter_phase(i)
                return

    def _enter_phase(self, phase_index: int):
        """进入指定阶段"""
        if phase_index >= len(self.phases):
            return

        old_phase = self.current_phase_index
        self.current_phase_index = phase_index
        self.phase_changed_this_frame = True

        phase = self.phases[phase_index]

        logger.info(f"Boss '{self.boss_name}' 进入阶段 {phase.phase_number}")

        # 移除旧阶段的增益
        if old_phase < len(self.phases) and old_phase != phase_index:
            old_phase_obj = self.phases[old_phase]
            self._remove_phase_buffs(old_phase_obj)

        # 应用新阶段的增益
        self._apply_phase_buffs(phase)

        # 应用阶段倍率
        if phase.damage_multiplier != 1.0:
            self.enemy.attack = int(self.enemy.attack * phase.damage_multiplier)

        # 触发进入阶段效果
        for effect in phase.on_enter_effects:
            self._trigger_phase_effect(effect)

        # 播放阶段转换音效和特效
        if self.battle_manager:
            if hasattr(self.battle_manager, 'sound_system'):
                from core.sound_system import SoundPresets
                self.battle_manager.sound_system.play_sound(SoundPresets.BOSS_PHASE_CHANGE, volume=0.8)

            if hasattr(self.battle_manager, 'hit_feedback'):
                self.battle_manager.hit_feedback.trigger_screen_shake(intensity=15, duration=0.4)

                # 在Boss位置创建特效粒子
                y_pos = getattr(self.enemy, 'y', 0)
                if y_pos == 0 and hasattr(self.enemy, 'lane'):
                    y_pos = self.battle_manager.grid_start_y + self.enemy.lane * self.battle_manager.cell_size + self.battle_manager.cell_size // 2
                self.battle_manager.hit_feedback.create_explosion_particles(self.enemy.x, y_pos, count=25)

        # 通知战斗管理器（用于UI更新、音效等）
        if hasattr(self.battle_manager, 'on_boss_phase_change'):
            self.battle_manager.on_boss_phase_change(self, phase.phase_number)

    def _apply_phase_buffs(self, phase: BossPhase):
        """应用阶段增益"""
        from core.skill_system import SkillEffect

        for buff_config in phase.buffs:
            effect = SkillEffect(
                buff_config.get('type'),
                buff_config.get('value', 0),
                duration=999999  # 阶段增益持续到阶段结束
            )

            if not hasattr(self.enemy, 'active_effects'):
                self.enemy.active_effects = []

            # 标记为阶段效果
            effect.is_phase_buff = True
            effect.phase_number = phase.phase_number

            self.enemy.active_effects.append(effect)
            effect.apply_to_unit(self.enemy)

            logger.debug(f"Boss阶段{phase.phase_number}增益: {buff_config.get('type')}")

    def _remove_phase_buffs(self, phase: BossPhase):
        """移除阶段增益"""
        if not hasattr(self.enemy, 'active_effects'):
            return

        effects_to_remove = []
        for effect in self.enemy.active_effects:
            if (hasattr(effect, 'is_phase_buff') and
                effect.is_phase_buff and
                effect.phase_number == phase.phase_number):
                effects_to_remove.append(effect)

        for effect in effects_to_remove:
            effect.remove_from_unit(self.enemy)
            self.enemy.active_effects.remove(effect)

    def _trigger_phase_effect(self, effect_config: dict):
        """触发阶段特效"""
        effect_type = effect_config.get('type')

        if effect_type == 'screen_shake':
            # 屏幕震动效果（需要在渲染层实现）
            if hasattr(self.battle_manager, 'trigger_screen_shake'):
                intensity = effect_config.get('intensity', 10)
                duration = effect_config.get('duration', 0.5)
                self.battle_manager.trigger_screen_shake(intensity, duration)

        elif effect_type == 'spawn_minions':
            # 召唤小怪
            minion_id = effect_config.get('minion_id')
            count = effect_config.get('count', 3)
            if minion_id:
                self._spawn_minions(minion_id, count)

        elif effect_type == 'heal':
            # Boss回血
            heal_percent = effect_config.get('value', 0.2)
            heal_amount = int(self.enemy.max_hp * heal_percent)
            self.enemy.hp = min(self.enemy.hp + heal_amount, self.enemy.max_hp)
            logger.info(f"Boss '{self.boss_name}' 回复 {heal_amount} 生命值")

        elif effect_type == 'invulnerable':
            # 短暂无敌
            duration = effect_config.get('duration', 3.0)
            from core.skill_system import SkillEffect
            invuln_effect = SkillEffect('invulnerable', 1.0, duration)
            if not hasattr(self.enemy, 'active_effects'):
                self.enemy.active_effects = []
            self.enemy.active_effects.append(invuln_effect)
            invuln_effect.apply_to_unit(self.enemy)

    def _handle_phase_summon(self, phase: BossPhase):
        """处理阶段召唤"""
        if not phase.summon_config:
            return

        # 检查召唤冷却
        phase_num = phase.phase_number
        if phase_num in self.summon_cooldowns:
            return

        minion_id = phase.summon_config.get('minion_id')
        count = phase.summon_config.get('count', 2)
        cooldown = phase.summon_config.get('cooldown', 30.0)

        if minion_id:
            self._spawn_minions(minion_id, count)
            self.summon_cooldowns[phase_num] = cooldown

    def _spawn_minions(self, minion_id: str, count: int):
        """召唤小怪"""
        # 获取小怪配置
        if not hasattr(self.battle_manager, 'config_loader'):
            return

        minion_config = self.battle_manager.config_loader.characters.get(minion_id)
        if not minion_config:
            logger.warning(f"找不到小怪配置: {minion_id}")
            return

        # 在Boss附近生成小怪
        from core.battle_manager import Enemy

        for i in range(count):
            # 计算生成位置（Boss左右两侧）
            offset_y = (i - count // 2) * 60
            spawn_x = self.enemy.x
            spawn_y = max(0, min(self.enemy.y + offset_y,
                                 self.battle_manager.screen_height - 100))

            # 创建小怪
            minion = Enemy(
                minion_config,
                spawn_x,
                spawn_y,
                self.battle_manager.grid_start_y,
                self.battle_manager.cell_size
            )

            # 标记为Boss召唤物
            minion.is_summoned_by_boss = True
            minion.summoner = self.enemy

            self.battle_manager.enemies.append(minion)
            logger.info(f"Boss召唤了 {minion.name} 在 ({spawn_x}, {spawn_y})")

    def _trigger_enrage(self):
        """触发狂暴"""
        self.is_enraged = True
        bonus_damage = self.enrage_config.get('bonus_damage', 2.0)

        # 大幅提升攻击力
        self.enemy.attack = int(self.enemy.attack * bonus_damage)

        # 应用狂暴视觉效果（变红等）
        if hasattr(self.enemy, 'is_enraged'):
            self.enemy.is_enraged = True

        logger.warning(f"Boss '{self.boss_name}' 进入狂暴状态！攻击力提升 {bonus_damage}x")

        # 播放狂暴音效和特效
        if self.battle_manager:
            if hasattr(self.battle_manager, 'sound_system'):
                from core.sound_system import SoundPresets
                self.battle_manager.sound_system.play_sound(SoundPresets.BOSS_ENRAGE, volume=0.9)

            if hasattr(self.battle_manager, 'hit_feedback'):
                self.battle_manager.hit_feedback.trigger_screen_shake(intensity=20, duration=0.6)

                # 在Boss位置创建强烈的特效粒子
                y_pos = getattr(self.enemy, 'y', 0)
                if y_pos == 0 and hasattr(self.enemy, 'lane'):
                    y_pos = self.battle_manager.grid_start_y + self.enemy.lane * self.battle_manager.cell_size + self.battle_manager.cell_size // 2
                self.battle_manager.hit_feedback.create_explosion_particles(self.enemy.x, y_pos, count=35)

        # 触发特效
        if hasattr(self.battle_manager, 'on_boss_enrage'):
            self.battle_manager.on_boss_enrage(self)

    def can_apply_effect(self, effect_type: str) -> bool:
        """检查是否可以对Boss施加某种效果"""
        return effect_type not in self.immunities

    def on_death(self):
        """Boss死亡时调用"""
        logger.info(f"Boss '{self.boss_name}' 已被击败！")

        # 发放奖励
        self._grant_rewards()

        # 通知战斗管理器
        if hasattr(self.battle_manager, 'on_boss_defeated'):
            self.battle_manager.on_boss_defeated(self)

    def _grant_rewards(self):
        """发放击败Boss的奖励"""
        # 金币奖励
        gold_reward = self.rewards.get('gold', 0)
        if gold_reward > 0:
            self.battle_manager.gold += gold_reward
            logger.info(f"获得金币奖励: {gold_reward}")

        # 经验奖励
        exp_reward = self.rewards.get('experience', 0)
        if exp_reward > 0:
            # TODO: 实现经验系统
            logger.info(f"获得经验奖励: {exp_reward}")

        # 物品掉落
        items = self.rewards.get('items', [])
        for item_config in items:
            item_id = item_config.get('item_id')
            drop_chance = item_config.get('drop_chance', 1.0)

            if random.random() < drop_chance:
                # TODO: 实现物品系统
                logger.info(f"掉落物品: {item_id}")

    def get_current_phase(self) -> Optional[BossPhase]:
        """获取当前阶段"""
        if self.current_phase_index < len(self.phases):
            return self.phases[self.current_phase_index]
        return None

    def get_phase_progress(self) -> float:
        """获取当前阶段进度（0.0-1.0）"""
        if not self.phases:
            return 1.0

        current_phase = self.get_current_phase()
        if not current_phase:
            return 1.0

        hp_percent = self.enemy.hp / self.enemy.max_hp
        phase_range = current_phase.hp_threshold - current_phase.hp_min

        if phase_range == 0:
            return 1.0

        progress = (current_phase.hp_threshold - hp_percent) / phase_range
        return max(0.0, min(1.0, progress))


class BossManager:
    """Boss系统管理器"""

    def __init__(self):
        self.active_bosses: List[BossUnit] = []

    def create_boss(self, boss_config: dict, enemy: 'Enemy',
                   battle_manager: 'BattleManager') -> BossUnit:
        """
        创建Boss单位

        参数:
            boss_config: Boss配置数据
            enemy: 已创建的Enemy单位
            battle_manager: 战斗管理器引用

        返回:
            BossUnit实例
        """
        boss = BossUnit(enemy, boss_config, battle_manager)
        self.active_bosses.append(boss)
        return boss

    def update(self, delta_time: float):
        """更新所有Boss"""
        for boss in self.active_bosses[:]:
            if not boss.enemy.is_alive():
                # Boss已死亡
                boss.on_death()
                self.active_bosses.remove(boss)
            else:
                boss.update(delta_time)

    def clear(self):
        """清除所有Boss"""
        self.active_bosses.clear()

    def get_boss_by_enemy(self, enemy: 'Enemy') -> Optional[BossUnit]:
        """根据Enemy单位查找对应的BossUnit"""
        for boss in self.active_bosses:
            if boss.enemy == enemy:
                return boss
        return None

    def has_active_boss(self) -> bool:
        """是否有活跃的Boss"""
        return len(self.active_bosses) > 0
