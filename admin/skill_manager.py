"""
技能管理器 - 技能的完整CRUD操作
支持创建、编辑、删除技能，配置伤害、反馈、效果、资源
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
import logging
from pathlib import Path
from typing import Dict, Optional, List
import yaml
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)


class SkillManager:
    """
    技能管理器
    功能：
    1. 新增技能（创建技能配置文件）
    2. 编辑技能（修改所有配置）
    3. 删除技能（移动到回收站）
    4. 配置伤害参数（基础伤害、类型、多段等）
    5. 配置打击反馈（音效、振动、屏幕抖动等）
    6. 配置区域效果（AOE技能）
    7. 上传技能资源（icon、音效、粒子等）
    """

    def __init__(self, parent: tk.Frame, config_loader, admin_manager):
        """
        初始化技能管理器

        参数:
            parent: 父容器
            config_loader: ConfigLoader实例
            admin_manager: AdminManager实例
        """
        self.parent = parent
        self.config_loader = config_loader
        self.admin_manager = admin_manager
        self.root_dir = Path(config_loader.root_dir)

        # 当前编辑的技能（None表示新建）
        self.current_skill_id: Optional[str] = None

        # 技能列表（从角色配置中提取）
        self.skills_data: Dict = {}

        # 创建UI
        self._create_ui()

        logger.info("技能管理器初始化完成")

    def _create_ui(self):
        """创建UI组件"""
        # 标题
        title_frame = tk.Frame(self.parent, bg="#f0f0f0")
        title_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(
            title_frame,
            text="技能管理",
            font=('Arial', 18, 'bold'),
            bg="#f0f0f0"
        ).pack(side=tk.LEFT)

        # 工具栏
        toolbar = tk.Frame(self.parent, bg="#f0f0f0")
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(toolbar, text="新增技能", command=self._new_skill, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="刷新列表", command=self._refresh_list, width=12).pack(side=tk.LEFT, padx=5)

        # 主容器：左侧列表 + 右侧编辑器
        main_container = tk.Frame(self.parent)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧：技能列表
        list_frame = ttk.LabelFrame(main_container, text="已有技能", padding=10)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        # 列表框和滚动条
        list_scroll = ttk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.skill_listbox = tk.Listbox(
            list_frame,
            width=35,
            yscrollcommand=list_scroll.set
        )
        self.skill_listbox.pack(fill=tk.BOTH, expand=True)
        list_scroll.config(command=self.skill_listbox.yview)

        # 绑定选择事件
        self.skill_listbox.bind('<<ListboxSelect>>', self._on_select_skill)

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

        # 页面2: 伤害配置
        self.page_damage = self._create_damage_page()
        self.notebook.add(self.page_damage, text="伤害配置")

        # 页面3: 打击反馈
        self.page_feedback = self._create_feedback_page()
        self.notebook.add(self.page_feedback, text="打击反馈")

        # 页面4: 区域效果
        self.page_area = self._create_area_page()
        self.notebook.add(self.page_area, text="区域效果(AOE)")

        # 页面5: 资源配置
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

        # 技能ID
        tk.Label(content, text="技能ID *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.skill_id_var = tk.StringVar()
        self.skill_id_entry = tk.Entry(content, textvariable=self.skill_id_var, width=40)
        self.skill_id_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            content,
            text="(英文字母、数字、下划线)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 技能名称
        tk.Label(content, text="技能名称 *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.skill_name_var = tk.StringVar()
        tk.Entry(content, textvariable=self.skill_name_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 技能类型
        tk.Label(content, text="技能类型 *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.skill_type_var = tk.StringVar(value="projectile")
        type_combo = ttk.Combobox(
            content,
            textvariable=self.skill_type_var,
            values=["projectile", "aoe", "summon", "buff", "debuff", "passive", "heal", "shield"],
            state="readonly",
            width=37
        )
        type_combo.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            content,
            text="(projectile=弹道 aoe=范围 summon=召唤)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 冷却时间
        tk.Label(content, text="冷却时间(秒):", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.skill_cooldown_var = tk.DoubleVar(value=10.0)
        tk.Spinbox(content, from_=0.0, to=999.0, increment=0.5, textvariable=self.skill_cooldown_var, width=38).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 技能描述
        tk.Label(content, text="技能描述:", bg="white", anchor=tk.NW).grid(
            row=row, column=0, sticky=tk.NW, padx=5, pady=5
        )
        self.skill_desc_text = tk.Text(content, width=40, height=4)
        self.skill_desc_text.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 按钮区域
        btn_frame = tk.Frame(content, bg="white")
        btn_frame.grid(row=row, column=0, columnspan=3, pady=20)

        tk.Button(btn_frame, text="保存技能", command=self._save_skill, width=15, bg="#4CAF50", fg="white").pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="取消", command=self._clear_editor, width=15).pack(side=tk.LEFT, padx=5)

        return page

    def _create_damage_page(self):
        """创建伤害配置页面"""
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

        # 基础伤害
        tk.Label(content, text="基础伤害:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.damage_base_var = tk.IntVar(value=50)
        tk.Spinbox(content, from_=0, to=9999, textvariable=self.damage_base_var, width=38).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 伤害类型
        tk.Label(content, text="伤害类型:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.damage_type_var = tk.StringVar(value="physical")
        ttk.Combobox(
            content,
            textvariable=self.damage_type_var,
            values=["physical", "magic", "true"],
            state="readonly",
            width=37
        ).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            content,
            text="(physical=物理 magic=魔法 true=真实)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 是否多段攻击
        tk.Label(content, text="多段攻击:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.damage_multi_hit_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            content,
            variable=self.damage_multi_hit_var,
            bg="white",
            command=self._toggle_multi_hit
        ).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 攻击次数（多段攻击才启用）
        tk.Label(content, text="攻击次数:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.damage_hit_times_var = tk.IntVar(value=3)
        self.damage_hit_times_spin = tk.Spinbox(
            content,
            from_=1,
            to=20,
            textvariable=self.damage_hit_times_var,
            width=38,
            state=tk.DISABLED
        )
        self.damage_hit_times_spin.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 攻击间隔（多段攻击才启用）
        tk.Label(content, text="攻击间隔(秒):", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.damage_interval_var = tk.DoubleVar(value=0.5)
        self.damage_interval_spin = tk.Spinbox(
            content,
            from_=0.1,
            to=10.0,
            increment=0.1,
            textvariable=self.damage_interval_var,
            width=38,
            state=tk.DISABLED
        )
        self.damage_interval_spin.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 暴击率
        tk.Label(content, text="暴击率:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.damage_crit_var = tk.DoubleVar(value=0.05)
        tk.Spinbox(content, from_=0.0, to=1.0, increment=0.01, textvariable=self.damage_crit_var, width=38).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        tk.Label(
            content,
            text="(0.0-1.0, 例如0.05=5%)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        return page

    def _create_feedback_page(self):
        """创建打击反馈页面"""
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

        # 反馈类型
        tk.Label(content, text="反馈类型:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.feedback_type_var = tk.StringVar(value="light")
        ttk.Combobox(
            content,
            textvariable=self.feedback_type_var,
            values=["light", "heavy", "critical", "magic"],
            state="readonly",
            width=37
        ).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 打击音效
        tk.Label(content, text="打击音效:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        frame = tk.Frame(content, bg="white")
        frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        self.feedback_sound_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.feedback_sound_var, width=30).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(frame, text="选择", command=lambda: self._select_asset(self.feedback_sound_var, "音频"), width=8).pack(side=tk.LEFT)
        row += 1

        # 振动持续时间
        tk.Label(content, text="振动持续时间(秒):", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.feedback_vib_duration_var = tk.DoubleVar(value=0.1)
        tk.Spinbox(content, from_=0.0, to=2.0, increment=0.05, textvariable=self.feedback_vib_duration_var, width=38).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 振动强度
        tk.Label(content, text="振动强度(0-100):", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.feedback_vib_strength_var = tk.IntVar(value=50)
        tk.Spinbox(content, from_=0, to=100, textvariable=self.feedback_vib_strength_var, width=38).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 伤害文字颜色
        tk.Label(content, text="伤害文字颜色:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        color_frame = tk.Frame(content, bg="white")
        color_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        self.feedback_color_r_var = tk.DoubleVar(value=1.0)
        self.feedback_color_g_var = tk.DoubleVar(value=1.0)
        self.feedback_color_b_var = tk.DoubleVar(value=1.0)

        tk.Label(color_frame, text="R:", bg="white").pack(side=tk.LEFT)
        tk.Spinbox(color_frame, from_=0.0, to=1.0, increment=0.1, textvariable=self.feedback_color_r_var, width=8).pack(side=tk.LEFT, padx=2)
        tk.Label(color_frame, text="G:", bg="white").pack(side=tk.LEFT)
        tk.Spinbox(color_frame, from_=0.0, to=1.0, increment=0.1, textvariable=self.feedback_color_g_var, width=8).pack(side=tk.LEFT, padx=2)
        tk.Label(color_frame, text="B:", bg="white").pack(side=tk.LEFT)
        tk.Spinbox(color_frame, from_=0.0, to=1.0, increment=0.1, textvariable=self.feedback_color_b_var, width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(color_frame, text="颜色选择器", command=self._pick_color, width=10).pack(side=tk.LEFT, padx=5)
        row += 1

        # 屏幕抖动
        tk.Label(content, text="屏幕抖动强度:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.feedback_screen_shake_var = tk.DoubleVar(value=0.0)
        tk.Spinbox(content, from_=0.0, to=1.0, increment=0.01, textvariable=self.feedback_screen_shake_var, width=38).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        tk.Label(
            content,
            text="(0.0=无抖动 1.0=最大抖动)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        return page

    def _create_area_page(self):
        """创建区域效果页面"""
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
            text="注意: 区域效果仅对AOE类型技能生效",
            font=('Arial', 10, 'bold'),
            bg="white",
            fg="orange"
        ).grid(row=row, column=0, columnspan=2, pady=10)
        row += 1

        # 作用半径
        tk.Label(content, text="作用半径:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.area_radius_var = tk.IntVar(value=100)
        tk.Spinbox(content, from_=10, to=1000, textvariable=self.area_radius_var, width=38).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 区域形状
        tk.Label(content, text="区域形状:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.area_shape_var = tk.StringVar(value="circle")
        ttk.Combobox(
            content,
            textvariable=self.area_shape_var,
            values=["circle", "rectangle", "cone", "line"],
            state="readonly",
            width=37
        ).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
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
            ("技能图标:", "icon", "图片"),
            ("施法音效:", "sound_cast", "音频"),
            ("命中音效:", "sound_hit", "音频"),
            ("技能动画:", "animation", "模型"),
            ("粒子效果:", "particle", "模型"),
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
        """刷新技能列表"""
        try:
            # 触发配置重新扫描
            self.config_loader.scan_configs()

            # 清空列表
            self.skill_listbox.delete(0, tk.END)

            # 从所有角色的技能中提取
            self.skills_data = {}
            characters = self.config_loader.characters

            for char_id, char_data in characters.items():
                skills = char_data.get("skills", [])
                for skill in skills:
                    skill_id = skill.get("skill_id")
                    if skill_id and skill_id not in self.skills_data:
                        # 保存技能数据（包含来源角色信息）
                        skill_copy = skill.copy()
                        skill_copy["source_character"] = char_id
                        self.skills_data[skill_id] = skill_copy

            # 显示在列表中
            for skill_id, skill_data in self.skills_data.items():
                skill_name = skill_data.get("name", skill_id)
                skill_type = skill_data.get("type", "unknown")
                self.skill_listbox.insert(tk.END, f"{skill_name} ({skill_id}) [{skill_type}]")

            logger.info(f"技能列表已刷新: {len(self.skills_data)}个技能")

        except Exception as e:
            logger.error(f"刷新技能列表失败: {e}")
            messagebox.showerror("错误", f"刷新列表失败:\n{e}")

    def _on_select_skill(self, event):
        """选择技能时触发"""
        selection = self.skill_listbox.curselection()
        if not selection:
            return

        # 从列表文本中提取skill_id
        text = self.skill_listbox.get(selection[0])
        # 格式: "技能名称 (skill_id) [type]"
        import re
        match = re.search(r'\(([^)]+)\)', text)
        if match:
            skill_id = match.group(1)
            self._load_skill(skill_id)

    def _new_skill(self):
        """新增技能"""
        self.current_skill_id = None
        self._clear_editor()
        self.skill_id_entry.config(state=tk.NORMAL)
        logger.info("准备新增技能")

    def _edit_selected(self):
        """编辑选中的技能"""
        selection = self.skill_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要编辑的技能")
            return

        self._on_select_skill(None)

    def _delete_selected(self):
        """删除选中的技能"""
        messagebox.showinfo(
            "提示",
            "技能数据存储在角色配置文件中。\n"
            "要删除技能，请在角色管理器中编辑对应角色，\n"
            "从技能列表中移除该技能。"
        )

    def _load_skill(self, skill_id: str):
        """加载技能数据到编辑器"""
        try:
            skill_data = self.skills_data.get(skill_id)
            if not skill_data:
                messagebox.showerror("错误", f"技能不存在: {skill_id}")
                return

            self.current_skill_id = skill_id

            # 填充基础信息
            self.skill_id_var.set(skill_id)
            self.skill_id_entry.config(state=tk.DISABLED)
            self.skill_name_var.set(skill_data.get("name", ""))
            self.skill_type_var.set(skill_data.get("type", "projectile"))
            self.skill_cooldown_var.set(skill_data.get("cooldown", 10.0))

            desc = skill_data.get("description", "")
            self.skill_desc_text.delete("1.0", tk.END)
            self.skill_desc_text.insert("1.0", desc)

            # 填充伤害配置
            damage = skill_data.get("damage", {})
            self.damage_base_var.set(damage.get("base_damage", 50))
            self.damage_type_var.set(damage.get("damage_type", "physical"))
            self.damage_multi_hit_var.set(damage.get("is_multi_hit", False))
            self.damage_hit_times_var.set(damage.get("hit_times", 3))
            self.damage_interval_var.set(damage.get("interval", 0.5))
            self.damage_crit_var.set(damage.get("crit_chance", 0.05))
            self._toggle_multi_hit()

            # 填充打击反馈
            feedback = skill_data.get("hit_feedback", {})
            self.feedback_type_var.set(feedback.get("type", "light"))
            self.feedback_sound_var.set(feedback.get("sound", ""))
            self.feedback_vib_duration_var.set(feedback.get("vibration_duration", 0.1))
            self.feedback_vib_strength_var.set(feedback.get("vibration_strength", 50))

            color = feedback.get("damage_text_color", [1.0, 1.0, 1.0])
            if len(color) >= 3:
                self.feedback_color_r_var.set(color[0])
                self.feedback_color_g_var.set(color[1])
                self.feedback_color_b_var.set(color[2])

            self.feedback_screen_shake_var.set(feedback.get("screen_shake", 0.0))

            # 填充区域效果
            area = skill_data.get("area", {})
            self.area_radius_var.set(area.get("radius", 100))
            self.area_shape_var.set(area.get("shape", "circle"))

            # 填充资源
            assets = skill_data.get("assets", {})
            for key, var in self.assets_vars.items():
                var.set(assets.get(key, ""))

            logger.info(f"已加载技能: {skill_id}")

        except Exception as e:
            logger.error(f"加载技能失败: {e}")
            messagebox.showerror("错误", f"加载失败:\n{e}")

    def _clear_editor(self):
        """清空编辑器"""
        self.current_skill_id = None

        # 清空基础信息
        self.skill_id_var.set("")
        self.skill_id_entry.config(state=tk.NORMAL)
        self.skill_name_var.set("")
        self.skill_type_var.set("projectile")
        self.skill_cooldown_var.set(10.0)
        self.skill_desc_text.delete("1.0", tk.END)

        # 清空伤害配置
        self.damage_base_var.set(50)
        self.damage_type_var.set("physical")
        self.damage_multi_hit_var.set(False)
        self.damage_hit_times_var.set(3)
        self.damage_interval_var.set(0.5)
        self.damage_crit_var.set(0.05)
        self._toggle_multi_hit()

        # 清空打击反馈
        self.feedback_type_var.set("light")
        self.feedback_sound_var.set("")
        self.feedback_vib_duration_var.set(0.1)
        self.feedback_vib_strength_var.set(50)
        self.feedback_color_r_var.set(1.0)
        self.feedback_color_g_var.set(1.0)
        self.feedback_color_b_var.set(1.0)
        self.feedback_screen_shake_var.set(0.0)

        # 清空区域效果
        self.area_radius_var.set(100)
        self.area_shape_var.set("circle")

        # 清空资源
        for var in self.assets_vars.values():
            var.set("")

    def _toggle_multi_hit(self):
        """切换多段攻击选项"""
        if self.damage_multi_hit_var.get():
            self.damage_hit_times_spin.config(state=tk.NORMAL)
            self.damage_interval_spin.config(state=tk.NORMAL)
        else:
            self.damage_hit_times_spin.config(state=tk.DISABLED)
            self.damage_interval_spin.config(state=tk.DISABLED)

    def _select_asset(self, var: tk.StringVar, file_type: str):
        """选择资源文件"""
        if file_type == "图片":
            filetypes = [("图片文件", "*.png *.jpg *.jpeg"), ("所有文件", "*.*")]
        elif file_type == "音频":
            filetypes = [("音频文件", "*.wav *.ogg *.mp3"), ("所有文件", "*.*")]
        elif file_type == "模型":
            filetypes = [("模型文件", "*.glb *.fbx"), ("所有文件", "*.*")]
        else:
            filetypes = [("所有文件", "*.*")]

        file_path = filedialog.askopenfilename(
            title="选择资源文件",
            filetypes=filetypes
        )
        if file_path:
            var.set(file_path)

    def _pick_color(self):
        """颜色选择器"""
        # 将当前RGB值转换为Tkinter颜色格式
        r = int(self.feedback_color_r_var.get() * 255)
        g = int(self.feedback_color_g_var.get() * 255)
        b = int(self.feedback_color_b_var.get() * 255)
        initial_color = f"#{r:02x}{g:02x}{b:02x}"

        color = colorchooser.askcolor(initialcolor=initial_color, title="选择伤害文字颜色")
        if color[0]:
            # color[0] 是RGB元组 (r, g, b)
            self.feedback_color_r_var.set(color[0][0] / 255.0)
            self.feedback_color_g_var.set(color[0][1] / 255.0)
            self.feedback_color_b_var.set(color[0][2] / 255.0)

    def _save_skill(self):
        """保存技能"""
        messagebox.showinfo(
            "保存技能",
            "技能数据存储在角色配置文件中。\n\n"
            "新增技能:\n"
            "请在角色管理器中编辑对应角色，\n"
            "在技能列表中添加该技能ID。\n\n"
            "编辑技能:\n"
            "技能的详细配置会在角色配置文件中保存。\n"
            "您可以在此界面配置所有参数后，\n"
            "在角色编辑器中保存角色配置来应用更改。\n\n"
            "注: Phase 5将在后续完善独立的技能配置文件系统。"
        )


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    root = tk.Tk()
    root.title("技能管理器测试")
    root.geometry("1100x750")

    from core.config_loader import get_config_loader
    from core.admin_manager import AdminManager

    config_loader = get_config_loader(".")
    admin_manager = AdminManager(".")

    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)

    manager = SkillManager(frame, config_loader, admin_manager)

    root.mainloop()
