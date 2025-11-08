"""
实体管理器 - CrossVerse Arena核心模块
负责管理所有游戏实体的生命周期
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
import pygame

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """实体类型枚举"""
    CHARACTER = "character"  # 角色
    PROJECTILE = "projectile"  # 投射物/子弹
    SUMMON = "summon"  # 召唤物
    EFFECT = "effect"  # 特效
    OBSTACLE = "obstacle"  # 障碍物


class EntityState(Enum):
    """实体状态枚举"""
    IDLE = "idle"  # 待机
    MOVING = "moving"  # 移动
    ATTACKING = "attacking"  # 攻击
    CASTING = "casting"  # 施法
    HIT = "hit"  # 受伤
    DYING = "dying"  # 濒死
    DEAD = "dead"  # 死亡


class Entity:
    """
    游戏实体基类
    所有游戏对象（角色、技能、子弹等）都继承此类
    """

    def __init__(self, entity_id: str, entity_type: EntityType, config: Dict):
        """
        初始化实体

        参数:
            entity_id: 实体唯一ID
            entity_type: 实体类型
            config: 实体配置字典
        """
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.config = config

        # 基础属性
        self.name = config.get('name', 'Unknown')
        self.position = [0, 0]  # [x, y]
        self.velocity = [0, 0]  # [vx, vy]
        self.state = EntityState.IDLE

        # 生命值
        self.max_hp = config.get('stats', {}).get('hp', 100)
        self.current_hp = self.max_hp

        # 攻击属性
        self.attack = config.get('stats', {}).get('attack', 10)
        self.attack_range = config.get('stats', {}).get('attack_range', 100)
        self.attack_speed = config.get('stats', {}).get('attack_speed', 1.0)
        self.attack_cooldown = 0  # 攻击冷却计时器

        # 移动属性
        self.speed = config.get('stats', {}).get('speed', 0)

        # 视觉属性
        self.sprite: Optional[pygame.Surface] = None
        self.animation_frame = 0
        self.animation_timer = 0

        # 状态标志
        self.is_alive = True
        self.is_active = True

        # 效果列表
        self.active_effects: List[Dict] = []

        # 引用计数（用于资源管理）
        self.ref_count = 0

        logger.debug(f"创建实体: {self.name} ({entity_id}, {entity_type.value})")

    def update(self, delta_time: float) -> None:
        """
        更新实体状态

        参数:
            delta_time: 帧间隔时间（秒）
        """
        if not self.is_active:
            return

        # 更新冷却计时器
        if self.attack_cooldown > 0:
            self.attack_cooldown -= delta_time

        # 更新动画
        self.animation_timer += delta_time
        if self.animation_timer >= 0.1:  # 每0.1秒切换一帧
            self.animation_frame = (self.animation_frame + 1) % 4
            self.animation_timer = 0

        # 更新位置
        if self.speed > 0:
            self.position[0] += self.velocity[0] * delta_time
            self.position[1] += self.velocity[1] * delta_time

        # 更新效果
        self.update_effects(delta_time)

        # 检查死亡
        if self.current_hp <= 0 and self.is_alive:
            self.on_death()

    def update_effects(self, delta_time: float) -> None:
        """
        更新实体上的效果

        参数:
            delta_time: 帧间隔时间（秒）
        """
        expired_effects = []

        for effect in self.active_effects:
            # 更新效果持续时间
            effect['remaining_time'] -= delta_time

            if effect['remaining_time'] <= 0:
                expired_effects.append(effect)

        # 移除过期效果
        for effect in expired_effects:
            self.remove_effect(effect)

    def render(self, screen: pygame.Surface) -> None:
        """
        渲染实体

        参数:
            screen: pygame屏幕对象
        """
        if not self.is_active or self.sprite is None:
            return

        # 绘制精灵
        screen.blit(self.sprite, self.position)

        # 绘制血条
        if self.entity_type == EntityType.CHARACTER and self.is_alive:
            self.draw_health_bar(screen)

    def draw_health_bar(self, screen: pygame.Surface) -> None:
        """
        绘制血条

        参数:
            screen: pygame屏幕对象
        """
        bar_width = 50
        bar_height = 5
        bar_x = self.position[0]
        bar_y = self.position[1] - 10

        # 背景（红色）
        pygame.draw.rect(screen, (255, 0, 0),
                        (bar_x, bar_y, bar_width, bar_height))

        # 前景（绿色，根据血量比例）
        hp_ratio = self.current_hp / self.max_hp
        pygame.draw.rect(screen, (0, 255, 0),
                        (bar_x, bar_y, bar_width * hp_ratio, bar_height))

        # 边框
        pygame.draw.rect(screen, (0, 0, 0),
                        (bar_x, bar_y, bar_width, bar_height), 1)

    def take_damage(self, damage: int, damage_type: str = "physical") -> None:
        """
        受到伤害

        参数:
            damage: 伤害值
            damage_type: 伤害类型（physical/magic/true）
        """
        if not self.is_alive:
            return

        # 应用伤害
        self.current_hp -= damage
        self.current_hp = max(0, self.current_hp)

        logger.debug(f"{self.name} 受到 {damage} 点{damage_type}伤害, 剩余HP: {self.current_hp}/{self.max_hp}")

        # 触发受伤状态
        self.state = EntityState.HIT

        # 调用受伤回调
        self.on_hit(damage, damage_type)

    def heal(self, amount: int) -> None:
        """
        治疗

        参数:
            amount: 治疗量
        """
        if not self.is_alive:
            return

        old_hp = self.current_hp
        self.current_hp += amount
        self.current_hp = min(self.max_hp, self.current_hp)

        actual_heal = self.current_hp - old_hp
        logger.debug(f"{self.name} 治疗 {actual_heal} HP, 当前HP: {self.current_hp}/{self.max_hp}")

    def add_effect(self, effect: Dict) -> None:
        """
        添加效果

        参数:
            effect: 效果配置字典
        """
        self.active_effects.append(effect)
        logger.debug(f"{self.name} 获得效果: {effect.get('name', 'Unknown')}")

    def remove_effect(self, effect: Dict) -> None:
        """
        移除效果

        参数:
            effect: 效果配置字典
        """
        if effect in self.active_effects:
            self.active_effects.remove(effect)
            logger.debug(f"{self.name} 移除效果: {effect.get('name', 'Unknown')}")

    def can_attack(self) -> bool:
        """
        检查是否可以攻击

        返回:
            是否可以攻击
        """
        return self.is_alive and self.attack_cooldown <= 0

    def attack_target(self, target: 'Entity') -> None:
        """
        攻击目标

        参数:
            target: 目标实体
        """
        if not self.can_attack():
            return

        # 造成伤害
        target.take_damage(self.attack)

        # 重置冷却
        self.attack_cooldown = 1.0 / self.attack_speed

        # 切换状态
        self.state = EntityState.ATTACKING

        logger.debug(f"{self.name} 攻击 {target.name}")

    def on_hit(self, damage: int, damage_type: str) -> None:
        """
        受伤回调（可被子类重写）

        参数:
            damage: 伤害值
            damage_type: 伤害类型
        """
        pass

    def on_death(self) -> None:
        """
        死亡回调（可被子类重写）
        """
        self.is_alive = False
        self.state = EntityState.DEAD
        logger.info(f"{self.name} 死亡")

    def destroy(self) -> None:
        """
        销毁实体（释放资源）
        """
        self.is_active = False
        self.sprite = None
        logger.debug(f"销毁实体: {self.name} ({self.entity_id})")


class EntityManager:
    """
    实体管理器类
    功能：
    1. 创建、销毁和管理所有游戏实体
    2. 提供实体查询和过滤功能
    3. 统一调度实体的更新和渲染
    """

    def __init__(self):
        """初始化实体管理器"""
        self.entities: Dict[str, Entity] = {}  # 所有实体
        self.entity_counter = 0  # 实体计数器（用于生成唯一ID）

        logger.info("实体管理器初始化完成")

    def create_entity(self, entity_type: EntityType, config: Dict) -> Entity:
        """
        创建实体

        参数:
            entity_type: 实体类型
            config: 实体配置

        返回:
            创建的实体对象
        """
        # 生成唯一ID
        self.entity_counter += 1
        entity_id = f"{entity_type.value}_{self.entity_counter}"

        # 创建实体
        entity = Entity(entity_id, entity_type, config)

        # 注册实体
        self.entities[entity_id] = entity

        logger.debug(f"创建实体: {entity.name} ({entity_id})")
        return entity

    def destroy_entity(self, entity_id: str) -> None:
        """
        销毁实体

        参数:
            entity_id: 实体ID
        """
        if entity_id in self.entities:
            entity = self.entities[entity_id]
            entity.destroy()
            del self.entities[entity_id]
            logger.debug(f"销毁实体: {entity_id}")

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        获取实体

        参数:
            entity_id: 实体ID

        返回:
            实体对象，不存在返回None
        """
        return self.entities.get(entity_id)

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """
        按类型获取实体列表

        参数:
            entity_type: 实体类型

        返回:
            实体列表
        """
        return [e for e in self.entities.values() if e.entity_type == entity_type]

    def get_alive_entities(self) -> List[Entity]:
        """
        获取所有存活实体

        返回:
            存活实体列表
        """
        return [e for e in self.entities.values() if e.is_alive]

    def update_all(self, delta_time: float) -> None:
        """
        更新所有实体

        参数:
            delta_time: 帧间隔时间（秒）
        """
        # 更新所有活跃实体
        for entity in list(self.entities.values()):
            if entity.is_active:
                entity.update(delta_time)

        # 清理死亡实体
        self.cleanup_dead_entities()

    def render_all(self, screen: pygame.Surface) -> None:
        """
        渲染所有实体

        参数:
            screen: pygame屏幕对象
        """
        for entity in self.entities.values():
            if entity.is_active:
                entity.render(screen)

    def cleanup_dead_entities(self) -> None:
        """
        清理死亡实体
        """
        dead_entities = [eid for eid, e in self.entities.items()
                        if not e.is_alive and e.state == EntityState.DEAD]

        for entity_id in dead_entities:
            # 延迟一段时间后再销毁（播放死亡动画）
            # TODO: 实现死亡动画播放完成后再销毁
            pass

    def clear_all(self) -> None:
        """
        清空所有实体
        """
        count = len(self.entities)
        self.entities.clear()
        self.entity_counter = 0
        logger.info(f"清空所有实体，共{count}个")

    def get_entity_count(self) -> int:
        """
        获取实体数量

        返回:
            实体数量
        """
        return len(self.entities)

    def get_stats(self) -> Dict[str, int]:
        """
        获取实体统计信息

        返回:
            统计信息字典
        """
        stats = {
            'total': len(self.entities),
            'alive': len(self.get_alive_entities()),
            'characters': len(self.get_entities_by_type(EntityType.CHARACTER)),
            'projectiles': len(self.get_entities_by_type(EntityType.PROJECTILE)),
            'summons': len(self.get_entities_by_type(EntityType.SUMMON)),
            'effects': len(self.get_entities_by_type(EntityType.EFFECT)),
        }
        return stats


# 全局实体管理器实例（单例模式）
_entity_manager_instance: Optional[EntityManager] = None


def get_entity_manager() -> EntityManager:
    """
    获取实体管理器实例（单例）

    返回:
        EntityManager实例
    """
    global _entity_manager_instance

    if _entity_manager_instance is None:
        _entity_manager_instance = EntityManager()

    return _entity_manager_instance
