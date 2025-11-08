"""
UI主题管理器 - Phase 9
提供全局UI主题和关卡级主题覆盖的编辑功能
包含颜色选择器、布局配置、实时预览
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple
from logger_config import logger


class ThemeManager:
    """UI主题管理器"""

    def __init__(self, parent, config_loader, admin_manager):
        self.parent = parent
        self.config_loader = config_loader
        self.admin_manager = admin_manager
        self.root_dir = Path(__file__).parent.parent

        # 当前主题数据
        self.global_theme = {}
        self.level_theme = {}
        self.current_level = None
        self.current_campaign = None

        # 颜色编辑器变量字典
        self.color_vars = {}
        self.layout_vars = {}

        # 创建主布局
        self._create_layout()

        # 加载全局主题
        self._load_global_theme()

    def _create_layout(self):
        """创建主布局"""
        # 标签页
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: 全局主题
        self.global_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.global_tab, text="全局UI主题")

        # Tab 2: 关卡主题覆盖
        self.level_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.level_tab, text="关卡主题覆盖")

        self._create_global_theme_tab()
        self._create_level_theme_tab()

    def _create_global_theme_tab(self):
        """创建全局主题标签页"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.global_tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(toolbar, text="编辑全局UI主题配置 (settings.yaml)", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="保存全局主题", command=self._save_global_theme).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="重置为默认", command=self._reset_global_theme).pack(side=tk.RIGHT, padx=5)

        # 分隔线
        ttk.Separator(self.global_tab, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # 左侧：类别树
        left_frame = ttk.Frame(self.global_tab, width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="配置类别", font=("Arial", 10, "bold")).pack(pady=5)

        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.category_tree = ttk.Treeview(tree_frame, yscrollcommand=scrollbar.set, show='tree')
        self.category_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.category_tree.yview)

        self.category_tree.bind("<<TreeviewSelect>>", self._on_category_selected)

        # 构建类别树
        self._build_category_tree()

        # 右侧：编辑器
        right_frame = ttk.Frame(self.global_tab)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(right_frame, text="配置编辑器", font=("Arial", 10, "bold")).pack(pady=5)

        # 滚动区域
        canvas = tk.Canvas(right_frame)
        scrollbar_r = ttk.Scrollbar(right_frame, orient="vertical", command=canvas.yview)
        self.global_editor_frame = ttk.Frame(canvas)

        self.global_editor_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.global_editor_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_r.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_r.pack(side=tk.RIGHT, fill=tk.Y)

        # 默认提示
        ttk.Label(self.global_editor_frame, text="← 请从左侧选择要编辑的配置类别", foreground="gray", font=("Arial", 10)).pack(pady=50)

    def _create_level_theme_tab(self):
        """创建关卡主题覆盖标签页"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.level_tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(toolbar, text="关卡选择:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        # 战役选择
        self.level_campaign_var = tk.StringVar()
        self.level_campaign_combo = ttk.Combobox(toolbar, textvariable=self.level_campaign_var, state="readonly", width=20)
        self.level_campaign_combo.pack(side=tk.LEFT, padx=5)
        self.level_campaign_combo.bind("<<ComboboxSelected>>", self._on_level_campaign_selected)

        # 关卡选择
        self.level_select_var = tk.StringVar()
        self.level_select_combo = ttk.Combobox(toolbar, textvariable=self.level_select_var, state="readonly", width=30)
        self.level_select_combo.pack(side=tk.LEFT, padx=5)
        self.level_select_combo.bind("<<ComboboxSelected>>", self._on_level_selected)

        ttk.Button(toolbar, text="保存关卡主题", command=self._save_level_theme).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="清空覆盖", command=self._clear_level_theme).pack(side=tk.RIGHT, padx=5)

        # 分隔线
        ttk.Separator(self.level_tab, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # 说明
        info_frame = ttk.Frame(self.level_tab)
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(info_frame, text="💡 关卡主题覆盖说明:", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(info_frame, text="• 关卡可以部分覆盖全局UI主题，实现特殊视觉效果", foreground="gray", font=("Arial", 8)).pack(anchor=tk.W, padx=20)
        ttk.Label(info_frame, text="• 只需配置需要覆盖的颜色，未配置的使用全局默认值", foreground="gray", font=("Arial", 8)).pack(anchor=tk.W, padx=20)
        ttk.Label(info_frame, text="• 适用于特殊主题的关卡（如暗黑风格、节日主题等）", foreground="gray", font=("Arial", 8)).pack(anchor=tk.W, padx=20)

        # 滚动区域
        canvas = tk.Canvas(self.level_tab)
        scrollbar = ttk.Scrollbar(self.level_tab, orient="vertical", command=canvas.yview)
        self.level_editor_frame = ttk.Frame(canvas)

        self.level_editor_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.level_editor_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 默认提示
        ttk.Label(self.level_editor_frame, text="请选择要编辑主题的关卡", foreground="gray", font=("Arial", 10)).pack(pady=50)

        # 加载关卡列表
        self._load_level_list()

    def _build_category_tree(self):
        """构建类别树"""
        # 颜色配置
        colors_node = self.category_tree.insert("", "end", text="颜色配置", tags=("category",))
        self.category_tree.insert(colors_node, "end", text="页面背景颜色", values=("colors.background",))
        self.category_tree.insert(colors_node, "end", text="文字颜色", values=("colors.text",))
        self.category_tree.insert(colors_node, "end", text="按钮颜色", values=("colors.button",))
        self.category_tree.insert(colors_node, "end", text="卡片颜色", values=("colors.card",))
        self.category_tree.insert(colors_node, "end", text="游戏UI颜色", values=("colors.game_ui",))
        self.category_tree.insert(colors_node, "end", text="图标颜色", values=("colors.icon",))

        # 布局配置
        layout_node = self.category_tree.insert("", "end", text="布局配置", tags=("category",))
        self.category_tree.insert(layout_node, "end", text="边距配置", values=("layout.padding",))
        self.category_tree.insert(layout_node, "end", text="按钮尺寸", values=("layout.button",))
        self.category_tree.insert(layout_node, "end", text="卡片尺寸", values=("layout.card",))

    def _on_category_selected(self, event):
        """类别选中时显示编辑器"""
        selection = self.category_tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.category_tree.item(item, "values")

        if not values or not values[0]:
            return

        category = values[0]
        self._show_category_editor(category)

    def _show_category_editor(self, category: str):
        """显示类别编辑器"""
        # 清空编辑器
        for widget in self.global_editor_frame.winfo_children():
            widget.destroy()

        # 分割类别路径
        parts = category.split(".")
        if len(parts) != 2:
            return

        section_type = parts[0]  # colors 或 layout
        section_name = parts[1]  # background, text, etc.

        # 获取配置数据
        theme_data = self.global_theme.get(section_type, {}).get(section_name, {})

        # 标题
        title_map = {
            "colors.background": "页面背景颜色",
            "colors.text": "文字颜色",
            "colors.button": "按钮颜色",
            "colors.card": "卡片颜色",
            "colors.game_ui": "游戏UI颜色",
            "colors.icon": "图标颜色",
            "layout.padding": "边距配置",
            "layout.button": "按钮尺寸",
            "layout.card": "卡片尺寸"
        }

        ttk.Label(self.global_editor_frame, text=title_map.get(category, category), font=("Arial", 11, "bold")).pack(pady=10)

        # 根据类型显示编辑器
        if section_type == "colors":
            self._show_color_editor(section_name, theme_data, category)
        elif section_type == "layout":
            self._show_layout_editor(section_name, theme_data, category)

    def _show_color_editor(self, section_name: str, data: Dict, category: str):
        """显示颜色编辑器"""
        # 创建网格
        grid_frame = ttk.Frame(self.global_editor_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        row = 0
        for key, value in data.items():
            # 标签
            label_text = self._format_label(key)
            ttk.Label(grid_frame, text=f"{label_text}:", width=25, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)

            # RGB值输入
            if isinstance(value, list):
                # 创建变量
                var_key = f"{category}.{key}"
                if var_key not in self.color_vars:
                    self.color_vars[var_key] = []
                    for v in value:
                        self.color_vars[var_key].append(tk.IntVar(value=v))

                # RGB输入框
                rgb_frame = ttk.Frame(grid_frame)
                rgb_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

                for i, component in enumerate(['R', 'G', 'B', 'A'][:len(value)]):
                    ttk.Label(rgb_frame, text=component, width=2).pack(side=tk.LEFT, padx=2)
                    spinbox = ttk.Spinbox(rgb_frame, from_=0, to=255, textvariable=self.color_vars[var_key][i], width=5)
                    spinbox.pack(side=tk.LEFT, padx=2)

                # 颜色预览
                preview_frame = tk.Frame(grid_frame, width=50, height=25, relief=tk.SUNKEN, bd=2)
                preview_frame.grid(row=row, column=2, padx=5, pady=5)
                self._update_color_preview(preview_frame, self.color_vars[var_key])

                # 颜色选择器按钮
                ttk.Button(grid_frame, text="选择颜色",
                          command=lambda pf=preview_frame, vk=var_key: self._pick_color(pf, vk)).grid(row=row, column=3, padx=5, pady=5)

            row += 1

    def _show_layout_editor(self, section_name: str, data: Dict, category: str):
        """显示布局编辑器"""
        # 创建网格
        grid_frame = ttk.Frame(self.global_editor_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        row = 0
        for key, value in data.items():
            # 标签
            label_text = self._format_label(key)
            ttk.Label(grid_frame, text=f"{label_text}:", width=25, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)

            # 数值输入
            if isinstance(value, (int, float)):
                var_key = f"{category}.{key}"
                if var_key not in self.layout_vars:
                    if isinstance(value, int):
                        self.layout_vars[var_key] = tk.IntVar(value=value)
                    else:
                        self.layout_vars[var_key] = tk.DoubleVar(value=value)

                # Spinbox
                spinbox = ttk.Spinbox(grid_frame, from_=0, to=2000, textvariable=self.layout_vars[var_key], width=15)
                spinbox.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

                # 单位提示
                unit = "像素" if section_name != "padding" else "像素"
                ttk.Label(grid_frame, text=unit, foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

            row += 1

    def _update_color_preview(self, preview_frame: tk.Frame, color_vars: List):
        """更新颜色预览"""
        def update():
            try:
                r = color_vars[0].get()
                g = color_vars[1].get()
                b = color_vars[2].get()
                color = f"#{r:02x}{g:02x}{b:02x}"
                preview_frame.config(bg=color)
            except:
                preview_frame.config(bg="gray")

        # 绑定变量更新
        for var in color_vars:
            var.trace_add("write", lambda *args: update())

        update()

    def _pick_color(self, preview_frame: tk.Frame, var_key: str):
        """打开颜色选择器"""
        color_vars = self.color_vars[var_key]
        r = color_vars[0].get()
        g = color_vars[1].get()
        b = color_vars[2].get()
        initial_color = f"#{r:02x}{g:02x}{b:02x}"

        color = colorchooser.askcolor(initialcolor=initial_color, title="选择颜色")
        if color[0]:
            color_vars[0].set(int(color[0][0]))
            color_vars[1].set(int(color[0][1]))
            color_vars[2].set(int(color[0][2]))

    def _format_label(self, key: str) -> str:
        """格式化标签文本"""
        # 映射表
        label_map = {
            # Background
            "main_menu": "主菜单背景",
            "campaign_select": "战役选择背景",
            "level_select": "关卡选择背景",
            "character_select": "角色选择背景",
            "battle": "战斗背景",
            "pause": "暂停遮罩",
            "victory": "胜利背景",
            "defeat": "失败背景",
            # Text
            "title": "标题文字",
            "normal": "普通文字",
            "subtitle": "副标题文字",
            "hint": "提示文字",
            "success": "成功文字",
            "warning": "警告文字",
            "error": "错误文字",
            "info": "信息文字",
            # Button
            "normal_bg": "正常状态背景",
            "normal_border": "正常状态边框",
            "normal_text": "正常状态文字",
            "hover_bg": "悬停状态背景",
            "hover_border": "悬停状态边框",
            "hover_text": "悬停状态文字",
            "disabled_bg": "禁用状态背景",
            "disabled_border": "禁用状态边框",
            "disabled_text": "禁用状态文字",
            # Card - Level
            "level_completed_bg": "关卡-已完成背景",
            "level_completed_border": "关卡-已完成边框",
            "level_completed_text": "关卡-已完成文字",
            "level_unlocked_bg": "关卡-已解锁背景",
            "level_unlocked_hover_bg": "关卡-已解锁悬停背景",
            "level_unlocked_border": "关卡-已解锁边框",
            "level_unlocked_hover_border": "关卡-已解锁悬停边框",
            "level_unlocked_text": "关卡-已解锁文字",
            "level_locked_bg": "关卡-未解锁背景",
            "level_locked_border": "关卡-未解锁边框",
            "level_locked_text": "关卡-未解锁文字",
            # Card - Character
            "character_selected_bg": "角色-已选中背景",
            "character_selected_border": "角色-已选中边框",
            "character_hover_bg": "角色-悬停背景",
            "character_hover_border": "角色-悬停边框",
            "character_normal_bg": "角色-正常背景",
            "character_normal_border": "角色-正常边框",
            # Game UI
            "grid_dark": "网格深色",
            "grid_light": "网格浅色",
            "grid_border": "网格边框",
            "hp_bar_bg": "血条背景",
            "hp_bar_fg": "血条前景",
            "gold_text": "金币文字",
            "hp_text": "血量文字",
            "wave_text": "波次文字",
            "enemy_text": "敌人数量文字",
            # Icon
            "gold": "金币图标",
            "hp": "血量图标",
            "wave": "波次图标",
            "reward": "奖励图标",
            "exp": "经验图标",
            # Layout - Padding
            "small": "小边距",
            "large": "大边距",
            # Layout - Button
            "width": "按钮宽度",
            "height": "按钮高度",
            "spacing": "按钮间距",
            # Layout - Card
            "level_width": "关卡卡片宽度",
            "level_height": "关卡卡片高度",
            "level_spacing_x": "关卡卡片横向间距",
            "level_spacing_y": "关卡卡片纵向间距",
            "character_width": "角色卡片宽度",
            "character_height": "角色卡片高度",
            "character_spacing": "角色卡片间距"
        }

        return label_map.get(key, key.replace("_", " ").title())

    def _load_global_theme(self):
        """加载全局主题"""
        settings_file = self.root_dir / "settings.yaml"
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)
                self.global_theme = settings.get("ui_theme", {})
                logger.info("全局UI主题已加载")
        except Exception as e:
            logger.error(f"加载全局主题失败: {e}")
            messagebox.showerror("错误", f"加载全局主题失败:\n{e}")

    def _save_global_theme(self):
        """保存全局主题"""
        # 收集所有修改
        for var_key, color_vars in self.color_vars.items():
            # 解析路径: colors.background.main_menu
            parts = var_key.split(".")
            if len(parts) == 3 and parts[0] == "colors":
                section = parts[1]
                key = parts[2]

                # 更新值
                color_value = [var.get() for var in color_vars]
                if section not in self.global_theme.get("colors", {}):
                    if "colors" not in self.global_theme:
                        self.global_theme["colors"] = {}
                    self.global_theme["colors"][section] = {}

                self.global_theme["colors"][section][key] = color_value

        for var_key, var in self.layout_vars.items():
            # 解析路径: layout.padding.small
            parts = var_key.split(".")
            if len(parts) == 3 and parts[0] == "layout":
                section = parts[1]
                key = parts[2]

                # 更新值
                if section not in self.global_theme.get("layout", {}):
                    if "layout" not in self.global_theme:
                        self.global_theme["layout"] = {}
                    self.global_theme["layout"][section] = {}

                self.global_theme["layout"][section][key] = var.get()

        # 保存到settings.yaml
        settings_file = self.root_dir / "settings.yaml"
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)

            settings["ui_theme"] = self.global_theme

            with open(settings_file, 'w', encoding='utf-8') as f:
                yaml.dump(settings, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

            logger.info("全局UI主题已保存")
            messagebox.showinfo("成功", "全局UI主题已保存到 settings.yaml")

        except Exception as e:
            logger.error(f"保存全局主题失败: {e}")
            messagebox.showerror("错误", f"保存全局主题失败:\n{e}")

    def _reset_global_theme(self):
        """重置为默认主题"""
        if not messagebox.askyesno("确认", "确定要重置为默认主题吗？\n当前修改将丢失"):
            return

        # 重新加载
        self._load_global_theme()

        # 清空变量
        self.color_vars.clear()
        self.layout_vars.clear()

        # 刷新编辑器
        for widget in self.global_editor_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.global_editor_frame, text="← 请从左侧选择要编辑的配置类别", foreground="gray", font=("Arial", 10)).pack(pady=50)

        messagebox.showinfo("成功", "已重置为默认主题")

    def _load_level_list(self):
        """加载关卡列表"""
        campaigns = []
        campaigns_dir = self.root_dir / "campaigns"
        if campaigns_dir.exists():
            for campaign_dir in campaigns_dir.iterdir():
                if campaign_dir.is_dir():
                    campaign_file = campaign_dir / f"{campaign_dir.name}.yaml"
                    if campaign_file.exists():
                        try:
                            with open(campaign_file, 'r', encoding='utf-8') as f:
                                campaign_data = yaml.safe_load(f)
                                campaign_name = campaign_data.get("name", campaign_dir.name)
                                campaigns.append(f"{campaign_name} ({campaign_dir.name})")
                        except:
                            pass

        self.level_campaign_combo['values'] = campaigns

    def _on_level_campaign_selected(self, event):
        """战役选择时加载关卡"""
        campaign_str = self.level_campaign_var.get()
        if not campaign_str:
            return

        # 提取campaign_id
        import re
        match = re.search(r'\((.+?)\)$', campaign_str)
        if not match:
            return

        campaign_id = match.group(1)

        # 加载关卡列表
        levels = []
        levels_dir = self.root_dir / "campaigns" / campaign_id / "levels"
        if levels_dir.exists():
            for level_file in levels_dir.glob("*.yaml"):
                try:
                    with open(level_file, 'r', encoding='utf-8') as f:
                        level_data = yaml.safe_load(f)
                        level_name = level_data.get("name", level_file.stem)
                        level_id = level_data.get("level_id", level_file.stem)
                        levels.append(f"{level_name} ({level_id})")
                except:
                    pass

        self.level_select_combo['values'] = levels

    def _on_level_selected(self, event):
        """关卡选择时加载主题"""
        level_str = self.level_select_var.get()
        campaign_str = self.level_campaign_var.get()

        if not level_str or not campaign_str:
            return

        import re
        # 提取IDs
        match_campaign = re.search(r'\((.+?)\)$', campaign_str)
        match_level = re.search(r'\((.+?)\)$', level_str)

        if not match_campaign or not match_level:
            return

        campaign_id = match_campaign.group(1)
        level_id = match_level.group(1)

        self.current_campaign = campaign_id
        self.current_level = level_id

        # 加载关卡主题
        level_file = self.root_dir / "campaigns" / campaign_id / "levels" / f"{level_id}.yaml"
        try:
            with open(level_file, 'r', encoding='utf-8') as f:
                level_data = yaml.safe_load(f)
                self.level_theme = level_data.get("ui_theme", {})

            self._show_level_theme_editor()
            logger.info(f"加载关卡主题: {campaign_id}/{level_id}")

        except Exception as e:
            logger.error(f"加载关卡主题失败: {e}")
            messagebox.showerror("错误", f"加载关卡主题失败:\n{e}")

    def _show_level_theme_editor(self):
        """显示关卡主题编辑器"""
        # 清空编辑器
        for widget in self.level_editor_frame.winfo_children():
            widget.destroy()

        # 说明
        info_frame = ttk.Frame(self.level_editor_frame)
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(info_frame, text=f"正在编辑: {self.current_campaign}/{self.current_level}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(info_frame, text="只配置需要覆盖的颜色，留空则使用全局默认值", foreground="gray", font=("Arial", 8)).pack(anchor=tk.W)

        # 常用颜色覆盖
        common_frame = ttk.LabelFrame(self.level_editor_frame, text="常用颜色覆盖")
        common_frame.pack(fill=tk.X, padx=20, pady=10)

        # 简化编辑器：只显示最常用的配置
        common_colors = [
            ("colors.background.battle", "战斗背景"),
            ("colors.text.title", "标题文字"),
            ("colors.text.success", "成功文字"),
            ("colors.icon.gold", "金币图标"),
            ("colors.icon.hp", "血量图标"),
            ("colors.icon.wave", "波次图标")
        ]

        row = 0
        for path, label_text in common_colors:
            parts = path.split(".")
            section = parts[1]
            key = parts[2]

            # 获取当前值（如果有）
            current_value = self.level_theme.get("colors", {}).get(section, {}).get(key, None)

            ttk.Label(common_frame, text=f"{label_text}:", width=15, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)

            # 创建变量
            var_key = f"level.{path}"
            if var_key not in self.color_vars:
                self.color_vars[var_key] = []
                if current_value:
                    for v in current_value:
                        self.color_vars[var_key].append(tk.IntVar(value=v))
                else:
                    # 默认值
                    for _ in range(3):
                        self.color_vars[var_key].append(tk.IntVar(value=128))

            # RGB输入
            rgb_frame = ttk.Frame(common_frame)
            rgb_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

            for i, component in enumerate(['R', 'G', 'B']):
                ttk.Label(rgb_frame, text=component, width=2).pack(side=tk.LEFT, padx=2)
                spinbox = ttk.Spinbox(rgb_frame, from_=0, to=255, textvariable=self.color_vars[var_key][i], width=5)
                spinbox.pack(side=tk.LEFT, padx=2)

            # 预览
            preview_frame = tk.Frame(common_frame, width=50, height=25, relief=tk.SUNKEN, bd=2)
            preview_frame.grid(row=row, column=2, padx=5, pady=5)
            self._update_color_preview(preview_frame, self.color_vars[var_key])

            # 颜色选择器
            ttk.Button(common_frame, text="选择",
                      command=lambda pf=preview_frame, vk=var_key: self._pick_color(pf, vk)).grid(row=row, column=3, padx=5, pady=5)

            # 清空按钮
            ttk.Button(common_frame, text="清空",
                      command=lambda vk=var_key: self._clear_level_color(vk)).grid(row=row, column=4, padx=5, pady=5)

            row += 1

    def _clear_level_color(self, var_key: str):
        """清空关卡颜色覆盖"""
        if var_key in self.color_vars:
            # 重置为默认灰色
            for var in self.color_vars[var_key]:
                var.set(128)

    def _save_level_theme(self):
        """保存关卡主题"""
        if not self.current_level or not self.current_campaign:
            messagebox.showwarning("警告", "请先选择关卡")
            return

        # 收集关卡主题覆盖
        level_theme = {"colors": {}}

        for var_key, color_vars in self.color_vars.items():
            if var_key.startswith("level.colors."):
                # 解析路径: level.colors.background.battle
                parts = var_key.split(".")
                if len(parts) == 4:
                    section = parts[2]
                    key = parts[3]

                    # 检查是否被修改（不是默认的128）
                    color_value = [var.get() for var in color_vars]
                    if color_value != [128, 128, 128]:
                        if section not in level_theme["colors"]:
                            level_theme["colors"][section] = {}
                        level_theme["colors"][section][key] = color_value

        # 如果没有任何覆盖，清空ui_theme
        if not level_theme["colors"]:
            level_theme = None

        # 保存到关卡文件
        level_file = self.root_dir / "campaigns" / self.current_campaign / "levels" / f"{self.current_level}.yaml"
        try:
            with open(level_file, 'r', encoding='utf-8') as f:
                level_data = yaml.safe_load(f)

            if level_theme:
                level_data["ui_theme"] = level_theme
            else:
                level_data.pop("ui_theme", None)

            with open(level_file, 'w', encoding='utf-8') as f:
                yaml.dump(level_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

            logger.info(f"保存关卡主题: {self.current_campaign}/{self.current_level}")
            messagebox.showinfo("成功", "关卡主题已保存")

        except Exception as e:
            logger.error(f"保存关卡主题失败: {e}")
            messagebox.showerror("错误", f"保存关卡主题失败:\n{e}")

    def _clear_level_theme(self):
        """清空关卡主题覆盖"""
        if not self.current_level or not self.current_campaign:
            messagebox.showwarning("警告", "请先选择关卡")
            return

        if not messagebox.askyesno("确认", "确定要清空当前关卡的主题覆盖吗？\n将使用全局默认主题"):
            return

        # 清空变量
        for var_key in list(self.color_vars.keys()):
            if var_key.startswith("level."):
                for var in self.color_vars[var_key]:
                    var.set(128)

        messagebox.showinfo("成功", "已清空关卡主题覆盖（记得点击保存）")
