"""
Boss管理器 - Boss的完整CRUD操作
支持创建、编辑、删除Boss，配置阶段、技能、特殊机制、奖励
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import logging
from pathlib import Path
from typing import Dict, Optional, List
import yaml

logger = logging.getLogger(__name__)


class BossManager:
    """
    Boss管理器
    功能：
    1. 新增Boss（创建Boss配置文件）
    2. 编辑Boss（修改所有属性）
    3. 删除Boss（移动到回收站）
    4. 配置多阶段系统
    5. 管理特殊机制
    6. 配置奖励
    """

    def __init__(self, parent: tk.Frame, config_loader, admin_manager):
        """
        初始化Boss管理器

        参数:
            parent: 父容器
            config_loader: ConfigLoader实例
            admin_manager: AdminManager实例
        """
        self.parent = parent
        self.config_loader = config_loader
        self.admin_manager = admin_manager
        self.root_dir = Path(config_loader.root_dir)

        # 当前编辑的Boss（None表示新建）
        self.current_boss_id: Optional[str] = None
        self.current_game_id: Optional[str] = None

        # 阶段和机制数据
        self.phases_data: List[Dict] = []
        self.mechanics_data: List[Dict] = []

        # 创建UI
        self._create_ui()

        logger.info("Boss管理器初始化完成")

    def _create_ui(self):
        """创建UI组件"""
        # 标题
        title_frame = tk.Frame(self.parent, bg="#f0f0f0")
        title_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(
            title_frame,
            text="Boss管理",
            font=('Arial', 18, 'bold'),
            bg="#f0f0f0"
        ).pack(side=tk.LEFT)

        # 工具栏
        toolbar = tk.Frame(self.parent, bg="#f0f0f0")
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(toolbar, text="新增Boss", command=self._new_boss, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="刷新列表", command=self._refresh_list, width=12).pack(side=tk.LEFT, padx=5)

        # 主容器：左侧列表 + 右侧编辑器
        main_container = tk.Frame(self.parent)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧：Boss列表
        list_frame = ttk.LabelFrame(main_container, text="已有Boss", padding=10)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        # 列表框和滚动条
        list_scroll = ttk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.boss_listbox = tk.Listbox(
            list_frame,
            width=35,
            yscrollcommand=list_scroll.set
        )
        self.boss_listbox.pack(fill=tk.BOTH, expand=True)
        list_scroll.config(command=self.boss_listbox.yview)

        # 绑定选择事件
        self.boss_listbox.bind('<<ListboxSelect>>', self._on_select_boss)

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

        # 页面3: 阶段管理
        self.page_phases = self._create_phases_page()
        self.notebook.add(self.page_phases, text="阶段管理")

        # 页面4: 特殊机制
        self.page_mechanics = self._create_mechanics_page()
        self.notebook.add(self.page_mechanics, text="特殊机制")

        # 页面5: 奖励配置
        self.page_rewards = self._create_rewards_page()
        self.notebook.add(self.page_rewards, text="奖励配置")

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

        # Boss ID
        tk.Label(content, text="Boss ID *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.boss_id_var = tk.StringVar()
        self.boss_id_entry = tk.Entry(content, textvariable=self.boss_id_var, width=40)
        self.boss_id_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            content,
            text="(英文字母、数字、下划线)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # Boss名称
        tk.Label(content, text="Boss名称 *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.boss_name_var = tk.StringVar()
        tk.Entry(content, textvariable=self.boss_name_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # Boss类型
        tk.Label(content, text="Boss类型:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.boss_type_var = tk.StringVar(value="boss")
        tk.Entry(content, textvariable=self.boss_type_var, width=40, state="readonly").grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # Boss描述
        tk.Label(content, text="Boss描述:", bg="white", anchor=tk.NW).grid(
            row=row, column=0, sticky=tk.NW, padx=5, pady=5
        )
        self.boss_desc_text = tk.Text(content, width=40, height=4)
        self.boss_desc_text.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 攻击类型
        tk.Label(content, text="攻击类型:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.attack_type_var = tk.StringVar(value="ranged")
        attack_type_combo = ttk.Combobox(
            content,
            textvariable=self.attack_type_var,
            values=["melee", "ranged"],
            state="readonly",
            width=37
        )
        attack_type_combo.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 按钮区域
        btn_frame = tk.Frame(content, bg="white")
        btn_frame.grid(row=row, column=0, columnspan=3, pady=20)

        tk.Button(btn_frame, text="保存Boss", command=self._save_boss, width=15, bg="#4CAF50", fg="white").pack(
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
            ("生命值 (HP):", "hp", 5000, 1000, 50000),
            ("攻击力 (Attack):", "attack", 100, 10, 1000),
            ("攻击范围 (Range):", "attack_range", 200, 0, 1000),
            ("攻击速度 (Attack Speed):", "attack_speed", 0.8, 0.1, 5.0),
            ("移动速度 (Speed):", "speed", 20, 0, 100),
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
                    increment=0.1 if max_val <= 10 else 10,
                    textvariable=var,
                    width=38
                )
            else:
                var = tk.IntVar(value=default)
                spinbox = tk.Spinbox(
                    content,
                    from_=min_val,
                    to=max_val,
                    increment=100 if max_val > 1000 else 10,
                    textvariable=var,
                    width=38
                )

            spinbox.grid(row=idx, column=1, sticky=tk.W, padx=5, pady=5)
            self.stats_vars[key] = var

        return page

    def _create_phases_page(self):
        """创建阶段管理页面"""
        page = tk.Frame(self.notebook, bg="white", padx=10, pady=10)

        # 顶部说明
        tk.Label(
            page,
            text="Boss阶段配置 - Boss会根据血量百分比自动切换阶段",
            font=('Arial', 10),
            bg="white",
            fg="gray"
        ).pack(pady=5)

        # 工具栏
        toolbar = tk.Frame(page, bg="white")
        toolbar.pack(fill=tk.X, pady=5)

        tk.Button(toolbar, text="添加阶段", command=self._add_phase, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="编辑阶段", command=self._edit_phase, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="删除阶段", command=self._remove_phase, width=12).pack(side=tk.LEFT, padx=5)

        # 阶段列表
        list_frame = tk.Frame(page, bg="white")
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.phases_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=12
        )
        self.phases_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.phases_listbox.yview)

        # 双击编辑
        self.phases_listbox.bind('<Double-Button-1>', lambda e: self._edit_phase())

        return page

    def _create_mechanics_page(self):
        """创建特殊机制页面"""
        page = tk.Frame(self.notebook, bg="white", padx=10, pady=10)

        # 顶部说明
        tk.Label(
            page,
            text="特殊机制 - 免疫、狂暴等特殊能力",
            font=('Arial', 10),
            bg="white",
            fg="gray"
        ).pack(pady=5)

        # 工具栏
        toolbar = tk.Frame(page, bg="white")
        toolbar.pack(fill=tk.X, pady=5)

        tk.Button(toolbar, text="添加机制", command=self._add_mechanic, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="删除机制", command=self._remove_mechanic, width=12).pack(side=tk.LEFT, padx=5)

        # 机制列表
        list_frame = tk.Frame(page, bg="white")
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.mechanics_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=12
        )
        self.mechanics_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.mechanics_listbox.yview)

        return page

    def _create_rewards_page(self):
        """创建奖励配置页面"""
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

        # 标题
        tk.Label(
            content,
            text="击败Boss的奖励",
            font=('Arial', 12, 'bold'),
            bg="white"
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, padx=5, pady=10)
        row += 1

        # 金币奖励
        tk.Label(content, text="金币奖励:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.reward_gold_var = tk.IntVar(value=500)
        tk.Spinbox(content, from_=0, to=10000, increment=50, textvariable=self.reward_gold_var, width=38).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 经验奖励
        tk.Label(content, text="经验奖励:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.reward_exp_var = tk.IntVar(value=1000)
        tk.Spinbox(content, from_=0, to=50000, increment=100, textvariable=self.reward_exp_var, width=38).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 物品掉落（简化版）
        tk.Label(content, text="掉落物品ID:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.reward_items_var = tk.StringVar(value="")
        tk.Entry(content, textvariable=self.reward_items_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        tk.Label(
            content,
            text="(逗号分隔，如: item1,item2)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)

        return page

    def _refresh_list(self):
        """刷新Boss列表"""
        try:
            # 触发配置重新扫描
            self.config_loader.scan_all()

            # 清空列表
            self.boss_listbox.delete(0, tk.END)

            # 更新游戏IP下拉列表
            games = list(self.config_loader.games.keys())
            self.game_combo['values'] = games

            # 加载Boss
            bosses = self.config_loader.bosses
            for boss_id, boss_data in bosses.items():
                boss_name = boss_data.get("name", boss_id)
                game_id = boss_data.get("game_id", "unknown")
                game_name = self.config_loader.games.get(game_id, {}).get("name", game_id)
                self.boss_listbox.insert(tk.END, f"{boss_name} ({boss_id}) - {game_name}")

            logger.info(f"Boss列表已刷新: {len(bosses)}个Boss")

        except Exception as e:
            logger.error(f"刷新Boss列表失败: {e}")
            messagebox.showerror("错误", f"刷新列表失败:\n{e}")

    def _on_select_boss(self, event):
        """选择Boss时触发"""
        selection = self.boss_listbox.curselection()
        if not selection:
            return

        # 从列表文本中提取boss_id
        text = self.boss_listbox.get(selection[0])
        import re
        match = re.search(r'\(([^)]+)\)', text)
        if match:
            boss_id = match.group(1)
            self._load_boss(boss_id)

    def _new_boss(self):
        """新增Boss"""
        self.current_boss_id = None
        self.current_game_id = None
        self._clear_editor()
        self.boss_id_entry.config(state=tk.NORMAL)
        logger.info("准备新增Boss")

    def _edit_selected(self):
        """编辑选中的Boss"""
        selection = self.boss_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要编辑的Boss")
            return

        self._on_select_boss(None)

    def _delete_selected(self):
        """删除选中的Boss"""
        selection = self.boss_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的Boss")
            return

        # 从列表文本中提取boss_id
        text = self.boss_listbox.get(selection[0])
        import re
        match = re.search(r'\(([^)]+)\)', text)
        if not match:
            return

        boss_id = match.group(1)
        boss_data = self.config_loader.bosses.get(boss_id, {})
        boss_name = boss_data.get("name", boss_id)
        game_id = boss_data.get("game_id")

        # 确认删除
        if not messagebox.askyesno(
            "确认删除",
            f"确定要删除Boss '{boss_name}' 吗？\n\n"
            f"删除的内容将移动到回收站，可以恢复。"
        ):
            return

        try:
            # 删除Boss文件
            boss_file = self.root_dir / "games" / game_id / "bosses" / f"{boss_id}.yaml"
            if boss_file.exists():
                self.admin_manager.delete_config(str(boss_file))
                logger.info(f"Boss已删除: {boss_id}")
                messagebox.showinfo("成功", f"Boss '{boss_name}' 已删除并移动到回收站")

                # 刷新列表
                self._refresh_list()
                self._clear_editor()
            else:
                messagebox.showerror("错误", f"Boss文件不存在: {boss_file}")

        except Exception as e:
            logger.error(f"删除Boss失败: {e}")
            messagebox.showerror("错误", f"删除失败:\n{e}")

    def _load_boss(self, boss_id: str):
        """加载Boss数据到编辑器"""
        try:
            boss_data = self.config_loader.bosses.get(boss_id)
            if not boss_data:
                messagebox.showerror("错误", f"Boss不存在: {boss_id}")
                return

            self.current_boss_id = boss_id
            self.current_game_id = boss_data.get("game_id")

            # 填充基础信息
            self.game_id_var.set(self.current_game_id)
            self.boss_id_var.set(boss_id)
            self.boss_id_entry.config(state=tk.DISABLED)
            self.boss_name_var.set(boss_data.get("name", ""))
            self.boss_type_var.set(boss_data.get("type", "boss"))

            desc = boss_data.get("description", "")
            self.boss_desc_text.delete("1.0", tk.END)
            self.boss_desc_text.insert("1.0", desc)

            attack_type = boss_data.get("attack_type", "ranged")
            self.attack_type_var.set(attack_type)

            # 填充属性
            stats = boss_data.get("stats", {})
            for key, var in self.stats_vars.items():
                var.set(stats.get(key, var.get()))

            # 填充阶段列表
            self.phases_listbox.delete(0, tk.END)
            self.phases_data = boss_data.get("phases", [])
            for i, phase in enumerate(self.phases_data):
                hp_threshold = phase.get('hp_threshold', 1.0)
                hp_min = phase.get('hp_min', 0.0)
                self.phases_listbox.insert(tk.END, f"阶段{i+1}: {hp_min*100:.0f}%-{hp_threshold*100:.0f}%")

            # 填充特殊机制列表
            self.mechanics_listbox.delete(0, tk.END)
            self.mechanics_data = boss_data.get("special_mechanics", [])
            for mechanic in self.mechanics_data:
                mech_type = mechanic.get('type', 'unknown')
                self.mechanics_listbox.insert(tk.END, f"机制: {mech_type}")

            # 填充奖励
            rewards = boss_data.get("rewards", {})
            self.reward_gold_var.set(rewards.get('gold', 500))
            self.reward_exp_var.set(rewards.get('experience', 1000))

            logger.info(f"已加载Boss: {boss_id}")

        except Exception as e:
            logger.error(f"加载Boss失败: {e}")
            messagebox.showerror("错误", f"加载失败:\n{e}")

    def _clear_editor(self):
        """清空编辑器"""
        self.current_boss_id = None
        self.current_game_id = None

        # 清空基础信息
        self.game_id_var.set("")
        self.boss_id_var.set("")
        self.boss_id_entry.config(state=tk.NORMAL)
        self.boss_name_var.set("")
        self.boss_type_var.set("boss")
        self.boss_desc_text.delete("1.0", tk.END)
        self.attack_type_var.set("ranged")

        # 清空属性
        defaults = {
            "hp": 5000, "attack": 100, "attack_range": 200,
            "attack_speed": 0.8, "speed": 20
        }
        for key, var in self.stats_vars.items():
            var.set(defaults.get(key, 0))

        # 清空阶段和机制
        self.phases_listbox.delete(0, tk.END)
        self.mechanics_listbox.delete(0, tk.END)
        self.phases_data = []
        self.mechanics_data = []

        # 清空奖励
        self.reward_gold_var.set(500)
        self.reward_exp_var.set(1000)
        self.reward_items_var.set("")

    def _add_phase(self):
        """添加阶段"""
        dialog = PhaseEditDialog(self.parent, None, len(self.phases_data) + 1)
        if dialog.result:
            self.phases_data.append(dialog.result)
            phase = dialog.result
            hp_threshold = phase.get('hp_threshold', 1.0)
            hp_min = phase.get('hp_min', 0.0)
            self.phases_listbox.insert(tk.END, f"阶段{len(self.phases_data)}: {hp_min*100:.0f}%-{hp_threshold*100:.0f}%")

    def _edit_phase(self):
        """编辑阶段"""
        selection = self.phases_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要编辑的阶段")
            return

        index = selection[0]
        phase_data = self.phases_data[index]
        dialog = PhaseEditDialog(self.parent, phase_data, index + 1)

        if dialog.result:
            self.phases_data[index] = dialog.result
            phase = dialog.result
            hp_threshold = phase.get('hp_threshold', 1.0)
            hp_min = phase.get('hp_min', 0.0)
            self.phases_listbox.delete(index)
            self.phases_listbox.insert(index, f"阶段{index+1}: {hp_min*100:.0f}%-{hp_threshold*100:.0f}%")

    def _remove_phase(self):
        """删除阶段"""
        selection = self.phases_listbox.curselection()
        if selection:
            index = selection[0]
            self.phases_data.pop(index)
            self.phases_listbox.delete(index)

    def _add_mechanic(self):
        """添加特殊机制"""
        dialog = MechanicEditDialog(self.parent, None)
        if dialog.result:
            self.mechanics_data.append(dialog.result)
            mech_type = dialog.result.get('type', 'unknown')
            self.mechanics_listbox.insert(tk.END, f"机制: {mech_type}")

    def _remove_mechanic(self):
        """删除特殊机制"""
        selection = self.mechanics_listbox.curselection()
        if selection:
            index = selection[0]
            self.mechanics_data.pop(index)
            self.mechanics_listbox.delete(index)

    def _save_boss(self):
        """保存Boss"""
        try:
            # 验证必填字段
            game_id = self.game_id_var.get().strip()
            boss_id = self.boss_id_var.get().strip()
            boss_name = self.boss_name_var.get().strip()

            if not game_id:
                messagebox.showwarning("验证失败", "请选择所属游戏IP")
                return

            if not boss_id:
                messagebox.showwarning("验证失败", "请输入Boss ID")
                return

            if not boss_name:
                messagebox.showwarning("验证失败", "请输入Boss名称")
                return

            # 验证Boss ID格式
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', boss_id):
                messagebox.showwarning(
                    "验证失败",
                    "Boss ID只能包含英文字母、数字和下划线"
                )
                return

            # 验证游戏IP是否存在
            if game_id not in self.config_loader.games:
                messagebox.showerror("错误", f"游戏IP '{game_id}' 不存在")
                return

            # 如果是新增，检查ID是否已存在
            is_new = self.current_boss_id is None
            if is_new and boss_id in self.config_loader.bosses:
                messagebox.showwarning("验证失败", f"Boss ID '{boss_id}' 已存在")
                return

            # 收集属性数据
            stats = {key: var.get() for key, var in self.stats_vars.items()}

            # 收集奖励数据
            rewards = {
                "gold": self.reward_gold_var.get(),
                "experience": self.reward_exp_var.get()
            }

            # 处理物品掉落
            items_str = self.reward_items_var.get().strip()
            if items_str:
                items = [
                    {"item_id": item.strip(), "drop_chance": 1.0}
                    for item in items_str.split(',') if item.strip()
                ]
                if items:
                    rewards['items'] = items

            # 构建配置数据
            boss_config = {
                "boss_id": boss_id,
                "game_id": game_id,
                "name": boss_name,
                "type": self.boss_type_var.get(),
                "description": self.boss_desc_text.get("1.0", tk.END).strip(),
                "stats": stats,
                "attack_type": self.attack_type_var.get(),
                "phases": self.phases_data,
                "special_mechanics": self.mechanics_data,
                "rewards": rewards,
                "skills": [],  # TODO: 技能配置
                "passive_traits": [],  # TODO: 被动特质配置
                "available_skins": ["basic"],
                "assets": {},
            }

            # 保存Boss配置文件
            boss_dir = self.root_dir / "games" / game_id / "bosses"
            boss_dir.mkdir(parents=True, exist_ok=True)

            boss_file = boss_dir / f"{boss_id}.yaml"
            with open(boss_file, 'w', encoding='utf-8') as f:
                yaml.dump(boss_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            logger.info(f"Boss配置已保存: {boss_file}")

            # 记录操作日志
            operation = "创建" if is_new else "更新"
            self.admin_manager.log_operation(f"{operation}Boss", f"{boss_name} ({boss_id})")

            messagebox.showinfo("成功", f"Boss '{boss_name}' 已{operation}成功！")

            # 刷新列表
            self._refresh_list()

            # 清空编辑器
            self._clear_editor()

        except Exception as e:
            logger.error(f"保存Boss失败: {e}")
            messagebox.showerror("错误", f"保存失败:\n{e}")


class PhaseEditDialog:
    """阶段编辑对话框"""

    def __init__(self, parent, phase_data: Optional[Dict], phase_number: int):
        self.result = None

        dialog = tk.Toplevel(parent)
        dialog.title(f"编辑阶段 {phase_number}")
        dialog.geometry("500x400")
        dialog.transient(parent)
        dialog.grab_set()

        # 阶段血量范围
        tk.Label(dialog, text=f"阶段 {phase_number} 配置", font=('Arial', 12, 'bold')).pack(pady=10)

        frame = tk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        row = 0

        # 血量上限
        tk.Label(frame, text="血量上限 (%):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        hp_threshold_var = tk.DoubleVar(value=phase_data.get('hp_threshold', 1.0)*100 if phase_data else 100.0)
        tk.Spinbox(frame, from_=0, to=100, increment=5, textvariable=hp_threshold_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 血量下限
        tk.Label(frame, text="血量下限 (%):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        hp_min_var = tk.DoubleVar(value=phase_data.get('hp_min', 0.7)*100 if phase_data else 70.0)
        tk.Spinbox(frame, from_=0, to=100, increment=5, textvariable=hp_min_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 伤害倍率
        tk.Label(frame, text="伤害倍率:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        damage_mult_var = tk.DoubleVar(value=phase_data.get('damage_multiplier', 1.0) if phase_data else 1.0)
        tk.Spinbox(frame, from_=0.1, to=5.0, increment=0.1, textvariable=damage_mult_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 防御倍率
        tk.Label(frame, text="防御倍率:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        defense_mult_var = tk.DoubleVar(value=phase_data.get('defense_multiplier', 1.0) if phase_data else 1.0)
        tk.Spinbox(frame, from_=0.1, to=5.0, increment=0.1, textvariable=defense_mult_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 速度倍率
        tk.Label(frame, text="速度倍率:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        speed_mult_var = tk.DoubleVar(value=phase_data.get('speed_multiplier', 1.0) if phase_data else 1.0)
        tk.Spinbox(frame, from_=0.1, to=5.0, increment=0.1, textvariable=speed_mult_var, width=20).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )

        # 按钮
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=20)

        def on_ok():
            self.result = {
                "phase": phase_number,
                "hp_threshold": hp_threshold_var.get() / 100,
                "hp_min": hp_min_var.get() / 100,
                "damage_multiplier": damage_mult_var.get(),
                "defense_multiplier": defense_mult_var.get(),
                "speed_multiplier": speed_mult_var.get(),
                "skills": phase_data.get('skills', []) if phase_data else [],
                "buffs": phase_data.get('buffs', []) if phase_data else [],
                "on_enter_effects": phase_data.get('on_enter_effects', []) if phase_data else []
            }
            dialog.destroy()

        tk.Button(btn_frame, text="确定", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)

        dialog.wait_window()


class MechanicEditDialog:
    """特殊机制编辑对话框"""

    def __init__(self, parent, mechanic_data: Optional[Dict]):
        self.result = None

        dialog = tk.Toplevel(parent)
        dialog.title("添加特殊机制")
        dialog.geometry("450x300")
        dialog.transient(parent)
        dialog.grab_set()

        frame = tk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 机制类型
        tk.Label(frame, text="机制类型:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        mech_type_var = tk.StringVar(value=mechanic_data.get('type', 'immunity') if mechanic_data else 'immunity')
        mech_combo = ttk.Combobox(
            frame,
            textvariable=mech_type_var,
            values=["immunity", "enrage", "shield", "flying"],
            state="readonly",
            width=30
        )
        mech_combo.grid(row=0, column=1, padx=5, pady=5)

        # 免疫列表（仅immunity类型）
        tk.Label(frame, text="免疫效果:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        tk.Label(frame, text="(逗号分隔)", font=('Arial', 8), fg="gray").grid(row=1, column=2, sticky=tk.W)

        immune_var = tk.StringVar(value=",".join(mechanic_data.get('immune_to', [])) if mechanic_data and mechanic_data.get('type') == 'immunity' else "stun,knockup")
        tk.Entry(frame, textvariable=immune_var, width=35).grid(row=1, column=1, padx=5, pady=5)

        # 狂暴时间（仅enrage类型）
        tk.Label(frame, text="狂暴时间(秒):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        enrage_time_var = tk.IntVar(value=mechanic_data.get('time', 180) if mechanic_data and mechanic_data.get('type') == 'enrage' else 180)
        tk.Spinbox(frame, from_=30, to=600, increment=30, textvariable=enrage_time_var, width=33).grid(
            row=2, column=1, padx=5, pady=5
        )

        # 狂暴伤害加成（仅enrage类型）
        tk.Label(frame, text="狂暴伤害倍率:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        enrage_dmg_var = tk.DoubleVar(value=mechanic_data.get('bonus_damage', 2.0) if mechanic_data and mechanic_data.get('type') == 'enrage' else 2.0)
        tk.Spinbox(frame, from_=1.0, to=10.0, increment=0.5, textvariable=enrage_dmg_var, width=33).grid(
            row=3, column=1, padx=5, pady=5
        )

        # 按钮
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=20)

        def on_ok():
            mech_type = mech_type_var.get()

            if mech_type == 'immunity':
                immune_list = [s.strip() for s in immune_var.get().split(',') if s.strip()]
                self.result = {
                    "type": "immunity",
                    "immune_to": immune_list
                }
            elif mech_type == 'enrage':
                self.result = {
                    "type": "enrage",
                    "time": enrage_time_var.get(),
                    "bonus_damage": enrage_dmg_var.get()
                }
            elif mech_type == 'shield':
                self.result = {
                    "type": "shield",
                    "initial_shield": 1000
                }
            elif mech_type == 'flying':
                self.result = {
                    "type": "flying",
                    "immune_to_ground_effects": True
                }

            dialog.destroy()

        tk.Button(btn_frame, text="确定", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)

        dialog.wait_window()


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    root = tk.Tk()
    root.title("Boss管理器测试")
    root.geometry("1200x800")

    from core.config_loader import ConfigLoader
    from core.admin_manager import AdminManager

    config_loader = ConfigLoader(".")
    config_loader.scan_all()
    admin_manager = AdminManager(".")

    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)

    manager = BossManager(frame, config_loader, admin_manager)

    root.mainloop()
