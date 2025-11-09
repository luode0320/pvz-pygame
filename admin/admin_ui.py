"""
管理界面主UI - CrossVerse Arena管理系统
使用Tkinter实现独立的管理界面窗口
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class AdminUI:
    """
    管理界面主类
    功能：
    1. 密码验证
    2. 主窗口布局
    3. 导航菜单
    4. 各功能模块的入口
    """

    def __init__(self, admin_manager, config_loader, root_dir: str = "."):
        """
        初始化管理界面

        参数:
            admin_manager: AdminManager实例
            config_loader: ConfigLoader实例
            root_dir: 项目根目录
        """
        self.admin_manager = admin_manager
        self.config_loader = config_loader
        self.root_dir = Path(root_dir)

        # 主窗口（初始为None，验证后创建）
        self.root: Optional[tk.Tk] = None

        # 当前显示的内容面板
        self.current_panel: Optional[tk.Frame] = None

        # 是否已通过验证
        self.authenticated = False

        logger.info("管理界面UI初始化完成")

    def show_login_dialog(self) -> bool:
        """
        显示密码验证对话框

        返回:
            是否验证成功
        """
        login_window = tk.Tk()
        login_window.title("CrossVerse Arena - 管理界面登录")
        login_window.geometry("400x200")
        login_window.resizable(False, False)

        # 居中显示
        login_window.update_idletasks()
        x = (login_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (login_window.winfo_screenheight() // 2) - (200 // 2)
        login_window.geometry(f"+{x}+{y}")

        # 验证结果
        auth_result = {'success': False}

        # 创建UI元素
        frame = ttk.Frame(login_window, padding="20")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 标题
        title_label = ttk.Label(frame, text="管理界面登录", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # 密码输入
        ttk.Label(frame, text="密码:").grid(row=1, column=0, sticky=tk.W, pady=5)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(frame, textvariable=password_var, show="*", width=30)
        password_entry.grid(row=1, column=1, pady=5)
        password_entry.focus()

        # 提示信息
        hint_label = ttk.Label(frame, text="默认密码: admin", foreground="gray")
        hint_label.grid(row=2, column=0, columnspan=2, pady=5)

        def verify_password():
            """验证密码"""
            from core.config_loader import get_config_loader
            config_loader = get_config_loader(".")
            settings = config_loader.settings

            correct_password = settings.get('admin', {}).get('password', 'admin')
            entered_password = password_var.get()

            if entered_password == correct_password:
                auth_result['success'] = True
                login_window.destroy()
                logger.info("管理界面密码验证成功")
            else:
                messagebox.showerror("错误", "密码错误，请重试")
                password_var.set("")
                logger.warning("管理界面密码验证失败")

        def cancel_login():
            """取消登录"""
            login_window.destroy()
            logger.info("用户取消管理界面登录")

        # 按钮
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="登录", command=verify_password).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=cancel_login).pack(side=tk.LEFT, padx=5)

        # 绑定回车键
        password_entry.bind('<Return>', lambda e: verify_password())
        login_window.bind('<Escape>', lambda e: cancel_login())

        # 运行登录窗口
        login_window.mainloop()

        self.authenticated = auth_result['success']
        return auth_result['success']

    def show_main_window(self):
        """显示主管理界面"""
        if not self.authenticated:
            logger.error("未通过验证，无法打开主界面")
            return

        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("CrossVerse Arena - 管理界面")
        self.root.geometry("1200x800")

        # 居中显示
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.root.winfo_screenheight() // 2) - (800 // 2)
        self.root.geometry(f"+{x}+{y}")

        # 创建主布局
        self._create_main_layout()

        # 显示欢迎页面
        self.show_welcome_page()

        logger.info("管理界面主窗口已打开")

        # 运行主窗口
        self.root.mainloop()

    def _create_main_layout(self):
        """创建主窗口布局"""
        # 创建菜单栏
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 配置管理菜单
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="配置管理", menu=config_menu)
        config_menu.add_command(label="游戏IP管理", command=self.show_game_manager)
        config_menu.add_command(label="角色管理", command=self.show_character_manager)
        config_menu.add_command(label="技能管理", command=self.show_skill_manager)
        config_menu.add_command(label="皮肤管理", command=self.show_skin_manager)
        config_menu.add_separator()
        config_menu.add_command(label="战役管理", command=self.show_campaign_manager)
        config_menu.add_command(label="关卡管理", command=self.show_level_manager)

        # UI主题管理菜单
        theme_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="UI主题", menu=theme_menu)
        theme_menu.add_command(label="全局UI主题", command=self.show_theme_editor)
        theme_menu.add_command(label="关卡UI主题", command=self.show_level_theme_editor)

        # 关卡配置菜单
        level_config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="关卡配置", menu=level_config_menu)
        level_config_menu.add_command(label="角色选择配置", command=self.show_character_selection_config)
        level_config_menu.add_command(label="战场网格配置", command=self.show_battlefield_config)
        level_config_menu.add_command(label="经济系统配置", command=self.show_economy_config)
        level_config_menu.add_command(label="战斗系统配置", command=self.show_battle_config)

        # 资源管理菜单
        resource_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="资源管理", menu=resource_menu)
        resource_menu.add_command(label="资源浏览器", command=self.show_resource_browser)
        resource_menu.add_command(label="上传图片", command=self.upload_image)
        resource_menu.add_command(label="上传音频", command=self.upload_audio)
        resource_menu.add_command(label="上传模型", command=self.upload_model)

        # 系统菜单
        system_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="系统", menu=system_menu)
        system_menu.add_command(label="配置浏览器", command=self.show_config_browser)
        system_menu.add_command(label="回收站", command=self.show_recycle_bin)
        system_menu.add_command(label="操作日志", command=self.show_operation_log)
        system_menu.add_command(label="存档管理", command=self.show_save_manager)
        system_menu.add_separator()
        system_menu.add_command(label="刷新配置", command=self.refresh_config)
        system_menu.add_command(label="关于", command=self.show_about)
        system_menu.add_separator()
        system_menu.add_command(label="退出", command=self.close)

        # 创建主容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 创建左侧导航栏
        nav_frame = ttk.Frame(main_container, width=200)
        nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        nav_frame.pack_propagate(False)

        # 导航标题
        ttk.Label(nav_frame, text="快捷导航", font=('Arial', 12, 'bold')).pack(pady=10)

        # 导航按钮
        nav_buttons = [
            ("配置浏览器", self.show_config_browser),
            ("游戏IP", self.show_game_manager),
            ("角色", self.show_character_manager),
            ("技能", self.show_skill_manager),
            ("皮肤", self.show_skin_manager),
            ("战役", self.show_campaign_manager),
            ("关卡", self.show_level_manager),
            ("UI主题", self.show_theme_editor),
            ("资源", self.show_resource_browser),
            ("回收站", self.show_recycle_bin),
            ("日志", self.show_operation_log),
        ]

        for text, command in nav_buttons:
            ttk.Button(nav_frame, text=text, command=command, width=18).pack(pady=2)

        # 创建右侧内容区域
        self.content_frame = ttk.Frame(main_container)
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建状态栏
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(status_frame, text="就绪", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def show_welcome_page(self):
        """显示欢迎页面"""
        self._clear_content()

        frame = ttk.Frame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 欢迎标题
        title = ttk.Label(frame, text="CrossVerse Arena 管理界面",
                         font=('Arial', 24, 'bold'))
        title.pack(pady=30)

        # 欢迎信息
        welcome_text = """
        欢迎使用 CrossVerse Arena 管理界面！

        这是一个完全配置驱动的游戏管理系统，
        所有游戏内容都可以通过此界面进行管理，
        无需修改任何代码。

        请使用左侧导航或顶部菜单栏选择功能。

        核心功能：
        • 游戏IP管理 - 创建和管理游戏IP
        • 角色管理 - 配置角色属性和技能
        • 战役/关卡管理 - 设计游戏关卡
        • UI主题管理 - 自定义界面主题
        • 资源管理 - 上传和管理游戏资源

        所有删除操作都会进入回收站，可以随时恢复。
        所有操作都会被记录在日志中。
        """

        info_label = ttk.Label(frame, text=welcome_text, justify=tk.LEFT,
                              font=('Arial', 11))
        info_label.pack(pady=20)

        # 快速入口按钮
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=30)

        quick_buttons = [
            ("创建游戏IP", self.show_game_manager),
            ("创建角色", self.show_character_manager),
            ("创建关卡", self.show_level_manager),
            ("查看日志", self.show_operation_log),
        ]

        for i, (text, command) in enumerate(quick_buttons):
            btn = ttk.Button(button_frame, text=text, command=command, width=15)
            btn.grid(row=0, column=i, padx=10)

        self.update_status("欢迎使用管理界面")

    def _clear_content(self):
        """清除当前内容区域"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.current_panel = None

    def update_status(self, message: str):
        """更新状态栏信息"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)
            logger.info(f"状态: {message}")

    # ==================== 功能入口（待实现） ====================

    def show_config_browser(self):
        """显示配置浏览器"""
        self._clear_content()
        self.update_status("配置浏览器")

        try:
            from admin.config_browser import ConfigBrowser

            # 创建配置浏览器
            browser = ConfigBrowser(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            # 注册编辑器回调（当相应的编辑器实现后）
            browser.register_editor("game", self.show_game_manager)
            browser.register_editor("character", self.show_character_manager)
            browser.register_editor("skill", self.show_skill_manager)
            browser.register_editor("skin", self.show_skin_manager)
            browser.register_editor("campaign", self.show_campaign_manager)
            browser.register_editor("level", self.show_level_manager)

            logger.info("配置浏览器已打开")

        except Exception as e:
            logger.error(f"打开配置浏览器失败: {e}")
            messagebox.showerror("错误", f"打开配置浏览器失败:\n{e}")

    def show_game_manager(self):
        """显示游戏IP管理界面"""
        self._clear_content()
        self.update_status("游戏IP管理")

        try:
            from admin.game_manager import GameManager

            # 创建游戏IP管理器
            manager = GameManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            logger.info("游戏IP管理器已打开")

        except Exception as e:
            logger.error(f"打开游戏IP管理器失败: {e}")
            messagebox.showerror("错误", f"打开游戏IP管理器失败:\n{e}")

    def show_character_manager(self):
        """显示角色管理界面"""
        self._clear_content()
        self.update_status("角色管理")

        try:
            from admin.character_manager import CharacterManager

            # 创建角色管理器
            manager = CharacterManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            logger.info("角色管理器已打开")

        except Exception as e:
            logger.error(f"打开角色管理器失败: {e}")
            messagebox.showerror("错误", f"打开角色管理器失败:\n{e}")

    def show_skill_manager(self):
        """显示技能管理界面"""
        self._clear_content()
        self.update_status("技能管理")

        try:
            from admin.skill_manager import SkillManager

            # 创建技能管理器
            manager = SkillManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            logger.info("技能管理器已打开")

        except Exception as e:
            logger.error(f"打开技能管理器失败: {e}")
            messagebox.showerror("错误", f"打开技能管理器失败:\n{e}")

    def show_skin_manager(self):
        """显示皮肤管理界面"""
        self._clear_content()
        self.update_status("皮肤管理")

        try:
            from admin.skin_manager import SkinManager

            # 创建皮肤管理器
            manager = SkinManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            logger.info("皮肤管理器已打开")

        except Exception as e:
            logger.error(f"打开皮肤管理器失败: {e}")
            messagebox.showerror("错误", f"打开皮肤管理器失败:\n{e}")

    def show_campaign_manager(self):
        """显示战役管理界面"""
        self._clear_content()
        self.update_status("战役管理")

        try:
            from admin.campaign_manager import CampaignManager

            # 创建战役管理器
            manager = CampaignManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            logger.info("战役管理器已打开")

        except Exception as e:
            logger.error(f"打开战役管理器失败: {e}")
            messagebox.showerror("错误", f"打开战役管理器失败:\n{e}")

    def show_level_manager(self):
        """显示关卡管理界面"""
        self._clear_content()
        self.update_status("关卡管理")

        try:
            from admin.level_manager import LevelManager

            manager = LevelManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            logger.info("关卡管理器已打开")

        except Exception as e:
            logger.error(f"打开关卡管理器失败: {e}")
            messagebox.showerror("错误", f"打开关卡管理器失败:\n{e}")

    def show_theme_editor(self):
        """显示UI主题编辑器"""
        self._clear_content()
        self.update_status("UI主题管理")

        try:
            from admin.theme_manager import ThemeManager

            manager = ThemeManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            logger.info("UI主题管理器已打开")

        except Exception as e:
            logger.error(f"打开UI主题管理器失败: {e}")
            messagebox.showerror("错误", f"打开UI主题管理器失败:\n{e}")

    def show_level_theme_editor(self):
        """显示关卡UI主题编辑器"""
        self._clear_content()
        self.update_status("UI主题管理")

        try:
            from admin.theme_manager import ThemeManager

            manager = ThemeManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            # 切换到关卡主题Tab
            manager.notebook.select(1)

            logger.info("UI主题管理器已打开（关卡主题）")

        except Exception as e:
            logger.error(f"打开UI主题管理器失败: {e}")
            messagebox.showerror("错误", f"打开UI主题管理器失败:\n{e}")

    def show_character_selection_config(self):
        """显示角色选择配置"""
        self._clear_content()
        self.update_status("游戏配置管理")

        try:
            from admin.gameplay_config_manager import GameplayConfigManager

            manager = GameplayConfigManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            # 切换到角色选择Tab
            manager.notebook.select(0)

            logger.info("游戏配置管理器已打开（角色选择）")

        except Exception as e:
            logger.error(f"打开游戏配置管理器失败: {e}")
            messagebox.showerror("错误", f"打开游戏配置管理器失败:\n{e}")

    def show_battlefield_config(self):
        """显示战场网格配置"""
        self._clear_content()
        self.update_status("游戏配置管理")

        try:
            from admin.gameplay_config_manager import GameplayConfigManager

            manager = GameplayConfigManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            # 切换到战场网格Tab
            manager.notebook.select(1)

            logger.info("游戏配置管理器已打开（战场网格）")

        except Exception as e:
            logger.error(f"打开游戏配置管理器失败: {e}")
            messagebox.showerror("错误", f"打开游戏配置管理器失败:\n{e}")

    def show_economy_config(self):
        """显示经济系统配置"""
        self._clear_content()
        self.update_status("游戏配置管理")

        try:
            from admin.gameplay_config_manager import GameplayConfigManager

            manager = GameplayConfigManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            # 切换到经济系统Tab
            manager.notebook.select(2)

            logger.info("游戏配置管理器已打开（经济系统）")

        except Exception as e:
            logger.error(f"打开游戏配置管理器失败: {e}")
            messagebox.showerror("错误", f"打开游戏配置管理器失败:\n{e}")

    def show_battle_config(self):
        """显示战斗系统配置"""
        self._clear_content()
        self.update_status("游戏配置管理")

        try:
            from admin.gameplay_config_manager import GameplayConfigManager

            manager = GameplayConfigManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            # 切换到战斗系统Tab
            manager.notebook.select(3)

            logger.info("游戏配置管理器已打开（战斗系统）")

        except Exception as e:
            logger.error(f"打开游戏配置管理器失败: {e}")
            messagebox.showerror("错误", f"打开游戏配置管理器失败:\n{e}")

    def show_resource_browser(self):
        """显示资源浏览器"""
        self._clear_content()
        self.update_status("资源管理")

        try:
            from admin.resource_manager import ResourceManager

            manager = ResourceManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            logger.info("资源管理器已打开")

        except Exception as e:
            logger.error(f"打开资源管理器失败: {e}")
            messagebox.showerror("错误", f"打开资源管理器失败:\n{e}")

    def upload_image(self):
        """上传图片"""
        self.show_resource_browser()

    def upload_audio(self):
        """上传音频"""
        self.show_resource_browser()

    def upload_model(self):
        """上传模型"""
        self.show_resource_browser()

    def show_recycle_bin(self):
        """显示回收站"""
        self._clear_content()
        self.update_status("回收站与日志")

        try:
            from admin.recycle_log_manager import RecycleLogManager

            manager = RecycleLogManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            # 切换到回收站Tab
            manager.notebook.select(0)

            logger.info("回收站与日志管理器已打开（回收站）")

        except Exception as e:
            logger.error(f"打开回收站与日志管理器失败: {e}")
            messagebox.showerror("错误", f"打开回收站与日志管理器失败:\n{e}")

    def show_operation_log(self):
        """显示操作日志"""
        self._clear_content()
        self.update_status("回收站与日志")

        try:
            from admin.recycle_log_manager import RecycleLogManager

            manager = RecycleLogManager(
                self.content_frame,
                self.config_loader,
                self.admin_manager
            )

            # 切换到操作日志Tab
            manager.notebook.select(1)

            logger.info("回收站与日志管理器已打开（操作日志）")

        except Exception as e:
            logger.error(f"打开回收站与日志管理器失败: {e}")
            messagebox.showerror("错误", f"打开回收站与日志管理器失败:\n{e}")

    def show_save_manager(self):
        """显示存档管理"""
        self._clear_content()
        self.update_status("存档管理 - 功能开发中")

        frame = ttk.Frame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(frame, text="存档管理", font=('Arial', 18, 'bold')).pack(pady=20)
        ttk.Label(frame, text="此功能正在开发中",
                 font=('Arial', 12)).pack(pady=10)

    def refresh_config(self):
        """刷新配置"""
        self.config_loader.scan_all()
        messagebox.showinfo("成功", "配置已刷新！")
        self.update_status("配置已刷新")
        logger.info("手动刷新配置")

    def show_about(self):
        """显示关于信息"""
        about_text = """
        CrossVerse Arena 管理界面

        版本: 0.1.0
        开发: AI Assistant

        这是一个完全配置驱动的游戏管理系统。
        所有游戏内容都可以通过此界面进行管理。

        核心原则:
        • 绝对零硬编码
        • 管理界面驱动
        • 配置文件驱动

        所有操作都会被记录，所有删除都可恢复。
        """
        messagebox.showinfo("关于", about_text)

    def close(self):
        """关闭管理界面"""
        if messagebox.askokcancel("退出", "确定要关闭管理界面吗？"):
            logger.info("关闭管理界面")
            if self.root:
                self.root.destroy()


def launch_admin_ui():
    """
    启动管理界面的便捷函数
    可以从main.py调用
    """
    from core.admin_manager import AdminManager
    from core.config_loader import get_config_loader

    # 初始化必要的管理器
    config_loader = get_config_loader(".")
    admin_manager = AdminManager(".")

    # 创建并显示管理界面
    ui = AdminUI(admin_manager, config_loader, ".")

    # 验证密码
    if ui.show_login_dialog():
        # 显示主窗口
        ui.show_main_window()
    else:
        logger.info("管理界面登录取消")


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    launch_admin_ui()
