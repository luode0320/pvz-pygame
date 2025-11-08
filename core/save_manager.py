"""
存档管理器 - 负责玩家进度存储和加载
包括：关卡解锁状态、角色解锁、成就等
"""

import json
import os
import logging
from typing import Dict, Set, Optional

logger = logging.getLogger(__name__)


class SaveManager:
    """
    存档管理器
    管理玩家的游戏进度、解锁状态等数据
    """

    def __init__(self, save_dir: str = "saves"):
        """
        初始化存档管理器

        参数:
            save_dir: 存档文件目录
        """
        self.save_dir = save_dir
        self.save_file = os.path.join(save_dir, "player_save.json")

        # 确保存档目录存在
        os.makedirs(save_dir, exist_ok=True)

        # 存档数据结构
        self.data = {
            "unlocked_levels": set(),  # 已解锁的关卡ID集合
            "completed_levels": set(),  # 已完成的关卡ID集合
            "unlocked_characters": set(),  # 已解锁的角色ID集合
            "unlocked_skins": set(),  # 已解锁的皮肤ID集合
            "player_stats": {  # 玩家统计数据
                "total_gold": 0,
                "total_exp": 0,
                "total_battles": 0,
                "total_victories": 0,
            }
        }

        # 加载存档
        self.load()

        logger.info("存档管理器初始化完成")

    def load(self):
        """加载存档文件"""
        if not os.path.exists(self.save_file):
            logger.info("未找到存档文件，创建新存档")
            # 默认解锁所有战役的第一关
            self._init_default_unlocks()
            self.save()
            return

        try:
            with open(self.save_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)

                # 转换列表为集合
                self.data["unlocked_levels"] = set(loaded_data.get("unlocked_levels", []))
                self.data["completed_levels"] = set(loaded_data.get("completed_levels", []))
                self.data["unlocked_characters"] = set(loaded_data.get("unlocked_characters", []))
                self.data["unlocked_skins"] = set(loaded_data.get("unlocked_skins", []))
                self.data["player_stats"] = loaded_data.get("player_stats", self.data["player_stats"])

                logger.info(f"存档加载成功: {len(self.data['unlocked_levels'])} 个已解锁关卡")
        except Exception as e:
            logger.error(f"加载存档失败: {e}")
            self._init_default_unlocks()

    def save(self):
        """保存存档文件"""
        try:
            # 转换集合为列表以便JSON序列化
            save_data = {
                "unlocked_levels": list(self.data["unlocked_levels"]),
                "completed_levels": list(self.data["completed_levels"]),
                "unlocked_characters": list(self.data["unlocked_characters"]),
                "unlocked_skins": list(self.data["unlocked_skins"]),
                "player_stats": self.data["player_stats"]
            }

            with open(self.save_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            logger.debug("存档保存成功")
        except Exception as e:
            logger.error(f"保存存档失败: {e}")

    def _init_default_unlocks(self):
        """初始化默认解锁内容（所有战役的第一关）"""
        # 默认解锁所有战役的第一关
        self.data["unlocked_levels"].add("dnf_vs_lol/level_01")
        # 可以添加更多默认解锁的战役第一关
        logger.info("初始化默认解锁：第一关")

    def is_level_unlocked(self, level_id: str) -> bool:
        """
        检查关卡是否已解锁

        参数:
            level_id: 关卡ID（格式：campaign_id/level_id）

        返回:
            是否已解锁
        """
        return level_id in self.data["unlocked_levels"]

    def is_level_completed(self, level_id: str) -> bool:
        """
        检查关卡是否已完成

        参数:
            level_id: 关卡ID

        返回:
            是否已完成
        """
        return level_id in self.data["completed_levels"]

    def unlock_level(self, level_id: str):
        """
        解锁关卡

        参数:
            level_id: 关卡ID
        """
        self.data["unlocked_levels"].add(level_id)
        self.save()
        logger.info(f"解锁关卡: {level_id}")

    def complete_level(self, level_id: str, rewards: dict = None):
        """
        完成关卡并解锁下一关

        参数:
            level_id: 已完成的关卡ID
            rewards: 奖励信息（金币、经验等）
        """
        # 标记关卡为已完成
        self.data["completed_levels"].add(level_id)

        # 处理奖励
        if rewards:
            self.data["player_stats"]["total_gold"] += rewards.get("gold", 0)
            self.data["player_stats"]["total_exp"] += rewards.get("exp", 0)

            # 解锁下一关
            unlock_levels = rewards.get("unlock_levels", [])
            for next_level in unlock_levels:
                # 构造完整的关卡ID
                campaign_id = level_id.split('/')[0]
                full_level_id = f"{campaign_id}/{next_level}"
                self.unlock_level(full_level_id)

        # 更新统计
        self.data["player_stats"]["total_battles"] += 1
        self.data["player_stats"]["total_victories"] += 1

        self.save()
        logger.info(f"完成关卡: {level_id}")

    def unlock_character(self, character_id: str):
        """解锁角色"""
        self.data["unlocked_characters"].add(character_id)
        self.save()
        logger.info(f"解锁角色: {character_id}")

    def unlock_skin(self, skin_id: str):
        """解锁皮肤"""
        self.data["unlocked_skins"].add(skin_id)
        self.save()
        logger.info(f"解锁皮肤: {skin_id}")

    def get_campaign_progress(self, campaign_id: str, all_levels: list) -> dict:
        """
        获取战役进度

        参数:
            campaign_id: 战役ID
            all_levels: 该战役的所有关卡列表

        返回:
            进度信息字典
        """
        campaign_levels = [lvl for lvl in all_levels if lvl.startswith(campaign_id)]
        completed = sum(1 for lvl in campaign_levels if self.is_level_completed(lvl))
        total = len(campaign_levels)

        return {
            "completed": completed,
            "total": total,
            "percentage": (completed / total * 100) if total > 0 else 0
        }

    def reset_progress(self):
        """重置所有进度（调试用）"""
        self.data["unlocked_levels"].clear()
        self.data["completed_levels"].clear()
        self.data["unlocked_characters"].clear()
        self.data["unlocked_skins"].clear()
        self.data["player_stats"] = {
            "total_gold": 0,
            "total_exp": 0,
            "total_battles": 0,
            "total_victories": 0,
        }
        self._init_default_unlocks()
        self.save()
        logger.warning("已重置所有进度")


# 全局单例
_save_manager: Optional[SaveManager] = None


def get_save_manager(save_dir: str = "saves") -> SaveManager:
    """
    获取存档管理器单例

    参数:
        save_dir: 存档目录

    返回:
        存档管理器实例
    """
    global _save_manager
    if _save_manager is None:
        _save_manager = SaveManager(save_dir)
    return _save_manager
