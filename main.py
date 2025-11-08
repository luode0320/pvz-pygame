"""
CrossVerse Arena - 宇宙竞技场
主程序入口

一个高度模块化、完全由配置驱动的跨IP角色对战塔防平台
"""

import sys
import os
import logging
import pygame
from typing import Optional

# 设置标准输出编码为UTF-8（修复Windows控制台乱码）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入核心模块
from core.config_loader import get_config_loader
from core.resource_loader import get_resource_loader
from core.game_engine import GameEngine, GameState
from core.entity_manager import get_entity_manager
from core.performance_monitor import get_performance_monitor
from core.battle_manager import BattleManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class CrossVerseArena:
    """
    CrossVerse Arena 主类
    负责初始化和协调所有游戏系统
    """

    def __init__(self):
        """初始化游戏"""
        logger.info("=" * 60)
        logger.info("CrossVerse Arena - 宇宙竞技场")
        logger.info("启动中...")
        logger.info("=" * 60)

        # 加载配置
        self.config_loader = get_config_loader(".")
        self.config_loader.scan_all()

        # 获取全局设置
        self.settings = self.config_loader.settings

        # 初始化资源加载器
        self.resource_loader = get_resource_loader(".")
        self.resource_loader.init_pygame()

        # 初始化中文字体
        self.fonts = self._init_fonts()

        # 初始化游戏引擎
        self.engine = GameEngine(self.settings)

        # 初始化性能监控
        perf_config = self.settings.get('performance_system', {})
        self.performance_monitor = get_performance_monitor(perf_config)

        # 初始化实体管理器
        self.entity_manager = get_entity_manager()

        # 战斗管理器（在进入战斗时初始化）
        self.battle_manager: Optional[BattleManager] = None
        self.current_level_config: Optional[dict] = None

        # 选中的角色列表（在角色选择界面选择）
        self.selected_characters: list = []

        # 鼠标状态（用于防止连点）
        self.mouse_pressed_last_frame = False

        # 注册状态处理器
        self.register_state_handlers()

        # 启动配置自动扫描
        if self.settings.get('admin', {}).get('enabled', True):
            self.config_loader.start_auto_scan()

        logger.info("游戏初始化完成")

    def _init_fonts(self):
        """
        初始化支持中文的字体

        返回:
            字体字典，包含不同尺寸的字体
        """
        fonts = {}

        # 尝试加载系统中文字体
        font_names = [
            'simhei.ttf',      # 黑体
            'msyh.ttc',        # 微软雅黑
            'simsun.ttc',      # 宋体
            'arial.ttf',       # Arial（备用）
        ]

        # 在Windows系统字体目录查找
        font_dirs = []
        if sys.platform == 'win32':
            font_dirs.append('C:\\Windows\\Fonts')
        elif sys.platform == 'darwin':  # macOS
            font_dirs.extend(['/System/Library/Fonts', '/Library/Fonts'])
        else:  # Linux
            font_dirs.extend(['/usr/share/fonts', '/usr/local/share/fonts'])

        # 查找可用的中文字体
        font_path = None
        for font_dir in font_dirs:
            if not os.path.exists(font_dir):
                continue
            for font_name in font_names:
                test_path = os.path.join(font_dir, font_name)
                if os.path.exists(test_path):
                    font_path = test_path
                    logger.info(f"找到中文字体: {font_path}")
                    break
            if font_path:
                break

        # 创建不同尺寸的字体
        sizes = {
            'small': 24,
            'normal': 32,
            'large': 42,
            'title': 54,
            'huge': 72
        }

        for size_name, size_value in sizes.items():
            try:
                if font_path:
                    fonts[size_name] = pygame.font.Font(font_path, size_value)
                else:
                    # 如果找不到中文字体，使用系统默认字体
                    logger.warning(f"未找到中文字体，使用默认字体（可能无法显示中文）")
                    fonts[size_name] = pygame.font.SysFont('arial', size_value)
            except Exception as e:
                logger.error(f"加载字体失败 ({size_name}): {e}")
                fonts[size_name] = pygame.font.Font(None, size_value)

        return fonts

    def register_state_handlers(self):
        """注册游戏状态处理器"""
        self.engine.register_state_handler(GameState.LOADING, self.state_loading)
        self.engine.register_state_handler(GameState.MENU, self.state_menu)
        self.engine.register_state_handler(GameState.CAMPAIGN_SELECT, self.state_campaign_select)
        self.engine.register_state_handler(GameState.CHARACTER_SELECT, self.state_character_select)
        self.engine.register_state_handler(GameState.BATTLE, self.state_battle)
        self.engine.register_state_handler(GameState.PAUSE, self.state_pause)
        self.engine.register_state_handler(GameState.VICTORY, self.state_victory)
        self.engine.register_state_handler(GameState.DEFEAT, self.state_defeat)

    def state_loading(self, screen: pygame.Surface, delta_time: float):
        """加载状态处理"""
        screen.fill((0, 0, 0))

        # 显示加载文字
        text = self.fonts['large'].render("Loading...", True, (255, 255, 255))
        text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(text, text_rect)

        # 加载完成后切换到主菜单
        if self.engine.frame_count > 60:  # 等待1秒
            self.engine.change_state(GameState.MENU)

    def state_menu(self, screen: pygame.Surface, delta_time: float):
        """主菜单状态处理"""
        screen.fill((20, 20, 40))

        # 绘制标题
        title = self.fonts['huge'].render("CrossVerse Arena", True, (255, 200, 50))
        title_rect = title.get_rect(center=(screen.get_width() // 2, 150))
        screen.blit(title, title_rect)

        # 绘制副标题
        subtitle = self.fonts['normal'].render("宇宙竞技场", True, (200, 200, 200))
        subtitle_rect = subtitle.get_rect(center=(screen.get_width() // 2, 220))
        screen.blit(subtitle, subtitle_rect)

        # 绘制菜单选项
        menu_items = [
            ("开始游戏", GameState.CAMPAIGN_SELECT),
            ("设置", GameState.SETTINGS),
            ("退出", GameState.QUIT)
        ]

        y_start = 320
        for i, (text, target_state) in enumerate(menu_items):
            color = (255, 255, 255) if i == 0 else (180, 180, 180)
            menu_text = self.fonts['large'].render(text, True, color)
            menu_rect = menu_text.get_rect(center=(screen.get_width() // 2, y_start + i * 70))
            screen.blit(menu_text, menu_rect)

            # 处理点击
            if pygame.mouse.get_pressed()[0]:
                mouse_pos = pygame.mouse.get_pos()
                if menu_rect.collidepoint(mouse_pos):
                    self.engine.change_state(target_state)

        # 显示统计信息
        stats = [
            f"游戏IP: {len(self.config_loader.games)}",
            f"角色: {len(self.config_loader.characters)}",
            f"皮肤: {len(self.config_loader.skins)}",
            f"战役: {len(self.config_loader.campaigns)}",
            f"关卡: {len(self.config_loader.levels)}",
            f"FPS: {self.engine.get_fps():.1f}"
        ]

        for i, stat in enumerate(stats):
            stat_text = self.fonts['small'].render(stat, True, (150, 150, 150))
            screen.blit(stat_text, (20, 20 + i * 30))

        # 底部提示信息
        tips = [
            "F11 或 Alt+Enter: 切换全屏",
            "ESC: 返回上一级 / 暂停游戏",
            "Ctrl+Shift+D: 打开管理界面"
        ]

        for i, tip_text in enumerate(tips):
            color = (100, 150, 100) if i == 2 else (120, 120, 150)
            tip = self.fonts['small'].render(tip_text, True, color)
            tip_rect = tip.get_rect(center=(screen.get_width() // 2, screen.get_height() - 80 + i * 25))
            screen.blit(tip, tip_rect)

    def state_campaign_select(self, screen: pygame.Surface, delta_time: float):
        """战役选择状态处理"""
        screen.fill((30, 30, 50))

        # 标题
        title = self.fonts['title'].render("选择战役", True, (255, 200, 50))
        title_rect = title.get_rect(center=(screen.get_width() // 2, 80))
        screen.blit(title, title_rect)

        # 显示战役列表
        y = 160

        if not self.config_loader.campaigns:
            no_campaign = self.fonts['normal'].render("暂无可用战役", True, (200, 200, 200))
            screen.blit(no_campaign, (screen.get_width() // 2 - 100, y))
        else:
            for campaign_id, campaign in self.config_loader.campaigns.items():
                campaign_name = campaign.get('name', campaign_id)
                desc = campaign.get('description', '')

                # 战役名称
                name_text = self.fonts['normal'].render(campaign_name, True, (255, 255, 255))
                name_rect = name_text.get_rect(center=(screen.get_width() // 2, y))
                screen.blit(name_text, name_rect)

                # 描述
                desc_text = self.fonts['small'].render(desc[:60], True, (180, 180, 180))
                desc_rect = desc_text.get_rect(center=(screen.get_width() // 2, y + 35))
                screen.blit(desc_text, desc_rect)

                # 点击检测
                click_rect = pygame.Rect(
                    screen.get_width() // 2 - 300,
                    y - 20,
                    600,
                    70
                )

                # 检测悬停
                is_hover = click_rect.collidepoint(pygame.mouse.get_pos())
                border_color = (100, 100, 180) if is_hover else (60, 60, 100)
                border_width = 3 if is_hover else 2
                pygame.draw.rect(screen, border_color, click_rect, border_width)

                if pygame.mouse.get_pressed()[0] and is_hover:
                    logger.info(f"选择战役: {campaign_name}")

                    # 保存选择的战役和关卡信息
                    level_id = f"{campaign_id}/level_01"
                    if level_id in self.config_loader.levels:
                        self.current_level_config = self.config_loader.levels[level_id].copy()
                        self.current_level_config['campaign_id'] = campaign_id

                        # 跳转到角色选择界面
                        self.engine.change_state(GameState.CHARACTER_SELECT)
                    else:
                        logger.warning(f"未找到关卡配置: {level_id}")

                    pygame.time.wait(200)

                y += 100

        # 返回按钮
        back_text = self.fonts['normal'].render("返回 (ESC)", True, (200, 200, 200))
        back_rect = back_text.get_rect(topleft=(40, 40))
        screen.blit(back_text, back_rect)

        if pygame.mouse.get_pressed()[0]:
            if back_rect.collidepoint(pygame.mouse.get_pos()):
                self.engine.change_state(GameState.MENU)
                pygame.time.wait(200)

    def state_character_select(self, screen: pygame.Surface, delta_time: float):
        """角色选择状态处理"""
        screen.fill((30, 40, 60))

        # 标题
        title = self.fonts['title'].render("选择角色", True, (255, 200, 50))
        title_rect = title.get_rect(center=(screen.get_width() // 2, 60))
        screen.blit(title, title_rect)

        # 提示文字
        hint = self.fonts['normal'].render("点击角色卡片选择/取消，最多选择6个", True, (200, 200, 200))
        hint_rect = hint.get_rect(center=(screen.get_width() // 2, 120))
        screen.blit(hint, hint_rect)

        # 获取所有防守方角色
        if not self.current_level_config:
            error_text = self.fonts['normal'].render("错误：未选择关卡", True, (255, 100, 100))
            screen.blit(error_text, (screen.get_width() // 2 - 100, 300))
            return

        campaign_id = self.current_level_config.get('campaign_id', '')
        campaign = self.config_loader.campaigns.get(campaign_id, {})
        defender_game = campaign.get('defender_game', 'dnf')

        # 筛选防守方角色
        available_chars = []
        for char_id, char_config in self.config_loader.characters.items():
            if char_config.get('type') == 'defender':
                available_chars.append((char_id, char_config))

        if not available_chars:
            no_char_text = self.fonts['normal'].render("暂无可用角色", True, (200, 200, 200))
            screen.blit(no_char_text, (screen.get_width() // 2 - 100, 300))
            return

        # 绘制角色卡片
        card_width = 150
        card_height = 200
        card_spacing = 20
        cards_per_row = 4
        start_x = (screen.get_width() - (cards_per_row * card_width + (cards_per_row - 1) * card_spacing)) // 2
        start_y = 180

        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]
        mouse_just_clicked = mouse_pressed and not self.mouse_pressed_last_frame

        for i, (char_id, char_config) in enumerate(available_chars):
            row = i // cards_per_row
            col = i % cards_per_row

            x = start_x + col * (card_width + card_spacing)
            y = start_y + row * (card_height + card_spacing)

            card_rect = pygame.Rect(x, y, card_width, card_height)

            # 检查是否已选中
            is_selected = char_id in self.selected_characters
            is_hover = card_rect.collidepoint(mouse_pos)

            # 绘制卡片背景
            if is_selected:
                bg_color = (100, 150, 255)  # 蓝色表示已选中
                border_color = (150, 200, 255)
            elif is_hover:
                bg_color = (70, 90, 120)
                border_color = (150, 180, 220)
            else:
                bg_color = (50, 60, 80)
                border_color = (100, 120, 150)

            pygame.draw.rect(screen, bg_color, card_rect)
            pygame.draw.rect(screen, border_color, card_rect, 3)

            # 绘制角色名
            name = char_config.get('name', char_id)
            name_text = self.fonts['normal'].render(name, True, (255, 255, 255))
            name_rect = name_text.get_rect(center=(x + card_width // 2, y + 60))
            screen.blit(name_text, name_rect)

            # 绘制角色费用
            cost = char_config.get('cost', 100)
            cost_text = self.fonts['small'].render(f"费用: {cost}", True, (255, 200, 50))
            cost_rect = cost_text.get_rect(center=(x + card_width // 2, y + 100))
            screen.blit(cost_text, cost_rect)

            # 绘制角色属性
            stats = char_config.get('stats', {})
            hp_text = self.fonts['small'].render(f"HP: {stats.get('hp', 0)}", True, (100, 255, 100))
            atk_text = self.fonts['small'].render(f"攻击: {stats.get('attack', 0)}", True, (255, 100, 100))
            hp_rect = hp_text.get_rect(center=(x + card_width // 2, y + 130))
            atk_rect = atk_text.get_rect(center=(x + card_width // 2, y + 155))
            screen.blit(hp_text, hp_rect)
            screen.blit(atk_text, atk_rect)

            # 处理点击
            if is_hover and mouse_just_clicked:
                if is_selected:
                    # 取消选择
                    self.selected_characters.remove(char_id)
                    logger.info(f"取消选择角色: {name}")
                else:
                    # 选择角色（最多6个）
                    if len(self.selected_characters) < 6:
                        self.selected_characters.append(char_id)
                        logger.info(f"选择角色: {name}")
                    else:
                        logger.warning("最多只能选择6个角色")

        # 更新鼠标状态
        self.mouse_pressed_last_frame = mouse_pressed

        # 显示已选择数量
        count_text = self.fonts['normal'].render(
            f"已选择: {len(self.selected_characters)}/6",
            True,
            (255, 255, 100) if len(self.selected_characters) > 0 else (200, 200, 200)
        )
        count_rect = count_text.get_rect(center=(screen.get_width() // 2, screen.get_height() - 120))
        screen.blit(count_text, count_rect)

        # 开始游戏按钮
        button_width = 200
        button_height = 50
        button_x = screen.get_width() // 2 - button_width // 2
        button_y = screen.get_height() - 80
        button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

        button_enabled = len(self.selected_characters) > 0
        is_button_hover = button_rect.collidepoint(mouse_pos)

        if button_enabled:
            if is_button_hover:
                button_color = (100, 200, 100)
                text_color = (255, 255, 255)
            else:
                button_color = (70, 150, 70)
                text_color = (220, 220, 220)
        else:
            button_color = (60, 60, 60)
            text_color = (120, 120, 120)

        pygame.draw.rect(screen, button_color, button_rect)
        pygame.draw.rect(screen, (150, 150, 150), button_rect, 2)

        button_text = self.fonts['large'].render("开始游戏", True, text_color)
        button_text_rect = button_text.get_rect(center=(screen.get_width() // 2, button_y + button_height // 2))
        screen.blit(button_text, button_text_rect)

        # 处理开始游戏按钮点击
        if is_button_hover and mouse_just_clicked and button_enabled:
            # 初始化战斗管理器
            self.battle_manager = BattleManager(self.config_loader, self.current_level_config)

            # 将选中的角色传递给战斗管理器
            self.battle_manager.selected_characters = self.selected_characters.copy()

            # 初始化卡片槽
            self.battle_manager._init_card_slots()

            logger.info(f"开始游戏，选择了 {len(self.selected_characters)} 个角色")
            self.engine.change_state(GameState.BATTLE)

        # 返回按钮
        back_text = self.fonts['normal'].render("返回 (ESC)", True, (200, 200, 200))
        back_rect = back_text.get_rect(topleft=(40, 40))
        screen.blit(back_text, back_rect)

        if back_rect.collidepoint(mouse_pos) and mouse_just_clicked:
            # 清空选择
            self.selected_characters.clear()
            self.engine.change_state(GameState.CAMPAIGN_SELECT)

    def state_battle(self, screen: pygame.Surface, delta_time: float):
        """战斗状态处理"""
        screen.fill((40, 60, 40))

        # 如果战斗管理器未初始化，返回菜单
        if self.battle_manager is None:
            logger.warning("战斗管理器未初始化，返回主菜单")
            self.engine.change_state(GameState.MENU)
            return

        # 更新战斗管理器
        self.battle_manager.update(delta_time, screen.get_width())

        # 渲染战斗场景
        self.battle_manager.render(screen, self.fonts)

        # 绘制菜单按钮（右上角）
        menu_button_rect = pygame.Rect(screen.get_width() - 140, 50, 120, 40)
        mouse_pos = pygame.mouse.get_pos()
        is_hover = menu_button_rect.collidepoint(mouse_pos)

        # 按钮背景和边框
        if is_hover:
            pygame.draw.rect(screen, (80, 100, 120), menu_button_rect)
            pygame.draw.rect(screen, (150, 180, 220), menu_button_rect, 3)
            button_color = (255, 255, 100)
        else:
            pygame.draw.rect(screen, (50, 70, 90), menu_button_rect)
            pygame.draw.rect(screen, (100, 130, 160), menu_button_rect, 2)
            button_color = (220, 220, 220)

        # 按钮文字
        pause_text = self.fonts['small'].render("菜单 (ESC)", True, button_color)
        pause_text_rect = pause_text.get_rect(center=menu_button_rect.center)
        screen.blit(pause_text, pause_text_rect)

        # 获取当前鼠标状态
        mouse_pressed = pygame.mouse.get_pressed()[0]
        mouse_just_clicked = mouse_pressed and not self.mouse_pressed_last_frame

        # 处理点击菜单按钮（只在鼠标刚按下时触发）
        if is_hover and mouse_just_clicked:
            self.engine.change_state(GameState.PAUSE)

        # 处理游戏内点击（卡片和网格）（只在鼠标刚按下时触发）
        if mouse_just_clicked and not is_hover:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            self.battle_manager.handle_click(mouse_x, mouse_y, screen.get_height())

        # 更新鼠标状态
        self.mouse_pressed_last_frame = mouse_pressed

        # 显示FPS
        fps_text = self.fonts['small'].render(f"FPS: {self.engine.get_fps():.1f}", True, (200, 200, 200))
        screen.blit(fps_text, (screen.get_width() - 120, 20))

        # 底部游戏提示
        hint_y = screen.get_height() - 20
        hint_text = self.fonts['small'].render(
            "提示: 点击卡片后点击网格放置单位 | ESC 打开菜单",
            True,
            (180, 180, 180)
        )
        hint_rect = hint_text.get_rect(center=(screen.get_width() // 2, hint_y))
        screen.blit(hint_text, hint_rect)

        # 检查游戏结束
        if self.battle_manager.game_over:
            if self.battle_manager.victory:
                self.engine.change_state(GameState.VICTORY)
            else:
                self.engine.change_state(GameState.DEFEAT)

        # 更新性能监控
        if self.performance_monitor:
            self.performance_monitor.update(self.engine.get_fps())

    def state_pause(self, screen: pygame.Surface, delta_time: float):
        """暂停状态处理"""
        # 绘制半透明遮罩
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # 暂停文字
        title = self.fonts['huge'].render("游戏暂停", True, (255, 255, 255))
        title_rect = title.get_rect(center=(screen.get_width() // 2, 180))
        screen.blit(title, title_rect)

        # 菜单选项
        menu_items = [
            ("继续游戏 (ESC)", "resume"),
            ("返回战役选择", "campaign"),
            ("返回主菜单", "menu"),
            ("退出游戏", "quit")
        ]

        y_start = 300
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = pygame.mouse.get_pressed()[0]

        for i, (text, action) in enumerate(menu_items):
            # 计算按钮位置
            button_y = y_start + i * 80
            button_rect = pygame.Rect(
                screen.get_width() // 2 - 200,
                button_y - 25,
                400,
                60
            )

            # 检测鼠标悬停
            is_hover = button_rect.collidepoint(mouse_pos)

            # 绘制按钮背景
            if is_hover:
                pygame.draw.rect(screen, (80, 80, 120), button_rect)
                pygame.draw.rect(screen, (150, 150, 200), button_rect, 3)
                color = (255, 255, 100)
            else:
                pygame.draw.rect(screen, (40, 40, 60), button_rect)
                pygame.draw.rect(screen, (100, 100, 140), button_rect, 2)
                color = (220, 220, 220)

            # 绘制文字
            menu_text = self.fonts['large'].render(text, True, color)
            text_rect = menu_text.get_rect(center=(screen.get_width() // 2, button_y))
            screen.blit(menu_text, text_rect)

            # 处理点击
            if is_hover and mouse_clicked:
                if action == "resume":
                    self.engine.change_state(GameState.BATTLE)
                elif action == "campaign":
                    self.engine.change_state(GameState.CAMPAIGN_SELECT)
                elif action == "menu":
                    self.engine.change_state(GameState.MENU)
                elif action == "quit":
                    self.engine.change_state(GameState.QUIT)
                # 避免重复点击
                pygame.time.wait(200)

        # 显示快捷键提示
        hint = self.fonts['small'].render("F11: 全屏切换", True, (150, 150, 150))
        screen.blit(hint, (screen.get_width() // 2 - 80, screen.get_height() - 60))

    def state_victory(self, screen: pygame.Surface, delta_time: float):
        """胜利状态处理"""
        screen.fill((40, 80, 40))

        # 胜利标题
        text = self.fonts['huge'].render("胜利！", True, (100, 255, 100))
        text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 100))
        screen.blit(text, text_rect)

        # 胜利信息
        victory_info = self.fonts['normal'].render("恭喜完成本关卡！", True, (200, 255, 200))
        info_rect = victory_info.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(victory_info, info_rect)

        # 菜单选项
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = pygame.mouse.get_pressed()[0]

        menu_items = [
            ("下一关", "next"),
            ("返回主菜单", "menu"),
        ]

        button_width = 300
        button_height = 50
        start_y = screen.get_height() // 2 + 80

        for i, (text, action) in enumerate(menu_items):
            button_y = start_y + i * 70
            button_rect = pygame.Rect(
                screen.get_width() // 2 - button_width // 2,
                button_y - button_height // 2,
                button_width,
                button_height
            )

            # 检测鼠标悬停
            is_hover = button_rect.collidepoint(mouse_pos)

            # 绘制按钮
            if is_hover:
                pygame.draw.rect(screen, (70, 120, 70), button_rect)
                pygame.draw.rect(screen, (100, 255, 100), button_rect, 3)
                color = (255, 255, 150)
            else:
                pygame.draw.rect(screen, (40, 80, 40), button_rect)
                pygame.draw.rect(screen, (80, 160, 80), button_rect, 2)
                color = (200, 255, 200)

            # 绘制文字
            button_text = self.fonts['normal'].render(text, True, color)
            text_rect = button_text.get_rect(center=(screen.get_width() // 2, button_y))
            screen.blit(button_text, text_rect)

            # 处理点击
            if is_hover and mouse_clicked:
                if action == "next":
                    # TODO: 实现下一关逻辑
                    logger.info("进入下一关")
                    self.engine.change_state(GameState.BATTLE)
                elif action == "menu":
                    self.engine.change_state(GameState.MENU)
                pygame.time.wait(200)

        # 底部提示
        hint = self.fonts['small'].render("ESC: 返回主菜单", True, (150, 200, 150))
        screen.blit(hint, (screen.get_width() // 2 - 100, screen.get_height() - 60))

    def state_defeat(self, screen: pygame.Surface, delta_time: float):
        """失败状态处理"""
        screen.fill((80, 40, 40))

        # 失败标题
        text = self.fonts['huge'].render("失败", True, (255, 100, 100))
        text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 100))
        screen.blit(text, text_rect)

        # 失败信息
        defeat_info = self.fonts['normal'].render("再接再厉，再试一次！", True, (255, 180, 180))
        info_rect = defeat_info.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(defeat_info, info_rect)

        # 菜单选项
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = pygame.mouse.get_pressed()[0]

        menu_items = [
            ("重试本关", "retry"),
            ("返回主菜单", "menu"),
        ]

        button_width = 300
        button_height = 50
        start_y = screen.get_height() // 2 + 80

        for i, (text, action) in enumerate(menu_items):
            button_y = start_y + i * 70
            button_rect = pygame.Rect(
                screen.get_width() // 2 - button_width // 2,
                button_y - button_height // 2,
                button_width,
                button_height
            )

            # 检测鼠标悬停
            is_hover = button_rect.collidepoint(mouse_pos)

            # 绘制按钮
            if is_hover:
                pygame.draw.rect(screen, (120, 60, 60), button_rect)
                pygame.draw.rect(screen, (255, 100, 100), button_rect, 3)
                color = (255, 255, 150)
            else:
                pygame.draw.rect(screen, (80, 40, 40), button_rect)
                pygame.draw.rect(screen, (160, 80, 80), button_rect, 2)
                color = (255, 180, 180)

            # 绘制文字
            button_text = self.fonts['normal'].render(text, True, color)
            text_rect = button_text.get_rect(center=(screen.get_width() // 2, button_y))
            screen.blit(button_text, text_rect)

            # 处理点击
            if is_hover and mouse_clicked:
                if action == "retry":
                    logger.info("重试关卡")
                    self.engine.change_state(GameState.BATTLE)
                elif action == "menu":
                    self.engine.change_state(GameState.MENU)
                pygame.time.wait(200)

        # 底部提示
        hint = self.fonts['small'].render("ESC: 返回主菜单", True, (200, 150, 150))
        screen.blit(hint, (screen.get_width() // 2 - 100, screen.get_height() - 60))

    def run(self):
        """运行游戏"""
        try:
            self.engine.run()
        except KeyboardInterrupt:
            logger.info("用户中断")
        except Exception as e:
            logger.error(f"游戏运行错误: {e}", exc_info=True)
        finally:
            self.cleanup()

    def cleanup(self):
        """清理资源"""
        logger.info("清理资源...")
        self.config_loader.stop_auto_scan()
        self.entity_manager.clear_all()
        logger.info("游戏退出")


def main():
    """主函数"""
    try:
        game = CrossVerseArena()
        game.run()
    except Exception as e:
        logger.error(f"游戏启动失败: {e}", exc_info=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
