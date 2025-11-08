"""
技能执行引擎 - CrossVerse Arena核心模块
负责技能的执行、冷却管理和效果触发
"""

import logging
from typing import Dict, List, Optional, Callable
import time

logger = logging.getLogger(__name__)


class SkillExecutor:
    """
    技能执行引擎类
    功能：
    1. 执行技能逻辑（多线程/协程支持）
    2. 冷却时间管理
    3. 技能释放条件判断
    4. 帧同步控制
    """

    def __init__(self):
        """初始化技能执行引擎"""
        self.skill_cooldowns: Dict[str, float] = {}  # 技能冷却记录
        self.active_skills: List[Dict] = []  # 正在执行的技能
        logger.info("技能执行引擎初始化完成")

    def can_cast_skill(self, entity_id: str, skill_id: str, skill_config: Dict) -> bool:
        """
        判断是否可以释放技能

        参数:
            entity_id: 实体ID
            skill_id: 技能ID
            skill_config: 技能配置

        返回:
            是否可以释放
        """
        cooldown_key = f"{entity_id}_{skill_id}"

        # 检查冷却
        if cooldown_key in self.skill_cooldowns:
            remaining = self.skill_cooldowns[cooldown_key] - time.time()
            if remaining > 0:
                return False

        return True

    def execute_skill(self, entity_id: str, skill_id: str, skill_config: Dict,
                     target_pos: tuple = None) -> bool:
        """
        执行技能

        参数:
            entity_id: 释放者实体ID
            skill_id: 技能ID
            skill_config: 技能配置
            target_pos: 目标位置

        返回:
            是否成功执行
        """
        if not self.can_cast_skill(entity_id, skill_id, skill_config):
            return False

        # 设置冷却
        cooldown = skill_config.get('cooldown', 0)
        cooldown_key = f"{entity_id}_{skill_id}"
        self.skill_cooldowns[cooldown_key] = time.time() + cooldown

        # 记录技能执行
        skill_instance = {
            'entity_id': entity_id,
            'skill_id': skill_id,
            'config': skill_config,
            'target_pos': target_pos,
            'start_time': time.time()
        }
        self.active_skills.append(skill_instance)

        logger.info(f"实体{entity_id}释放技能{skill_id}")
        return True

    def update(self, delta_time: float) -> None:
        """
        更新技能执行状态

        参数:
            delta_time: 帧间隔时间
        """
        # 移除完成的技能
        completed = []
        for skill in self.active_skills:
            elapsed = time.time() - skill['start_time']
            if elapsed > 5.0:  # 假设技能最多执行5秒
                completed.append(skill)

        for skill in completed:
            self.active_skills.remove(skill)

    def clear_cooldowns(self) -> None:
        """清空所有冷却"""
        self.skill_cooldowns.clear()


# 全局实例
_skill_executor_instance: Optional[SkillExecutor] = None


def get_skill_executor() -> SkillExecutor:
    """获取技能执行引擎实例"""
    global _skill_executor_instance
    if _skill_executor_instance is None:
        _skill_executor_instance = SkillExecutor()
    return _skill_executor_instance
