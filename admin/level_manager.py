"""
关卡管理器 - Phase 8
提供关卡的新增、编辑、删除功能
包含完整的波次编辑器、Boss配置、条件和奖励管理
"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
import yaml
from pathlib import Path
import re
import shutil
from typing import Dict, Any, Optional, List
from logger_config import logger


class LevelManager:
    """关卡管理器"""

    def __init__(self, parent, config_loader, admin_manager):
        self.parent = parent
        self.config_loader = config_loader
        self.admin_manager = admin_manager
        self.root_dir = Path(__file__).parent.parent

        # 当前编辑的关卡数据
        self.current_level = None
        self.current_campaign = None

        # 波次数据
        self.waves_data = []
        self.current_wave_index = -1

        # 创建主布局
        self._create_layout()

        # 加载关卡列表
        self._load_level_list()

    def _create_layout(self):
        """创建主布局"""
        # 左侧：关卡列表
        left_frame = ttk.Frame(self.parent, width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="关卡列表", font=("Arial", 12, "bold")).pack(pady=5)

        # 战役筛选
        filter_frame = ttk.Frame(left_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(filter_frame, text="战役筛选:").pack(side=tk.LEFT)
        self.campaign_filter_var = tk.StringVar(value="全部")
        self.campaign_filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.campaign_filter_var,
            state="readonly",
            width=15
        )
        self.campaign_filter_combo.pack(side=tk.LEFT, padx=5)
        self.campaign_filter_combo.bind("<<ComboboxSelected>>", lambda e: self._load_level_list())

        # 关卡列表
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.level_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.level_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.level_listbox.yview)

        self.level_listbox.bind("<<ListboxSelect>>", self._on_level_selected)

        # 按钮区
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="新增关卡", command=self._new_level).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="删除关卡", command=self._delete_level).pack(fill=tk.X, pady=2)

        # 右侧：编辑器
        right_frame = ttk.Frame(self.parent)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(right_frame, text="关卡编辑器", font=("Arial", 12, "bold")).pack(pady=5)

        # 多标签页编辑器
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 6个标签页
        self.basic_tab = ttk.Frame(self.notebook)
        self.override_tab = ttk.Frame(self.notebook)
        self.wave_tab = ttk.Frame(self.notebook)
        self.boss_tab = ttk.Frame(self.notebook)
        self.condition_tab = ttk.Frame(self.notebook)
        self.performance_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.basic_tab, text="基本信息")
        self.notebook.add(self.override_tab, text="配置覆盖")
        self.notebook.add(self.wave_tab, text="波次管理")
        self.notebook.add(self.boss_tab, text="Boss配置")
        self.notebook.add(self.condition_tab, text="条件与奖励")
        self.notebook.add(self.performance_tab, text="性能配置")

        self._create_basic_tab()
        self._create_override_tab()
        self._create_wave_tab()
        self._create_boss_tab()
        self._create_condition_tab()
        self._create_performance_tab()

        # 保存按钮
        ttk.Button(right_frame, text="保存关卡", command=self._save_level).pack(pady=10)

        # 加载战役列表
        self._load_campaign_filter()

    def _create_basic_tab(self):
        """创建基本信息标签页"""
        canvas = tk.Canvas(self.basic_tab)
        scrollbar = ttk.Scrollbar(self.basic_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 关卡ID
        row = 0
        ttk.Label(scrollable_frame, text="关卡ID*:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.level_id_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.level_id_var, width=30).grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(scrollable_frame, text="格式: level_xx", foreground="gray").grid(row=row, column=2, sticky=tk.W)

        # 关卡名称
        row += 1
        ttk.Label(scrollable_frame, text="关卡名称*:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.level_name_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.level_name_var, width=30).grid(row=row, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5)

        # 所属战役
        row += 1
        ttk.Label(scrollable_frame, text="所属战役*:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.campaign_var = tk.StringVar()
        self.campaign_combo = ttk.Combobox(scrollable_frame, textvariable=self.campaign_var, state="readonly", width=28)
        self.campaign_combo.grid(row=row, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5)

        # 地图ID
        row += 1
        ttk.Label(scrollable_frame, text="地图ID*:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.map_id_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.map_id_var, width=30).grid(row=row, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5)

        # 地图背景
        row += 1
        ttk.Label(scrollable_frame, text="地图背景*:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.map_bg_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.map_bg_var, width=30).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(scrollable_frame, text="浏览", command=lambda: self._browse_file(self.map_bg_var, "image")).grid(row=row, column=2, padx=5)

        # 放置遮罩
        row += 1
        ttk.Label(scrollable_frame, text="放置遮罩*:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.placement_mask_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.placement_mask_var, width=30).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(scrollable_frame, text="浏览", command=lambda: self._browse_file(self.placement_mask_var, "image")).grid(row=row, column=2, padx=5)

        # 路径点配置
        row += 1
        ttk.Label(scrollable_frame, text="路径点配置*:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.path_points_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.path_points_var, width=30).grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(scrollable_frame, text="浏览", command=lambda: self._browse_file(self.path_points_var, "json")).grid(row=row, column=2, padx=5)

    def _create_override_tab(self):
        """创建配置覆盖标签页"""
        canvas = tk.Canvas(self.override_tab)
        scrollbar = ttk.Scrollbar(self.override_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        row = 0

        # === 角色选择配置 ===
        ttk.Label(scrollable_frame, text="角色选择配置", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1
        ttk.Label(scrollable_frame, text="最少角色数:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.min_chars_var = tk.IntVar(value=1)
        ttk.Spinbox(scrollable_frame, from_=0, to=10, textvariable=self.min_chars_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(scrollable_frame, text="最多角色数:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.max_chars_var = tk.IntVar(value=5)
        ttk.Spinbox(scrollable_frame, from_=1, to=10, textvariable=self.max_chars_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        # === 战场配置 ===
        row += 1
        ttk.Label(scrollable_frame, text="战场配置", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1
        ttk.Label(scrollable_frame, text="网格行数:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.grid_rows_var = tk.IntVar(value=5)
        ttk.Spinbox(scrollable_frame, from_=3, to=10, textvariable=self.grid_rows_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(scrollable_frame, text="网格列数:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.grid_cols_var = tk.IntVar(value=9)
        ttk.Spinbox(scrollable_frame, from_=5, to=15, textvariable=self.grid_cols_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(scrollable_frame, text="格子大小:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.cell_size_var = tk.IntVar(value=80)
        ttk.Spinbox(scrollable_frame, from_=50, to=150, increment=10, textvariable=self.cell_size_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(scrollable_frame, text="网格起始X:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.grid_start_x_var = tk.IntVar(value=100)
        ttk.Spinbox(scrollable_frame, from_=0, to=500, increment=10, textvariable=self.grid_start_x_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(scrollable_frame, text="网格起始Y:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.grid_start_y_var = tk.IntVar(value=150)
        ttk.Spinbox(scrollable_frame, from_=0, to=500, increment=10, textvariable=self.grid_start_y_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        # === 战斗系统配置 ===
        row += 1
        ttk.Label(scrollable_frame, text="战斗系统配置", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1
        ttk.Label(scrollable_frame, text="卡牌冷却(秒):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.card_cooldown_var = tk.DoubleVar(value=3.0)
        ttk.Spinbox(scrollable_frame, from_=0.1, to=10.0, increment=0.5, textvariable=self.card_cooldown_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(scrollable_frame, text="敌人攻击间隔(秒):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.enemy_attack_var = tk.DoubleVar(value=2.5)
        ttk.Spinbox(scrollable_frame, from_=0.5, to=10.0, increment=0.5, textvariable=self.enemy_attack_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(scrollable_frame, text="基础伤害倍率:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.damage_mult_var = tk.IntVar(value=5)
        ttk.Spinbox(scrollable_frame, from_=1, to=20, textvariable=self.damage_mult_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(scrollable_frame, text="阻挡距离:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.block_dist_var = tk.IntVar(value=50)
        ttk.Spinbox(scrollable_frame, from_=10, to=200, increment=10, textvariable=self.block_dist_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(scrollable_frame, text="默认敌人速度:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.enemy_speed_var = tk.IntVar(value=15)
        ttk.Spinbox(scrollable_frame, from_=5, to=50, textvariable=self.enemy_speed_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        # === 经济配置 ===
        row += 1
        ttk.Label(scrollable_frame, text="经济配置", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1
        ttk.Label(scrollable_frame, text="初始金币:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.initial_gold_var = tk.IntVar(value=200)
        ttk.Spinbox(scrollable_frame, from_=0, to=10000, increment=50, textvariable=self.initial_gold_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(scrollable_frame, text="金币生成速率:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.gold_rate_var = tk.IntVar(value=25)
        ttk.Spinbox(scrollable_frame, from_=0, to=200, increment=5, textvariable=self.gold_rate_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(scrollable_frame, text="击杀奖励:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.kill_reward_var = tk.IntVar(value=25)
        ttk.Spinbox(scrollable_frame, from_=0, to=500, increment=5, textvariable=self.kill_reward_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        # === 基地配置 ===
        row += 1
        ttk.Label(scrollable_frame, text="基地配置", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1
        ttk.Label(scrollable_frame, text="初始生命值:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.base_hp_var = tk.IntVar(value=1000)
        ttk.Spinbox(scrollable_frame, from_=100, to=10000, increment=100, textvariable=self.base_hp_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

        row += 1
        ttk.Label(scrollable_frame, text="最大生命值:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.base_max_hp_var = tk.IntVar(value=1000)
        ttk.Spinbox(scrollable_frame, from_=100, to=10000, increment=100, textvariable=self.base_max_hp_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5)

    def _create_wave_tab(self):
        """创建波次管理标签页"""
        # 左侧：波次列表
        left_pane = ttk.Frame(self.wave_tab)
        left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)

        ttk.Label(left_pane, text="波次列表", font=("Arial", 10, "bold")).pack(pady=5)

        list_frame = ttk.Frame(left_pane)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.wave_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, width=25)
        self.wave_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.wave_listbox.yview)

        self.wave_listbox.bind("<<ListboxSelect>>", self._on_wave_selected)

        btn_frame = ttk.Frame(left_pane)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="新增波次", command=self._add_wave).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="删除波次", command=self._delete_wave).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="上移", command=lambda: self._move_wave(-1)).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="下移", command=lambda: self._move_wave(1)).pack(fill=tk.X, pady=2)

        # 右侧：波次编辑
        right_pane = ttk.Frame(self.wave_tab)
        right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(right_pane, text="波次编辑", font=("Arial", 10, "bold")).pack(pady=5)

        # 波次基本信息
        info_frame = ttk.LabelFrame(right_pane, text="波次信息")
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(info_frame, text="波次ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.wave_id_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.wave_id_var, width=20).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(info_frame, text="出现时间(秒):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.wave_time_var = tk.DoubleVar(value=10.0)
        ttk.Spinbox(info_frame, from_=0, to=1000, increment=5, textvariable=self.wave_time_var, width=18).grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(info_frame, text="更新波次", command=self._update_wave).grid(row=2, column=0, columnspan=2, pady=5)

        # 敌人列表
        enemy_frame = ttk.LabelFrame(right_pane, text="敌人配置")
        enemy_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 敌人列表
        enemy_list_frame = ttk.Frame(enemy_frame)
        enemy_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        enemy_scrollbar = ttk.Scrollbar(enemy_list_frame)
        enemy_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.enemy_listbox = tk.Listbox(enemy_list_frame, yscrollcommand=enemy_scrollbar.set, height=8)
        self.enemy_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        enemy_scrollbar.config(command=self.enemy_listbox.yview)

        self.enemy_listbox.bind("<<ListboxSelect>>", self._on_enemy_selected)

        # 敌人编辑
        enemy_edit_frame = ttk.Frame(enemy_frame)
        enemy_edit_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(enemy_edit_frame, text="角色:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.enemy_char_var = tk.StringVar()
        self.enemy_char_combo = ttk.Combobox(enemy_edit_frame, textvariable=self.enemy_char_var, state="readonly", width=15)
        self.enemy_char_combo.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(enemy_edit_frame, text="数量:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.enemy_count_var = tk.IntVar(value=1)
        ttk.Spinbox(enemy_edit_frame, from_=1, to=50, textvariable=self.enemy_count_var, width=8).grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(enemy_edit_frame, text="间隔(秒):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.enemy_interval_var = tk.DoubleVar(value=2.0)
        ttk.Spinbox(enemy_edit_frame, from_=0.1, to=10, increment=0.5, textvariable=self.enemy_interval_var, width=13).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(enemy_edit_frame, text="生命倍率:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.enemy_health_mult_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(enemy_edit_frame, from_=0.1, to=10, increment=0.1, textvariable=self.enemy_health_mult_var, width=6).grid(row=1, column=3, padx=5, pady=2)

        ttk.Label(enemy_edit_frame, text="皮肤覆盖:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.enemy_skin_var = tk.StringVar()
        ttk.Entry(enemy_edit_frame, textvariable=self.enemy_skin_var, width=17).grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(enemy_edit_frame, text="模型缩放:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        self.enemy_scale_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(enemy_edit_frame, from_=0.1, to=5, increment=0.1, textvariable=self.enemy_scale_var, width=6).grid(row=2, column=3, padx=5, pady=2)

        ttk.Label(enemy_edit_frame, text="动画速度:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.enemy_anim_speed_var = tk.DoubleVar(value=1.0)
        ttk.Spinbox(enemy_edit_frame, from_=0.1, to=3, increment=0.1, textvariable=self.enemy_anim_speed_var, width=13).grid(row=3, column=1, padx=5, pady=2)

        enemy_btn_frame = ttk.Frame(enemy_frame)
        enemy_btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(enemy_btn_frame, text="添加敌人", command=self._add_enemy).pack(side=tk.LEFT, padx=2)
        ttk.Button(enemy_btn_frame, text="更新敌人", command=self._update_enemy).pack(side=tk.LEFT, padx=2)
        ttk.Button(enemy_btn_frame, text="删除敌人", command=self._delete_enemy).pack(side=tk.LEFT, padx=2)

    def _create_boss_tab(self):
        """创建Boss配置标签页"""
        canvas = tk.Canvas(self.boss_tab)
        scrollbar = ttk.Scrollbar(self.boss_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Boss启用开关
        self.boss_enable_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(scrollable_frame, text="启用Boss战", variable=self.boss_enable_var, command=self._toggle_boss).grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=5, pady=10)

        row = 1

        # Boss角色
        ttk.Label(scrollable_frame, text="Boss角色:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.boss_char_var = tk.StringVar()
        self.boss_char_combo = ttk.Combobox(scrollable_frame, textvariable=self.boss_char_var, state="readonly", width=20)
        self.boss_char_combo.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        # 触发时间
        row += 1
        ttk.Label(scrollable_frame, text="触发时间(秒):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.boss_time_var = tk.DoubleVar(value=120.0)
        ttk.Spinbox(scrollable_frame, from_=0, to=1000, increment=10, textvariable=self.boss_time_var, width=18).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        # 生命倍率
        row += 1
        ttk.Label(scrollable_frame, text="生命倍率:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.boss_health_mult_var = tk.DoubleVar(value=3.0)
        ttk.Spinbox(scrollable_frame, from_=1.0, to=20.0, increment=0.5, textvariable=self.boss_health_mult_var, width=18).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        # 攻击倍率
        row += 1
        ttk.Label(scrollable_frame, text="攻击倍率:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.boss_attack_mult_var = tk.DoubleVar(value=2.0)
        ttk.Spinbox(scrollable_frame, from_=1.0, to=10.0, increment=0.5, textvariable=self.boss_attack_mult_var, width=18).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        # 速度倍率
        row += 1
        ttk.Label(scrollable_frame, text="速度倍率:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.boss_speed_mult_var = tk.DoubleVar(value=0.8)
        ttk.Spinbox(scrollable_frame, from_=0.1, to=3.0, increment=0.1, textvariable=self.boss_speed_mult_var, width=18).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        # 皮肤覆盖
        row += 1
        ttk.Label(scrollable_frame, text="皮肤覆盖:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.boss_skin_var = tk.StringVar()
        ttk.Entry(scrollable_frame, textvariable=self.boss_skin_var, width=22).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        # 模型缩放
        row += 1
        ttk.Label(scrollable_frame, text="模型缩放:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.boss_scale_var = tk.DoubleVar(value=1.5)
        ttk.Spinbox(scrollable_frame, from_=0.5, to=5.0, increment=0.1, textvariable=self.boss_scale_var, width=18).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        # 特殊技能列表
        row += 1
        ttk.Label(scrollable_frame, text="特殊技能:", font=("Arial", 9, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1
        skills_frame = ttk.Frame(scrollable_frame)
        skills_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)

        skills_scrollbar = ttk.Scrollbar(skills_frame)
        skills_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.boss_skills_listbox = tk.Listbox(skills_frame, yscrollcommand=skills_scrollbar.set, height=5)
        self.boss_skills_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        skills_scrollbar.config(command=self.boss_skills_listbox.yview)

        row += 1
        skill_btn_frame = ttk.Frame(scrollable_frame)
        skill_btn_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)

        self.boss_skill_var = tk.StringVar()
        ttk.Entry(skill_btn_frame, textvariable=self.boss_skill_var, width=20).pack(side=tk.LEFT, padx=2)
        ttk.Button(skill_btn_frame, text="添加", command=self._add_boss_skill).pack(side=tk.LEFT, padx=2)
        ttk.Button(skill_btn_frame, text="删除", command=self._delete_boss_skill).pack(side=tk.LEFT, padx=2)

        self._toggle_boss()  # 初始化状态

    def _create_condition_tab(self):
        """创建条件与奖励标签页"""
        canvas = tk.Canvas(self.condition_tab)
        scrollbar = ttk.Scrollbar(self.condition_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        row = 0

        # === 胜利条件 ===
        ttk.Label(scrollable_frame, text="胜利条件", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1
        victory_frame = ttk.Frame(scrollable_frame)
        victory_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)

        victory_scrollbar = ttk.Scrollbar(victory_frame)
        victory_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.victory_listbox = tk.Listbox(victory_frame, yscrollcommand=victory_scrollbar.set, height=5)
        self.victory_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        victory_scrollbar.config(command=self.victory_listbox.yview)

        row += 1
        victory_btn_frame = ttk.Frame(scrollable_frame)
        victory_btn_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)

        self.victory_cond_var = tk.StringVar()
        ttk.Entry(victory_btn_frame, textvariable=self.victory_cond_var, width=30).pack(side=tk.LEFT, padx=2)
        ttk.Button(victory_btn_frame, text="添加", command=lambda: self._add_condition("victory")).pack(side=tk.LEFT, padx=2)
        ttk.Button(victory_btn_frame, text="删除", command=lambda: self._delete_condition("victory")).pack(side=tk.LEFT, padx=2)

        row += 1
        ttk.Label(scrollable_frame, text="常用: base_hp > 0, all_waves_cleared, boss_defeated", foreground="gray", font=("Arial", 8)).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5)

        # === 失败条件 ===
        row += 1
        ttk.Label(scrollable_frame, text="失败条件", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1
        defeat_frame = ttk.Frame(scrollable_frame)
        defeat_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)

        defeat_scrollbar = ttk.Scrollbar(defeat_frame)
        defeat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.defeat_listbox = tk.Listbox(defeat_frame, yscrollcommand=defeat_scrollbar.set, height=5)
        self.defeat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        defeat_scrollbar.config(command=self.defeat_listbox.yview)

        row += 1
        defeat_btn_frame = ttk.Frame(scrollable_frame)
        defeat_btn_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)

        self.defeat_cond_var = tk.StringVar()
        ttk.Entry(defeat_btn_frame, textvariable=self.defeat_cond_var, width=30).pack(side=tk.LEFT, padx=2)
        ttk.Button(defeat_btn_frame, text="添加", command=lambda: self._add_condition("defeat")).pack(side=tk.LEFT, padx=2)
        ttk.Button(defeat_btn_frame, text="删除", command=lambda: self._delete_condition("defeat")).pack(side=tk.LEFT, padx=2)

        row += 1
        ttk.Label(scrollable_frame, text="常用: base_hp <= 0, time_limit_exceeded", foreground="gray", font=("Arial", 8)).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5)

        # === 奖励配置 ===
        row += 1
        ttk.Label(scrollable_frame, text="奖励配置", font=("Arial", 10, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1
        ttk.Label(scrollable_frame, text="金币奖励:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.reward_gold_var = tk.IntVar(value=500)
        ttk.Spinbox(scrollable_frame, from_=0, to=100000, increment=100, textvariable=self.reward_gold_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        row += 1
        ttk.Label(scrollable_frame, text="经验奖励:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.reward_exp_var = tk.IntVar(value=100)
        ttk.Spinbox(scrollable_frame, from_=0, to=10000, increment=50, textvariable=self.reward_exp_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        row += 1
        ttk.Label(scrollable_frame, text="解锁关卡:", font=("Arial", 9, "bold")).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1
        unlock_frame = ttk.Frame(scrollable_frame)
        unlock_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)

        unlock_scrollbar = ttk.Scrollbar(unlock_frame)
        unlock_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.unlock_listbox = tk.Listbox(unlock_frame, yscrollcommand=unlock_scrollbar.set, height=5)
        self.unlock_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        unlock_scrollbar.config(command=self.unlock_listbox.yview)

        row += 1
        unlock_btn_frame = ttk.Frame(scrollable_frame)
        unlock_btn_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)

        self.unlock_level_var = tk.StringVar()
        ttk.Entry(unlock_btn_frame, textvariable=self.unlock_level_var, width=20).pack(side=tk.LEFT, padx=2)
        ttk.Button(unlock_btn_frame, text="添加", command=self._add_unlock_level).pack(side=tk.LEFT, padx=2)
        ttk.Button(unlock_btn_frame, text="删除", command=self._delete_unlock_level).pack(side=tk.LEFT, padx=2)

    def _create_performance_tab(self):
        """创建性能配置标签页"""
        canvas = tk.Canvas(self.performance_tab)
        scrollbar = ttk.Scrollbar(self.performance_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        row = 0

        ttk.Label(scrollable_frame, text="波次粒子限制:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.wave_particle_var = tk.IntVar(value=300)
        ttk.Spinbox(scrollable_frame, from_=100, to=1000, increment=50, textvariable=self.wave_particle_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        row += 1
        ttk.Label(scrollable_frame, text="Boss战粒子限制:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.boss_particle_var = tk.IntVar(value=500)
        ttk.Spinbox(scrollable_frame, from_=100, to=1000, increment=50, textvariable=self.boss_particle_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        row += 1
        self.dynamic_quality_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(scrollable_frame, text="启用动态质量调整", variable=self.dynamic_quality_var).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10)

        row += 1
        ttk.Label(scrollable_frame, text="低端设备禁用特效:", font=("Arial", 9, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=(10, 5))

        row += 1
        disable_frame = ttk.Frame(scrollable_frame)
        disable_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)

        disable_scrollbar = ttk.Scrollbar(disable_frame)
        disable_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.disable_effects_listbox = tk.Listbox(disable_frame, yscrollcommand=disable_scrollbar.set, height=6)
        self.disable_effects_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        disable_scrollbar.config(command=self.disable_effects_listbox.yview)

        row += 1
        disable_btn_frame = ttk.Frame(scrollable_frame)
        disable_btn_frame.grid(row=row, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)

        self.disable_effect_var = tk.StringVar()
        ttk.Entry(disable_btn_frame, textvariable=self.disable_effect_var, width=20).pack(side=tk.LEFT, padx=2)
        ttk.Button(disable_btn_frame, text="添加", command=self._add_disable_effect).pack(side=tk.LEFT, padx=2)
        ttk.Button(disable_btn_frame, text="删除", command=self._delete_disable_effect).pack(side=tk.LEFT, padx=2)

    def _load_campaign_filter(self):
        """加载战役筛选列表"""
        campaigns = ["全部"]
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

        self.campaign_filter_combo['values'] = campaigns

        # 同时更新基本信息页的战役下拉框
        self.campaign_combo['values'] = campaigns[1:]  # 排除"全部"

    def _load_level_list(self):
        """加载关卡列表"""
        self.level_listbox.delete(0, tk.END)

        campaign_filter = self.campaign_filter_var.get()

        campaigns_dir = self.root_dir / "campaigns"
        if not campaigns_dir.exists():
            return

        for campaign_dir in campaigns_dir.iterdir():
            if not campaign_dir.is_dir():
                continue

            # 战役筛选
            if campaign_filter != "全部":
                if not campaign_filter.endswith(f"({campaign_dir.name})"):
                    continue

            levels_dir = campaign_dir / "levels"
            if not levels_dir.exists():
                continue

            for level_file in levels_dir.glob("*.yaml"):
                try:
                    with open(level_file, 'r', encoding='utf-8') as f:
                        level_data = yaml.safe_load(f)
                        level_name = level_data.get("name", level_file.stem)
                        level_id = level_data.get("level_id", level_file.stem)
                        self.level_listbox.insert(tk.END, f"{level_name} ({campaign_dir.name}/{level_id})")
                except Exception as e:
                    logger.error(f"加载关卡文件失败 {level_file}: {e}")

        # 加载敌方角色列表（用于波次编辑）
        self._load_enemy_characters()

        # 加载Boss角色列表
        self._load_boss_characters()

    def _load_enemy_characters(self):
        """加载敌方角色列表"""
        characters = []
        for char_id, char_data in self.config_loader.characters.items():
            char_name = char_data.get("name", char_id)
            characters.append(f"{char_name} ({char_id})")

        self.enemy_char_combo['values'] = characters

    def _load_boss_characters(self):
        """加载Boss角色列表"""
        characters = []
        for char_id, char_data in self.config_loader.characters.items():
            char_name = char_data.get("name", char_id)
            characters.append(f"{char_name} ({char_id})")

        self.boss_char_combo['values'] = characters

    def _on_level_selected(self, event):
        """选中关卡时加载数据"""
        selection = self.level_listbox.curselection()
        if not selection:
            return

        level_str = self.level_listbox.get(selection[0])
        # 格式: "关卡名 (campaign_id/level_id)"
        match = re.search(r'\((.+?)/(.+?)\)$', level_str)
        if not match:
            return

        campaign_id = match.group(1)
        level_id = match.group(2)

        level_file = self.root_dir / "campaigns" / campaign_id / "levels" / f"{level_id}.yaml"
        if not level_file.exists():
            messagebox.showerror("错误", f"关卡文件不存在: {level_file}")
            return

        try:
            with open(level_file, 'r', encoding='utf-8') as f:
                level_data = yaml.safe_load(f)

            self.current_level = level_id
            self.current_campaign = campaign_id
            self._populate_level_data(level_data)

            logger.info(f"加载关卡: {campaign_id}/{level_id}")

        except Exception as e:
            logger.error(f"加载关卡失败: {e}")
            messagebox.showerror("错误", f"加载关卡失败:\n{e}")

    def _populate_level_data(self, data: Dict[str, Any]):
        """填充关卡数据到编辑器"""
        # 基本信息
        self.level_id_var.set(data.get("level_id", ""))
        self.level_name_var.set(data.get("name", ""))

        # 设置战役（需要找到匹配的项）
        campaign_name = ""
        campaign_file = self.root_dir / "campaigns" / self.current_campaign / f"{self.current_campaign}.yaml"
        if campaign_file.exists():
            try:
                with open(campaign_file, 'r', encoding='utf-8') as f:
                    campaign_data = yaml.safe_load(f)
                    campaign_name = campaign_data.get("name", self.current_campaign)
            except:
                campaign_name = self.current_campaign

        for idx, val in enumerate(self.campaign_combo['values']):
            if val.endswith(f"({self.current_campaign})"):
                self.campaign_combo.current(idx)
                break

        self.map_id_var.set(data.get("map_id", ""))
        self.map_bg_var.set(data.get("map_background", ""))
        self.placement_mask_var.set(data.get("placement_mask", ""))
        self.path_points_var.set(data.get("path_points", ""))

        # 配置覆盖
        char_sel = data.get("character_selection", {})
        self.min_chars_var.set(char_sel.get("min_characters", 1))
        self.max_chars_var.set(char_sel.get("max_characters", 5))

        battlefield = data.get("battlefield", {})
        self.grid_rows_var.set(battlefield.get("grid_rows", 5))
        self.grid_cols_var.set(battlefield.get("grid_cols", 9))
        self.cell_size_var.set(battlefield.get("cell_size", 80))
        self.grid_start_x_var.set(battlefield.get("grid_start_x", 100))
        self.grid_start_y_var.set(battlefield.get("grid_start_y", 150))

        battle = data.get("battle_system", {})
        self.card_cooldown_var.set(battle.get("card_cooldown", 3.0))
        self.enemy_attack_var.set(battle.get("enemy_attack_interval", 2.5))
        self.damage_mult_var.set(battle.get("base_damage_multiplier", 5))
        self.block_dist_var.set(battle.get("block_distance", 50))
        self.enemy_speed_var.set(battle.get("default_enemy_speed", 15))

        economy = data.get("economy", {})
        self.initial_gold_var.set(economy.get("initial_gold", 200))
        self.gold_rate_var.set(economy.get("gold_generation_rate", 25))
        self.kill_reward_var.set(economy.get("kill_reward", 25))

        base = data.get("base", {})
        self.base_hp_var.set(base.get("initial_hp", 1000))
        self.base_max_hp_var.set(base.get("max_hp", 1000))

        # 波次数据
        self.waves_data = data.get("waves", [])
        self._refresh_wave_list()

        # Boss配置
        boss = data.get("boss")
        if boss:
            self.boss_enable_var.set(True)

            # 找到角色并设置
            boss_char = boss.get("character", "")
            for idx, val in enumerate(self.boss_char_combo['values']):
                if val.endswith(f"({boss_char})"):
                    self.boss_char_combo.current(idx)
                    break

            self.boss_time_var.set(boss.get("trigger_time", 120.0))
            self.boss_health_mult_var.set(boss.get("health_multiplier", 3.0))
            self.boss_attack_mult_var.set(boss.get("attack_multiplier", 2.0))
            self.boss_speed_mult_var.set(boss.get("speed_multiplier", 0.8))
            self.boss_skin_var.set(boss.get("skin_override", ""))
            self.boss_scale_var.set(boss.get("model_scale", 1.5))

            # Boss技能
            self.boss_skills_listbox.delete(0, tk.END)
            for skill in boss.get("special_skills", []):
                self.boss_skills_listbox.insert(tk.END, skill)
        else:
            self.boss_enable_var.set(False)

        self._toggle_boss()

        # 条件与奖励
        self.victory_listbox.delete(0, tk.END)
        for cond in data.get("victory_conditions", []):
            self.victory_listbox.insert(tk.END, cond)

        self.defeat_listbox.delete(0, tk.END)
        for cond in data.get("defeat_conditions", []):
            self.defeat_listbox.insert(tk.END, cond)

        rewards = data.get("rewards", {})
        self.reward_gold_var.set(rewards.get("gold", 500))
        self.reward_exp_var.set(rewards.get("exp", 100))

        self.unlock_listbox.delete(0, tk.END)
        for level in rewards.get("unlock_levels", []):
            self.unlock_listbox.insert(tk.END, level)

        # 性能配置
        perf = data.get("performance_config", {})
        self.wave_particle_var.set(perf.get("wave_particle_limit", 300))
        self.boss_particle_var.set(perf.get("boss_fight_particle_limit", 500))
        self.dynamic_quality_var.set(perf.get("dynamic_quality_adjust", True))

        self.disable_effects_listbox.delete(0, tk.END)
        for effect in perf.get("low_end_disable_effects", []):
            self.disable_effects_listbox.insert(tk.END, effect)

    def _new_level(self):
        """新建关卡"""
        self.current_level = None
        self.current_campaign = None

        # 清空所有字段
        self.level_id_var.set("")
        self.level_name_var.set("")
        self.campaign_var.set("")
        self.map_id_var.set("")
        self.map_bg_var.set("")
        self.placement_mask_var.set("")
        self.path_points_var.set("")

        # 重置为默认值
        self.min_chars_var.set(1)
        self.max_chars_var.set(5)
        self.grid_rows_var.set(5)
        self.grid_cols_var.set(9)
        self.cell_size_var.set(80)
        self.grid_start_x_var.set(100)
        self.grid_start_y_var.set(150)
        self.card_cooldown_var.set(3.0)
        self.enemy_attack_var.set(2.5)
        self.damage_mult_var.set(5)
        self.block_dist_var.set(50)
        self.enemy_speed_var.set(15)
        self.initial_gold_var.set(200)
        self.gold_rate_var.set(25)
        self.kill_reward_var.set(25)
        self.base_hp_var.set(1000)
        self.base_max_hp_var.set(1000)

        self.waves_data = []
        self._refresh_wave_list()

        self.boss_enable_var.set(False)
        self._toggle_boss()

        self.victory_listbox.delete(0, tk.END)
        self.defeat_listbox.delete(0, tk.END)
        self.unlock_listbox.delete(0, tk.END)

        self.reward_gold_var.set(500)
        self.reward_exp_var.set(100)

        self.wave_particle_var.set(300)
        self.boss_particle_var.set(500)
        self.dynamic_quality_var.set(True)
        self.disable_effects_listbox.delete(0, tk.END)

        logger.info("新建关卡")

    def _delete_level(self):
        """删除关卡"""
        if not self.current_level or not self.current_campaign:
            messagebox.showwarning("警告", "请先选择要删除的关卡")
            return

        if not messagebox.askyesno("确认删除", f"确定要删除关卡 {self.current_campaign}/{self.current_level} 吗？\n将移动到回收站"):
            return

        level_file = self.root_dir / "campaigns" / self.current_campaign / "levels" / f"{self.current_level}.yaml"

        try:
            self.admin_manager.move_to_recycle_bin(level_file, f"level_{self.current_campaign}_{self.current_level}")
            logger.info(f"删除关卡: {self.current_campaign}/{self.current_level}")
            messagebox.showinfo("成功", "关卡已删除")

            self._load_level_list()
            self._new_level()

        except Exception as e:
            logger.error(f"删除关卡失败: {e}")
            messagebox.showerror("错误", f"删除关卡失败:\n{e}")

    def _save_level(self):
        """保存关卡"""
        # 验证必填字段
        level_id = self.level_id_var.get().strip()
        level_name = self.level_name_var.get().strip()
        campaign = self.campaign_var.get().strip()

        if not level_id or not level_name or not campaign:
            messagebox.showwarning("警告", "请填写所有必填字段（标记*）")
            return

        # 验证ID格式
        if not re.match(r'^level_\w+$', level_id):
            messagebox.showwarning("警告", "关卡ID格式错误，应为: level_xx")
            return

        # 提取campaign_id
        match = re.search(r'\((.+?)\)$', campaign)
        if not match:
            messagebox.showwarning("警告", "无效的战役选择")
            return

        campaign_id = match.group(1)

        # 构建关卡数据
        level_data = {
            "level_id": level_id,
            "name": level_name,
            "map_id": self.map_id_var.get(),
            "map_background": self.map_bg_var.get(),
            "placement_mask": self.placement_mask_var.get(),
            "path_points": self.path_points_var.get(),
            "character_selection": {
                "min_characters": self.min_chars_var.get(),
                "max_characters": self.max_chars_var.get()
            },
            "battlefield": {
                "grid_rows": self.grid_rows_var.get(),
                "grid_cols": self.grid_cols_var.get(),
                "cell_size": self.cell_size_var.get(),
                "grid_start_x": self.grid_start_x_var.get(),
                "grid_start_y": self.grid_start_y_var.get()
            },
            "battle_system": {
                "card_cooldown": self.card_cooldown_var.get(),
                "enemy_attack_interval": self.enemy_attack_var.get(),
                "base_damage_multiplier": self.damage_mult_var.get(),
                "block_distance": self.block_dist_var.get(),
                "default_enemy_speed": self.enemy_speed_var.get()
            },
            "economy": {
                "initial_gold": self.initial_gold_var.get(),
                "gold_generation_rate": self.gold_rate_var.get(),
                "kill_reward": self.kill_reward_var.get()
            },
            "base": {
                "initial_hp": self.base_hp_var.get(),
                "max_hp": self.base_max_hp_var.get()
            },
            "waves": self.waves_data,
            "boss": None,
            "victory_conditions": list(self.victory_listbox.get(0, tk.END)),
            "defeat_conditions": list(self.defeat_listbox.get(0, tk.END)),
            "rewards": {
                "gold": self.reward_gold_var.get(),
                "exp": self.reward_exp_var.get(),
                "unlock_levels": list(self.unlock_listbox.get(0, tk.END))
            },
            "performance_config": {
                "wave_particle_limit": self.wave_particle_var.get(),
                "boss_fight_particle_limit": self.boss_particle_var.get(),
                "low_end_disable_effects": list(self.disable_effects_listbox.get(0, tk.END)),
                "dynamic_quality_adjust": self.dynamic_quality_var.get()
            }
        }

        # Boss配置
        if self.boss_enable_var.get():
            boss_char_str = self.boss_char_combo.get()
            match = re.search(r'\((.+?)\)$', boss_char_str)
            if match:
                level_data["boss"] = {
                    "character": match.group(1),
                    "trigger_time": self.boss_time_var.get(),
                    "health_multiplier": self.boss_health_mult_var.get(),
                    "attack_multiplier": self.boss_attack_mult_var.get(),
                    "speed_multiplier": self.boss_speed_mult_var.get(),
                    "skin_override": self.boss_skin_var.get() or None,
                    "model_scale": self.boss_scale_var.get(),
                    "special_skills": list(self.boss_skills_listbox.get(0, tk.END))
                }

        # 保存文件
        is_new = (self.current_level != level_id or self.current_campaign != campaign_id)

        level_file = self.root_dir / "campaigns" / campaign_id / "levels" / f"{level_id}.yaml"
        level_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(level_file, 'w', encoding='utf-8') as f:
                yaml.dump(level_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

            logger.info(f"{'新增' if is_new else '更新'}关卡: {campaign_id}/{level_id}")
            messagebox.showinfo("成功", f"关卡已{'新增' if is_new else '更新'}")

            self.current_level = level_id
            self.current_campaign = campaign_id

            self._load_level_list()

        except Exception as e:
            logger.error(f"保存关卡失败: {e}")
            messagebox.showerror("错误", f"保存关卡失败:\n{e}")

    def _browse_file(self, var, file_type):
        """浏览文件"""
        filetypes = {
            "image": [("图片文件", "*.png *.jpg *.jpeg")],
            "json": [("JSON文件", "*.json")]
        }

        filename = filedialog.askopenfilename(
            title=f"选择{file_type}文件",
            filetypes=filetypes.get(file_type, [("所有文件", "*.*")])
        )

        if filename:
            # 转换为相对路径
            try:
                rel_path = Path(filename).relative_to(self.root_dir)
                var.set(str(rel_path).replace("\\", "/"))
            except ValueError:
                var.set(filename.replace("\\", "/"))

    # === 波次管理方法 ===

    def _refresh_wave_list(self):
        """刷新波次列表"""
        self.wave_listbox.delete(0, tk.END)
        for i, wave in enumerate(self.waves_data):
            wave_id = wave.get("wave_id", f"wave_{i+1}")
            wave_time = wave.get("time", 0)
            enemy_count = len(wave.get("enemies", []))
            self.wave_listbox.insert(tk.END, f"{wave_id} (t={wave_time}s, {enemy_count}敌人)")

    def _add_wave(self):
        """新增波次"""
        wave_id = f"wave_{len(self.waves_data) + 1}"
        new_wave = {
            "wave_id": wave_id,
            "time": 10.0,
            "enemies": []
        }
        self.waves_data.append(new_wave)
        self._refresh_wave_list()

        # 选中新波次
        self.wave_listbox.selection_clear(0, tk.END)
        self.wave_listbox.selection_set(tk.END)
        self._on_wave_selected(None)

    def _delete_wave(self):
        """删除波次"""
        selection = self.wave_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的波次")
            return

        idx = selection[0]
        del self.waves_data[idx]
        self._refresh_wave_list()
        self.current_wave_index = -1
        self._clear_wave_editor()

    def _move_wave(self, direction):
        """移动波次顺序"""
        selection = self.wave_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要移动的波次")
            return

        idx = selection[0]
        new_idx = idx + direction

        if new_idx < 0 or new_idx >= len(self.waves_data):
            return

        self.waves_data[idx], self.waves_data[new_idx] = self.waves_data[new_idx], self.waves_data[idx]
        self._refresh_wave_list()

        self.wave_listbox.selection_clear(0, tk.END)
        self.wave_listbox.selection_set(new_idx)

    def _on_wave_selected(self, event):
        """选中波次时加载数据"""
        selection = self.wave_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        self.current_wave_index = idx
        wave = self.waves_data[idx]

        self.wave_id_var.set(wave.get("wave_id", ""))
        self.wave_time_var.set(wave.get("time", 10.0))

        # 加载敌人列表
        self.enemy_listbox.delete(0, tk.END)
        for enemy in wave.get("enemies", []):
            char = enemy.get("character", "")
            count = enemy.get("count", 1)
            self.enemy_listbox.insert(tk.END, f"{char} x{count}")

    def _update_wave(self):
        """更新波次信息"""
        if self.current_wave_index < 0:
            messagebox.showwarning("警告", "请先选择波次")
            return

        wave = self.waves_data[self.current_wave_index]
        wave["wave_id"] = self.wave_id_var.get()
        wave["time"] = self.wave_time_var.get()

        self._refresh_wave_list()
        self.wave_listbox.selection_clear(0, tk.END)
        self.wave_listbox.selection_set(self.current_wave_index)

    def _clear_wave_editor(self):
        """清空波次编辑器"""
        self.wave_id_var.set("")
        self.wave_time_var.set(10.0)
        self.enemy_listbox.delete(0, tk.END)

    # === 敌人管理方法 ===

    def _add_enemy(self):
        """添加敌人"""
        if self.current_wave_index < 0:
            messagebox.showwarning("警告", "请先选择波次")
            return

        char_str = self.enemy_char_combo.get()
        match = re.search(r'\((.+?)\)$', char_str)
        if not match:
            messagebox.showwarning("警告", "请选择角色")
            return

        char_id = match.group(1)

        enemy = {
            "character": char_id,
            "count": self.enemy_count_var.get(),
            "interval": self.enemy_interval_var.get(),
            "health_multiplier": self.enemy_health_mult_var.get(),
            "model_scale": self.enemy_scale_var.get()
        }

        # 可选字段
        if self.enemy_skin_var.get():
            enemy["skin_override"] = self.enemy_skin_var.get()

        if self.enemy_anim_speed_var.get() != 1.0:
            enemy["animation_speed"] = self.enemy_anim_speed_var.get()

        wave = self.waves_data[self.current_wave_index]
        if "enemies" not in wave:
            wave["enemies"] = []

        wave["enemies"].append(enemy)

        self.enemy_listbox.insert(tk.END, f"{char_id} x{enemy['count']}")
        self._refresh_wave_list()

    def _update_enemy(self):
        """更新敌人"""
        if self.current_wave_index < 0:
            messagebox.showwarning("警告", "请先选择波次")
            return

        selection = self.enemy_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择敌人")
            return

        enemy_idx = selection[0]

        char_str = self.enemy_char_combo.get()
        match = re.search(r'\((.+?)\)$', char_str)
        if not match:
            messagebox.showwarning("警告", "请选择角色")
            return

        char_id = match.group(1)

        wave = self.waves_data[self.current_wave_index]
        enemy = wave["enemies"][enemy_idx]

        enemy["character"] = char_id
        enemy["count"] = self.enemy_count_var.get()
        enemy["interval"] = self.enemy_interval_var.get()
        enemy["health_multiplier"] = self.enemy_health_mult_var.get()
        enemy["model_scale"] = self.enemy_scale_var.get()

        if self.enemy_skin_var.get():
            enemy["skin_override"] = self.enemy_skin_var.get()
        else:
            enemy.pop("skin_override", None)

        if self.enemy_anim_speed_var.get() != 1.0:
            enemy["animation_speed"] = self.enemy_anim_speed_var.get()
        else:
            enemy.pop("animation_speed", None)

        self.enemy_listbox.delete(enemy_idx)
        self.enemy_listbox.insert(enemy_idx, f"{char_id} x{enemy['count']}")
        self._refresh_wave_list()

    def _delete_enemy(self):
        """删除敌人"""
        if self.current_wave_index < 0:
            messagebox.showwarning("警告", "请先选择波次")
            return

        selection = self.enemy_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择敌人")
            return

        enemy_idx = selection[0]
        wave = self.waves_data[self.current_wave_index]
        del wave["enemies"][enemy_idx]

        self.enemy_listbox.delete(enemy_idx)
        self._refresh_wave_list()

    def _on_enemy_selected(self, event):
        """选中敌人时加载数据"""
        if self.current_wave_index < 0:
            return

        selection = self.enemy_listbox.curselection()
        if not selection:
            return

        enemy_idx = selection[0]
        wave = self.waves_data[self.current_wave_index]
        enemy = wave["enemies"][enemy_idx]

        # 设置角色
        char_id = enemy.get("character", "")
        for idx, val in enumerate(self.enemy_char_combo['values']):
            if val.endswith(f"({char_id})"):
                self.enemy_char_combo.current(idx)
                break

        self.enemy_count_var.set(enemy.get("count", 1))
        self.enemy_interval_var.set(enemy.get("interval", 2.0))
        self.enemy_health_mult_var.set(enemy.get("health_multiplier", 1.0))
        self.enemy_skin_var.set(enemy.get("skin_override", ""))
        self.enemy_scale_var.set(enemy.get("model_scale", 1.0))
        self.enemy_anim_speed_var.set(enemy.get("animation_speed", 1.0))

    # === Boss管理方法 ===

    def _toggle_boss(self):
        """切换Boss启用状态"""
        enabled = self.boss_enable_var.get()
        state = tk.NORMAL if enabled else tk.DISABLED

        self.boss_char_combo.config(state="readonly" if enabled else tk.DISABLED)

        # 找到所有Boss配置控件并设置状态
        for child in self.boss_tab.winfo_children():
            if isinstance(child, tk.Canvas):
                scrollable_frame = child.winfo_children()[0]  # 获取 scrollable_frame
                for widget in scrollable_frame.winfo_children():
                    if isinstance(widget, (ttk.Spinbox, ttk.Entry, tk.Listbox)):
                        widget.config(state=state)

    def _add_boss_skill(self):
        """添加Boss技能"""
        skill = self.boss_skill_var.get().strip()
        if skill and skill not in self.boss_skills_listbox.get(0, tk.END):
            self.boss_skills_listbox.insert(tk.END, skill)
            self.boss_skill_var.set("")

    def _delete_boss_skill(self):
        """删除Boss技能"""
        selection = self.boss_skills_listbox.curselection()
        if selection:
            self.boss_skills_listbox.delete(selection[0])

    # === 条件与奖励方法 ===

    def _add_condition(self, cond_type):
        """添加条件"""
        if cond_type == "victory":
            cond = self.victory_cond_var.get().strip()
            if cond and cond not in self.victory_listbox.get(0, tk.END):
                self.victory_listbox.insert(tk.END, cond)
                self.victory_cond_var.set("")
        else:
            cond = self.defeat_cond_var.get().strip()
            if cond and cond not in self.defeat_listbox.get(0, tk.END):
                self.defeat_listbox.insert(tk.END, cond)
                self.defeat_cond_var.set("")

    def _delete_condition(self, cond_type):
        """删除条件"""
        if cond_type == "victory":
            selection = self.victory_listbox.curselection()
            if selection:
                self.victory_listbox.delete(selection[0])
        else:
            selection = self.defeat_listbox.curselection()
            if selection:
                self.defeat_listbox.delete(selection[0])

    def _add_unlock_level(self):
        """添加解锁关卡"""
        level = self.unlock_level_var.get().strip()
        if level and level not in self.unlock_listbox.get(0, tk.END):
            self.unlock_listbox.insert(tk.END, level)
            self.unlock_level_var.set("")

    def _delete_unlock_level(self):
        """删除解锁关卡"""
        selection = self.unlock_listbox.curselection()
        if selection:
            self.unlock_listbox.delete(selection[0])

    # === 性能配置方法 ===

    def _add_disable_effect(self):
        """添加禁用特效"""
        effect = self.disable_effect_var.get().strip()
        if effect and effect not in self.disable_effects_listbox.get(0, tk.END):
            self.disable_effects_listbox.insert(tk.END, effect)
            self.disable_effect_var.set("")

    def _delete_disable_effect(self):
        """删除禁用特效"""
        selection = self.disable_effects_listbox.curselection()
        if selection:
            self.disable_effects_listbox.delete(selection[0])
