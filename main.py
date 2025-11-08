"""
CrossVerse Arena - 宇宙竞技场
主程序入口

一个高度模块化、完全由配置驱动的跨IP角色对战塔防平台
"""

import sys
import os
import logging
import pygame

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入核心模块
from core.config_loader import get_config_loader
from core.resource_loader import get_resource_loader
from core.game_engine import GameEngine, GameState
from core.entity_manager import get_entity_manager
from core.performance_monitor import get_performance_monitor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game.log', encoding='utf-8'),
        logging.StreamHandler()
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

        # 初始化游戏引擎
        self.engine = GameEngine(self.settings)

        # 初始化性能监控
        perf_config = self.settings.get('performance_system', {})
        self.performance_monitor = get_performance_monitor(perf_config)

        # 初始化实体管理器
        self.entity_manager = get_entity_manager()

        # 注册状态处理器
        self.register_state_handlers()

        # 启动配置自动扫描
        if self.settings.get('admin', {}).get('enabled', True):
            self.config_loader.start_auto_scan()

        logger.info("游戏初始化完成")

    def register_state_handlers(self):
        """注册游戏状态处理器"""
        self.engine.register_state_handler(GameState.LOADING, self.state_loading)
        self.engine.register_state_handler(GameState.MENU, self.state_menu)
        self.engine.register_state_handler(GameState.CAMPAIGN_SELECT, self.state_campaign_select)
        self.engine.register_state_handler(GameState.BATTLE, self.state_battle)
        self.engine.register_state_handler(GameState.PAUSE, self.state_pause)
        self.engine.register_state_handler(GameState.VICTORY, self.state_victory)
        self.engine.register_state_handler(GameState.DEFEAT, self.state_defeat)

    def state_loading(self, screen: pygame.Surface, delta_time: float):
        """加载状态处理"""
        screen.fill((0, 0, 0))

        # 显示加载文字
        font = pygame.font.Font(None, 48)
        text = font.render("Loading...", True, (255, 255, 255))
        text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(text, text_rect)

        # 加载完成后切换到主菜单
        if self.engine.frame_count > 60:  # 等待1秒
            self.engine.change_state(GameState.MENU)

    def state_menu(self, screen: pygame.Surface, delta_time: float):
        """主菜单状态处理"""
        screen.fill((20, 20, 40))

        # 绘制标题
        font_title = pygame.font.Font(None, 72)
        title = font_title.render("CrossVerse Arena", True, (255, 200, 50))
        title_rect = title.get_rect(center=(screen.get_width() // 2, 150))
        screen.blit(title, title_rect)

        # 绘制副标题
        font_subtitle = pygame.font.Font(None, 36)
        subtitle = font_subtitle.render("宇宙竞技场", True, (200, 200, 200))
        subtitle_rect = subtitle.get_rect(center=(screen.get_width() // 2, 220))
        screen.blit(subtitle, subtitle_rect)

        # 绘制菜单选项
        font_menu = pygame.font.Font(None, 42)
        menu_items = [
            ("开始游戏", GameState.CAMPAIGN_SELECT),
            ("设置", GameState.SETTINGS),
            ("退出", GameState.QUIT)
        ]

        y_start = 320
        for i, (text, target_state) in enumerate(menu_items):
            color = (255, 255, 255) if i == 0 else (180, 180, 180)
            menu_text = font_menu.render(text, True, color)
            menu_rect = menu_text.get_rect(center=(screen.get_width() // 2, y_start + i * 70))
            screen.blit(menu_text, menu_rect)

            # 处理点击
            if pygame.mouse.get_pressed()[0]:
                mouse_pos = pygame.mouse.get_pos()
                if menu_rect.collidepoint(mouse_pos):
                    self.engine.change_state(target_state)

        # 显示统计信息
        font_info = pygame.font.Font(None, 24)
        stats = [
            f"游戏IP: {len(self.config_loader.games)}",
            f"角色: {len(self.config_loader.characters)}",
            f"皮肤: {len(self.config_loader.skins)}",
            f"战役: {len(self.config_loader.campaigns)}",
            f"关卡: {len(self.config_loader.levels)}",
            f"FPS: {self.engine.get_fps():.1f}"
        ]

        for i, stat in enumerate(stats):
            stat_text = font_info.render(stat, True, (150, 150, 150))
            screen.blit(stat_text, (20, 20 + i * 30))

        # 显示提示
        tip = font_info.render("按 Ctrl+Shift+D 打开管理界面", True, (100, 150, 100))
        screen.blit(tip, (screen.get_width() - 300, screen.get_height() - 40))

    def state_campaign_select(self, screen: pygame.Surface, delta_time: float):
        """战役选择状态处理"""
        screen.fill((30, 30, 50))

        # 标题
        font_title = pygame.font.Font(None, 54)
        title = font_title.render("选择战役", True, (255, 200, 50))
        title_rect = title.get_rect(center=(screen.get_width() // 2, 80))
        screen.blit(title, title_rect)

        # 显示战役列表
        font_campaign = pygame.font.Font(None, 36)
        y = 160

        if not self.config_loader.campaigns:
            no_campaign = font_campaign.render("暂无可用战役", True, (200, 200, 200))
            screen.blit(no_campaign, (screen.get_width() // 2 - 100, y))
        else:
            for campaign_id, campaign in self.config_loader.campaigns.items():
                campaign_name = campaign.get('name', campaign_id)
                desc = campaign.get('description', '')

                # 战役名称
                name_text = font_campaign.render(campaign_name, True, (255, 255, 255))
                name_rect = name_text.get_rect(center=(screen.get_width() // 2, y))
                screen.blit(name_text, name_rect)

                # 描述
                font_desc = pygame.font.Font(None, 24)
                desc_text = font_desc.render(desc[:60], True, (180, 180, 180))
                desc_rect = desc_text.get_rect(center=(screen.get_width() // 2, y + 35))
                screen.blit(desc_text, desc_rect)

                # 点击检测
                click_rect = pygame.Rect(
                    screen.get_width() // 2 - 300,
                    y - 20,
                    600,
                    70
                )
                pygame.draw.rect(screen, (60, 60, 100), click_rect, 2)

                if pygame.mouse.get_pressed()[0]:
                    if click_rect.collidepoint(pygame.mouse.get_pos()):
                        logger.info(f"选择战役: {campaign_name}")
                        self.engine.change_state(GameState.BATTLE)

                y += 100

        # 返回按钮
        font_back = pygame.font.Font(None, 32)
        back_text = font_back.render("返回", True, (200, 200, 200))
        back_rect = back_text.get_rect(topleft=(40, 40))
        screen.blit(back_text, back_rect)

        if pygame.mouse.get_pressed()[0]:
            if back_rect.collidepoint(pygame.mouse.get_pos()):
                self.engine.change_state(GameState.MENU)

    def state_battle(self, screen: pygame.Surface, delta_time: float):
        """战斗状态处理"""
        screen.fill((40, 60, 40))

        # 更新实体
        self.entity_manager.update_all(delta_time)

        # 渲染实体
        self.entity_manager.render_all(screen)

        # 绘制战斗UI
        font = pygame.font.Font(None, 32)

        # 显示基地血量
        hp_text = font.render("基地 HP: 1000 / 1000", True, (255, 100, 100))
        screen.blit(hp_text, (20, 20))

        # 显示资源
        resource_text = font.render("金币: 500", True, (255, 200, 50))
        screen.blit(resource_text, (20, 60))

        # 显示FPS
        fps_text = font.render(f"FPS: {self.engine.get_fps():.1f}", True, (200, 200, 200))
        screen.blit(fps_text, (screen.get_width() - 150, 20))

        # 暂停按钮
        pause_text = font.render("暂停 (ESC)", True, (200, 200, 200))
        pause_rect = pause_text.get_rect(topright=(screen.get_width() - 20, 60))
        screen.blit(pause_text, pause_rect)

        # 更新性能监控
        if self.performance_monitor:
            self.performance_monitor.update(self.engine.get_fps())

    def state_pause(self, screen: pygame.Surface, delta_time: float):
        """暂停状态处理"""
        # 绘制半透明遮罩
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        screen.blit(overlay, (0, 0))

        # 暂停文字
        font_title = pygame.font.Font(None, 72)
        title = font_title.render("暂停", True, (255, 255, 255))
        title_rect = title.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 50))
        screen.blit(title, title_rect)

        # 提示
        font = pygame.font.Font(None, 36)
        hint = font.render("按 ESC 继续", True, (200, 200, 200))
        hint_rect = hint.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 + 30))
        screen.blit(hint, hint_rect)

    def state_victory(self, screen: pygame.Surface, delta_time: float):
        """胜利状态处理"""
        screen.fill((40, 80, 40))

        font = pygame.font.Font(None, 72)
        text = font.render("胜利！", True, (100, 255, 100))
        text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(text, text_rect)

    def state_defeat(self, screen: pygame.Surface, delta_time: float):
        """失败状态处理"""
        screen.fill((80, 40, 40))

        font = pygame.font.Font(None, 72)
        text = font.render("失败", True, (255, 100, 100))
        text_rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(text, text_rect)

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
