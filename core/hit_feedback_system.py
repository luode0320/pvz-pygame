"""
打击感反馈系统 - Hit Feedback System
处理屏幕震动、伤害数字、粒子效果等视觉反馈
"""

import pygame
import random
import math
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DamageNumber:
    """伤害数字"""
    x: float
    y: float
    text: str
    color: Tuple[int, int, int]
    velocity_y: float = -100  # 向上飘动速度
    lifetime: float = 1.5  # 存活时间
    age: float = 0  # 已存在时间
    font_size: int = 24
    is_crit: bool = False  # 是否暴击


@dataclass
class Particle:
    """粒子"""
    x: float
    y: float
    vx: float  # X方向速度
    vy: float  # Y方向速度
    size: int
    color: Tuple[int, int, int]
    lifetime: float
    age: float = 0


class ScreenShake:
    """屏幕震动效果"""

    def __init__(self):
        self.offset_x = 0
        self.offset_y = 0
        self.intensity = 0
        self.duration = 0
        self.time_remaining = 0

    def trigger(self, intensity: float = 10, duration: float = 0.3):
        """
        触发屏幕震动

        参数:
            intensity: 震动强度（像素）
            duration: 持续时间（秒）
        """
        self.intensity = intensity
        self.duration = duration
        self.time_remaining = duration

    def update(self, delta_time: float):
        """更新震动"""
        if self.time_remaining <= 0:
            self.offset_x = 0
            self.offset_y = 0
            return

        self.time_remaining -= delta_time

        # 震动强度随时间衰减
        progress = 1.0 - (self.time_remaining / self.duration)
        current_intensity = self.intensity * (1.0 - progress)

        # 随机偏移
        self.offset_x = random.uniform(-current_intensity, current_intensity)
        self.offset_y = random.uniform(-current_intensity, current_intensity)

    def get_offset(self) -> Tuple[int, int]:
        """获取当前偏移量"""
        return (int(self.offset_x), int(self.offset_y))

    def is_active(self) -> bool:
        """是否正在震动"""
        return self.time_remaining > 0


