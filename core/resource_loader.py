"""
资源加载器 - CrossVerse Arena核心模块
负责加载和管理游戏资源（图片、音频、模型、材质等）
支持预加载、缓存管理和资源池优化
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List
import pygame

# 配置日志
logger = logging.getLogger(__name__)


class ResourceLoader:
    """
    资源加载器类
    功能：
    1. 加载和缓存游戏资源（图片、音频、特效、模型）
    2. 支持资源预加载，提升游戏性能
    3. 资源缺失时使用占位资源
    4. 资源池管理，自动释放未使用资源
    """

    def __init__(self, root_dir: str = "."):
        """
        初始化资源加载器

        参数:
            root_dir: 项目根目录路径
        """
        self.root_dir = Path(root_dir).resolve()

        # 资源缓存
        self.images: Dict[str, pygame.Surface] = {}  # 图片缓存
        self.sounds: Dict[str, pygame.mixer.Sound] = {}  # 音效缓存
        self.music_paths: Dict[str, str] = {}  # 音乐路径缓存
        self.animations: Dict[str, Any] = {}  # 动画缓存
        self.models: Dict[str, Any] = {}  # 3D模型缓存
        self.materials: Dict[str, Any] = {}  # 材质缓存
        self.shaders: Dict[str, Any] = {}  # 着色器缓存

        # 资源引用计数（用于资源池管理）
        self.ref_counts: Dict[str, int] = {}

        # 占位资源
        self.placeholder_image: Optional[pygame.Surface] = None
        self.placeholder_sound: Optional[pygame.mixer.Sound] = None

        # 预加载列表
        self.preload_list: List[str] = []

        logger.info(f"资源加载器初始化完成，根目录: {self.root_dir}")

    def init_pygame(self) -> None:
        """
        初始化pygame模块（图像和音频）
        """
        try:
            if not pygame.get_init():
                pygame.init()

            if not pygame.mixer.get_init():
                pygame.mixer.init()

            logger.info("Pygame模块初始化成功")
        except Exception as e:
            logger.error(f"Pygame初始化失败: {e}")

    def create_placeholder_image(self, width: int = 64, height: int = 64,
                                 color: tuple = (128, 128, 128)) -> pygame.Surface:
        """
        创建占位图片（灰色方块）

        参数:
            width: 宽度
            height: 高度
            color: 颜色（RGB）

        返回:
            pygame.Surface对象
        """
        surface = pygame.Surface((width, height))
        surface.fill(color)

        # 绘制边框
        pygame.draw.rect(surface, (64, 64, 64), surface.get_rect(), 2)

        # 绘制对角线
        pygame.draw.line(surface, (64, 64, 64), (0, 0), (width, height), 2)
        pygame.draw.line(surface, (64, 64, 64), (0, height), (width, 0), 2)

        return surface

    def get_placeholder_image(self) -> pygame.Surface:
        """
        获取占位图片

        返回:
            pygame.Surface对象
        """
        if self.placeholder_image is None:
            self.placeholder_image = self.create_placeholder_image()

        return self.placeholder_image

    def resolve_path(self, relative_path: str) -> Optional[Path]:
        """
        解析相对路径为绝对路径

        参数:
            relative_path: 相对路径

        返回:
            绝对路径，失败返回None
        """
        try:
            if os.path.isabs(relative_path):
                return Path(relative_path)
            else:
                return (self.root_dir / relative_path).resolve()
        except Exception as e:
            logger.error(f"路径解析失败 {relative_path}: {e}")
            return None

    def load_image(self, path: str, use_alpha: bool = True,
                   cache: bool = True) -> Optional[pygame.Surface]:
        """
        加载图片

        参数:
            path: 图片路径（相对或绝对）
            use_alpha: 是否使用Alpha通道
            cache: 是否缓存

        返回:
            pygame.Surface对象，失败返回占位图片
        """
        # 检查缓存
        if path in self.images:
            logger.debug(f"从缓存加载图片: {path}")
            self.ref_counts[path] = self.ref_counts.get(path, 0) + 1
            return self.images[path]

        # 解析路径
        abs_path = self.resolve_path(path)

        if abs_path is None or not abs_path.exists():
            logger.warning(f"图片不存在: {path}，使用占位图片")
            return self.get_placeholder_image()

        try:
            # 加载图片
            if use_alpha:
                image = pygame.image.load(str(abs_path)).convert_alpha()
            else:
                image = pygame.image.load(str(abs_path)).convert()

            # 缓存
            if cache:
                self.images[path] = image
                self.ref_counts[path] = 1

            logger.info(f"加载图片: {path}")
            return image

        except Exception as e:
            logger.error(f"加载图片失败 {path}: {e}")
            return self.get_placeholder_image()

    def load_sound(self, path: str, cache: bool = True) -> Optional[pygame.mixer.Sound]:
        """
        加载音效

        参数:
            path: 音效路径（相对或绝对）
            cache: 是否缓存

        返回:
            pygame.mixer.Sound对象，失败返回None
        """
        # 检查缓存
        if path in self.sounds:
            logger.debug(f"从缓存加载音效: {path}")
            self.ref_counts[path] = self.ref_counts.get(path, 0) + 1
            return self.sounds[path]

        # 解析路径
        abs_path = self.resolve_path(path)

        if abs_path is None or not abs_path.exists():
            logger.warning(f"音效不存在: {path}")
            return None

        try:
            # 加载音效
            sound = pygame.mixer.Sound(str(abs_path))

            # 缓存
            if cache:
                self.sounds[path] = sound
                self.ref_counts[path] = 1

            logger.info(f"加载音效: {path}")
            return sound

        except Exception as e:
            logger.error(f"加载音效失败 {path}: {e}")
            return None

    def load_music_path(self, path: str, cache: bool = True) -> Optional[str]:
        """
        加载音乐路径（背景音乐不预加载，只记录路径）

        参数:
            path: 音乐路径（相对或绝对）
            cache: 是否缓存路径

        返回:
            绝对路径字符串，失败返回None
        """
        # 检查缓存
        if path in self.music_paths:
            logger.debug(f"从缓存获取音乐路径: {path}")
            return self.music_paths[path]

        # 解析路径
        abs_path = self.resolve_path(path)

        if abs_path is None or not abs_path.exists():
            logger.warning(f"音乐文件不存在: {path}")
            return None

        abs_path_str = str(abs_path)

        # 缓存
        if cache:
            self.music_paths[path] = abs_path_str

        logger.info(f"记录音乐路径: {path}")
        return abs_path_str

    def load_animation(self, path: str, cache: bool = True) -> Optional[Any]:
        """
        加载动画配置（JSON格式）

        参数:
            path: 动画配置路径
            cache: 是否缓存

        返回:
            动画配置字典，失败返回None
        """
        # 检查缓存
        if path in self.animations:
            logger.debug(f"从缓存加载动画: {path}")
            return self.animations[path]

        # 解析路径
        abs_path = self.resolve_path(path)

        if abs_path is None or not abs_path.exists():
            logger.warning(f"动画配置不存在: {path}")
            return None

        try:
            import json
            with open(abs_path, 'r', encoding='utf-8') as f:
                animation_data = json.load(f)

            # 缓存
            if cache:
                self.animations[path] = animation_data

            logger.info(f"加载动画配置: {path}")
            return animation_data

        except Exception as e:
            logger.error(f"加载动画配置失败 {path}: {e}")
            return None

    def load_model(self, path: str, cache: bool = True) -> Optional[Any]:
        """
        加载3D模型（预留接口，需要3D渲染库支持）

        参数:
            path: 模型路径
            cache: 是否缓存

        返回:
            模型对象，失败返回None
        """
        # 检查缓存
        if path in self.models:
            logger.debug(f"从缓存加载模型: {path}")
            return self.models[path]

        # 解析路径
        abs_path = self.resolve_path(path)

        if abs_path is None or not abs_path.exists():
            logger.warning(f"模型文件不存在: {path}")
            return None

        # TODO: 实现3D模型加载（需要OpenGL/PyOpenGL/Panda3D等库）
        logger.warning(f"3D模型加载功能待实现: {path}")

        # 占位：返回模型路径信息
        model_data = {
            'path': str(abs_path),
            'format': abs_path.suffix,
            'loaded': False
        }

        # 缓存
        if cache:
            self.models[path] = model_data

        return model_data

    def load_material(self, path: str, cache: bool = True) -> Optional[Any]:
        """
        加载材质配置

        参数:
            path: 材质配置路径
            cache: 是否缓存

        返回:
            材质配置字典，失败返回None
        """
        # 检查缓存
        if path in self.materials:
            logger.debug(f"从缓存加载材质: {path}")
            return self.materials[path]

        # 解析路径
        abs_path = self.resolve_path(path)

        if abs_path is None or not abs_path.exists():
            logger.warning(f"材质配置不存在: {path}")
            return None

        try:
            import yaml
            with open(abs_path, 'r', encoding='utf-8') as f:
                material_data = yaml.safe_load(f)

            # 缓存
            if cache:
                self.materials[path] = material_data

            logger.info(f"加载材质配置: {path}")
            return material_data

        except Exception as e:
            logger.error(f"加载材质配置失败 {path}: {e}")
            return None

    def preload_resources(self, resource_list: List[Dict[str, str]]) -> None:
        """
        预加载资源列表

        参数:
            resource_list: 资源列表，格式: [{"type": "image", "path": "..."}, ...]
        """
        logger.info(f"开始预加载{len(resource_list)}个资源")

        for resource in resource_list:
            resource_type = resource.get('type')
            resource_path = resource.get('path')

            if not resource_path:
                continue

            try:
                if resource_type == 'image':
                    self.load_image(resource_path)
                elif resource_type == 'sound':
                    self.load_sound(resource_path)
                elif resource_type == 'music':
                    self.load_music_path(resource_path)
                elif resource_type == 'animation':
                    self.load_animation(resource_path)
                elif resource_type == 'model':
                    self.load_model(resource_path)
                elif resource_type == 'material':
                    self.load_material(resource_path)
                else:
                    logger.warning(f"未知资源类型: {resource_type}")

            except Exception as e:
                logger.error(f"预加载资源失败 {resource_path}: {e}")

        logger.info("资源预加载完成")

    def release_resource(self, path: str) -> None:
        """
        释放资源（减少引用计数）

        参数:
            path: 资源路径
        """
        if path in self.ref_counts:
            self.ref_counts[path] -= 1

            if self.ref_counts[path] <= 0:
                # 引用计数为0，从缓存中移除
                self.ref_counts.pop(path, None)

                if path in self.images:
                    self.images.pop(path)
                    logger.debug(f"释放图片资源: {path}")
                elif path in self.sounds:
                    self.sounds.pop(path)
                    logger.debug(f"释放音效资源: {path}")
                elif path in self.animations:
                    self.animations.pop(path)
                    logger.debug(f"释放动画资源: {path}")
                elif path in self.models:
                    self.models.pop(path)
                    logger.debug(f"释放模型资源: {path}")
                elif path in self.materials:
                    self.materials.pop(path)
                    logger.debug(f"释放材质资源: {path}")

    def clear_cache(self, resource_type: Optional[str] = None) -> None:
        """
        清空资源缓存

        参数:
            resource_type: 资源类型（image/sound/animation/model/material），
                          None表示清空所有
        """
        if resource_type is None or resource_type == 'image':
            count = len(self.images)
            self.images.clear()
            logger.info(f"清空图片缓存，释放{count}个资源")

        if resource_type is None or resource_type == 'sound':
            count = len(self.sounds)
            self.sounds.clear()
            logger.info(f"清空音效缓存，释放{count}个资源")

        if resource_type is None or resource_type == 'animation':
            count = len(self.animations)
            self.animations.clear()
            logger.info(f"清空动画缓存，释放{count}个资源")

        if resource_type is None or resource_type == 'model':
            count = len(self.models)
            self.models.clear()
            logger.info(f"清空模型缓存，释放{count}个资源")

        if resource_type is None or resource_type == 'material':
            count = len(self.materials)
            self.materials.clear()
            logger.info(f"清空材质缓存，释放{count}个资源")

        if resource_type is None:
            self.ref_counts.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息

        返回:
            缓存统计字典
        """
        return {
            'images': len(self.images),
            'sounds': len(self.sounds),
            'music_paths': len(self.music_paths),
            'animations': len(self.animations),
            'models': len(self.models),
            'materials': len(self.materials),
            'total': (len(self.images) + len(self.sounds) +
                     len(self.animations) + len(self.models) +
                     len(self.materials))
        }


# 全局资源加载器实例（单例模式）
_resource_loader_instance: Optional[ResourceLoader] = None


def get_resource_loader(root_dir: str = ".") -> ResourceLoader:
    """
    获取资源加载器实例（单例）

    参数:
        root_dir: 项目根目录

    返回:
        ResourceLoader实例
    """
    global _resource_loader_instance

    if _resource_loader_instance is None:
        _resource_loader_instance = ResourceLoader(root_dir)

    return _resource_loader_instance
