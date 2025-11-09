"""
游戏引擎 - CrossVerse Arena核心模块
负责游戏主循环、状态机管理和帧同步控制
"""

import pygame
import logging
from enum import Enum
from typing import Optional, Callable
import time

logger = logging.getLogger(__name__)


class GameState(Enum):
    """游戏状态枚举"""
    LOADING = "loading"  # 加载中
    MENU = "menu"  # 主菜单
    CAMPAIGN_SELECT = "campaign_select"  # 战役选择
    LEVEL_SELECT = "level_select"  # 关卡选择
    CHARACTER_SELECT = "character_select"  # 角色选择
    BATTLE = "battle"  # 战斗中
    PAUSE = "pause"  # 暂停
    VICTORY = "victory"  # 胜利
    DEFEAT = "defeat"  # 失败
    SETTINGS = "settings"  # 设置
    ADMIN = "admin"  # 管理界面
    QUIT = "quit"  # 退出


class GameEngine:
    """
    游戏引擎类
    功能：
    1. 管理游戏主循环和状态机
    2. 帧率控制和同步
    3. 事件分发和处理
    4. 全局游戏状态管理
    """

    def __init__(self, config: dict):
        """
        初始化游戏引擎

        参数:
            config: 游戏配置字典
        """
        self.config = config

        # 窗口设置
        self.resolution = tuple(config.get('resolution', [1280, 720]))
        self.fps_target = config.get('fps', 60)
        self.fullscreen = config.get('fullscreen', False)

        # Pygame初始化
        pygame.init()
        pygame.mixer.init()

        # 创建窗口
        if self.fullscreen:
            self.screen = pygame.display.set_mode(self.resolution, pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self.resolution)

        pygame.display.set_caption("CrossVerse Arena - 宇宙竞技场")

        # 时钟对象（用于帧率控制）
        self.clock = pygame.time.Clock()

        # 游戏状态
        self.current_state = GameState.LOADING
        self.previous_state: Optional[GameState] = None

        # 状态处理器字典
        self.state_handlers: dict[GameState, Callable] = {}

        # 运行标志
        self.running = True

        # 帧数统计
        self.frame_count = 0
        self.current_fps = 0
        self.delta_time = 0  # 帧间隔时间（秒）
        self.last_frame_time = time.time()

        # 游戏加速（从配置读取）
        time_config = self.config.get('gameplay', {}).get('time_control', {})
        self.available_speeds = time_config.get('available_speeds', [1.0, 1.5, 2.0])
        self.time_scale = time_config.get('default_speed', 1.0)

        # 全局计时器
        self.game_time = 0  # 游戏总运行时间（秒）

        # 事件监听器
        self.event_listeners = []

        logger.info(f"游戏引擎初始化完成: {self.resolution[0]}x{self.resolution[1]} @ {self.fps_target}FPS")

    def register_state_handler(self, state: GameState, handler: Callable) -> None:
        """
        注册状态处理器

        参数:
            state: 游戏状态
            handler: 处理函数，签名: handler(screen, delta_time) -> None
        """
        self.state_handlers[state] = handler
        logger.debug(f"注册状态处理器: {state.value}")

    def change_state(self, new_state: GameState) -> None:
        """
        切换游戏状态

        参数:
            new_state: 新状态
        """
        if new_state == self.current_state:
            return

        logger.info(f"状态切换: {self.current_state.value} -> {new_state.value}")

        # 离开战斗状态时重置速度
        if self.current_state == GameState.BATTLE and new_state != GameState.PAUSE:
            self.time_scale = 1.0

        self.previous_state = self.current_state
        self.current_state = new_state

        # 触发状态切换事件
        self.dispatch_event('state_change', {
            'previous': self.previous_state,
            'current': self.current_state
        })

    def add_event_listener(self, listener: Callable) -> None:
        """
        添加事件监听器

        参数:
            listener: 监听器函数，签名: listener(event_type, event_data)
        """
        self.event_listeners.append(listener)

    def dispatch_event(self, event_type: str, event_data: dict) -> None:
        """
        分发事件到所有监听器

        参数:
            event_type: 事件类型
            event_data: 事件数据
        """
        for listener in self.event_listeners:
            try:
                listener(event_type, event_data)
            except Exception as e:
                logger.error(f"事件监听器执行失败 [{event_type}]: {e}")

    def _get_pygame_key(self, key_name: str) -> int:
        """
        将键名字符串转换为pygame键码

        参数:
            key_name: 键名（如 "space", "escape", "f11"）

        返回:
            pygame键码
        """
        key_map = {
            'space': pygame.K_SPACE,
            'escape': pygame.K_ESCAPE,
            'f11': pygame.K_F11,
            'enter': pygame.K_RETURN,
            'tab': pygame.K_TAB,
            'shift': pygame.K_LSHIFT,
            'ctrl': pygame.K_LCTRL,
            'alt': pygame.K_LALT,
        }
        # 支持单个字母键
        if len(key_name) == 1 and key_name.isalpha():
            return getattr(pygame, f'K_{key_name.lower()}', pygame.K_SPACE)
        return key_map.get(key_name.lower(), pygame.K_SPACE)

    def _check_shortcut(self, shortcut_str: str, event, keys) -> bool:
        """
        检查快捷键是否被按下

        参数:
            shortcut_str: 快捷键字符串（如 "ctrl+shift+d"）
            event: pygame事件
            keys: 当前按键状态

        返回:
            是否匹配
        """
        if not shortcut_str:
            return False

        # 解析快捷键字符串
        parts = [p.strip().lower() for p in shortcut_str.split('+')]

        # 检查修饰键
        ctrl_required = 'ctrl' in parts
        shift_required = 'shift' in parts
        alt_required = 'alt' in parts

        # 获取主键
        main_key = None
        for part in parts:
            if part not in ['ctrl', 'shift', 'alt']:
                main_key = part
                break

        if not main_key:
            return False

        # 检查修饰键状态
        ctrl_pressed = keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]
        shift_pressed = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        alt_pressed = keys[pygame.K_LALT] or keys[pygame.K_RALT]

        # 修饰键必须完全匹配
        if ctrl_required != ctrl_pressed:
            return False
        if shift_required != shift_pressed:
            return False
        if alt_required != alt_pressed:
            return False

        # 检查主键
        main_key_code = self._get_pygame_key(main_key)
        return event.key == main_key_code

    def handle_events(self) -> None:
        """
        处理pygame事件
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                # ESC键 - 根据不同状态执行不同操作
                if event.key == pygame.K_ESCAPE:
                    if self.current_state == GameState.BATTLE:
                        # 战斗中按ESC -> 暂停
                        self.change_state(GameState.PAUSE)
                    elif self.current_state == GameState.PAUSE:
                        # 暂停中按ESC -> 继续战斗
                        self.change_state(GameState.BATTLE)
                    elif self.current_state == GameState.CAMPAIGN_SELECT:
                        # 战役选择按ESC -> 返回主菜单
                        self.change_state(GameState.MENU)
                    elif self.current_state == GameState.LEVEL_SELECT:
                        # 关卡选择按ESC -> 返回战役选择
                        self.change_state(GameState.CAMPAIGN_SELECT)
                    elif self.current_state == GameState.CHARACTER_SELECT:
                        # 角色选择按ESC -> 返回关卡选择
                        self.change_state(GameState.LEVEL_SELECT)
                    elif self.current_state == GameState.SETTINGS:
                        # 设置界面按ESC -> 返回主菜单
                        self.change_state(GameState.MENU)
                    elif self.current_state == GameState.VICTORY or self.current_state == GameState.DEFEAT:
                        # 胜利/失败界面按ESC -> 返回主菜单
                        self.change_state(GameState.MENU)

                # F11键 - 切换全屏
                elif event.key == pygame.K_F11:
                    self.toggle_fullscreen()

                # 游戏速度切换（从配置读取快捷键）
                speed_key_name = self.config.get('controls', {}).get('speed_toggle', 'space')
                speed_key = self._get_pygame_key(speed_key_name)
                if event.key == speed_key:
                    if self.current_state == GameState.BATTLE:
                        current_index = self.available_speeds.index(self.time_scale)
                        next_index = (current_index + 1) % len(self.available_speeds)
                        self.time_scale = self.available_speeds[next_index]
                        logger.info(f"游戏速度切换至: {self.time_scale}x")

                # Alt+Enter - 切换全屏（备用快捷键）
                keys = pygame.key.get_pressed()
                if event.key == pygame.K_RETURN and (keys[pygame.K_LALT] or keys[pygame.K_RALT]):
                    self.toggle_fullscreen()

                # 管理界面快捷键（从配置读取）
                admin_config = self.config.get('admin', {})
                admin_shortcut = admin_config.get('shortcut', 'ctrl+shift+d')
                if self._check_shortcut(admin_shortcut, event, keys):
                    if self.current_state != GameState.ADMIN:
                        self.change_state(GameState.ADMIN)
                    else:
                        self.change_state(self.previous_state or GameState.MENU)

            # 分发事件到监听器
            self.dispatch_event('pygame_event', {'event': event})

    def update(self) -> None:
        """
        更新游戏逻辑
        """
        # 计算delta time
        current_time = time.time()
        raw_delta = current_time - self.last_frame_time
        self.last_frame_time = current_time

        # 应用时间倍率（仅在战斗状态）
        if self.current_state == GameState.BATTLE:
            self.delta_time = raw_delta * self.time_scale
        else:
            self.delta_time = raw_delta

        # 更新游戏时间
        self.game_time += self.delta_time

        # 调用当前状态的处理器
        if self.current_state in self.state_handlers:
            try:
                self.state_handlers[self.current_state](self.screen, self.delta_time)
            except Exception as e:
                logger.error(f"状态处理器执行失败 [{self.current_state.value}]: {e}")

        # 检查是否需要退出
        if self.current_state == GameState.QUIT:
            self.running = False

    def render(self) -> None:
        """
        渲染游戏画面
        """
        # 更新显示
        pygame.display.flip()

    def run(self) -> None:
        """
        运行游戏主循环
        """
        logger.info("游戏主循环启动")

        while self.running:
            # 事件处理
            self.handle_events()

            # 更新逻辑
            self.update()

            # 渲染画面
            self.render()

            # 帧率控制
            self.clock.tick(self.fps_target)

            # 更新FPS统计
            self.frame_count += 1
            self.current_fps = self.clock.get_fps()

        logger.info("游戏主循环结束")
        self.quit()

    def quit(self) -> None:
        """
        退出游戏，清理资源
        """
        logger.info("游戏引擎关闭")
        pygame.quit()

    def get_fps(self) -> float:
        """
        获取当前帧率

        返回:
            当前FPS
        """
        return self.current_fps

    def get_delta_time(self) -> float:
        """
        获取帧间隔时间

        返回:
            Delta time（秒）
        """
        return self.delta_time

    def get_game_time(self) -> float:
        """
        获取游戏运行总时间

        返回:
            游戏时间（秒）
        """
        return self.game_time

    def set_fps_target(self, fps: int) -> None:
        """
        设置目标帧率

        参数:
            fps: 目标帧率
        """
        self.fps_target = fps
        logger.info(f"目标帧率设置为: {fps} FPS")

    def toggle_fullscreen(self) -> None:
        """
        切换全屏/窗口模式
        """
        self.fullscreen = not self.fullscreen

        if self.fullscreen:
            self.screen = pygame.display.set_mode(self.resolution, pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self.resolution)

        logger.info(f"切换显示模式: {'全屏' if self.fullscreen else '窗口'}")

    def set_resolution(self, width: int, height: int) -> None:
        """
        设置分辨率

        参数:
            width: 宽度
            height: 高度
        """
        self.resolution = (width, height)

        if self.fullscreen:
            self.screen = pygame.display.set_mode(self.resolution, pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self.resolution)

        logger.info(f"分辨率设置为: {width}x{height}")