class HitFeedbackSystem:
    """
    打击感反馈系统
    功能：
    1. 屏幕震动
    2. 伤害数字显示
    3. 粒子效果
    4. 命中闪烁
    """

    def __init__(self):
        """初始化打击感反馈系统"""
        # 屏幕震动
        self.screen_shake = ScreenShake()

        # 伤害数字列表
        self.damage_numbers: List[DamageNumber] = []

        # 粒子列表
        self.particles: List[Particle] = []

        # 字体缓存
        self.fonts = {
            20: pygame.font.Font(None, 20),
            24: pygame.font.Font(None, 24),
            32: pygame.font.Font(None, 32),
            48: pygame.font.Font(None, 48)
        }

        # 配置
        self.max_damage_numbers = 50
        self.max_particles = 200

        logger.info("打击感反馈系统初始化完成")

    def trigger_screen_shake(self, intensity: float = 10, duration: float = 0.3):
        """
        触发屏幕震动

        参数:
            intensity: 震动强度
            duration: 持续时间
        """
        self.screen_shake.trigger(intensity, duration)

    def show_damage(self, x: float, y: float, damage: int, is_crit: bool = False,
                   color: Optional[Tuple[int, int, int]] = None):
        """
        显示伤害数字

        参数:
            x, y: 位置
            damage: 伤害值
            is_crit: 是否暴击
            color: 颜色（None=自动选择）
        """
        if len(self.damage_numbers) >= self.max_damage_numbers:
            self.damage_numbers.pop(0)

        # 自动选择颜色
        if color is None:
            if is_crit:
                color = (255, 200, 0)  # 金黄色 - 暴击
            elif damage > 100:
                color = (255, 100, 100)  # 红色 - 高伤害
            else:
                color = (255, 255, 255)  # 白色 - 普通伤害

        # 字体大小
        font_size = 48 if is_crit else 24

        # 添加随机偏移避免重叠
        offset_x = random.uniform(-20, 20)

        damage_num = DamageNumber(
            x=x + offset_x,
            y=y - 30,
            text=str(damage),
            color=color,
            font_size=font_size,
            is_crit=is_crit
        )

        self.damage_numbers.append(damage_num)

    def show_heal(self, x: float, y: float, heal_amount: int):
        """
        显示治疗数字

        参数:
            x, y: 位置
            heal_amount: 治疗量
        """
        self.show_damage(x, y, heal_amount, is_crit=False, color=(100, 255, 100))

    def create_hit_particles(self, x: float, y: float, count: int = 10,
                            color: Optional[Tuple[int, int, int]] = None):
        """
        创建命中粒子效果

        参数:
            x, y: 位置
            count: 粒子数量
            color: 粒子颜色
        """
        if len(self.particles) >= self.max_particles:
            return

        if color is None:
            color = (255, 200, 100)

        for _ in range(count):
            # 随机速度和方向
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 150)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            particle = Particle(
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                size=random.randint(3, 8),
                color=color,
                lifetime=random.uniform(0.3, 0.8)
            )

            self.particles.append(particle)

    def create_explosion_particles(self, x: float, y: float, count: int = 30):
        """
        创建爆炸粒子效果

        参数:
            x, y: 位置
            count: 粒子数量
        """
        colors = [
            (255, 100, 0),   # 橙色
            (255, 200, 0),   # 黄色
            (255, 50, 50),   # 红色
        ]

        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(100, 300)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            particle = Particle(
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                size=random.randint(5, 12),
                color=random.choice(colors),
                lifetime=random.uniform(0.5, 1.2)
            )

            self.particles.append(particle)

    def update(self, delta_time: float):
        """更新所有效果"""
        # 更新屏幕震动
        self.screen_shake.update(delta_time)

        # 更新伤害数字
        for dmg_num in self.damage_numbers[:]:
            dmg_num.age += delta_time
            dmg_num.y += dmg_num.velocity_y * delta_time

            if dmg_num.age >= dmg_num.lifetime:
                self.damage_numbers.remove(dmg_num)

        # 更新粒子
        for particle in self.particles[:]:
            particle.age += delta_time
            particle.x += particle.vx * delta_time
            particle.y += particle.vy * delta_time

            # 重力影响
            particle.vy += 300 * delta_time

            if particle.age >= particle.lifetime:
                self.particles.remove(particle)

    def render(self, screen: pygame.Surface):
        """渲染所有效果"""
        # 渲染粒子
        for particle in self.particles:
            # 根据生命周期调整透明度
            alpha = 1.0 - (particle.age / particle.lifetime)
            color = tuple(int(c * alpha) for c in particle.color)

            pygame.draw.circle(
                screen,
                color,
                (int(particle.x), int(particle.y)),
                particle.size
            )

        # 渲染伤害数字
        for dmg_num in self.damage_numbers:
            # 根据生命周期调整透明度
            alpha = 1.0 - (dmg_num.age / dmg_num.lifetime)

            # 获取字体
            font = self.fonts.get(dmg_num.font_size, self.fonts[24])

            # 渲染文字
            text_surface = font.render(dmg_num.text, True, dmg_num.color)

            # 应用透明度（需要转换为带alpha的surface）
            text_surface = text_surface.convert_alpha()
            text_surface.set_alpha(int(255 * alpha))

            # 绘制
            text_rect = text_surface.get_rect(center=(int(dmg_num.x), int(dmg_num.y)))

            # 暴击效果：添加描边
            if dmg_num.is_crit:
                outline_color = (255, 255, 255)
                for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    outline_surface = font.render(dmg_num.text, True, outline_color)
                    outline_surface.set_alpha(int(255 * alpha))
                    outline_rect = outline_surface.get_rect(
                        center=(int(dmg_num.x + dx), int(dmg_num.y + dy))
                    )
                    screen.blit(outline_surface, outline_rect)

            screen.blit(text_surface, text_rect)

    def clear(self):
        """清除所有效果"""
        self.damage_numbers.clear()
        self.particles.clear()
        self.screen_shake.time_remaining = 0


# 全局打击感反馈系统实例
_hit_feedback_system: Optional[HitFeedbackSystem] = None


def get_hit_feedback_system() -> HitFeedbackSystem:
    """获取全局打击感反馈系统实例"""
    global _hit_feedback_system
    if _hit_feedback_system is None:
        _hit_feedback_system = HitFeedbackSystem()
    return _hit_feedback_system
