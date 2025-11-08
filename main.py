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
from core.save_manager import get_save_manager
from core.theme_manager import get_theme_manager

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

        # 初始化存档管理器
        self.save_manager = get_save_manager("saves")

        # 初始化UI主题管理器
        self.theme_manager = get_theme_manager(self.settings)

        # 战斗管理器（在进入战斗时初始化）
        self.battle_manager: Optional[BattleManager] = None
        self.current_level_config: Optional[dict] = None
        self.current_campaign_id: Optional[str] = None  # 当前选择的战役ID

        # 选中的角色列表（在角色选择界面选择）
        self.selected_characters: list = []

        # 关卡选择界面分页
        self.level_page = 0  # 当前页码
        self.levels_per_page = 6  # 每页显示关卡数

        # 胜利/失败状态标志
        self.level_completed_saved = False  # 是否已保存关卡完成状态

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
        self.engine.register_state_handler(GameState.LEVEL_SELECT, self.state_level_select)
        self.engine.register_state_handler(GameState.CHARACTER_SELECT, self.state_character_select)
        self.engine.register_state_handler(GameState.BATTLE, self.state_battle)
        self.engine.register_state_handler(GameState.PAUSE, self.state_pause)
        self.engine.register_state_handler(GameState.VICTORY, self.state_victory)
        self.engine.register_state_handler(GameState.DEFEAT, self.state_defeat)

    def state_loading(self, screen: pygame.Surface, delta_time: float):
        """加载状态处理"""
        # 使用主菜单背景颜色（加载屏幕没有单独配置）
        bg_color = self.theme_manager.get_background_color("main_menu")
        screen.fill(bg_color)

        # 显示加载文字 - 使用普通文字颜色
        text_color = self.theme_manager.get_text_color("normal")
        text = self.fonts['large'].render("Loading...", True, text_color)
        text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(text, text_rect)

        # 加载完成后切换到主菜单
        if self.engine.frame_count > 60:  # 等待1秒
            self.engine.change_state(GameState.MENU)

    def state_menu(self, screen: pygame.Surface, delta_time: float):
        """主菜单状态处理"""
        # 使用主题管理器获取背景颜色
        bg_color = self.theme_manager.get_background_color("main_menu")
        screen.fill(bg_color)

        # 绘制标题 - 使用标题文字颜色
        title_color = self.theme_manager.get_text_color("title")
        title = self.fonts['huge'].render("CrossVerse Arena", True, title_color)
        title_rect = title.get_rect(center=(screen.get_width() // 2, 150))
        screen.blit(title, title_rect)

        # 绘制副标题 - 使用副标题文字颜色
        subtitle_color = self.theme_manager.get_text_color("subtitle")
        subtitle = self.fonts['normal'].render("宇宙竞技场", True, subtitle_color)
        subtitle_rect = subtitle.get_rect(center=(screen.get_width() // 2, 220))
        screen.blit(subtitle, subtitle_rect)

        # 绘制菜单选项
        menu_items = [
            ("开始游戏", GameState.CAMPAIGN_SELECT),
            ("设置", GameState.SETTINGS),
            ("退出", GameState.QUIT)
        ]

        # 使用普通文字颜色和副标题颜色
        normal_color = self.theme_manager.get_text_color("normal")
        secondary_color = self.theme_manager.get_text_color("subtitle")

        y_start = 320
        for i, (text, target_state) in enumerate(menu_items):
            color = normal_color if i == 0 else secondary_color
            menu_text = self.fonts['large'].render(text, True, color)
            menu_rect = menu_text.get_rect(center=(screen.get_width() // 2, y_start + i * 70))
            screen.blit(menu_text, menu_rect)

            # 处理点击
            if pygame.mouse.get_pressed()[0]:
                mouse_pos = pygame.mouse.get_pos()
                if menu_rect.collidepoint(mouse_pos):
                    self.engine.change_state(target_state)

        # 显示统计信息 - 使用提示文字颜色
        hint_color = self.theme_manager.get_text_color("hint")
        stats = [
            f"FPS: {self.engine.get_fps():.1f}"
        ]

        for i, stat in enumerate(stats):
            stat_text = self.fonts['small'].render(stat, True, hint_color)
            screen.blit(stat_text, (20, 20 + i * 30))

        # 底部提示信息
        info_color = self.theme_manager.get_text_color("info")
        tips = [
            "F11 或 Alt+Enter: 切换全屏",
            "ESC: 返回上一级 / 暂停游戏",
            "Ctrl+Shift+D: 打开管理界面"
        ]

        for i, tip_text in enumerate(tips):
            # 第3条提示使用info颜色，其他使用hint颜色
            color = info_color if i == 2 else hint_color
            tip = self.fonts['small'].render(tip_text, True, color)
            tip_rect = tip.get_rect(center=(screen.get_width() // 2, screen.get_height() - 80 + i * 25))
            screen.blit(tip, tip_rect)

    def state_campaign_select(self, screen: pygame.Surface, delta_time: float):
        """战役选择状态处理"""
        # 使用主题管理器获取背景颜色
        bg_color = self.theme_manager.get_background_color("campaign_select")
        screen.fill(bg_color)

        # 标题 - 使用标题文字颜色
        title_color = self.theme_manager.get_text_color("title")
        title = self.fonts['title'].render("选择战役", True, title_color)
        title_rect = title.get_rect(center=(screen.get_width() // 2, 80))
        screen.blit(title, title_rect)

        # 显示战役列表
        y = 160

        if not self.config_loader.campaigns:
            # 使用副标题文字颜色
            subtitle_color = self.theme_manager.get_text_color("subtitle")
            no_campaign = self.fonts['normal'].render("暂无可用战役", True, subtitle_color)
            screen.blit(no_campaign, (screen.get_width() // 2 - 100, y))
        else:
            # 使用普通文字颜色和副标题颜色
            normal_color = self.theme_manager.get_text_color("normal")
            subtitle_color = self.theme_manager.get_text_color("subtitle")

            for campaign_id, campaign in self.config_loader.campaigns.items():
                campaign_name = campaign.get('name', campaign_id)
                desc = campaign.get('description', '')

                # 战役名称 - 使用普通文字颜色
                name_text = self.fonts['normal'].render(campaign_name, True, normal_color)
                name_rect = name_text.get_rect(center=(screen.get_width() // 2, y))
                screen.blit(name_text, name_rect)

                # 描述 - 使用副标题颜色
                desc_text = self.fonts['small'].render(desc[:60], True, subtitle_color)
                desc_rect = desc_text.get_rect(center=(screen.get_width() // 2, y + 35))
                screen.blit(desc_text, desc_rect)

                # 点击检测
                click_rect = pygame.Rect(
                    screen.get_width() // 2 - 300,
                    y - 20,
                    600,
                    70
                )

                # 检测悬停 - 使用按钮边框颜色
                is_hover = click_rect.collidepoint(pygame.mouse.get_pos())
                border_color = self.theme_manager.get_color("button", "hover_border" if is_hover else "normal_border")
                border_width = 3 if is_hover else 2
                pygame.draw.rect(screen, border_color, click_rect, border_width)

                if pygame.mouse.get_pressed()[0] and is_hover:
                    logger.info(f"选择战役: {campaign_name}")

                    # 保存选择的战役ID
                    self.current_campaign_id = campaign_id
                    self.level_page = 0  # 重置分页

                    # 跳转到关卡选择界面
                    self.engine.change_state(GameState.LEVEL_SELECT)

                    pygame.time.wait(200)

                y += 100

        # 返回按钮 - 使用副标题颜色
        back_color = self.theme_manager.get_text_color("subtitle")
        back_text = self.fonts['normal'].render("返回 (ESC)", True, back_color)
        back_rect = back_text.get_rect(topleft=(40, 40))
        screen.blit(back_text, back_rect)

        if pygame.mouse.get_pressed()[0]:
            if back_rect.collidepoint(pygame.mouse.get_pos()):
                self.engine.change_state(GameState.MENU)
                pygame.time.wait(200)

    def state_level_select(self, screen: pygame.Surface, delta_time: float):
        """关卡选择状态处理"""
        # 使用主题管理器获取背景颜色
        bg_color = self.theme_manager.get_background_color("level_select")
        screen.fill(bg_color)

        # 获取当前战役的所有关卡
        if not self.current_campaign_id:
            # 使用主题管理器获取错误文字颜色
            error_color = self.theme_manager.get_text_color("error")
            error_text = self.fonts['normal'].render("错误：未选择战役", True, error_color)
            screen.blit(error_text, (screen.get_width() // 2 - 100, 300))
            return

        # 筛选当前战役的关卡
        campaign_levels = []
        for level_id, level_config in self.config_loader.levels.items():
            if level_id.startswith(self.current_campaign_id):
                campaign_levels.append((level_id, level_config))

        # 按关卡编号排序
        campaign_levels.sort(key=lambda x: x[0])

        # 获取战役信息
        campaign = self.config_loader.campaigns.get(self.current_campaign_id, {})
        campaign_name = campaign.get('name', self.current_campaign_id)

        # 标题 - 使用主题管理器获取标题颜色
        title_color = self.theme_manager.get_text_color("title")
        title = self.fonts['title'].render(f"{campaign_name} - 关卡选择", True, title_color)
        title_rect = title.get_rect(center=(screen.get_width() // 2, 60))
        screen.blit(title, title_rect)

        # 进度信息 - 使用主题管理器获取成功文字颜色
        progress = self.save_manager.get_campaign_progress(
            self.current_campaign_id,
            [lvl[0] for lvl in campaign_levels]
        )
        progress_color = self.theme_manager.get_text_color("success")
        progress_text = self.fonts['normal'].render(
            f"进度: {progress['completed']}/{progress['total']} ({progress['percentage']:.0f}%)",
            True,
            progress_color
        )
        progress_rect = progress_text.get_rect(center=(screen.get_width() // 2, 120))
        screen.blit(progress_text, progress_rect)

        # 分页计算
        total_levels = len(campaign_levels)
        total_pages = (total_levels + self.levels_per_page - 1) // self.levels_per_page
        start_idx = self.level_page * self.levels_per_page
        end_idx = min(start_idx + self.levels_per_page, total_levels)
        page_levels = campaign_levels[start_idx:end_idx]

        # 绘制关卡卡片（2行3列）
        card_width = 360
        card_height = 140
        card_spacing_x = 20
        card_spacing_y = 20
        cards_per_row = 2
        start_x = (screen.get_width() - (cards_per_row * card_width + (cards_per_row - 1) * card_spacing_x)) // 2
        start_y = 180

        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]
        mouse_just_clicked = mouse_pressed and not self.mouse_pressed_last_frame

        for i, (level_id, level_config) in enumerate(page_levels):
            row = i // cards_per_row
            col = i % cards_per_row

            x = start_x + col * (card_width + card_spacing_x)
            y = start_y + row * (card_height + card_spacing_y)

            card_rect = pygame.Rect(x, y, card_width, card_height)

            # 检查解锁和完成状态
            is_unlocked = self.save_manager.is_level_unlocked(level_id)
            is_completed = self.save_manager.is_level_completed(level_id)
            is_hover = card_rect.collidepoint(mouse_pos)

            # 绘制卡片背景 - 使用主题管理器获取颜色
            if is_completed:
                # 已完成状态 - 绿色
                bg_color = self.theme_manager.get_color("card", "level_completed_bg")
                border_color = self.theme_manager.get_color("card", "level_completed_border")
                status_text = "✓ 已完成"
                status_color = self.theme_manager.get_color("card", "level_completed_text")
            elif is_unlocked:
                # 已解锁状态 - 蓝色，悬停时变亮
                if is_hover:
                    bg_color = self.theme_manager.get_color("card", "level_unlocked_hover_bg")
                    border_color = self.theme_manager.get_color("card", "level_unlocked_hover_border")
                else:
                    bg_color = self.theme_manager.get_color("card", "level_unlocked_bg")
                    border_color = self.theme_manager.get_color("card", "level_unlocked_border")
                status_text = "可进入"
                status_color = self.theme_manager.get_color("card", "level_unlocked_text")
            else:
                # 未解锁状态 - 灰色
                bg_color = self.theme_manager.get_color("card", "level_locked_bg")
                border_color = self.theme_manager.get_color("card", "level_locked_border")
                status_text = "🔒 未解锁"
                status_color = self.theme_manager.get_color("card", "level_locked_text")

            pygame.draw.rect(screen, bg_color, card_rect)
            pygame.draw.rect(screen, border_color, card_rect, 3 if is_hover and is_unlocked else 2)

            # 关卡名称 - 使用普通文字颜色
            level_name = level_config.get('name', level_id)
            name_color = self.theme_manager.get_text_color("normal")
            name_text = self.fonts['large'].render(level_name[:20], True, name_color)
            name_rect = name_text.get_rect(topleft=(x + 15, y + 15))
            screen.blit(name_text, name_rect)

            # 状态标签（颜色已在上面根据状态设置）
            status_label = self.fonts['small'].render(status_text, True, status_color)
            status_rect = status_label.get_rect(topright=(x + card_width - 15, y + 15))
            screen.blit(status_label, status_rect)

            # 关卡信息（第二行） - 使用主题管理器的图标颜色
            info_y = y + 55
            info_x = x + 15

            # 初始金币 - 使用金币图标颜色
            economy = level_config.get('economy', {})
            gold_color = self.theme_manager.get_color("icon", "gold")
            gold_icon = self.fonts['small'].render(f"💰 金币: {economy.get('initial_gold', 200)}", True, gold_color)
            screen.blit(gold_icon, (info_x, info_y))

            # 基地血量 - 使用血量图标颜色
            base = level_config.get('base', {})
            hp_color = self.theme_manager.get_color("icon", "hp")
            hp_icon = self.fonts['small'].render(f"❤️ 血量: {base.get('initial_hp', 1000)}", True, hp_color)
            screen.blit(hp_icon, (info_x + 150, info_y))

            # 波次数量 - 使用波次图标颜色
            waves = level_config.get('waves', [])
            wave_color = self.theme_manager.get_color("icon", "wave")
            wave_icon = self.fonts['small'].render(f"🌊 波次: {len(waves)}", True, wave_color)
            screen.blit(wave_icon, (info_x, info_y + 30))

            # 奖励信息 - 使用奖励图标颜色
            rewards = level_config.get('rewards', {})
            reward_color = self.theme_manager.get_color("icon", "reward")
            reward_icon = self.fonts['small'].render(
                f"🏆 奖励: {rewards.get('gold', 0)} 金币",
                True,
                reward_color
            )
            screen.blit(reward_icon, (info_x, info_y + 60))

            # 处理点击（仅已解锁关卡可点击）
            if is_hover and mouse_just_clicked and is_unlocked:
                logger.info(f"选择关卡: {level_name}")
                self.current_level_config = level_config.copy()
                self.current_level_config['campaign_id'] = self.current_campaign_id
                self.current_level_config['level_id'] = level_id  # 保存完整的关卡ID

                # 跳转到角色选择界面
                self.engine.change_state(GameState.CHARACTER_SELECT)

        # 更新鼠标状态
        self.mouse_pressed_last_frame = mouse_pressed

        # 分页控制
        page_y = screen.get_height() - 120
        # 使用主题管理器获取副标题文字颜色
        subtitle_color = self.theme_manager.get_text_color("subtitle")
        page_info = self.fonts['normal'].render(
            f"第 {self.level_page + 1} / {total_pages} 页",
            True,
            subtitle_color
        )
        page_info_rect = page_info.get_rect(center=(screen.get_width() // 2, page_y))
        screen.blit(page_info, page_info_rect)

        # 上一页按钮 - 使用主题管理器获取按钮颜色
        if self.level_page > 0:
            prev_button = pygame.Rect(screen.get_width() // 2 - 150, page_y - 20, 60, 40)
            is_prev_hover = prev_button.collidepoint(mouse_pos)
            # 根据悬停状态使用不同颜色
            btn_bg = self.theme_manager.get_color("button", "hover_bg" if is_prev_hover else "normal_bg")
            btn_border = self.theme_manager.get_color("button", "hover_border" if is_prev_hover else "normal_border")
            btn_text_color = self.theme_manager.get_text_color("normal")
            pygame.draw.rect(screen, btn_bg, prev_button)
            pygame.draw.rect(screen, btn_border, prev_button, 2)
            prev_text = self.fonts['normal'].render("◀", True, btn_text_color)
            prev_text_rect = prev_text.get_rect(center=prev_button.center)
            screen.blit(prev_text, prev_text_rect)

            if is_prev_hover and mouse_just_clicked:
                self.level_page -= 1

        # 下一页按钮 - 使用主题管理器获取按钮颜色
        if self.level_page < total_pages - 1:
            next_button = pygame.Rect(screen.get_width() // 2 + 90, page_y - 20, 60, 40)
            is_next_hover = next_button.collidepoint(mouse_pos)
            # 根据悬停状态使用不同颜色
            btn_bg = self.theme_manager.get_color("button", "hover_bg" if is_next_hover else "normal_bg")
            btn_border = self.theme_manager.get_color("button", "hover_border" if is_next_hover else "normal_border")
            btn_text_color = self.theme_manager.get_text_color("normal")
            pygame.draw.rect(screen, btn_bg, next_button)
            pygame.draw.rect(screen, btn_border, next_button, 2)
            next_text = self.fonts['normal'].render("▶", True, btn_text_color)
            next_text_rect = next_text.get_rect(center=next_button.center)
            screen.blit(next_text, next_text_rect)

            if is_next_hover and mouse_just_clicked:
                self.level_page += 1

        # 返回按钮 - 使用主题管理器获取副标题颜色
        back_color = self.theme_manager.get_text_color("subtitle")
        back_text = self.fonts['normal'].render("返回战役选择 (ESC)", True, back_color)
        back_rect = back_text.get_rect(topleft=(40, 40))
        screen.blit(back_text, back_rect)

        if back_rect.collidepoint(mouse_pos) and mouse_just_clicked:
            self.engine.change_state(GameState.CAMPAIGN_SELECT)

    def state_character_select(self, screen: pygame.Surface, delta_time: float):
        """角色选择状态处理"""
        # 使用主题管理器获取背景颜色
        bg_color = self.theme_manager.get_background_color("character_select")
        screen.fill(bg_color)

        # 三级配置fallback：关卡配置 -> 全局配置 -> 硬编码默认值
        def get_character_limit(key: str, default: int) -> int:
            # 优先从关卡配置读取
            if self.current_level_config:
                level_char_config = self.current_level_config.get('character_selection', {})
                if key in level_char_config:
                    return level_char_config[key]

            # 其次从全局配置读取
            global_char_config = self.settings.get('gameplay', {}).get('character_selection', {})
            if key in global_char_config:
                return global_char_config[key]

            # 使用默认值
            return default

        max_characters = get_character_limit('max_characters', 6)
        min_characters = get_character_limit('min_characters', 1)

        # 标题 - 使用标题文字颜色
        title_color = self.theme_manager.get_text_color("title")
        title = self.fonts['title'].render("选择角色", True, title_color)
        title_rect = title.get_rect(center=(screen.get_width() // 2, 60))
        screen.blit(title, title_rect)

        # 提示文字 - 使用副标题颜色
        hint_color = self.theme_manager.get_text_color("subtitle")
        hint = self.fonts['normal'].render(f"点击角色卡片选择/取消，最多选择{max_characters}个", True, hint_color)
        hint_rect = hint.get_rect(center=(screen.get_width() // 2, 120))
        screen.blit(hint, hint_rect)

        # 获取所有防守方角色
        if not self.current_level_config:
            error_color = self.theme_manager.get_text_color("error")
            error_text = self.fonts['normal'].render("错误：未选择关卡", True, error_color)
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

            # 绘制卡片背景 - 使用主题管理器获取颜色
            if is_selected:
                bg_color = self.theme_manager.get_color("card", "character_selected_bg")
                border_color = self.theme_manager.get_color("card", "character_selected_border")
            elif is_hover:
                bg_color = self.theme_manager.get_color("card", "character_hover_bg")
                border_color = self.theme_manager.get_color("card", "character_hover_border")
            else:
                bg_color = self.theme_manager.get_color("card", "character_normal_bg")
                border_color = self.theme_manager.get_color("card", "character_normal_border")

            pygame.draw.rect(screen, bg_color, card_rect)
            pygame.draw.rect(screen, border_color, card_rect, 3)

            # 绘制角色名 - 使用普通文字颜色
            name = char_config.get('name', char_id)
            name_color = self.theme_manager.get_text_color("normal")
            name_text = self.fonts['normal'].render(name, True, name_color)
            name_rect = name_text.get_rect(center=(x + card_width // 2, y + 60))
            screen.blit(name_text, name_rect)

            # 绘制角色费用 - 使用金币图标颜色
            cost = char_config.get('cost', 100)
            cost_color = self.theme_manager.get_color("icon", "gold")
            cost_text = self.fonts['small'].render(f"费用: {cost}", True, cost_color)
            cost_rect = cost_text.get_rect(center=(x + card_width // 2, y + 100))
            screen.blit(cost_text, cost_rect)

            # 绘制角色属性 - 使用成功和错误文字颜色
            stats = char_config.get('stats', {})
            success_color = self.theme_manager.get_text_color("success")
            error_color = self.theme_manager.get_text_color("error")
            hp_text = self.fonts['small'].render(f"HP: {stats.get('hp', 0)}", True, success_color)
            atk_text = self.fonts['small'].render(f"攻击: {stats.get('attack', 0)}", True, error_color)
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
                    # 选择角色（从配置读取最大数量）
                    if len(self.selected_characters) < max_characters:
                        self.selected_characters.append(char_id)
                        logger.info(f"选择角色: {name}")
                    else:
                        logger.warning(f"最多只能选择{max_characters}个角色")

        # 更新鼠标状态
        self.mouse_pressed_last_frame = mouse_pressed

        # 显示已选择数量 - 使用警告色和副标题色
        warning_color = self.theme_manager.get_text_color("warning")
        subtitle_color = self.theme_manager.get_text_color("subtitle")
        count_text = self.fonts['normal'].render(
            f"已选择: {len(self.selected_characters)}/{max_characters}",
            True,
            warning_color if len(self.selected_characters) > 0 else subtitle_color
        )
        count_rect = count_text.get_rect(center=(screen.get_width() // 2, screen.get_height() - 120))
        screen.blit(count_text, count_rect)

        # 开始游戏按钮
        button_width = 200
        button_height = 50
        button_x = screen.get_width() // 2 - button_width // 2
        button_y = screen.get_height() - 80
        button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

        button_enabled = len(self.selected_characters) >= min_characters
        is_button_hover = button_rect.collidepoint(mouse_pos)

        # 使用主题管理器获取按钮颜色
        if button_enabled:
            if is_button_hover:
                button_color = self.theme_manager.get_color("button", "hover_bg")
                text_color = self.theme_manager.get_color("button", "hover_text")
                border_color = self.theme_manager.get_color("button", "hover_border")
            else:
                button_color = self.theme_manager.get_color("button", "normal_bg")
                text_color = self.theme_manager.get_color("button", "normal_text")
                border_color = self.theme_manager.get_color("button", "normal_border")
        else:
            button_color = self.theme_manager.get_color("button", "disabled_bg")
            text_color = self.theme_manager.get_color("button", "disabled_text")
            border_color = self.theme_manager.get_color("button", "disabled_border")

        pygame.draw.rect(screen, button_color, button_rect)
        pygame.draw.rect(screen, border_color, button_rect, 2)

        button_text = self.fonts['large'].render("开始游戏", True, text_color)
        button_text_rect = button_text.get_rect(center=(screen.get_width() // 2, button_y + button_height // 2))
        screen.blit(button_text, button_text_rect)

        # 处理开始游戏按钮点击
        if is_button_hover and mouse_just_clicked and button_enabled:
            # 初始化战斗管理器（传入settings配置）
            self.battle_manager = BattleManager(self.config_loader, self.current_level_config, self.settings)

            # 将选中的角色传递给战斗管理器
            self.battle_manager.selected_characters = self.selected_characters.copy()

            # 初始化卡片槽
            self.battle_manager._init_card_slots()

            # 重置关卡完成标志
            self.level_completed_saved = False

            logger.info(f"开始游戏，选择了 {len(self.selected_characters)} 个角色")
            self.engine.change_state(GameState.BATTLE)

        # 返回按钮 - 使用副标题颜色
        back_color = self.theme_manager.get_text_color("subtitle")
        back_text = self.fonts['normal'].render("返回 (ESC)", True, back_color)
        back_rect = back_text.get_rect(topleft=(40, 40))
        screen.blit(back_text, back_rect)

        if back_rect.collidepoint(mouse_pos) and mouse_just_clicked:
            # 清空选择
            self.selected_characters.clear()
            self.engine.change_state(GameState.CAMPAIGN_SELECT)

    def state_battle(self, screen: pygame.Surface, delta_time: float):
        """战斗状态处理"""
        # 使用主题管理器获取背景颜色
        bg_color = self.theme_manager.get_background_color("battle")
        screen.fill(bg_color)

        # 如果战斗管理器未初始化，返回菜单
        if self.battle_manager is None:
            logger.warning("战斗管理器未初始化，返回主菜单")
            self.engine.change_state(GameState.MENU)
            return

        # 更新战斗管理器
        self.battle_manager.update(delta_time, screen.get_width())

        # 渲染战斗场景
        self.battle_manager.render(screen, self.fonts)

        # 绘制菜单按钮（右上角，调整位置避免重叠）
        menu_button_rect = pygame.Rect(screen.get_width() - 140, 85, 120, 40)
        mouse_pos = pygame.mouse.get_pos()
        is_hover = menu_button_rect.collidepoint(mouse_pos)

        # 按钮背景和边框 - 使用主题管理器获取颜色
        if is_hover:
            btn_bg = self.theme_manager.get_color("button", "hover_bg")
            btn_border = self.theme_manager.get_color("button", "hover_border")
            button_text_color = self.theme_manager.get_color("button", "hover_text")
            pygame.draw.rect(screen, btn_bg, menu_button_rect)
            pygame.draw.rect(screen, btn_border, menu_button_rect, 3)
        else:
            btn_bg = self.theme_manager.get_color("button", "normal_bg")
            btn_border = self.theme_manager.get_color("button", "normal_border")
            button_text_color = self.theme_manager.get_color("button", "normal_text")
            pygame.draw.rect(screen, btn_bg, menu_button_rect)
            pygame.draw.rect(screen, btn_border, menu_button_rect, 2)

        # 按钮文字
        pause_text = self.fonts['small'].render("菜单 (ESC)", True, button_text_color)
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

        # 显示FPS（移到右下角避免重叠） - 使用提示文字颜色
        hint_color = self.theme_manager.get_text_color("hint")
        fps_text = self.fonts['small'].render(f"FPS: {self.engine.get_fps():.1f}", True, hint_color)
        screen.blit(fps_text, (screen.get_width() - 100, screen.get_height() - 30))

        # 底部游戏提示（左下角，避免和FPS重叠） - 使用提示文字颜色
        hint_text = self.fonts['small'].render(
            "点击卡片→点击网格放置 | ESC菜单",
            True,
            hint_color
        )
        screen.blit(hint_text, (20, screen.get_height() - 30))

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
        # 绘制半透明遮罩 - 使用主题管理器获取暂停背景色（RGBA）
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        pause_bg = self.theme_manager.get_background_color("pause")
        overlay.fill(pause_bg)
        screen.blit(overlay, (0, 0))

        # 暂停文字 - 使用普通文字颜色
        title_color = self.theme_manager.get_text_color("normal")
        title = self.fonts['huge'].render("游戏暂停", True, title_color)
        title_rect = title.get_rect(center=(screen.get_width() // 2, 180))
        screen.blit(title, title_rect)

        # 菜单选项
        menu_items = [
            ("继续游戏 (ESC)", "resume"),
            ("返回关卡选择", "levels"),
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

            # 绘制按钮背景 - 使用主题管理器获取颜色
            if is_hover:
                btn_bg = self.theme_manager.get_color("button", "hover_bg")
                btn_border = self.theme_manager.get_color("button", "hover_border")
                text_color = self.theme_manager.get_color("button", "hover_text")
                pygame.draw.rect(screen, btn_bg, button_rect)
                pygame.draw.rect(screen, btn_border, button_rect, 3)
            else:
                btn_bg = self.theme_manager.get_color("button", "normal_bg")
                btn_border = self.theme_manager.get_color("button", "normal_border")
                text_color = self.theme_manager.get_color("button", "normal_text")
                pygame.draw.rect(screen, btn_bg, button_rect)
                pygame.draw.rect(screen, btn_border, button_rect, 2)

            # 绘制文字
            menu_text = self.fonts['large'].render(text, True, text_color)
            text_rect = menu_text.get_rect(center=(screen.get_width() // 2, button_y))
            screen.blit(menu_text, text_rect)

            # 处理点击
            if is_hover and mouse_clicked:
                if action == "resume":
                    self.engine.change_state(GameState.BATTLE)
                elif action == "levels":
                    self.engine.change_state(GameState.LEVEL_SELECT)
                elif action == "menu":
                    self.engine.change_state(GameState.MENU)
                elif action == "quit":
                    self.engine.change_state(GameState.QUIT)
                # 避免重复点击
                pygame.time.wait(200)

        # 显示快捷键提示 - 使用提示文字颜色
        hint_color = self.theme_manager.get_text_color("hint")
        hint = self.fonts['small'].render("F11: 全屏切换", True, hint_color)
        screen.blit(hint, (screen.get_width() // 2 - 80, screen.get_height() - 60))

    def state_victory(self, screen: pygame.Surface, delta_time: float):
        """胜利状态处理"""
        # 使用主题管理器获取背景颜色
        bg_color = self.theme_manager.get_background_color("victory")
        screen.fill(bg_color)

        # 首次进入胜利界面时保存关卡完成状态
        if not self.level_completed_saved and self.current_level_config:
            level_id = self.current_level_config.get('level_id')
            if level_id:
                # 获取奖励配置
                rewards = self.current_level_config.get('rewards', {})

                # 保存关卡完成状态
                self.save_manager.complete_level(level_id, rewards)
                self.level_completed_saved = True

                logger.info(f"关卡完成已保存: {level_id}")

        # 胜利标题 - 使用成功文字颜色
        success_color = self.theme_manager.get_text_color("success")
        text = self.fonts['huge'].render("胜利！", True, success_color)
        text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 100))
        screen.blit(text, text_rect)

        # 胜利信息 - 使用成功文字颜色
        victory_info = self.fonts['normal'].render("恭喜完成本关卡！", True, success_color)
        info_rect = victory_info.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(victory_info, info_rect)

        # 菜单选项
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = pygame.mouse.get_pressed()[0]

        menu_items = [
            ("返回关卡选择", "levels"),
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

            # 绘制按钮 - 使用主题管理器获取颜色
            if is_hover:
                btn_bg = self.theme_manager.get_color("button", "hover_bg")
                btn_border = self.theme_manager.get_color("button", "hover_border")
                text_color = self.theme_manager.get_color("button", "hover_text")
                pygame.draw.rect(screen, btn_bg, button_rect)
                pygame.draw.rect(screen, btn_border, button_rect, 3)
            else:
                btn_bg = self.theme_manager.get_color("button", "normal_bg")
                btn_border = self.theme_manager.get_color("button", "normal_border")
                text_color = self.theme_manager.get_color("button", "normal_text")
                pygame.draw.rect(screen, btn_bg, button_rect)
                pygame.draw.rect(screen, btn_border, button_rect, 2)

            # 绘制文字
            button_text = self.fonts['normal'].render(text, True, text_color)
            text_rect = button_text.get_rect(center=(screen.get_width() // 2, button_y))
            screen.blit(button_text, text_rect)

            # 处理点击
            if is_hover and mouse_clicked:
                if action == "levels":
                    # 返回关卡选择界面
                    logger.info("返回关卡选择")
                    self.engine.change_state(GameState.LEVEL_SELECT)
                elif action == "menu":
                    # 返回主菜单
                    self.engine.change_state(GameState.MENU)
                pygame.time.wait(200)

        # 底部提示 - 使用提示文字颜色
        hint_color = self.theme_manager.get_text_color("hint")
        hint = self.fonts['small'].render("ESC: 返回主菜单", True, hint_color)
        screen.blit(hint, (screen.get_width() // 2 - 100, screen.get_height() - 60))

    def state_defeat(self, screen: pygame.Surface, delta_time: float):
        """失败状态处理"""
        # 使用主题管理器获取背景颜色
        bg_color = self.theme_manager.get_background_color("defeat")
        screen.fill(bg_color)

        # 失败标题 - 使用错误文字颜色
        error_color = self.theme_manager.get_text_color("error")
        text = self.fonts['huge'].render("失败", True, error_color)
        text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 100))
        screen.blit(text, text_rect)

        # 失败信息 - 使用错误文字颜色
        defeat_info = self.fonts['normal'].render("再接再厉，再试一次！", True, error_color)
        info_rect = defeat_info.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(defeat_info, info_rect)

        # 菜单选项
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = pygame.mouse.get_pressed()[0]

        menu_items = [
            ("重试本关", "retry"),
            ("返回关卡选择", "levels"),
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

            # 绘制按钮 - 使用主题管理器获取颜色
            if is_hover:
                btn_bg = self.theme_manager.get_color("button", "hover_bg")
                btn_border = self.theme_manager.get_color("button", "hover_border")
                text_color = self.theme_manager.get_color("button", "hover_text")
                pygame.draw.rect(screen, btn_bg, button_rect)
                pygame.draw.rect(screen, btn_border, button_rect, 3)
            else:
                btn_bg = self.theme_manager.get_color("button", "normal_bg")
                btn_border = self.theme_manager.get_color("button", "normal_border")
                text_color = self.theme_manager.get_color("button", "normal_text")
                pygame.draw.rect(screen, btn_bg, button_rect)
                pygame.draw.rect(screen, btn_border, button_rect, 2)

            # 绘制文字
            button_text = self.fonts['normal'].render(text, True, text_color)
            text_rect = button_text.get_rect(center=(screen.get_width() // 2, button_y))
            screen.blit(button_text, text_rect)

            # 处理点击
            if is_hover and mouse_clicked:
                if action == "retry":
                    logger.info("重试关卡")
                    # 重新初始化战斗管理器（传入settings配置）
                    if self.current_level_config and self.selected_characters:
                        self.battle_manager = BattleManager(self.config_loader, self.current_level_config, self.settings)
                        self.battle_manager.selected_characters = self.selected_characters.copy()
                        self.battle_manager._init_card_slots()
                        # 重置关卡完成标志
                        self.level_completed_saved = False
                        logger.info("战斗管理器已重新初始化")
                    self.engine.change_state(GameState.BATTLE)
                elif action == "levels":
                    # 返回关卡选择界面
                    logger.info("返回关卡选择")
                    self.engine.change_state(GameState.LEVEL_SELECT)
                elif action == "menu":
                    # 返回主菜单
                    self.engine.change_state(GameState.MENU)
                pygame.time.wait(200)

        # 底部提示 - 使用提示文字颜色
        hint_color = self.theme_manager.get_text_color("hint")
        hint = self.fonts['small'].render("ESC: 返回主菜单", True, hint_color)
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
