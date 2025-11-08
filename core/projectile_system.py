"""
弹道系统 - 处理远程攻击的弹道
包括：直线弹道、抛物线弹道、追踪弹道、穿透弹道
"""

import pygame
import logging
import math
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.battle_manager import Defender, Enemy, BattleManager

logger = logging.getLogger(__name__)


class Projectile:
    """弹道基类"""

    def __init__(self, caster, target, config: dict, battle_manager: 'BattleManager'):
        """
        config格式：
        {
            "projectile_type": "linear",  # linear, arc, homing, pierce
            "speed": 300,  # 弹道速度（像素/秒）
            "damage": 25,  # 伤害值
            "sprite": "assets/projectiles/arrow.png",  # 弹道贴图
            "size": 10,  # 弹道大小（渲染用）
            "color": [255, 200, 0],  # 弹道颜色（如果没有贴图）
            "pierce": false,  # 是否穿透
            "pierce_count": 0,  # 穿透次数（0=不穿透，-1=无限穿透）
            "splash_radius": 0,  # 溅射范围（0=无溅射）
            "on_hit_effects": [],  # 命中时的效果（如减速、燃烧等）
            "lifetime": 5.0,  # 最大存活时间（秒）
        }
        """
        self.caster = caster
        self.target = target
        self.config = config
        self.battle_manager = battle_manager

        # 弹道属性
        self.projectile_type = config.get('projectile_type', 'linear')
        self.speed = config.get('speed', 300)
        self.damage = config.get('damage', 0)
        self.size = config.get('size', 10)
        self.color = config.get('color', [255, 200, 0])

        # 穿透和溅射
        self.is_pierce = config.get('pierce', False)
        self.pierce_count = config.get('pierce_count', 0)
        self.pierce_remaining = self.pierce_count
        self.splash_radius = config.get('splash_radius', 0)

        # 命中效果
        self.on_hit_effects = config.get('on_hit_effects', [])

        # 生命周期
        self.lifetime = config.get('lifetime', 5.0)
        self.age = 0
        self.is_alive = True

        # 位置（从施法者位置开始）
        self.x, self.y = self._get_caster_position()

        # 目标位置
        if target:
            self.target_x, self.target_y = self._get_target_position()
        else:
            self.target_x, self.target_y = self.x + 100, self.y

        # 计算方向
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > 0:
            self.dir_x = dx / distance
            self.dir_y = dy / distance
        else:
            self.dir_x, self.dir_y = 1, 0

        # 抛物线弹道特有属性
        if self.projectile_type == 'arc':
            self.arc_height = config.get('arc_height', 100)  # 抛物线最高点
            self.start_x = self.x
            self.start_y = self.y
            self.travel_distance = 0
            self.total_distance = distance

        # 已命中的目标（用于穿透弹道）
        self.hit_targets = []

    def _get_caster_position(self) -> Tuple[float, float]:
        """获取施法者位置"""
        if hasattr(self.caster, 'get_screen_pos'):
            if hasattr(self.caster, 'grid_x'):  # Defender
                return self.caster.get_screen_pos(
                    self.battle_manager.grid_start_x,
                    self.battle_manager.grid_start_y,
                    self.battle_manager.cell_size
                )
            else:  # Enemy
                return self.caster.get_screen_pos(
                    self.battle_manager.grid_start_y,
                    self.battle_manager.cell_size
                )
        return (100, 100)

    def _get_target_position(self) -> Tuple[float, float]:
        """获取目标位置"""
        if hasattr(self.target, 'get_screen_pos'):
            if hasattr(self.target, 'grid_x'):  # Defender
                return self.target.get_screen_pos(
                    self.battle_manager.grid_start_x,
                    self.battle_manager.grid_start_y,
                    self.battle_manager.cell_size
                )
            else:  # Enemy
                return self.target.get_screen_pos(
                    self.battle_manager.grid_start_y,
                    self.battle_manager.cell_size
                )
        return (200, 100)

    def update(self, delta_time: float) -> bool:
        """
        更新弹道
        返回：是否还存活
        """
        self.age += delta_time

        # 检查生命周期
        if self.age >= self.lifetime:
            self.is_alive = False
            return False

        # 根据弹道类型更新位置
        if self.projectile_type == 'linear':
            self._update_linear(delta_time)
        elif self.projectile_type == 'arc':
            self._update_arc(delta_time)
        elif self.projectile_type == 'homing':
            self._update_homing(delta_time)
        elif self.projectile_type == 'pierce':
            self._update_pierce(delta_time)

        # 检查碰撞
        self._check_collision()

        return self.is_alive

    def _update_linear(self, delta_time: float):
        """更新直线弹道"""
        self.x += self.dir_x * self.speed * delta_time
        self.y += self.dir_y * self.speed * delta_time

    def _update_arc(self, delta_time: float):
        """更新抛物线弹道"""
        # 水平移动
        self.x += self.dir_x * self.speed * delta_time
        self.travel_distance += self.speed * delta_time

        # 垂直位置根据抛物线计算
        if self.total_distance > 0:
            progress = self.travel_distance / self.total_distance
            # 抛物线公式：y = -4h * x * (x - 1)，其中h是最高点
            arc_offset = -4 * self.arc_height * progress * (progress - 1)
            self.y = self.start_y + self.dir_y * self.travel_distance - arc_offset

    def _update_homing(self, delta_time: float):
        """更新追踪弹道"""
        if self.target and self.target.is_alive():
            # 重新计算目标位置和方向
            self.target_x, self.target_y = self._get_target_position()
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            distance = math.sqrt(dx * dx + dy * dy)
            if distance > 0:
                self.dir_x = dx / distance
                self.dir_y = dy / distance

        # 按方向移动
        self.x += self.dir_x * self.speed * delta_time
        self.y += self.dir_y * self.speed * delta_time

    def _update_pierce(self, delta_time: float):
        """更新穿透弹道（与直线相同，但碰撞处理不同）"""
        self._update_linear(delta_time)

    def _check_collision(self):
        """检查碰撞"""
        # 获取所有可能的目标
        targets = self._get_potential_targets()

        for target in targets:
            # 跳过已命中的目标（穿透弹道）
            if target in self.hit_targets:
                continue

            # 计算距离
            target_pos = self._get_target_position_of_unit(target)
            if target_pos:
                distance = math.sqrt((self.x - target_pos[0])**2 + (self.y - target_pos[1])**2)

                # 碰撞检测
                collision_radius = self.size + 20  # 20像素碰撞半径
                if distance <= collision_radius:
                    self._on_hit(target)

                    # 如果是穿透弹道
                    if self.is_pierce:
                        self.hit_targets.append(target)
                        if self.pierce_count > 0:
                            self.pierce_remaining -= 1
                            if self.pierce_remaining <= 0:
                                self.is_alive = False
                                return
                    else:
                        # 非穿透弹道，命中后消失
                        self.is_alive = False
                        return

    def _get_potential_targets(self) -> List:
        """获取所有潜在目标"""
        if hasattr(self.caster, 'grid_x'):  # Defender施放，攻击Enemy
            return self.battle_manager.enemies
        else:  # Enemy施放，攻击Defender
            return self.battle_manager.defenders

    def _get_target_position_of_unit(self, unit) -> Optional[Tuple[float, float]]:
        """获取单位的位置"""
        if hasattr(unit, 'get_screen_pos'):
            if hasattr(unit, 'grid_x'):  # Defender
                return unit.get_screen_pos(
                    self.battle_manager.grid_start_x,
                    self.battle_manager.grid_start_y,
                    self.battle_manager.cell_size
                )
            else:  # Enemy
                return unit.get_screen_pos(
                    self.battle_manager.grid_start_y,
                    self.battle_manager.cell_size
                )
        return None

    def _on_hit(self, target):
        """命中目标时的处理"""
        # 造成伤害
        if self.damage > 0:
            target.take_damage(self.damage)
            logger.debug(f"弹道命中 {target.name}，造成 {self.damage} 伤害")

        # 应用命中效果
        if self.on_hit_effects:
            from core.skill_system import SkillEffect
            for effect_config in self.on_hit_effects:
                effect_type = effect_config.get('type')
                effect_value = effect_config.get('value', 0)
                effect_duration = effect_config.get('duration', 1.0)

                # 特殊处理：heal效果作用于施法者而非目标
                if effect_type == 'heal':
                    if self.caster and self.caster.is_alive():
                        heal_amount = effect_value
                        self.caster.hp = min(self.caster.hp + heal_amount, self.caster.max_hp)
                        logger.debug(f"{self.caster.name} 通过弹道命中回复 {heal_amount} 生命值")
                    continue  # 不创建SkillEffect对象，直接处理

                # 其他效果作用于目标
                effect = SkillEffect(effect_type, effect_value, effect_duration)
                if not hasattr(target, 'active_effects'):
                    target.active_effects = []
                target.active_effects.append(effect)
                effect.apply_to_unit(target)

        # 溅射伤害
        if self.splash_radius > 0:
            self._apply_splash_damage(target)

    def _apply_splash_damage(self, center_target):
        """应用溅射伤害"""
        center_pos = self._get_target_position_of_unit(center_target)
        if not center_pos:
            return

        targets = self._get_potential_targets()
        splash_damage = int(self.damage * 0.5)  # 溅射伤害为50%

        for target in targets:
            if target == center_target:
                continue

            target_pos = self._get_target_position_of_unit(target)
            if target_pos:
                distance = math.sqrt((center_pos[0] - target_pos[0])**2 + (center_pos[1] - target_pos[1])**2)
                if distance <= self.splash_radius:
                    target.take_damage(splash_damage)
                    logger.debug(f"溅射伤害命中 {target.name}，造成 {splash_damage} 伤害")

    def render(self, screen: pygame.Surface):
        """渲染弹道"""
        # 简单渲染为圆形（后续可以替换为sprite）
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)
        # 绘制边框
        pygame.draw.circle(screen, (255, 255, 255), (int(self.x), int(self.y)), self.size, 2)


class ProjectileManager:
    """弹道管理器"""

    def __init__(self):
        self.projectiles: List[Projectile] = []

    def create_projectile(self, caster, target, config: dict, battle_manager: 'BattleManager') -> Projectile:
        """创建弹道"""
        projectile = Projectile(caster, target, config, battle_manager)
        self.projectiles.append(projectile)
        return projectile

    def update(self, delta_time: float):
        """更新所有弹道"""
        # 更新所有弹道
        for projectile in self.projectiles[:]:
            if not projectile.update(delta_time):
                self.projectiles.remove(projectile)

    def render(self, screen: pygame.Surface):
        """渲染所有弹道"""
        for projectile in self.projectiles:
            projectile.render(screen)

    def clear(self):
        """清除所有弹道"""
        self.projectiles.clear()
