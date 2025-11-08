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

    def handle_events(self) -> None:
        """
        处理pygame事件
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                # 全局快捷键
                if event.key == pygame.K_ESCAPE:
                    if self.current_state == GameState.BATTLE:
                        self.change_state(GameState.PAUSE)
                    elif self.current_state == GameState.PAUSE:
                        self.change_state(GameState.BATTLE)

                # 管理界面快捷键 (Ctrl+Shift+D)
                keys = pygame.key.get_pressed()
                if (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]) and \
                   (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and \
                   event.key == pygame.K_d:
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
        self.delta_time = current_time - self.last_frame_time
        self.last_frame_time = current_time

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
