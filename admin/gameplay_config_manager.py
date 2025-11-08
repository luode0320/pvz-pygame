"""
游戏玩法配置管理器 - Phase 10
提供全局游戏配置的编辑功能（settings.yaml中的gameplay部分）
包含角色选择、战场网格、经济系统、战斗系统的配置编辑器
"""

import tkinter as tk
from tkinter import ttk, messagebox, Canvas
import yaml
from pathlib import Path
from typing import Dict, Any
from logger_config import logger


class GameplayConfigManager:
    """游戏玩法配置管理器"""

    def __init__(self, parent, config_loader, admin_manager):
        self.parent = parent
        self.config_loader = config_loader
        self.admin_manager = admin_manager
        self.root_dir = Path(__file__).parent.parent

        # 当前配置数据
        self.gameplay_config = {}

        # 配置变量
        self.char_sel_vars = {}
        self.battlefield_vars = {}
        self.economy_vars = {}
        self.battle_vars = {}

        # 创建主布局
        self._create_layout()

        # 加载配置
        self._load_config()

    def _create_layout(self):
        """创建主布局"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(toolbar, text="全局游戏配置 (settings.yaml - gameplay)", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="保存配置", command=self._save_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="重置为默认", command=self._reset_config).pack(side=tk.RIGHT, padx=5)

        # 分隔线
        ttk.Separator(self.parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # 说明
        info_frame = ttk.Frame(self.parent)
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(info_frame, text="💡 全局配置说明:", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(info_frame, text="• 这些配置是游戏的全局默认值，关卡可以选择继承或覆盖", foreground="gray", font=("Arial", 8)).pack(anchor=tk.W, padx=20)
        ttk.Label(info_frame, text="• 修改后会影响所有未覆盖此配置的关卡", foreground="gray", font=("Arial", 8)).pack(anchor=tk.W, padx=20)
        ttk.Label(info_frame, text="• 战场网格配置提供可视化预览", foreground="gray", font=("Arial", 8)).pack(anchor=tk.W, padx=20)

        # 多标签页
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 4个标签页
        self.char_sel_tab = ttk.Frame(self.notebook)
        self.battlefield_tab = ttk.Frame(self.notebook)
        self.economy_tab = ttk.Frame(self.notebook)
        self.battle_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.char_sel_tab, text="角色选择配置")
        self.notebook.add(self.battlefield_tab, text="战场网格配置")
        self.notebook.add(self.economy_tab, text="经济系统配置")
        self.notebook.add(self.battle_tab, text="战斗系统配置")

        self._create_char_sel_tab()
        self._create_battlefield_tab()
        self._create_economy_tab()
        self._create_battle_tab()

    def _create_char_sel_tab(self):
        """创建角色选择配置标签页"""
        # 滚动区域
        canvas = tk.Canvas(self.char_sel_tab)
        scrollbar = ttk.Scrollbar(self.char_sel_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 标题
        ttk.Label(scrollable_frame, text="角色选择限制", font=("Arial", 11, "bold")).pack(pady=20)

        # 配置框
        config_frame = ttk.LabelFrame(scrollable_frame, text="选择数量限制")
        config_frame.pack(fill=tk.X, padx=50, pady=10)

        row = 0

        # 最少角色数
        ttk.Label(config_frame, text="最少选择角色数:", width=20, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=20, pady=10)
        self.char_sel_vars['min_characters'] = tk.IntVar(value=1)
        ttk.Spinbox(config_frame, from_=0, to=10, textvariable=self.char_sel_vars['min_characters'], width=15).grid(row=row, column=1, padx=10, pady=10)
        ttk.Label(config_frame, text="个", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # 最多角色数
        ttk.Label(config_frame, text="最多选择角色数:", width=20, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=20, pady=10)
        self.char_sel_vars['max_characters'] = tk.IntVar(value=6)
        ttk.Spinbox(config_frame, from_=1, to=20, textvariable=self.char_sel_vars['max_characters'], width=15).grid(row=row, column=1, padx=10, pady=10)
        ttk.Label(config_frame, text="个", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        # 说明
        help_frame = ttk.LabelFrame(scrollable_frame, text="配置说明")
        help_frame.pack(fill=tk.X, padx=50, pady=10)

        help_text = """
        角色选择限制说明：

        • 最少选择角色数：玩家开始关卡前至少要选择的角色数量
        • 最多选择角色数：玩家最多可以选择的角色数量

        建议设置：
        • 简单关卡：min=1, max=6
        • 困难关卡：min=3, max=3（强制选择固定数量）
        • 挑战关卡：min=1, max=1（单角色挑战）

        注意：
        • 最少数量不能大于最多数量
        • 关卡可以覆盖这些全局默认值
        """

        ttk.Label(help_frame, text=help_text, justify=tk.LEFT, foreground="gray", font=("Arial", 8)).pack(padx=20, pady=10)

    def _create_battlefield_tab(self):
        """创建战场网格配置标签页"""
        # 左侧：配置
        left_frame = ttk.Frame(self.battlefield_tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(left_frame, text="战场网格配置", font=("Arial", 11, "bold")).pack(pady=10)

        # 配置框
        config_frame = ttk.LabelFrame(left_frame, text="网格参数")
        config_frame.pack(fill=tk.X, padx=20, pady=10)

        row = 0

        # 网格行数
        ttk.Label(config_frame, text="网格行数:", width=15, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.battlefield_vars['grid_rows'] = tk.IntVar(value=5)
        ttk.Spinbox(config_frame, from_=3, to=10, textvariable=self.battlefield_vars['grid_rows'], width=10,
                   command=self._update_battlefield_preview).grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(config_frame, text="行", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # 网格列数
        ttk.Label(config_frame, text="网格列数:", width=15, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.battlefield_vars['grid_cols'] = tk.IntVar(value=9)
        ttk.Spinbox(config_frame, from_=5, to=15, textvariable=self.battlefield_vars['grid_cols'], width=10,
                   command=self._update_battlefield_preview).grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(config_frame, text="列", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # 格子大小
        ttk.Label(config_frame, text="格子大小:", width=15, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.battlefield_vars['cell_size'] = tk.IntVar(value=80)
        ttk.Spinbox(config_frame, from_=50, to=150, increment=10, textvariable=self.battlefield_vars['cell_size'], width=10,
                   command=self._update_battlefield_preview).grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(config_frame, text="像素", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # 网格起始X
        ttk.Label(config_frame, text="网格起始X:", width=15, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.battlefield_vars['grid_start_x'] = tk.IntVar(value=100)
        ttk.Spinbox(config_frame, from_=0, to=500, increment=10, textvariable=self.battlefield_vars['grid_start_x'], width=10,
                   command=self._update_battlefield_preview).grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(config_frame, text="像素", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # 网格起始Y
        ttk.Label(config_frame, text="网格起始Y:", width=15, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=10, pady=5)
        self.battlefield_vars['grid_start_y'] = tk.IntVar(value=150)
        ttk.Spinbox(config_frame, from_=0, to=500, increment=10, textvariable=self.battlefield_vars['grid_start_y'], width=10,
                   command=self._update_battlefield_preview).grid(row=row, column=1, padx=5, pady=5)
        ttk.Label(config_frame, text="像素", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        # 说明
        help_frame = ttk.LabelFrame(left_frame, text="配置说明")
        help_frame.pack(fill=tk.X, padx=20, pady=10)

        help_text = """
        战场网格配置说明：

        • 网格行数：战场纵向格子数量（3-10）
        • 网格列数：战场横向格子数量（5-15）
        • 格子大小：每个格子的像素大小
        • 起始坐标：网格左上角在屏幕的位置

        建议设置：
        • 标准：5行x9列，格子80像素
        • 紧凑：3行x7列，格子90像素
        • 大型：7行x12列，格子70像素
        """

        ttk.Label(help_frame, text=help_text, justify=tk.LEFT, foreground="gray", font=("Arial", 8)).pack(padx=10, pady=10)

        # 右侧：可视化预览
        right_frame = ttk.Frame(self.battlefield_tab)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(right_frame, text="网格预览（缩放版）", font=("Arial", 11, "bold")).pack(pady=10)

        preview_frame = ttk.LabelFrame(right_frame, text="战场网格可视化")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Canvas预览
        self.battlefield_canvas = Canvas(preview_frame, width=400, height=300, bg='#2a2a3a', highlightthickness=0)
        self.battlefield_canvas.pack(padx=20, pady=20)

        self._update_battlefield_preview()

    def _create_economy_tab(self):
        """创建经济系统配置标签页"""
        # 滚动区域
        canvas = tk.Canvas(self.economy_tab)
        scrollbar = ttk.Scrollbar(self.economy_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 标题
        ttk.Label(scrollable_frame, text="经济系统配置", font=("Arial", 11, "bold")).pack(pady=20)

        # 配置框
        config_frame = ttk.LabelFrame(scrollable_frame, text="经济参数")
        config_frame.pack(fill=tk.X, padx=50, pady=10)

        row = 0

        # 默认初始金币
        ttk.Label(config_frame, text="默认初始金币:", width=20, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=20, pady=10)
        self.economy_vars['default_initial_gold'] = tk.IntVar(value=200)
        ttk.Spinbox(config_frame, from_=0, to=10000, increment=50, textvariable=self.economy_vars['default_initial_gold'], width=15).grid(row=row, column=1, padx=10, pady=10)
        ttk.Label(config_frame, text="金币", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # 默认金币生成速率
        ttk.Label(config_frame, text="默认金币生成速率:", width=20, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=20, pady=10)
        self.economy_vars['default_gold_generation_rate'] = tk.IntVar(value=25)
        ttk.Spinbox(config_frame, from_=0, to=200, increment=5, textvariable=self.economy_vars['default_gold_generation_rate'], width=15).grid(row=row, column=1, padx=10, pady=10)
        ttk.Label(config_frame, text="金币/秒", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # 默认击杀奖励
        ttk.Label(config_frame, text="默认击杀奖励:", width=20, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=20, pady=10)
        self.economy_vars['default_kill_reward'] = tk.IntVar(value=25)
        ttk.Spinbox(config_frame, from_=0, to=500, increment=5, textvariable=self.economy_vars['default_kill_reward'], width=15).grid(row=row, column=1, padx=10, pady=10)
        ttk.Label(config_frame, text="金币/个", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        # 说明
        help_frame = ttk.LabelFrame(scrollable_frame, text="配置说明")
        help_frame.pack(fill=tk.X, padx=50, pady=10)

        help_text = """
        经济系统配置说明：

        • 默认初始金币：关卡开始时玩家拥有的金币数量
        • 默认金币生成速率：每秒自动生成的金币数量
        • 默认击杀奖励：击杀一个敌人获得的金币

        平衡建议：
        • 初始金币：150-300（足够购买1-2个角色）
        • 生成速率：20-30金币/秒（稳定收入）
        • 击杀奖励：20-30金币/个（鼓励击杀）

        难度调整：
        • 简单：初始300，生成30，击杀30
        • 普通：初始200，生成25，击杀25
        • 困难：初始150，生成20，击杀20

        注意：
        • 关卡可以覆盖这些默认值
        • 经济平衡影响游戏难度和节奏
        """

        ttk.Label(help_frame, text=help_text, justify=tk.LEFT, foreground="gray", font=("Arial", 8)).pack(padx=20, pady=10)

    def _create_battle_tab(self):
        """创建战斗系统配置标签页"""
        # 滚动区域
        canvas = tk.Canvas(self.battle_tab)
        scrollbar = ttk.Scrollbar(self.battle_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 标题
        ttk.Label(scrollable_frame, text="战斗系统配置", font=("Arial", 11, "bold")).pack(pady=20)

        # 配置框
        config_frame = ttk.LabelFrame(scrollable_frame, text="战斗参数")
        config_frame.pack(fill=tk.X, padx=50, pady=10)

        row = 0

        # 卡片冷却时间
        ttk.Label(config_frame, text="卡片冷却时间:", width=25, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=20, pady=10)
        self.battle_vars['card_cooldown'] = tk.DoubleVar(value=5.0)
        ttk.Spinbox(config_frame, from_=0.1, to=20.0, increment=0.5, textvariable=self.battle_vars['card_cooldown'], width=15).grid(row=row, column=1, padx=10, pady=10)
        ttk.Label(config_frame, text="秒", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # 敌人攻击间隔
        ttk.Label(config_frame, text="敌人攻击间隔:", width=25, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=20, pady=10)
        self.battle_vars['enemy_attack_interval'] = tk.DoubleVar(value=2.0)
        ttk.Spinbox(config_frame, from_=0.5, to=10.0, increment=0.5, textvariable=self.battle_vars['enemy_attack_interval'], width=15).grid(row=row, column=1, padx=10, pady=10)
        ttk.Label(config_frame, text="秒", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # 基地伤害倍数
        ttk.Label(config_frame, text="基地伤害倍数:", width=25, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=20, pady=10)
        self.battle_vars['base_damage_multiplier'] = tk.IntVar(value=10)
        ttk.Spinbox(config_frame, from_=1, to=50, textvariable=self.battle_vars['base_damage_multiplier'], width=15).grid(row=row, column=1, padx=10, pady=10)
        ttk.Label(config_frame, text="倍", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # 阻挡距离
        ttk.Label(config_frame, text="阻挡距离:", width=25, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=20, pady=10)
        self.battle_vars['block_distance'] = tk.IntVar(value=50)
        ttk.Spinbox(config_frame, from_=10, to=200, increment=10, textvariable=self.battle_vars['block_distance'], width=15).grid(row=row, column=1, padx=10, pady=10)
        ttk.Label(config_frame, text="像素", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        row += 1

        # 默认敌人速度
        ttk.Label(config_frame, text="默认敌人速度:", width=25, anchor=tk.W).grid(row=row, column=0, sticky=tk.W, padx=20, pady=10)
        self.battle_vars['default_enemy_speed'] = tk.IntVar(value=20)
        ttk.Spinbox(config_frame, from_=5, to=100, increment=5, textvariable=self.battle_vars['default_enemy_speed'], width=15).grid(row=row, column=1, padx=10, pady=10)
        ttk.Label(config_frame, text="像素/秒", foreground="gray").grid(row=row, column=2, sticky=tk.W, padx=5)

        # 说明
        help_frame = ttk.LabelFrame(scrollable_frame, text="配置说明")
        help_frame.pack(fill=tk.X, padx=50, pady=10)

        help_text = """
        战斗系统配置说明：

        • 卡片冷却时间：放置角色卡片后的冷却时间
        • 敌人攻击间隔：敌人攻击防守角色的间隔时间
        • 基地伤害倍数：敌人突破到基地时造成的伤害倍数
        • 阻挡距离：防守角色阻挡敌人的有效距离
        • 默认敌人速度：敌人在地图上的移动速度

        平衡建议：
        • 卡片冷却：3-5秒（控制部署速度）
        • 攻击间隔：1.5-2.5秒（战斗节奏）
        • 基地倍数：8-12倍（突破惩罚）
        • 阻挡距离：40-60像素（合理范围）
        • 敌人速度：15-25像素/秒（适中速度）

        难度调整：
        • 简单：冷却3秒，敌速15
        • 普通：冷却5秒，敌速20
        • 困难：冷却7秒，敌速30

        注意：
        • 这些是全局默认值
        • 关卡和波次可以覆盖敌人速度
        • 平衡影响游戏难度和策略深度
        """

        ttk.Label(help_frame, text=help_text, justify=tk.LEFT, foreground="gray", font=("Arial", 8)).pack(padx=20, pady=10)

    def _update_battlefield_preview(self):
        """更新战场网格预览"""
        # 清空canvas
        self.battlefield_canvas.delete("all")

        # 获取配置
        rows = self.battlefield_vars['grid_rows'].get()
        cols = self.battlefield_vars['grid_cols'].get()
        cell_size = self.battlefield_vars['cell_size'].get()

        # 缩放比例（适应canvas）
        canvas_width = 400
        canvas_height = 300
        scale_x = canvas_width / (cols * cell_size + 100)
        scale_y = canvas_height / (rows * cell_size + 100)
        scale = min(scale_x, scale_y, 1.0)  # 最大不超过1:1

        # 缩放后的参数
        scaled_cell = int(cell_size * scale)
        start_x = 50
        start_y = 50

        # 绘制网格
        for row in range(rows):
            for col in range(cols):
                x1 = start_x + col * scaled_cell
                y1 = start_y + row * scaled_cell
                x2 = x1 + scaled_cell
                y2 = y1 + scaled_cell

                # 交替颜色
                fill_color = '#3a4a3a' if (row + col) % 2 == 0 else '#4a5a4a'

                self.battlefield_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=fill_color,
                    outline='#5a6a5a',
                    width=1
                )

        # 绘制坐标标注
        grid_width = cols * scaled_cell
        grid_height = rows * scaled_cell

        # 标注尺寸
        self.battlefield_canvas.create_text(
            start_x + grid_width / 2, start_y - 20,
            text=f"{cols}列 x {rows}行 (格子:{cell_size}px)",
            fill='#aaaaaa',
            font=("Arial", 9)
        )

        # 标注缩放比例
        if scale < 1.0:
            self.battlefield_canvas.create_text(
                start_x + grid_width / 2, start_y + grid_height + 20,
                text=f"缩放: {int(scale*100)}%",
                fill='#888888',
                font=("Arial", 8)
            )

    def _load_config(self):
        """加载配置"""
        settings_file = self.root_dir / "settings.yaml"
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)
                self.gameplay_config = settings.get("gameplay", {})

            # 加载到变量
            # 角色选择
            char_sel = self.gameplay_config.get("character_selection", {})
            self.char_sel_vars['min_characters'].set(char_sel.get("min_characters", 1))
            self.char_sel_vars['max_characters'].set(char_sel.get("max_characters", 6))

            # 战场
            battlefield = self.gameplay_config.get("battlefield", {})
            self.battlefield_vars['grid_rows'].set(battlefield.get("grid_rows", 5))
            self.battlefield_vars['grid_cols'].set(battlefield.get("grid_cols", 9))
            self.battlefield_vars['cell_size'].set(battlefield.get("cell_size", 80))
            self.battlefield_vars['grid_start_x'].set(battlefield.get("grid_start_x", 100))
            self.battlefield_vars['grid_start_y'].set(battlefield.get("grid_start_y", 150))

            # 经济
            economy = self.gameplay_config.get("economy", {})
            self.economy_vars['default_initial_gold'].set(economy.get("default_initial_gold", 200))
            self.economy_vars['default_gold_generation_rate'].set(economy.get("default_gold_generation_rate", 25))
            self.economy_vars['default_kill_reward'].set(economy.get("default_kill_reward", 25))

            # 战斗
            battle = self.gameplay_config.get("battle_system", {})
            self.battle_vars['card_cooldown'].set(battle.get("card_cooldown", 5.0))
            self.battle_vars['enemy_attack_interval'].set(battle.get("enemy_attack_interval", 2.0))
            self.battle_vars['base_damage_multiplier'].set(battle.get("base_damage_multiplier", 10))
            self.battle_vars['block_distance'].set(battle.get("block_distance", 50))
            self.battle_vars['default_enemy_speed'].set(battle.get("default_enemy_speed", 20))

            # 更新预览
            self._update_battlefield_preview()

            logger.info("游戏玩法配置已加载")

        except Exception as e:
            logger.error(f"加载游戏玩法配置失败: {e}")
            messagebox.showerror("错误", f"加载游戏玩法配置失败:\n{e}")

    def _save_config(self):
        """保存配置"""
        # 验证
        if self.char_sel_vars['min_characters'].get() > self.char_sel_vars['max_characters'].get():
            messagebox.showwarning("警告", "最少角色数不能大于最多角色数")
            return

        # 收集配置
        gameplay_config = {
            "auto_save_interval": self.gameplay_config.get("auto_save_interval", 300),
            "difficulty": self.gameplay_config.get("difficulty", "normal"),
            "tutorial_enabled": self.gameplay_config.get("tutorial_enabled", True),
            "character_selection": {
                "min_characters": self.char_sel_vars['min_characters'].get(),
                "max_characters": self.char_sel_vars['max_characters'].get()
            },
            "battlefield": {
                "grid_rows": self.battlefield_vars['grid_rows'].get(),
                "grid_cols": self.battlefield_vars['grid_cols'].get(),
                "cell_size": self.battlefield_vars['cell_size'].get(),
                "grid_start_x": self.battlefield_vars['grid_start_x'].get(),
                "grid_start_y": self.battlefield_vars['grid_start_y'].get()
            },
            "economy": {
                "default_initial_gold": self.economy_vars['default_initial_gold'].get(),
                "default_gold_generation_rate": self.economy_vars['default_gold_generation_rate'].get(),
                "default_kill_reward": self.economy_vars['default_kill_reward'].get()
            },
            "battle_system": {
                "card_cooldown": self.battle_vars['card_cooldown'].get(),
                "enemy_attack_interval": self.battle_vars['enemy_attack_interval'].get(),
                "base_damage_multiplier": self.battle_vars['base_damage_multiplier'].get(),
                "block_distance": self.battle_vars['block_distance'].get(),
                "default_enemy_speed": self.battle_vars['default_enemy_speed'].get()
            }
        }

        # 保存到settings.yaml
        settings_file = self.root_dir / "settings.yaml"
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)

            settings["gameplay"] = gameplay_config

            with open(settings_file, 'w', encoding='utf-8') as f:
                yaml.dump(settings, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

            logger.info("游戏玩法配置已保存")
            messagebox.showinfo("成功", "游戏玩法配置已保存到 settings.yaml")

        except Exception as e:
            logger.error(f"保存游戏玩法配置失败: {e}")
            messagebox.showerror("错误", f"保存游戏玩法配置失败:\n{e}")

    def _reset_config(self):
        """重置配置"""
        if not messagebox.askyesno("确认", "确定要重置为默认配置吗？\n当前修改将丢失"):
            return

        # 重新加载
        self._load_config()
        messagebox.showinfo("成功", "已重置为默认配置")
