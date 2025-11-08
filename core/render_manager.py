"""
渲染管理器 - CrossVerse Arena核心模块
统一管理游戏渲染管线
"""

import logging
import pygame

logger = logging.getLogger(__name__)


class RenderManager:
    """
    渲染管理器类
    功能：
    1. 统一管理渲染管线
    2. 控制画质参数
    3. 优化渲染性能
    """

    def __init__(self, config: dict):
        """初始化渲染管理器"""
        self.config = config
        self.render_pipeline = config.get('render_pipeline', 'forward')
        self.anti_aliasing = config.get('anti_aliasing', 'fxaa')
        logger.info(f"渲染管理器初始化: {self.render_pipeline}管线, {self.anti_aliasing}抗锯齿")

    def render_frame(self, screen: pygame.Surface, entities: list) -> None:
        """渲染一帧"""
        # 简化实现：直接渲染实体
        for entity in entities:
            if hasattr(entity, 'render'):
                entity.render(screen)


# 全局实例
def get_render_manager(config: dict = None):
    """获取渲染管理器实例"""
    if config:
        return RenderManager(config)
    return None
