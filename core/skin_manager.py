"""
皮肤管理系统 - CrossVerse Arena核心模块
管理角色皮肤系统，支持动态切换皮肤
"""

import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class SkinManager:
    """
    皮肤管理器类
    功能：
    1. 管理角色皮肤系统
    2. 支持动态切换皮肤
    3. 处理皮肤专属资源加载
    """

    def __init__(self, config_loader, resource_loader):
        """
        初始化皮肤管理器

        参数:
            config_loader: 配置加载器
            resource_loader: 资源加载器
        """
        self.config_loader = config_loader
        self.resource_loader = resource_loader
        self.equipped_skins: Dict[str, str] = {}  # 角色ID -> 皮肤ID
        logger.info("皮肤管理器初始化完成")

    def get_available_skins(self, character_id: str) -> List[Dict]:
        """
        获取角色的可用皮肤列表

        参数:
            character_id: 角色ID

        返回:
            皮肤配置列表
        """
        character_config = self.config_loader.get_character(character_id)
        if not character_config:
            return []

        available_skin_ids = character_config.get('available_skins', [])
        skins = []

        for skin_id in available_skin_ids:
            skin_config = self.config_loader.get_skin(skin_id)
            if skin_config:
                skins.append(skin_config)

        return skins

    def equip_skin(self, character_id: str, skin_id: str) -> bool:
        """
        装备皮肤

        参数:
            character_id: 角色ID
            skin_id: 皮肤ID

        返回:
            是否成功
        """
        skin_config = self.config_loader.get_skin(skin_id)
        if not skin_config:
            logger.warning(f"皮肤{skin_id}不存在")
            return False

        if skin_config['character_id'] != character_id:
            logger.warning(f"皮肤{skin_id}不属于角色{character_id}")
            return False

        self.equipped_skins[character_id] = skin_id
        logger.info(f"角色{character_id}装备皮肤{skin_id}")
        return True

    def get_equipped_skin(self, character_id: str) -> Optional[str]:
        """
        获取角色当前装备的皮肤

        参数:
            character_id: 角色ID

        返回:
            皮肤ID
        """
        return self.equipped_skins.get(character_id, 'basic')


# 全局实例
_skin_manager_instance: Optional[SkinManager] = None


def get_skin_manager(config_loader=None, resource_loader=None) -> SkinManager:
    """获取皮肤管理器实例"""
    global _skin_manager_instance
    if _skin_manager_instance is None and config_loader and resource_loader:
        _skin_manager_instance = SkinManager(config_loader, resource_loader)
    return _skin_manager_instance
