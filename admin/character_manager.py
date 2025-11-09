"""
角色管理器 - 角色的完整CRUD操作
支持创建、编辑、删除角色，配置属性、技能、资源
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import logging
from pathlib import Path
from typing import Dict, Optional, List
import yaml
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)


class CharacterManager:
    """
    角色管理器
    功能：
    1. 新增角色（创建角色配置文件）
    2. 编辑角色（修改所有属性）
    3. 删除角色（移动到回收站）
    4. 配置基础属性（HP、攻击、速度等）
    5. 管理技能列表
    6. 上传角色资源（sprite、icon、sounds）
    """

    def __init__(self, parent: tk.Frame, config_loader, admin_manager):
        """
        初始化角色管理器

        参数:
            parent: 父容器
            config_loader: ConfigLoader实例
            admin_manager: AdminManager实例
        """
        self.parent = parent
        self.config_loader = config_loader
        self.admin_manager = admin_manager
        self.root_dir = Path(config_loader.root_dir)

        # 当前编辑的角色（None表示新建）
        self.current_character_id: Optional[str] = None
        self.current_game_id: Optional[str] = None

        # 创建UI
        self._create_ui()

        logger.info("角色管理器初始化完成")

    def _create_ui(self):
        """创建UI组件"""
        # 标题
        title_frame = tk.Frame(self.parent, bg="#f0f0f0")
        title_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(
            title_frame,
            text="角色管理",
            font=('Arial', 18, 'bold'),
            bg="#f0f0f0"
        ).pack(side=tk.LEFT)

        # 工具栏
        toolbar = tk.Frame(self.parent, bg="#f0f0f0")
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(toolbar, text="新增角色", command=self._new_character, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="刷新列表", command=self._refresh_list, width=12).pack(side=tk.LEFT, padx=5)

        # 主容器：左侧列表 + 右侧编辑器
        main_container = tk.Frame(self.parent)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧：角色列表
        list_frame = ttk.LabelFrame(main_container, text="已有角色", padding=10)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        # 列表框和滚动条
        list_scroll = ttk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.char_listbox = tk.Listbox(
            list_frame,
            width=35,
            yscrollcommand=list_scroll.set
        )
        self.char_listbox.pack(fill=tk.BOTH, expand=True)
        list_scroll.config(command=self.char_listbox.yview)

        # 绑定选择事件
        self.char_listbox.bind('<<ListboxSelect>>', self._on_select_character)

        # 列表下方按钮
        list_btn_frame = tk.Frame(list_frame)
        list_btn_frame.pack(fill=tk.X, pady=(10, 0))

        tk.Button(list_btn_frame, text="编辑", command=self._edit_selected, width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(list_btn_frame, text="删除", command=self._delete_selected, width=10).pack(side=tk.LEFT, padx=2)

        # 右侧：编辑器（使用Notebook分页）
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 页面1: 基础信息
        self.page_basic = self._create_basic_page()
        self.notebook.add(self.page_basic, text="基础信息")

        # 页面2: 属性配置
        self.page_stats = self._create_stats_page()
        self.notebook.add(self.page_stats, text="属性配置")

        # 页面3: 攻击与弹道配置
        self.page_attack = self._create_attack_page()
        self.notebook.add(self.page_attack, text="攻击配置")

        # 页面4: 被动特质
        self.page_traits = self._create_passive_traits_page()
        self.notebook.add(self.page_traits, text="被动特质")

        # 页面5: 技能管理
        self.page_skills = self._create_skills_page()
        self.notebook.add(self.page_skills, text="技能管理")

        # 页面6: 资源配置
        self.page_assets = self._create_assets_page()
        self.notebook.add(self.page_assets, text="资源配置")

        # 刷新列表
        self._refresh_list()

        # 显示空编辑器
        self._clear_editor()

    def _create_basic_page(self):
        """创建基础信息页面"""
        page = tk.Frame(self.notebook, bg="white")

        # 创建滚动容器
        canvas = tk.Canvas(page, bg="white")
        scrollbar = ttk.Scrollbar(page, orient=tk.VERTICAL, command=canvas.yview)
        content = tk.Frame(canvas, bg="white")

        content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=content, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        row = 0

        # 所属游戏IP
        tk.Label(content, text="所属游戏IP *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.game_id_var = tk.StringVar()
        self.game_combo = ttk.Combobox(
            content,
            textvariable=self.game_id_var,
            state="readonly",
            width=37
        )
        self.game_combo.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 角色ID
        tk.Label(content, text="角色ID *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_id_var = tk.StringVar()
        self.char_id_entry = tk.Entry(content, textvariable=self.char_id_var, width=40)
        self.char_id_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            content,
            text="(英文字母、数字、下划线)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 角色名称
        tk.Label(content, text="角色名称 *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_name_var = tk.StringVar()
        tk.Entry(content, textvariable=self.char_name_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 角色类型
        tk.Label(content, text="角色类型 *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_type_var = tk.StringVar(value="defender")
        type_combo = ttk.Combobox(
            content,
            textvariable=self.char_type_var,
            values=["defender", "attacker", "support", "tank", "dps"],
            state="readonly",
            width=37
        )
        type_combo.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 部署成本
        tk.Label(content, text="部署成本:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.char_cost_var = tk.IntVar(value=100)
        tk.Spinbox(content, from_=0, to=1000, textvariable=self.char_cost_var, width=38).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 角色描述
        tk.Label(content, text="角色描述:", bg="white", anchor=tk.NW).grid(
            row=row, column=0, sticky=tk.NW, padx=5, pady=5
        )
        self.char_desc_text = tk.Text(content, width=40, height=4)
        self.char_desc_text.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 按钮区域
        btn_frame = tk.Frame(content, bg="white")
        btn_frame.grid(row=row, column=0, columnspan=3, pady=20)

        tk.Button(btn_frame, text="保存角色", command=self._save_character, width=15, bg="#4CAF50", fg="white").pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="取消", command=self._clear_editor, width=15).pack(side=tk.LEFT, padx=5)

        return page

    def _create_stats_page(self):
        """创建属性配置页面"""
        page = tk.Frame(self.notebook, bg="white")

        # 创建滚动容器
        canvas = tk.Canvas(page, bg="white")
        scrollbar = ttk.Scrollbar(page, orient=tk.VERTICAL, command=canvas.yview)
        content = tk.Frame(canvas, bg="white")

        content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=content, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 属性字段
        stats_fields = [
            ("生命值 (HP):", "hp", 300, 1, 10000),
            ("攻击力 (Attack):", "attack", 20, 1, 1000),
            ("攻击范围 (Range):", "attack_range", 250, 0, 1000),
            ("攻击速度 (Attack Speed):", "attack_speed", 1.5, 0.1, 10.0),
            ("移动速度 (Speed):", "speed", 0, 0, 200),
            ("暴击率 (Crit Rate):", "crit_rate", 0.05, 0.0, 1.0),
            ("暴击伤害 (Crit Damage):", "crit_damage", 1.5, 1.0, 5.0),
            ("效果抵抗 (Effect Resistance):", "effect_resistance", 0.1, 0.0, 1.0),
        ]

        self.stats_vars = {}
        for idx, (label, key, default, min_val, max_val) in enumerate(stats_fields):
            tk.Label(content, text=label, bg="white", anchor=tk.W).grid(
                row=idx, column=0, sticky=tk.W, padx=5, pady=5
            )

            if isinstance(default, float):
                var = tk.DoubleVar(value=default)
                spinbox = tk.Spinbox(
                    content,
                    from_=min_val,
                    to=max_val,
                    increment=0.1 if max_val <= 10 else 1,
                    textvariable=var,
                    width=38
                )
            else:
                var = tk.IntVar(value=default)
                spinbox = tk.Spinbox(
                    content,
                    from_=min_val,
                    to=max_val,
                    textvariable=var,
                    width=38
                )

            spinbox.grid(row=idx, column=1, sticky=tk.W, padx=5, pady=5)
            self.stats_vars[key] = var

        return page

    def _create_attack_page(self):
        """创建攻击与弹道配置页面"""
        page = tk.Frame(self.notebook, bg="white")

        # 创建滚动容器
        canvas = tk.Canvas(page, bg="white")
        scrollbar = ttk.Scrollbar(page, orient=tk.VERTICAL, command=canvas.yview)
        content = tk.Frame(canvas, bg="white")

        content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=content, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        row = 0

        # === 攻击类型配置 ===
        tk.Label(
            content,
            text="攻击类型配置",
            font=('Arial', 12, 'bold'),
            bg="white"
        ).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))
        row += 1

        # 攻击类型
        tk.Label(content, text="攻击类型:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.attack_type_var = tk.StringVar(value="melee")
        attack_type_frame = tk.Frame(content, bg="white")
        attack_type_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        tk.Radiobutton(
            attack_type_frame,
            text="近战 (Melee)",
            variable=self.attack_type_var,
            value="melee",
            bg="white",
            command=self._on_attack_type_change
        ).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(
            attack_type_frame,
            text="远程 (Ranged)",
            variable=self.attack_type_var,
            value="ranged",
            bg="white",
            command=self._on_attack_type_change
        ).pack(side=tk.LEFT, padx=5)
        row += 1

        # === 弹道配置区域（仅远程显示）===
        self.projectile_frame = ttk.LabelFrame(content, text="弹道配置 (仅远程攻击)", padding=10)
        self.projectile_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W+tk.E, padx=5, pady=10)
        row += 1

        proj_row = 0

        # 弹道类型
        tk.Label(self.projectile_frame, text="弹道类型:", anchor=tk.W).grid(
            row=proj_row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.proj_type_var = tk.StringVar(value="linear")
        proj_type_combo = ttk.Combobox(
            self.projectile_frame,
            textvariable=self.proj_type_var,
            values=["linear", "arc", "homing", "pierce"],
            state="readonly",
            width=20
        )
        proj_type_combo.grid(row=proj_row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            self.projectile_frame,
            text="(直线/抛物线/追踪/穿透)",
            font=('Arial', 8),
            fg="gray"
        ).grid(row=proj_row, column=2, sticky=tk.W, padx=5, pady=5)
        proj_row += 1

        # 弹道速度
        tk.Label(self.projectile_frame, text="弹道速度:", anchor=tk.W).grid(
            row=proj_row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.proj_speed_var = tk.IntVar(value=400)
        tk.Spinbox(
            self.projectile_frame,
            from_=100,
            to=1000,
            increment=50,
            textvariable=self.proj_speed_var,
            width=20
        ).grid(row=proj_row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            self.projectile_frame,
            text="(像素/秒)",
            font=('Arial', 8),
            fg="gray"
        ).grid(row=proj_row, column=2, sticky=tk.W, padx=5, pady=5)
        proj_row += 1

        # 弹道大小
        tk.Label(self.projectile_frame, text="弹道大小:", anchor=tk.W).grid(
            row=proj_row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.proj_size_var = tk.IntVar(value=10)
        tk.Spinbox(
            self.projectile_frame,
            from_=5,
            to=50,
            textvariable=self.proj_size_var,
            width=20
        ).grid(row=proj_row, column=1, sticky=tk.W, padx=5, pady=5)
        proj_row += 1

        # 弹道颜色
        tk.Label(self.projectile_frame, text="弹道颜色 (R,G,B):", anchor=tk.W).grid(
            row=proj_row, column=0, sticky=tk.W, padx=5, pady=5
        )
        color_frame = tk.Frame(self.projectile_frame)
        color_frame.grid(row=proj_row, column=1, sticky=tk.W, padx=5, pady=5)

        self.proj_color_r = tk.IntVar(value=255)
        self.proj_color_g = tk.IntVar(value=200)
        self.proj_color_b = tk.IntVar(value=0)

        tk.Spinbox(color_frame, from_=0, to=255, textvariable=self.proj_color_r, width=5).pack(side=tk.LEFT, padx=2)
        tk.Spinbox(color_frame, from_=0, to=255, textvariable=self.proj_color_g, width=5).pack(side=tk.LEFT, padx=2)
        tk.Spinbox(color_frame, from_=0, to=255, textvariable=self.proj_color_b, width=5).pack(side=tk.LEFT, padx=2)
        proj_row += 1

        # 穿透选项
        tk.Label(self.projectile_frame, text="是否穿透:", anchor=tk.W).grid(
            row=proj_row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.proj_pierce_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self.projectile_frame,
            variable=self.proj_pierce_var,
            command=self._on_pierce_change
        ).grid(row=proj_row, column=1, sticky=tk.W, padx=5, pady=5)
        proj_row += 1

        # 穿透次数
        self.pierce_count_label = tk.Label(self.projectile_frame, text="穿透次数:", anchor=tk.W)
        self.pierce_count_label.grid(row=proj_row, column=0, sticky=tk.W, padx=5, pady=5)
        self.proj_pierce_count_var = tk.IntVar(value=3)
        self.pierce_count_spinbox = tk.Spinbox(
            self.projectile_frame,
            from_=1,
            to=10,
            textvariable=self.proj_pierce_count_var,
            width=20,
            state=tk.DISABLED
        )
        self.pierce_count_spinbox.grid(row=proj_row, column=1, sticky=tk.W, padx=5, pady=5)
        proj_row += 1

        # 溅射半径
        tk.Label(self.projectile_frame, text="溅射半径:", anchor=tk.W).grid(
            row=proj_row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.proj_splash_var = tk.IntVar(value=0)
        tk.Spinbox(
            self.projectile_frame,
            from_=0,
            to=200,
            textvariable=self.proj_splash_var,
            width=20
        ).grid(row=proj_row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            self.projectile_frame,
            text="(0=无溅射)",
            font=('Arial', 8),
            fg="gray"
        ).grid(row=proj_row, column=2, sticky=tk.W, padx=5, pady=5)
        proj_row += 1

        # 存活时间
        tk.Label(self.projectile_frame, text="最大存活时间:", anchor=tk.W).grid(
            row=proj_row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.proj_lifetime_var = tk.DoubleVar(value=3.0)
        tk.Spinbox(
            self.projectile_frame,
            from_=0.5,
            to=10.0,
            increment=0.5,
            textvariable=self.proj_lifetime_var,
            width=20
        ).grid(row=proj_row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            self.projectile_frame,
            text="(秒)",
            font=('Arial', 8),
            fg="gray"
        ).grid(row=proj_row, column=2, sticky=tk.W, padx=5, pady=5)

        # 初始状态：隐藏弹道配置
        self._on_attack_type_change()

        return page

    def _create_passive_traits_page(self):
        """创建被动特质管理页面"""
        page = tk.Frame(self.notebook, bg="white", padx=10, pady=10)

        # 顶部说明
        tk.Label(
            page,
            text="被动特质管理 - 角色固有的被动能力（不同于技能系统中的被动技能）",
            font=('Arial', 10),
            bg="white",
            fg="gray"
        ).pack(pady=5)

        # 工具栏
        toolbar = tk.Frame(page, bg="white")
        toolbar.pack(fill=tk.X, pady=5)

        tk.Button(toolbar, text="添加特质", command=self._add_passive_trait, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="删除特质", command=self._remove_passive_trait, width=12).pack(side=tk.LEFT, padx=5)

        # 特质列表
        list_frame = tk.Frame(page, bg="white")
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.traits_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=15
        )
        self.traits_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.traits_listbox.yview)

        # 双击编辑
        self.traits_listbox.bind('<Double-Button-1>', self._edit_passive_trait)

        return page

    def _on_attack_type_change(self):
        """攻击类型改变时的回调"""
        if self.attack_type_var.get() == "ranged":
            # 显示弹道配置
            for child in self.projectile_frame.winfo_children():
                child.configure(state=tk.NORMAL)
        else:
            # 隐藏弹道配置
            for child in self.projectile_frame.winfo_children():
                if isinstance(child, (tk.Entry, tk.Spinbox, ttk.Combobox)):
                    child.configure(state=tk.DISABLED)
                elif isinstance(child, tk.Checkbutton):
                    child.configure(state=tk.DISABLED)
                elif isinstance(child, tk.Frame):
                    for subchild in child.winfo_children():
                        if isinstance(subchild, (tk.Entry, tk.Spinbox)):
                            subchild.configure(state=tk.DISABLED)

    def _on_pierce_change(self):
        """穿透选项改变时的回调"""
        if self.proj_pierce_var.get():
            self.pierce_count_spinbox.configure(state=tk.NORMAL)
        else:
            self.pierce_count_spinbox.configure(state=tk.DISABLED)

    def _add_passive_trait(self):
        """添加被动特质"""
        # 弹出对话框选择特质类型
        trait_types = [
            "hp_regen", "shield_regen", "mana_regen",
            "lifesteal", "crit_rate", "crit_damage",
            "evasion", "damage_reduction", "thorns",
            "bonus_gold", "heal_on_kill", "cooldown_reduction_on_kill",
            "bonus_attack", "bonus_defense", "bonus_attack_speed",
            "bonus_move_speed", "bonus_hp", "bonus_attack_range"
        ]

        dialog = tk.Toplevel(self.parent)
        dialog.title("添加被动特质")
        dialog.geometry("400x200")
        dialog.transient(self.parent)
        dialog.grab_set()

        tk.Label(dialog, text="特质类型:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        trait_type_var = tk.StringVar()
        trait_combo = ttk.Combobox(
            dialog,
            textvariable=trait_type_var,
            values=trait_types,
            state="readonly",
            width=30
        )
        trait_combo.grid(row=0, column=1, padx=10, pady=10)
        trait_combo.current(0)

        tk.Label(dialog, text="数值:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        value_var = tk.DoubleVar(value=0.1)
        tk.Entry(dialog, textvariable=value_var, width=33).grid(row=1, column=1, padx=10, pady=10)

        def on_ok():
            trait_type = trait_type_var.get()
            value = value_var.get()
            self.traits_listbox.insert(tk.END, f"{trait_type}: {value}")
            dialog.destroy()

        tk.Button(dialog, text="确定", command=on_ok, width=10).grid(row=2, column=0, columnspan=2, pady=10)

    def _remove_passive_trait(self):
        """删除被动特质"""
        selection = self.traits_listbox.curselection()
        if selection:
            self.traits_listbox.delete(selection[0])

    def _edit_passive_trait(self, event):
        """编辑被动特质"""
        selection = self.traits_listbox.curselection()
        if not selection:
            return

        current_text = self.traits_listbox.get(selection[0])
        parts = current_text.split(": ")
        if len(parts) != 2:
            return

        trait_type = parts[0]
        current_value = float(parts[1])

        # 弹出编辑对话框
        new_value = simpledialog.askfloat(
            "编辑特质",
            f"修改 {trait_type} 的数值:",
            initialvalue=current_value
        )

        if new_value is not None:
            self.traits_listbox.delete(selection[0])
            self.traits_listbox.insert(selection[0], f"{trait_type}: {new_value}")

    def _create_skills_page(self):
        """创建技能管理页面"""
        page = tk.Frame(self.notebook, bg="white", padx=10, pady=10)

        # 顶部说明
        tk.Label(
            page,
            text="技能管理 (双击编辑技能ID，详细配置在Phase 5实现)",
            font=('Arial', 10),
            bg="white",
            fg="gray"
        ).pack(pady=5)

        # 工具栏
        toolbar = tk.Frame(page, bg="white")
        toolbar.pack(fill=tk.X, pady=5)

        tk.Button(toolbar, text="添加技能", command=self._add_skill, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="删除技能", command=self._remove_skill, width=12).pack(side=tk.LEFT, padx=5)

        # 技能列表
        list_frame = tk.Frame(page, bg="white")
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.skills_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=15
        )
        self.skills_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.skills_listbox.yview)

        return page

    def _create_assets_page(self):
        """创建资源配置页面"""
        page = tk.Frame(self.notebook, bg="white")

        # 创建滚动容器
        canvas = tk.Canvas(page, bg="white")
        scrollbar = ttk.Scrollbar(page, orient=tk.VERTICAL, command=canvas.yview)
        content = tk.Frame(canvas, bg="white")

        content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=content, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 资源字段
        assets_fields = [
            ("基础Sprite:", "basic_sprite", "图片文件 (*.png *.jpg)"),
            ("基础图标:", "basic_icon", "图片文件 (*.png *.jpg)"),
            ("攻击音效:", "sound_attack", "音频文件 (*.wav *.ogg *.mp3)"),
            ("死亡音效:", "sound_death", "音频文件 (*.wav *.ogg *.mp3)"),
        ]

        self.assets_vars = {}
        for idx, (label, key, file_types) in enumerate(assets_fields):
            tk.Label(content, text=label, bg="white", anchor=tk.W).grid(
                row=idx, column=0, sticky=tk.W, padx=5, pady=5
            )

            frame = tk.Frame(content, bg="white")
            frame.grid(row=idx, column=1, sticky=tk.W, padx=5, pady=5)

            var = tk.StringVar()
            tk.Entry(frame, textvariable=var, width=30).pack(side=tk.LEFT, padx=(0, 5))
            tk.Button(
                frame,
                text="选择文件",
                command=lambda v=var, ft=file_types: self._select_asset(v, ft),
                width=10
            ).pack(side=tk.LEFT)

            self.assets_vars[key] = var

        return page

    def _refresh_list(self):
        """刷新角色列表"""
        try:
            # 触发配置重新扫描
            self.config_loader.scan_all()

            # 清空列表
            self.char_listbox.delete(0, tk.END)

            # 更新游戏IP下拉列表
            games = list(self.config_loader.games.keys())
            self.game_combo['values'] = games

            # 加载角色
            characters = self.config_loader.characters
            for char_id, char_data in characters.items():
                char_name = char_data.get("name", char_id)
                game_id = char_data.get("game_id", "unknown")
                game_name = self.config_loader.games.get(game_id, {}).get("name", game_id)
                self.char_listbox.insert(tk.END, f"{char_name} ({char_id}) - {game_name}")

            logger.info(f"角色列表已刷新: {len(characters)}个角色")

        except Exception as e:
            logger.error(f"刷新角色列表失败: {e}")
            messagebox.showerror("错误", f"刷新列表失败:\n{e}")

    def _on_select_character(self, event):
        """选择角色时触发"""
        selection = self.char_listbox.curselection()
        if not selection:
            return

        # 从列表文本中提取character_id
        text = self.char_listbox.get(selection[0])
        # 格式: "角色名称 (character_id) - 游戏名称"
        import re
        match = re.search(r'\(([^)]+)\)', text)
        if match:
            char_id = match.group(1)
            self._load_character(char_id)

    def _new_character(self):
        """新增角色"""
        self.current_character_id = None
        self.current_game_id = None
        self._clear_editor()
        self.char_id_entry.config(state=tk.NORMAL)
        logger.info("准备新增角色")

    def _edit_selected(self):
        """编辑选中的角色"""
        selection = self.char_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要编辑的角色")
            return

        self._on_select_character(None)

    def _delete_selected(self):
        """删除选中的角色"""
        selection = self.char_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的角色")
            return

        # 从列表文本中提取character_id
        text = self.char_listbox.get(selection[0])
        import re
        match = re.search(r'\(([^)]+)\)', text)
        if not match:
            return

        char_id = match.group(1)
        char_data = self.config_loader.characters.get(char_id, {})
        char_name = char_data.get("name", char_id)
        game_id = char_data.get("game_id")

        # 确认删除
        if not messagebox.askyesno(
            "确认删除",
            f"确定要删除角色 '{char_name}' 吗？\n\n"
            f"删除的内容将移动到回收站，可以恢复。"
        ):
            return

        try:
            # 删除角色文件
            char_file = self.root_dir / "games" / game_id / "characters" / f"{char_id}.yaml"
            if char_file.exists():
                self.admin_manager.delete_config(str(char_file))
                logger.info(f"角色已删除: {char_id}")
                messagebox.showinfo("成功", f"角色 '{char_name}' 已删除并移动到回收站")

                # 刷新列表
                self._refresh_list()
                self._clear_editor()
            else:
                messagebox.showerror("错误", f"角色文件不存在: {char_file}")

        except Exception as e:
            logger.error(f"删除角色失败: {e}")
            messagebox.showerror("错误", f"删除失败:\n{e}")

    def _load_character(self, char_id: str):
        """加载角色数据到编辑器"""
        try:
            char_data = self.config_loader.characters.get(char_id)
            if not char_data:
                messagebox.showerror("错误", f"角色不存在: {char_id}")
                return

            self.current_character_id = char_id
            self.current_game_id = char_data.get("game_id")

            # 填充基础信息
            self.game_id_var.set(self.current_game_id)
            self.char_id_var.set(char_id)
            self.char_id_entry.config(state=tk.DISABLED)
            self.char_name_var.set(char_data.get("name", ""))
            self.char_type_var.set(char_data.get("type", "defender"))
            self.char_cost_var.set(char_data.get("cost", 100))

            desc = char_data.get("description", "")
            self.char_desc_text.delete("1.0", tk.END)
            self.char_desc_text.insert("1.0", desc)

            # 填充属性
            stats = char_data.get("stats", {})
            for key, var in self.stats_vars.items():
                var.set(stats.get(key, var.get()))

            # 填充技能列表
            self.skills_listbox.delete(0, tk.END)
            skills = char_data.get("skills", [])
            for skill in skills:
                skill_id = skill.get("skill_id", "unknown")
                skill_name = skill.get("name", skill_id)
                self.skills_listbox.insert(tk.END, f"{skill_name} ({skill_id})")

            # 填充攻击类型和弹道配置
            attack_type = char_data.get("attack_type", "melee")
            self.attack_type_var.set(attack_type)

            projectile = char_data.get("projectile", {})
            if projectile:
                self.proj_type_var.set(projectile.get("projectile_type", "linear"))
                self.proj_speed_var.set(projectile.get("speed", 400))
                self.proj_size_var.set(projectile.get("size", 10))
                color = projectile.get("color", [255, 200, 0])
                self.proj_color_r.set(color[0])
                self.proj_color_g.set(color[1])
                self.proj_color_b.set(color[2])
                self.proj_pierce_var.set(projectile.get("pierce", False))
                self.proj_pierce_count_var.set(projectile.get("pierce_count", 3))
                self.proj_splash_var.set(projectile.get("splash_radius", 0))
                self.proj_lifetime_var.set(projectile.get("lifetime", 3.0))

            self._on_attack_type_change()
            self._on_pierce_change()

            # 填充被动特质
            self.traits_listbox.delete(0, tk.END)
            passive_traits = char_data.get("passive_traits", [])
            for trait in passive_traits:
                trait_type = trait.get("type", "unknown")
                value = trait.get("value", 0)
                self.traits_listbox.insert(tk.END, f"{trait_type}: {value}")

            # 填充资源
            assets = char_data.get("assets", {})
            for key, var in self.assets_vars.items():
                var.set(assets.get(key, ""))

            logger.info(f"已加载角色: {char_id}")

        except Exception as e:
            logger.error(f"加载角色失败: {e}")
            messagebox.showerror("错误", f"加载失败:\n{e}")

    def _clear_editor(self):
        """清空编辑器"""
        self.current_character_id = None
        self.current_game_id = None

        # 清空基础信息
        self.game_id_var.set("")
        self.char_id_var.set("")
        self.char_id_entry.config(state=tk.NORMAL)
        self.char_name_var.set("")
        self.char_type_var.set("defender")
        self.char_cost_var.set(100)
        self.char_desc_text.delete("1.0", tk.END)

        # 清空属性（恢复默认值）
        defaults = {
            "hp": 300, "attack": 20, "attack_range": 250,
            "attack_speed": 1.5, "speed": 0, "crit_rate": 0.05,
            "crit_damage": 1.5, "effect_resistance": 0.1
        }
        for key, var in self.stats_vars.items():
            var.set(defaults.get(key, 0))

        # 清空攻击类型和弹道配置
        self.attack_type_var.set("melee")
        self.proj_type_var.set("linear")
        self.proj_speed_var.set(400)
        self.proj_size_var.set(10)
        self.proj_color_r.set(255)
        self.proj_color_g.set(200)
        self.proj_color_b.set(0)
        self.proj_pierce_var.set(False)
        self.proj_pierce_count_var.set(3)
        self.proj_splash_var.set(0)
        self.proj_lifetime_var.set(3.0)
        self._on_attack_type_change()
        self._on_pierce_change()

        # 清空被动特质列表
        self.traits_listbox.delete(0, tk.END)

        # 清空技能列表
        self.skills_listbox.delete(0, tk.END)

        # 清空资源
        for var in self.assets_vars.values():
            var.set("")

    def _add_skill(self):
        """添加技能"""
        skill_id = simpledialog.askstring("添加技能", "请输入技能ID\n(详细技能配置将在Phase 5实现):")
        if skill_id:
            skill_id = skill_id.strip()
            if skill_id:
                self.skills_listbox.insert(tk.END, f"未命名技能 ({skill_id})")

    def _remove_skill(self):
        """删除技能"""
        selection = self.skills_listbox.curselection()
        if selection:
            self.skills_listbox.delete(selection[0])

    def _select_asset(self, var: tk.StringVar, file_types: str):
        """选择资源文件"""
        # 解析文件类型
        if "图片" in file_types:
            filetypes = [("图片文件", "*.png *.jpg *.jpeg"), ("所有文件", "*.*")]
        elif "音频" in file_types:
            filetypes = [("音频文件", "*.wav *.ogg *.mp3"), ("所有文件", "*.*")]
        else:
            filetypes = [("所有文件", "*.*")]

        file_path = filedialog.askopenfilename(
            title="选择资源文件",
            filetypes=filetypes
        )
        if file_path:
            var.set(file_path)

    def _save_character(self):
        """保存角色"""
        try:
            # 验证必填字段
            game_id = self.game_id_var.get().strip()
            char_id = self.char_id_var.get().strip()
            char_name = self.char_name_var.get().strip()

            if not game_id:
                messagebox.showwarning("验证失败", "请选择所属游戏IP")
                return

            if not char_id:
                messagebox.showwarning("验证失败", "请输入角色ID")
                return

            if not char_name:
                messagebox.showwarning("验证失败", "请输入角色名称")
                return

            # 验证角色ID格式
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', char_id):
                messagebox.showwarning(
                    "验证失败",
                    "角色ID只能包含英文字母、数字和下划线"
                )
                return

            # 验证游戏IP是否存在
            if game_id not in self.config_loader.games:
                messagebox.showerror("错误", f"游戏IP '{game_id}' 不存在")
                return

            # 如果是新增，检查ID是否已存在
            is_new = self.current_character_id is None
            if is_new and char_id in self.config_loader.characters:
                messagebox.showwarning("验证失败", f"角色ID '{char_id}' 已存在")
                return

            # 收集属性数据
            stats = {key: var.get() for key, var in self.stats_vars.items()}

            # 收集技能列表（简化版，仅保存skill_id）
            skills = []
            for i in range(self.skills_listbox.size()):
                text = self.skills_listbox.get(i)
                match = re.search(r'\(([^)]+)\)$', text)
                if match:
                    skill_id = match.group(1)
                    skills.append({"skill_id": skill_id})

            # 处理资源文件
            assets = {}
            char_dir = self.root_dir / "games" / game_id / "characters"
            char_dir.mkdir(parents=True, exist_ok=True)

            for key, var in self.assets_vars.items():
                file_path = var.get().strip()
                if file_path and Path(file_path).exists():
                    # 复制资源文件
                    filename = Path(file_path).name
                    dest_file = char_dir / filename
                    shutil.copy2(file_path, dest_file)
                    assets[key] = f"games/{game_id}/characters/{filename}"
                    logger.info(f"资源已复制: {dest_file}")

            # 收集攻击类型和弹道配置
            attack_type = self.attack_type_var.get()
            projectile_config = None
            if attack_type == "ranged":
                projectile_config = {
                    "projectile_type": self.proj_type_var.get(),
                    "speed": self.proj_speed_var.get(),
                    "size": self.proj_size_var.get(),
                    "color": [
                        self.proj_color_r.get(),
                        self.proj_color_g.get(),
                        self.proj_color_b.get()
                    ],
                    "pierce": self.proj_pierce_var.get(),
                    "splash_radius": self.proj_splash_var.get(),
                    "lifetime": self.proj_lifetime_var.get()
                }
                # 如果开启穿透，添加穿透次数
                if self.proj_pierce_var.get():
                    projectile_config["pierce_count"] = self.proj_pierce_count_var.get()

            # 收集被动特质
            passive_traits = []
            for i in range(self.traits_listbox.size()):
                text = self.traits_listbox.get(i)
                parts = text.split(": ")
                if len(parts) == 2:
                    trait_type = parts[0]
                    value = float(parts[1])
                    passive_traits.append({"type": trait_type, "value": value})

            # 构建配置数据
            char_config = {
                "character_id": char_id,
                "game_id": game_id,
                "name": char_name,
                "type": self.char_type_var.get(),
                "cost": self.char_cost_var.get(),
                "description": self.char_desc_text.get("1.0", tk.END).strip(),
                "stats": stats,
                "attack_type": attack_type,
                "skills": skills,
                "available_skins": ["basic"],
                "assets": assets,
            }

            # 仅在远程攻击时添加弹道配置
            if projectile_config:
                char_config["projectile"] = projectile_config

            # 仅在有被动特质时添加
            if passive_traits:
                char_config["passive_traits"] = passive_traits

            # 保存角色配置文件
            char_file = self.root_dir / "games" / game_id / "characters" / f"{char_id}.yaml"
            with open(char_file, 'w', encoding='utf-8') as f:
                yaml.dump(char_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            logger.info(f"角色配置已保存: {char_file}")

            # 记录操作日志
            operation = "创建" if is_new else "更新"
            self.admin_manager.log_operation(f"{operation}角色", f"{char_name} ({char_id})")

            messagebox.showinfo("成功", f"角色 '{char_name}' 已{operation}成功！")

            # 刷新列表
            self._refresh_list()

            # 清空编辑器
            self._clear_editor()

        except Exception as e:
            logger.error(f"保存角色失败: {e}")
            messagebox.showerror("错误", f"保存失败:\n{e}")


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    root = tk.Tk()
    root.title("角色管理器测试")
    root.geometry("1100x750")

    from core.config_loader import get_config_loader
    from core.admin_manager import AdminManager

    config_loader = get_config_loader(".")
    admin_manager = AdminManager(".")

    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)

    manager = CharacterManager(frame, config_loader, admin_manager)

    root.mainloop()
