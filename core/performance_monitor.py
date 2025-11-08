"""
性能监控系统 - CrossVerse Arena核心模块
实时监控游戏运行性能
"""

import logging
import psutil
import time
from typing import Dict, List

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    性能监控器类
    功能：
    1. 实时监控帧率、CPU、内存占用
    2. 检测性能异常并触发告警
    3. 记录性能数据用于分析
    """

    def __init__(self, config: Dict):
        """
        初始化性能监控器

        参数:
            config: 性能配置
        """
        self.config = config
        self.enabled = config.get('enabled', True)

        # 性能阈值
        self.fps_warning = config.get('fps_warning_threshold', 30)
        self.fps_danger = config.get('fps_danger_threshold', 20)
        self.memory_warning = config.get('memory_warning_threshold', 0.6)

        # 性能数据记录
        self.fps_history: List[float] = []
        self.memory_history: List[float] = []

        # 统计数据
        self.frame_count = 0
        self.last_update_time = time.time()

        logger.info("性能监控系统初始化完成")

    def update(self, current_fps: float) -> None:
        """
        更新性能监控

        参数:
            current_fps: 当前帧率
        """
        if not self.enabled:
            return

        self.frame_count += 1

        # 记录FPS
        self.fps_history.append(current_fps)
        if len(self.fps_history) > 60:
            self.fps_history.pop(0)

        # 定期检查内存
        current_time = time.time()
        if current_time - self.last_update_time >= 1.0:
            memory_percent = psutil.virtual_memory().percent / 100.0
            self.memory_history.append(memory_percent)
            if len(self.memory_history) > 60:
                self.memory_history.pop(0)

            # 检查性能警告
            self.check_performance_warnings(current_fps, memory_percent)

            self.last_update_time = current_time

    def check_performance_warnings(self, fps: float, memory: float) -> None:
        """检查性能警告"""
        if fps < self.fps_danger:
            logger.warning(f"帧率严重下降: {fps:.1f} FPS")
        elif fps < self.fps_warning:
            logger.warning(f"帧率偏低: {fps:.1f} FPS")

        if memory > self.memory_warning:
            logger.warning(f"内存占用过高: {memory*100:.1f}%")

    def get_stats(self) -> Dict:
        """获取性能统计"""
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        avg_memory = sum(self.memory_history) / len(self.memory_history) if self.memory_history else 0

        return {
            'current_fps': self.fps_history[-1] if self.fps_history else 0,
            'avg_fps': avg_fps,
            'memory_percent': avg_memory,
            'frame_count': self.frame_count
        }


# 全局实例
_performance_monitor_instance = None


def get_performance_monitor(config: Dict = None):
    """获取性能监控器实例"""
    global _performance_monitor_instance
    if _performance_monitor_instance is None and config:
        _performance_monitor_instance = PerformanceMonitor(config)
    return _performance_monitor_instance
