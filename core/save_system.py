"""
存档系统 - CrossVerse Arena核心模块
管理游戏存档的保存和加载
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SaveSystem:
    """
    存档系统类
    功能：
    1. 保存和加载游戏进度
    2. 支持多个存档槽位
    3. 版本控制和数据迁移
    """

    def __init__(self, save_dir: str = "saves"):
        """
        初始化存档系统

        参数:
            save_dir: 存档目录
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"存档系统初始化完成，目录: {self.save_dir}")

    def save_game(self, slot_name: str, game_data: Dict) -> bool:
        """
        保存游戏

        参数:
            slot_name: 存档槽位名称
            game_data: 游戏数据

        返回:
            是否成功
        """
        try:
            save_file = self.save_dir / f"{slot_name}.json"

            # 添加元数据
            save_data = {
                'version': '1.0',
                'timestamp': datetime.now().isoformat(),
                'data': game_data
            }

            with open(save_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            logger.info(f"保存游戏成功: {slot_name}")
            return True

        except Exception as e:
            logger.error(f"保存游戏失败 {slot_name}: {e}")
            return False

    def load_game(self, slot_name: str) -> Optional[Dict]:
        """
        加载游戏

        参数:
            slot_name: 存档槽位名称

        返回:
            游戏数据字典，失败返回None
        """
        try:
            save_file = self.save_dir / f"{slot_name}.json"

            if not save_file.exists():
                logger.warning(f"存档不存在: {slot_name}")
                return None

            with open(save_file, 'r', encoding='utf-8') as f:
                save_data = json.load(f)

            logger.info(f"加载游戏成功: {slot_name}")
            return save_data.get('data', {})

        except Exception as e:
            logger.error(f"加载游戏失败 {slot_name}: {e}")
            return None

    def delete_save(self, slot_name: str) -> bool:
        """删除存档"""
        try:
            save_file = self.save_dir / f"{slot_name}.json"
            if save_file.exists():
                save_file.unlink()
                logger.info(f"删除存档: {slot_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除存档失败 {slot_name}: {e}")
            return False


# 全局实例
_save_system_instance: Optional[SaveSystem] = None


def get_save_system(save_dir: str = "saves") -> SaveSystem:
    """获取存档系统实例"""
    global _save_system_instance
    if _save_system_instance is None:
        _save_system_instance = SaveSystem(save_dir)
    return _save_system_instance
