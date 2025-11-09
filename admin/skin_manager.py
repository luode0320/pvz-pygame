"""
皮肤管理器 - 皮肤的完整CRUD操作
支持创建、编辑、删除皮肤，配置解锁条件、属性加成、特效、资源
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from pathlib import Path
from typing import Dict, Optional, List
import yaml
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)


class SkinManager:
    """
    皮肤管理器
    功能：
    1. 新增皮肤（创建皮肤配置文件）
    2. 编辑皮肤（修改所有配置）
    3. 删除皮肤（移动到回收站）
    4. 配置解锁条件
    5. 配置属性加成
    6. 配置特效加成
    7. 上传皮肤资源
    """

    def __init__(self, parent: tk.Frame, config_loader, admin_manager):
        """
        初始化皮肤管理器

        参数:
            parent: 父容器
            config_loader: ConfigLoader实例
            admin_manager: AdminManager实例
        """
        self.parent = parent
        self.config_loader = config_loader
        self.admin_manager = admin_manager
        self.root_dir = Path(config_loader.root_dir)

        # 当前编辑的皮肤（None表示新建）
        self.current_skin_id: Optional[str] = None
        self.current_game_id: Optional[str] = None

        # 创建UI
        self._create_ui()

        logger.info("皮肤管理器初始化完成")

    def _create_ui(self):
        """创建UI组件"""
        # 标题
        title_frame = tk.Frame(self.parent, bg="#f0f0f0")
        title_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(
            title_frame,
            text="皮肤管理",
            font=('Arial', 18, 'bold'),
            bg="#f0f0f0"
        ).pack(side=tk.LEFT)

        # 工具栏
        toolbar = tk.Frame(self.parent, bg="#f0f0f0")
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(toolbar, text="新增皮肤", command=self._new_skin, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="刷新列表", command=self._refresh_list, width=12).pack(side=tk.LEFT, padx=5)

        # 主容器：左侧列表 + 右侧编辑器
        main_container = tk.Frame(self.parent)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧：皮肤列表
        list_frame = ttk.LabelFrame(main_container, text="已有皮肤", padding=10)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        # 列表框和滚动条
        list_scroll = ttk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.skin_listbox = tk.Listbox(
            list_frame,
            width=35,
            yscrollcommand=list_scroll.set
        )
        self.skin_listbox.pack(fill=tk.BOTH, expand=True)
        list_scroll.config(command=self.skin_listbox.yview)

        # 绑定选择事件
        self.skin_listbox.bind('<<ListboxSelect>>', self._on_select_skin)

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

        # 页面2: 解锁条件
        self.page_unlock = self._create_unlock_page()
        self.notebook.add(self.page_unlock, text="解锁条件")

        # 页面3: 属性加成
        self.page_stats = self._create_stats_page()
        self.notebook.add(self.page_stats, text="属性加成")

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
        self.game_combo.bind('<<ComboboxSelected>>', self._on_game_selected)
        row += 1

        # 所属角色
        tk.Label(content, text="所属角色 *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.character_id_var = tk.StringVar()
        self.character_combo = ttk.Combobox(
            content,
            textvariable=self.character_id_var,
            state="readonly",
            width=37
        )
        self.character_combo.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 皮肤ID
        tk.Label(content, text="皮肤ID *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.skin_id_var = tk.StringVar()
        self.skin_id_entry = tk.Entry(content, textvariable=self.skin_id_var, width=40)
        self.skin_id_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            content,
            text="(英文字母、数字、下划线)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 皮肤名称
        tk.Label(content, text="皮肤名称 *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.skin_name_var = tk.StringVar()
        tk.Entry(content, textvariable=self.skin_name_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 皮肤描述
        tk.Label(content, text="皮肤描述:", bg="white", anchor=tk.NW).grid(
            row=row, column=0, sticky=tk.NW, padx=5, pady=5
        )
        self.skin_desc_text = tk.Text(content, width=40, height=4)
        self.skin_desc_text.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 作者
        tk.Label(content, text="作者:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.skin_author_var = tk.StringVar()
        tk.Entry(content, textvariable=self.skin_author_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 版本
        tk.Label(content, text="版本:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.skin_version_var = tk.StringVar(value="1.0")
        tk.Entry(content, textvariable=self.skin_version_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 按钮区域
        btn_frame = tk.Frame(content, bg="white")
        btn_frame.grid(row=row, column=0, columnspan=3, pady=20)

        tk.Button(btn_frame, text="保存皮肤", command=self._save_skin, width=15, bg="#4CAF50", fg="white").pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="取消", command=self._clear_editor, width=15).pack(side=tk.LEFT, padx=5)

        return page

    def _create_unlock_page(self):
        """创建解锁条件页面"""
        page = tk.Frame(self.notebook, bg="white")

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

        # 解锁类型
        tk.Label(content, text="解锁类型:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.unlock_type_var = tk.StringVar(value="level")
        ttk.Combobox(
            content,
            textvariable=self.unlock_type_var,
            values=["level", "achievement", "purchase", "free"],
            state="readonly",
            width=37
        ).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            content,
            text="(level=等级 achievement=成就 purchase=购买 free=免费)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 解锁值
        tk.Label(content, text="解锁值:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.unlock_value_var = tk.IntVar(value=10)
        tk.Spinbox(content, from_=0, to=9999, textvariable=self.unlock_value_var, width=38).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        tk.Label(
            content,
            text="(level类型=需要等级，achievement类型=成就ID)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 购买价格
        tk.Label(content, text="购买价格:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.unlock_price_var = tk.IntVar(value=1000)
        tk.Spinbox(content, from_=0, to=999999, textvariable=self.unlock_price_var, width=38).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        tk.Label(
            content,
            text="(仅对purchase类型生效)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        return page

    def _create_stats_page(self):
        """创建属性加成页面"""
        page = tk.Frame(self.notebook, bg="white")

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

        # 提示信息
        tk.Label(
            content,
            text="注意: 属性加成将叠加到角色基础属性上",
            font=('Arial', 10, 'bold'),
            bg="white",
            fg="orange"
        ).grid(row=row, column=0, columnspan=2, pady=10)
        row += 1

        # 属性加成字段
        stat_fields = [
            ("生命值加成:", "hp", 0, -1000, 1000),
            ("攻击力加成:", "attack", 0, -500, 500),
            ("攻击速度加成:", "attack_speed", 0.0, -5.0, 5.0),
            ("移动速度加成:", "speed", 0, -100, 100),
            ("暴击率加成:", "crit_rate", 0.0, -0.5, 0.5),
            ("暴击伤害加成:", "crit_damage", 0.0, -2.0, 2.0),
        ]

        self.stat_bonus_vars = {}
        for label, key, default, min_val, max_val in stat_fields:
            tk.Label(content, text=label, bg="white", anchor=tk.W).grid(
                row=row, column=0, sticky=tk.W, padx=5, pady=5
            )

            if isinstance(default, float):
                var = tk.DoubleVar(value=default)
                spinbox = tk.Spinbox(
                    content,
                    from_=min_val,
                    to=max_val,
                    increment=0.1,
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

            spinbox.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
            self.stat_bonus_vars[key] = var
            row += 1

        return page

    def _create_assets_page(self):
        """创建资源配置页面"""
        page = tk.Frame(self.notebook, bg="white")

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
            ("皮肤Sprite:", "sprite", "图片"),
            ("皮肤图标:", "icon", "图片"),
            ("攻击音效:", "sound_attack", "音频"),
            ("技能音效:", "sound_skill", "音频"),
            ("死亡音效:", "sound_death", "音频"),
            ("模型文件:", "override_model", "模型"),
            ("材质文件:", "override_material", "材质"),
        ]

        self.assets_vars = {}
        for idx, (label, key, file_type) in enumerate(assets_fields):
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
                command=lambda v=var, ft=file_type: self._select_asset(v, ft),
                width=10
            ).pack(side=tk.LEFT)

            self.assets_vars[key] = var

        return page

    def _refresh_list(self):
        """刷新皮肤列表"""
        try:
            # 触发配置重新扫描
            self.config_loader.scan_all()

            # 清空列表
            self.skin_listbox.delete(0, tk.END)

            # 更新游戏IP下拉列表
            games = list(self.config_loader.games.keys())
            self.game_combo['values'] = games

            # 加载皮肤
            skins = self.config_loader.skins
            for skin_id, skin_data in skins.items():
                skin_name = skin_data.get("name", skin_id)
                char_id = skin_data.get("character_id", "unknown")
                char_name = self.config_loader.characters.get(char_id, {}).get("name", char_id)
                self.skin_listbox.insert(tk.END, f"{skin_name} ({skin_id}) - {char_name}")

            logger.info(f"皮肤列表已刷新: {len(skins)}个皮肤")

        except Exception as e:
            logger.error(f"刷新皮肤列表失败: {e}")
            messagebox.showerror("错误", f"刷新列表失败:\n{e}")

    def _on_game_selected(self, event):
        """游戏IP选择时更新角色列表"""
        game_id = self.game_id_var.get()
        if not game_id:
            return

        # 获取该游戏的所有角色
        characters = []
        for char_id, char_data in self.config_loader.characters.items():
            if char_data.get("game_id") == game_id:
                char_name = char_data.get("name", char_id)
                characters.append(f"{char_name} ({char_id})")

        self.character_combo['values'] = characters
        if characters:
            self.character_combo.current(0)

    def _on_select_skin(self, event):
        """选择皮肤时触发"""
        selection = self.skin_listbox.curselection()
        if not selection:
            return

        # 从列表文本中提取skin_id
        text = self.skin_listbox.get(selection[0])
        # 格式: "皮肤名称 (skin_id) - 角色名称"
        import re
        match = re.search(r'\(([^)]+)\)', text)
        if match:
            skin_id = match.group(1)
            self._load_skin(skin_id)

    def _new_skin(self):
        """新增皮肤"""
        self.current_skin_id = None
        self.current_game_id = None
        self._clear_editor()
        self.skin_id_entry.config(state=tk.NORMAL)
        logger.info("准备新增皮肤")

    def _edit_selected(self):
        """编辑选中的皮肤"""
        selection = self.skin_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要编辑的皮肤")
            return

        self._on_select_skin(None)

    def _delete_selected(self):
        """删除选中的皮肤"""
        selection = self.skin_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的皮肤")
            return

        # 从列表文本中提取skin_id
        text = self.skin_listbox.get(selection[0])
        import re
        match = re.search(r'\(([^)]+)\)', text)
        if not match:
            return

        skin_id = match.group(1)
        skin_data = self.config_loader.skins.get(skin_id, {})
        skin_name = skin_data.get("name", skin_id)
        game_id = skin_data.get("game_id")

        # 确认删除
        if not messagebox.askyesno(
            "确认删除",
            f"确定要删除皮肤 '{skin_name}' 吗？\n\n"
            f"删除的内容将移动到回收站，可以恢复。"
        ):
            return

        try:
            # 删除皮肤文件
            skin_file = self.root_dir / "games" / game_id / "skins" / f"{skin_id}.yaml"
            if skin_file.exists():
                self.admin_manager.delete_config(str(skin_file), "皮肤")
                logger.info(f"皮肤已删除: {skin_id}")
                messagebox.showinfo("成功", f"皮肤 '{skin_name}' 已删除并移动到回收站")

                # 刷新列表
                self._refresh_list()
                self._clear_editor()
            else:
                messagebox.showerror("错误", f"皮肤文件不存在: {skin_file}")

        except Exception as e:
            logger.error(f"删除皮肤失败: {e}")
            messagebox.showerror("错误", f"删除失败:\n{e}")

    def _load_skin(self, skin_id: str):
        """加载皮肤数据到编辑器"""
        try:
            skin_data = self.config_loader.skins.get(skin_id)
            if not skin_data:
                messagebox.showerror("错误", f"皮肤不存在: {skin_id}")
                return

            self.current_skin_id = skin_id
            self.current_game_id = skin_data.get("game_id")

            # 填充基础信息
            char_id = skin_data.get("character_id")
            char_data = self.config_loader.characters.get(char_id, {})
            game_id = char_data.get("game_id") or self.current_game_id

            self.game_id_var.set(game_id)
            self._on_game_selected(None)  # 更新角色列表

            char_name = char_data.get("name", char_id)
            self.character_id_var.set(f"{char_name} ({char_id})")

            self.skin_id_var.set(skin_id)
            self.skin_id_entry.config(state=tk.DISABLED)
            self.skin_name_var.set(skin_data.get("name", ""))

            desc = skin_data.get("description", "")
            self.skin_desc_text.delete("1.0", tk.END)
            self.skin_desc_text.insert("1.0", desc)

            self.skin_author_var.set(skin_data.get("author", ""))
            self.skin_version_var.set(skin_data.get("version", "1.0"))

            # 填充解锁条件
            unlock = skin_data.get("unlock_conditions", {})
            self.unlock_type_var.set(unlock.get("type", "level"))
            self.unlock_value_var.set(unlock.get("value", 10))
            self.unlock_price_var.set(unlock.get("price", 1000))

            # 填充属性加成
            stat_bonus = skin_data.get("stat_bonus", {})
            for key, var in self.stat_bonus_vars.items():
                var.set(stat_bonus.get(key, 0))

            # 填充资源
            assets = skin_data.get("assets", {})
            self.assets_vars["sprite"].set(assets.get("sprite", ""))
            self.assets_vars["icon"].set(assets.get("icon", ""))

            sounds = assets.get("sounds", {})
            self.assets_vars["sound_attack"].set(sounds.get("attack", ""))
            self.assets_vars["sound_skill"].set(sounds.get("skill", ""))
            self.assets_vars["sound_death"].set(sounds.get("death", ""))

            model_config = skin_data.get("model_config", {})
            self.assets_vars["override_model"].set(model_config.get("override_model", ""))

            material_config = skin_data.get("material_config", {})
            self.assets_vars["override_material"].set(material_config.get("override_material", ""))

            logger.info(f"已加载皮肤: {skin_id}")

        except Exception as e:
            logger.error(f"加载皮肤失败: {e}")
            messagebox.showerror("错误", f"加载失败:\n{e}")

    def _clear_editor(self):
        """清空编辑器"""
        self.current_skin_id = None
        self.current_game_id = None

        # 清空基础信息
        self.game_id_var.set("")
        self.character_id_var.set("")
        self.skin_id_var.set("")
        self.skin_id_entry.config(state=tk.NORMAL)
        self.skin_name_var.set("")
        self.skin_desc_text.delete("1.0", tk.END)
        self.skin_author_var.set("")
        self.skin_version_var.set("1.0")

        # 清空解锁条件
        self.unlock_type_var.set("level")
        self.unlock_value_var.set(10)
        self.unlock_price_var.set(1000)

        # 清空属性加成
        for var in self.stat_bonus_vars.values():
            var.set(0)

        # 清空资源
        for var in self.assets_vars.values():
            var.set("")

    def _select_asset(self, var: tk.StringVar, file_type: str):
        """选择资源文件"""
        if file_type == "图片":
            filetypes = [("图片文件", "*.png *.jpg *.jpeg"), ("所有文件", "*.*")]
        elif file_type == "音频":
            filetypes = [("音频文件", "*.wav *.ogg *.mp3"), ("所有文件", "*.*")]
        elif file_type == "模型":
            filetypes = [("模型文件", "*.glb *.fbx"), ("所有文件", "*.*")]
        elif file_type == "材质":
            filetypes = [("材质文件", "*.mat"), ("所有文件", "*.*")]
        else:
            filetypes = [("所有文件", "*.*")]

        file_path = filedialog.askopenfilename(
            title="选择资源文件",
            filetypes=filetypes
        )
        if file_path:
            var.set(file_path)

    def _save_skin(self):
        """保存皮肤"""
        try:
            # 验证必填字段
            game_id = self.game_id_var.get().strip()
            character_text = self.character_id_var.get().strip()
            skin_id = self.skin_id_var.get().strip()
            skin_name = self.skin_name_var.get().strip()

            if not game_id:
                messagebox.showwarning("验证失败", "请选择所属游戏IP")
                return

            if not character_text:
                messagebox.showwarning("验证失败", "请选择所属角色")
                return

            if not skin_id:
                messagebox.showwarning("验证失败", "请输入皮肤ID")
                return

            if not skin_name:
                messagebox.showwarning("验证失败", "请输入皮肤名称")
                return

            # 验证皮肤ID格式
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', skin_id):
                messagebox.showwarning(
                    "验证失败",
                    "皮肤ID只能包含英文字母、数字和下划线"
                )
                return

            # 从角色文本中提取character_id
            match = re.search(r'\(([^)]+)\)$', character_text)
            if not match:
                messagebox.showerror("错误", "无法解析角色ID")
                return
            character_id = match.group(1)

            # 验证角色是否存在
            if character_id not in self.config_loader.characters:
                messagebox.showerror("错误", f"角色 '{character_id}' 不存在")
                return

            # 如果是新增，检查ID是否已存在
            is_new = self.current_skin_id is None
            if is_new and skin_id in self.config_loader.skins:
                messagebox.showwarning("验证失败", f"皮肤ID '{skin_id}' 已存在")
                return

            # 创建皮肤目录
            skin_dir = self.root_dir / "games" / game_id / "skins"
            skin_dir.mkdir(parents=True, exist_ok=True)

            # 处理资源文件
            assets_data = {
                "sprite": "",
                "icon": "",
                "sounds": {}
            }

            # 处理图片资源
            for key in ["sprite", "icon"]:
                file_path = self.assets_vars[key].get().strip()
                if file_path and Path(file_path).exists():
                    filename = Path(file_path).name
                    dest_file = skin_dir / filename
                    shutil.copy2(file_path, dest_file)
                    assets_data[key] = f"games/{game_id}/skins/{filename}"
                    logger.info(f"资源已复制: {dest_file}")

            # 处理音效资源
            for sound_key in ["sound_attack", "sound_skill", "sound_death"]:
                file_path = self.assets_vars[sound_key].get().strip()
                if file_path and Path(file_path).exists():
                    filename = Path(file_path).name
                    dest_file = skin_dir / filename
                    shutil.copy2(file_path, dest_file)
                    assets_data["sounds"][sound_key.replace("sound_", "")] = f"games/{game_id}/skins/{filename}"
                    logger.info(f"音效已复制: {dest_file}")

            # 收集属性加成
            stat_bonus = {key: var.get() for key, var in self.stat_bonus_vars.items() if var.get() != 0}

            # 构建配置数据
            skin_config = {
                "skin_id": skin_id,
                "name": skin_name,
                "character_id": character_id,
                "game_id": game_id,
                "description": self.skin_desc_text.get("1.0", tk.END).strip(),
                "author": self.skin_author_var.get().strip(),
                "version": self.skin_version_var.get().strip(),
                "unlock_conditions": {
                    "type": self.unlock_type_var.get(),
                    "value": self.unlock_value_var.get(),
                    "price": self.unlock_price_var.get(),
                },
                "stat_bonus": stat_bonus,
                "assets": assets_data,
            }

            # 添加模型配置（如果有）
            override_model = self.assets_vars["override_model"].get().strip()
            if override_model:
                skin_config["model_config"] = {
                    "override_model": override_model
                }

            # 添加材质配置（如果有）
            override_material = self.assets_vars["override_material"].get().strip()
            if override_material:
                skin_config["material_config"] = {
                    "override_material": override_material
                }

            # 保存皮肤配置文件
            skin_file = self.root_dir / "games" / game_id / "skins" / f"{skin_id}.yaml"
            with open(skin_file, 'w', encoding='utf-8') as f:
                yaml.dump(skin_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            logger.info(f"皮肤配置已保存: {skin_file}")

            # 记录操作日志
            operation = "创建" if is_new else "更新"
            self.admin_manager.log_operation(f"{operation}皮肤", f"{skin_name} ({skin_id})")

            messagebox.showinfo("成功", f"皮肤 '{skin_name}' 已{operation}成功！")

            # 刷新列表
            self._refresh_list()

            # 清空编辑器
            self._clear_editor()

        except Exception as e:
            logger.error(f"保存皮肤失败: {e}")
            messagebox.showerror("错误", f"保存失败:\n{e}")


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    root = tk.Tk()
    root.title("皮肤管理器测试")
    root.geometry("1100x750")

    from core.config_loader import get_config_loader
    from core.admin_manager import AdminManager

    config_loader = get_config_loader(".")
    admin_manager = AdminManager(".")

    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)

    manager = SkinManager(frame, config_loader, admin_manager)

    root.mainloop()
