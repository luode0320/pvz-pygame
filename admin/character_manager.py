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

        # 页面3: 技能管理
        self.page_skills = self._create_skills_page()
        self.notebook.add(self.page_skills, text="技能管理")

        # 页面4: 资源配置
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
            self.config_loader.scan_configs()

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

            # 构建配置数据
            char_config = {
                "character_id": char_id,
                "game_id": game_id,
                "name": char_name,
                "type": self.char_type_var.get(),
                "cost": self.char_cost_var.get(),
                "description": self.char_desc_text.get("1.0", tk.END).strip(),
                "stats": stats,
                "skills": skills,
                "available_skins": ["basic"],
                "assets": assets,
            }

            # 保存角色配置文件
            char_file = self.root_dir / "games" / game_id / "characters" / f"{char_id}.yaml"
            with open(char_file, 'w', encoding='utf-8') as f:
                yaml.dump(char_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            logger.info(f"角色配置已保存: {char_file}")

            # 记录操作日志
            operation = "创建" if is_new else "更新"
            self.admin_manager.log_operation(f"{operation}角色: {char_name} ({char_id})")

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
