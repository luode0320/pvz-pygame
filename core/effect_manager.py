"""
效果管理器 - CrossVerse Arena核心模块
管理技能效果的状态、持续时间、渲染层级
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class EffectManager:
    """
    效果管理器类
    功能：
    1. 管理技能效果的状态和持续时间
    2. 处理效果叠加和冲突解决
    3. 效果渲染控制
    """

    def __init__(self):
        """初始化效果管理器"""
        self.active_effects: Dict[str, List[Dict]] = {}  # 实体ID -> 效果列表
        logger.info("效果管理器初始化完成")

    def apply_effect(self, entity_id: str, effect_config: Dict) -> None:
        """
        应用效果到实体

        参数:
            entity_id: 实体ID
            effect_config: 效果配置
        """
        if entity_id not in self.active_effects:
            self.active_effects[entity_id] = []

        effect_instance = {
            'effect_id': effect_config.get('effect_id'),
            'name': effect_config.get('name'),
            'type': effect_config.get('type'),
            'duration': effect_config.get('parameters', {}).get('duration', 0),
            'remaining_time': effect_config.get('parameters', {}).get('duration', 0),
            'config': effect_config
        }

        self.active_effects[entity_id].append(effect_instance)
        logger.info(f"对实体{entity_id}应用效果: {effect_instance['name']}")

    def update(self, delta_time: float) -> None:
        """
        更新所有效果

        参数:
            delta_time: 帧间隔时间
        """
        for entity_id, effects in list(self.active_effects.items()):
            expired = []
            for effect in effects:
                effect['remaining_time'] -= delta_time
                if effect['remaining_time'] <= 0:
                    expired.append(effect)

            for effect in expired:
                effects.remove(effect)

            if not effects:
                del self.active_effects[entity_id]

    def clear_entity_effects(self, entity_id: str) -> None:
        """清除实体的所有效果"""
        if entity_id in self.active_effects:
            del self.active_effects[entity_id]


# 全局实例
_effect_manager_instance: Optional[EffectManager] = None


def get_effect_manager() -> EffectManager:
    """获取效果管理器实例"""
    global _effect_manager_instance
    if _effect_manager_instance is None:
        _effect_manager_instance = EffectManager()
    return _effect_manager_instance
