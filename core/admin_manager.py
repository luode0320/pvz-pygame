"""
管理界面核心引擎 - CrossVerse Arena核心模块
所有配置操作的唯一入口
"""

import logging
from pathlib import Path
from typing import Dict, Optional
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)


class AdminManager:
    """
    管理界面管理器类
    功能：
    1. 所有配置操作的唯一入口
    2. 配置验证和引用检查
    3. 回收站管理
    4. 操作日志记录
    """

    def __init__(self, root_dir: str = "."):
        """初始化管理界面管理器"""
        self.root_dir = Path(root_dir)
        self.recycle_bin = self.root_dir / "admin" / "recycle_bin"
        self.log_file = self.root_dir / "admin" / "admin_log.txt"

        # 确保目录存在
        self.recycle_bin.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info("管理界面管理器初始化完成")

    def log_operation(self, operation: str, details: str) -> None:
        """
        记录操作日志

        参数:
            operation: 操作类型
            details: 详细信息
        """
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {operation}: {details}\n"

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)

        logger.info(f"记录操作: {operation} - {details}")

    def delete_config(self, config_path: str, config_type: str) -> bool:
        """
        删除配置（移动到回收站）

        参数:
            config_path: 配置文件路径
            config_type: 配置类型

        返回:
            是否成功
        """
        try:
            source = Path(config_path)
            if not source.exists():
                logger.warning(f"配置文件不存在: {config_path}")
                return False

            # 移动到回收站
            recycle_path = self.recycle_bin / config_type / source.name
            recycle_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(recycle_path))

            self.log_operation("DELETE", f"{config_type}: {config_path}")
            logger.info(f"删除配置（移至回收站）: {config_path}")
            return True

        except Exception as e:
            logger.error(f"删除配置失败: {e}")
            return False

    def restore_config(self, recycle_path: str, original_path: str) -> bool:
        """
        从回收站恢复配置

        参数:
            recycle_path: 回收站中的路径
            original_path: 原始路径

        返回:
            是否成功
        """
        try:
            source = Path(recycle_path)
            target = Path(original_path)

            if not source.exists():
                logger.warning(f"回收站文件不存在: {recycle_path}")
                return False

            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))

            self.log_operation("RESTORE", f"{recycle_path} -> {original_path}")
            logger.info(f"恢复配置: {original_path}")
            return True

        except Exception as e:
            logger.error(f"恢复配置失败: {e}")
            return False


# 全局实例
_admin_manager_instance: Optional[AdminManager] = None


def get_admin_manager(root_dir: str = ".") -> AdminManager:
    """获取管理界面管理器实例"""
    global _admin_manager_instance
    if _admin_manager_instance is None:
        _admin_manager_instance = AdminManager(root_dir)
    return _admin_manager_instance
