"""
音效系统 - Sound System
处理背景音乐、音效播放、音量控制
"""

import pygame
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SoundSystem:
    """
    音效系统管理器
    功能：
    1. 背景音乐播放和控制
    2. 音效播放（支持多通道）
    3. 音量控制（主音量、音乐、音效分别控制）
    4. 音效缓存
    """

    def __init__(self, settings: Dict = None):
        """
        初始化音效系统

        参数:
            settings: 音效设置配置
        """
        self.settings = settings or {}

        # 初始化pygame音频模块
        try:
            pygame.mixer.init(
                frequency=44100,
                size=-16,
                channels=2,
                buffer=512
            )
            self.initialized = True
            logger.info("音效系统初始化成功")
        except Exception as e:
            logger.error(f"音效系统初始化失败: {e}")
            self.initialized = False
            return

        # 音量设置 (0.0 - 1.0)
        self.master_volume = self.settings.get('master_volume', 0.7)
        self.music_volume = self.settings.get('music_volume', 0.5)
        self.sfx_volume = self.settings.get('sfx_volume', 0.8)

        # 是否静音
        self.muted = False

        # 当前播放的音乐
        self.current_music: Optional[str] = None

        # 音效缓存 {sound_id: pygame.mixer.Sound}
        self.sound_cache: Dict[str, pygame.mixer.Sound] = {}

        # 音效通道数量
        pygame.mixer.set_num_channels(16)

        # 应用音量设置
        self._update_volumes()

        logger.info(f"音量设置 - 主: {self.master_volume}, 音乐: {self.music_volume}, 音效: {self.sfx_volume}")

    def _update_volumes(self):
        """更新音量设置"""
        if not self.initialized:
            return

        if self.muted:
            pygame.mixer.music.set_volume(0)
        else:
            pygame.mixer.music.set_volume(self.master_volume * self.music_volume)

    def play_music(self, music_path: str, loop: bool = True, fade_ms: int = 0):
        """
        播放背景音乐

        参数:
            music_path: 音乐文件路径
            loop: 是否循环播放
            fade_ms: 淡入时间（毫秒）
        """
        if not self.initialized:
            return

        try:
            # 如果已在播放相同音乐，跳过
            if self.current_music == music_path and pygame.mixer.music.get_busy():
                return

            # 停止当前音乐
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()

            # 加载并播放
            pygame.mixer.music.load(music_path)
            loops = -1 if loop else 0

            if fade_ms > 0:
                pygame.mixer.music.play(loops, fade_ms=fade_ms)
            else:
                pygame.mixer.music.play(loops)

            self.current_music = music_path
            self._update_volumes()

            logger.info(f"播放音乐: {Path(music_path).name}")

        except Exception as e:
            logger.error(f"播放音乐失败 {music_path}: {e}")

    def stop_music(self, fade_ms: int = 0):
        """
        停止背景音乐

        参数:
            fade_ms: 淡出时间（毫秒）
        """
        if not self.initialized:
            return

        try:
            if fade_ms > 0:
                pygame.mixer.music.fadeout(fade_ms)
            else:
                pygame.mixer.music.stop()

            self.current_music = None
            logger.info("音乐已停止")

        except Exception as e:
            logger.error(f"停止音乐失败: {e}")

    def pause_music(self):
        """暂停音乐"""
        if not self.initialized:
            return
        pygame.mixer.music.pause()

    def resume_music(self):
        """恢复音乐"""
        if not self.initialized:
            return
        pygame.mixer.music.unpause()

    def load_sound(self, sound_id: str, sound_path: str) -> bool:
        """
        加载音效到缓存

        参数:
            sound_id: 音效ID（用于后续播放）
            sound_path: 音效文件路径

        返回:
            是否加载成功
        """
        if not self.initialized:
            return False

        try:
            sound = pygame.mixer.Sound(sound_path)
            self.sound_cache[sound_id] = sound
            logger.debug(f"加载音效: {sound_id} <- {Path(sound_path).name}")
            return True

        except Exception as e:
            logger.error(f"加载音效失败 {sound_path}: {e}")
            return False

    def play_sound(self, sound_id: str, volume: float = 1.0, loops: int = 0):
        """
        播放音效

        参数:
            sound_id: 音效ID（需先通过load_sound加载）
            volume: 音量倍率 (0.0 - 1.0)
            loops: 循环次数（0=播放一次，-1=无限循环）
        """
        if not self.initialized or self.muted:
            return

        sound = self.sound_cache.get(sound_id)
        if not sound:
            logger.warning(f"音效未加载: {sound_id}")
            return

        try:
            # 计算最终音量
            final_volume = self.master_volume * self.sfx_volume * volume
            sound.set_volume(final_volume)
            sound.play(loops)

        except Exception as e:
            logger.error(f"播放音效失败 {sound_id}: {e}")

    def play_sound_from_file(self, sound_path: str, volume: float = 1.0):
        """
        直接从文件播放音效（不缓存）

        参数:
            sound_path: 音效文件路径
            volume: 音量倍率
        """
        if not self.initialized or self.muted:
            return

        try:
            sound = pygame.mixer.Sound(sound_path)
            final_volume = self.master_volume * self.sfx_volume * volume
            sound.set_volume(final_volume)
            sound.play()

        except Exception as e:
            logger.error(f"播放音效失败 {sound_path}: {e}")

    def set_master_volume(self, volume: float):
        """设置主音量 (0.0 - 1.0)"""
        self.master_volume = max(0.0, min(1.0, volume))
        self._update_volumes()
        logger.info(f"主音量设置为: {self.master_volume}")

    def set_music_volume(self, volume: float):
        """设置音乐音量 (0.0 - 1.0)"""
        self.music_volume = max(0.0, min(1.0, volume))
        self._update_volumes()
        logger.info(f"音乐音量设置为: {self.music_volume}")

    def set_sfx_volume(self, volume: float):
        """设置音效音量 (0.0 - 1.0)"""
        self.sfx_volume = max(0.0, min(1.0, volume))
        logger.info(f"音效音量设置为: {self.sfx_volume}")

    def toggle_mute(self):
        """切换静音状态"""
        self.muted = not self.muted
        self._update_volumes()
        logger.info(f"静音状态: {self.muted}")

    def cleanup(self):
        """清理资源"""
        if not self.initialized:
            return

        try:
            pygame.mixer.music.stop()
            self.sound_cache.clear()
            pygame.mixer.quit()
            logger.info("音效系统已清理")

        except Exception as e:
            logger.error(f"清理音效系统失败: {e}")


