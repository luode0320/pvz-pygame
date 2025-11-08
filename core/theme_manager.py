"""
UI主题管理器 - 负责管理所有UI样式配置
包括：颜色、字体大小、布局等
所有UI样式均可通过配置文件控制，支持三级fallback
"""

import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class ThemeManager:
    """
    UI主题管理器
    支持三级配置fallback：关卡配置 → 全局配置 → 硬编码默认值
    """

    def __init__(self, global_settings: dict):
        """
        初始化主题管理器

        参数:
            global_settings: 全局设置字典
        """
        self.global_settings = global_settings

        # 当前关卡的UI配置（可选）
        self.level_ui_config: Optional[dict] = None

        # 硬编码默认值（最后的fallback）
        self.default_config = self._init_default_config()

        logger.info("UI主题管理器初始化完成")

    def _init_default_config(self) -> dict:
        """
        初始化硬编码默认配置
        这是最后的fallback，确保即使配置文件缺失也能正常运行

        返回:
            默认配置字典
        """
        return {
            # ==================== 通用颜色配置 ====================
            "colors": {
                # 背景颜色
                "background": {
                    "main_menu": [20, 20, 40],              # 主菜单背景
                    "campaign_select": [30, 30, 50],        # 战役选择背景
                    "level_select": [25, 30, 45],           # 关卡选择背景
                    "character_select": [30, 40, 60],       # 角色选择背景
                    "battle": [40, 60, 40],                 # 战斗背景
                    "pause": [0, 0, 0, 180],                # 暂停遮罩（RGBA）
                    "victory": [40, 80, 40],                # 胜利背景
                    "defeat": [80, 40, 40]                  # 失败背景
                },

                # 文字颜色
                "text": {
                    "title": [255, 200, 50],                # 标题文字（金色）
                    "normal": [255, 255, 255],              # 普通文字（白色）
                    "subtitle": [200, 200, 200],            # 副标题文字（浅灰）
                    "hint": [120, 120, 150],                # 提示文字（深蓝灰）
                    "success": [100, 255, 100],             # 成功文字（绿色）
                    "warning": [255, 200, 50],              # 警告文字（黄色）
                    "error": [255, 100, 100],               # 错误文字（红色）
                    "info": [150, 200, 255]                 # 信息文字（蓝色）
                },

                # 按钮颜色
                "button": {
                    "normal_bg": [60, 60, 90],              # 正常背景
                    "normal_border": [100, 120, 160],       # 正常边框
                    "normal_text": [220, 220, 220],         # 正常文字
                    "hover_bg": [80, 80, 120],              # 悬停背景
                    "hover_border": [150, 180, 220],        # 悬停边框
                    "hover_text": [255, 255, 100],          # 悬停文字
                    "disabled_bg": [40, 40, 40],            # 禁用背景
                    "disabled_border": [80, 80, 80],        # 禁用边框
                    "disabled_text": [120, 120, 120]        # 禁用文字
                },

                # 卡片颜色（关卡选择、角色选择等）
                "card": {
                    # 关卡卡片
                    "level_completed_bg": [40, 80, 40],     # 已完成背景（绿色）
                    "level_completed_border": [80, 160, 80],# 已完成边框
                    "level_completed_text": [100, 255, 100],# 已完成文字
                    "level_unlocked_bg": [60, 70, 90],      # 已解锁背景（蓝色）
                    "level_unlocked_hover_bg": [80, 90, 120],# 已解锁悬停背景
                    "level_unlocked_border": [100, 120, 160],# 已解锁边框
                    "level_unlocked_hover_border": [150, 180, 220],# 已解锁悬停边框
                    "level_unlocked_text": [150, 200, 255], # 已解锁文字
                    "level_locked_bg": [40, 40, 40],        # 未解锁背景（灰色）
                    "level_locked_border": [80, 80, 80],    # 未解锁边框
                    "level_locked_text": [150, 150, 150],   # 未解锁文字

                    # 角色卡片
                    "character_selected_bg": [100, 150, 255],# 已选中背景
                    "character_selected_border": [150, 200, 255],# 已选中边框
                    "character_hover_bg": [70, 90, 120],    # 悬停背景
                    "character_hover_border": [150, 180, 220],# 悬停边框
                    "character_normal_bg": [50, 60, 80],    # 正常背景
                    "character_normal_border": [100, 120, 150]# 正常边框
                },

                # 游戏内UI颜色
                "game_ui": {
                    "grid_dark": [50, 70, 50],              # 深色网格
                    "grid_light": [60, 80, 60],             # 浅色网格
                    "grid_border": [80, 100, 80],           # 网格边框
                    "hp_bar_bg": [100, 0, 0],               # 血条背景
                    "hp_bar_fg": [0, 255, 0],               # 血条前景
                    "gold_text": [255, 200, 50],            # 金币文字
                    "hp_text": [255, 100, 100],             # 血量文字
                    "wave_text": [200, 200, 200],           # 波次文字
                    "enemy_text": [255, 150, 150]           # 敌人文字
                },

                # 图标颜色（用于文字图标）
                "icon": {
                    "gold": [255, 200, 50],                 # 金币图标
                    "hp": [255, 100, 100],                  # 血量图标
                    "wave": [100, 200, 255],                # 波次图标
                    "reward": [255, 200, 100],              # 奖励图标
                    "exp": [255, 150, 255]                  # 经验图标
                }
            },

            # ==================== 布局配置 ====================
            "layout": {
                # 边距和间距
                "padding": {
                    "small": 10,
                    "normal": 20,
                    "large": 40
                },

                # 按钮尺寸
                "button": {
                    "width": 300,
                    "height": 50,
                    "spacing": 70
                },

                # 卡片尺寸
                "card": {
                    "level_width": 360,
                    "level_height": 140,
                    "level_spacing_x": 20,
                    "level_spacing_y": 20,
                    "character_width": 150,
                    "character_height": 200,
                    "character_spacing": 20
                }
            }
        }

    def set_level_config(self, level_config: Optional[dict]):
        """
        设置当前关卡的UI配置

        参数:
            level_config: 关卡配置字典（可为None）
        """
        self.level_ui_config = level_config.get('ui_theme') if level_config else None
        if self.level_ui_config:
            logger.info("加载关卡自定义UI配置")

    def get_color(self, category: str, key: str) -> Tuple[int, int, int]:
        """
        获取颜色配置（RGB）
        支持三级fallback：关卡配置 → 全局配置 → 默认配置

        参数:
            category: 颜色类别（如 "background", "text", "button"等）
            key: 颜色键（如 "main_menu", "title"等）

        返回:
            RGB颜色元组 (r, g, b)
        """
        # 1. 尝试从关卡配置读取
        if self.level_ui_config:
            color = self.level_ui_config.get('colors', {}).get(category, {}).get(key)
            if color is not None:
                return tuple(color) if isinstance(color, list) else color

        # 2. 尝试从全局配置读取
        global_ui = self.global_settings.get('ui_theme', {})
        color = global_ui.get('colors', {}).get(category, {}).get(key)
        if color is not None:
            return tuple(color) if isinstance(color, list) else color

        # 3. 使用默认配置
        color = self.default_config['colors'].get(category, {}).get(key)
        if color is not None:
            return tuple(color) if isinstance(color, list) else color

        # 4. 如果都没有，返回白色作为最终fallback
        logger.warning(f"未找到颜色配置: {category}.{key}，使用白色")
        return (255, 255, 255)

    def get_layout(self, category: str, key: str, default: Any = 0) -> Any:
        """
        获取布局配置
        支持三级fallback：关卡配置 → 全局配置 → 默认配置

        参数:
            category: 布局类别（如 "padding", "button", "card"）
            key: 布局键（如 "small", "width"等）
            default: 默认值

        返回:
            布局值
        """
        # 1. 尝试从关卡配置读取
        if self.level_ui_config:
            value = self.level_ui_config.get('layout', {}).get(category, {}).get(key)
            if value is not None:
                return value

        # 2. 尝试从全局配置读取
        global_ui = self.global_settings.get('ui_theme', {})
        value = global_ui.get('layout', {}).get(category, {}).get(key)
        if value is not None:
            return value

        # 3. 使用默认配置
        value = self.default_config['layout'].get(category, {}).get(key)
        if value is not None:
            return value

        # 4. 返回提供的默认值
        return default

    def get_background_color(self, screen_name: str) -> Tuple[int, int, int]:
        """
        获取页面背景颜色的便捷方法

        参数:
            screen_name: 页面名称（如 "main_menu", "battle"等）

        返回:
            RGB颜色元组
        """
        return self.get_color("background", screen_name)

    def get_text_color(self, text_type: str) -> Tuple[int, int, int]:
        """
        获取文字颜色的便捷方法

        参数:
            text_type: 文字类型（如 "title", "normal", "hint"等）

        返回:
            RGB颜色元组
        """
        return self.get_color("text", text_type)


# 全局单例
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager(global_settings: dict = None) -> ThemeManager:
    """
    获取UI主题管理器单例

    参数:
        global_settings: 全局设置字典（仅首次调用时需要）

    返回:
        ThemeManager实例
    """
    global _theme_manager
    if _theme_manager is None:
        if global_settings is None:
            raise ValueError("首次调用get_theme_manager时必须提供global_settings")
        _theme_manager = ThemeManager(global_settings)
    return _theme_manager