class SoundPresets:
    """音效预设 - 常用音效ID定义"""

    # UI音效
    UI_CLICK = "ui_click"
    UI_HOVER = "ui_hover"
    UI_ERROR = "ui_error"
    UI_SUCCESS = "ui_success"

    # 战斗音效
    ATTACK_HIT = "attack_hit"
    ATTACK_MISS = "attack_miss"
    SKILL_CAST = "skill_cast"
    EXPLOSION = "explosion"

    # 单位音效
    UNIT_SPAWN = "unit_spawn"
    UNIT_DEATH = "unit_death"
    UNIT_MOVE = "unit_move"

    # Boss音效
    BOSS_APPEAR = "boss_appear"
    BOSS_PHASE_CHANGE = "boss_phase_change"
    BOSS_ENRAGE = "boss_enrage"
    BOSS_DEATH = "boss_death"

    # 奖励音效
    GOLD_COLLECT = "gold_collect"
    LEVEL_UP = "level_up"
    VICTORY = "victory"
    DEFEAT = "defeat"


# 全局音效系统实例
_sound_system: Optional[SoundSystem] = None


def get_sound_system(settings: Dict = None) -> SoundSystem:
    """获取全局音效系统实例"""
    global _sound_system
    if _sound_system is None:
        _sound_system = SoundSystem(settings)
    return _sound_system


def cleanup_sound_system():
    """清理全局音效系统"""
    global _sound_system
    if _sound_system:
        _sound_system.cleanup()
        _sound_system = None
