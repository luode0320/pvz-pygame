"""
战役管理器 - 战役的完整CRUD操作
支持创建、编辑、删除战役，配置对战双方、难度等级、封面图
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


class CampaignManager:
    """
    战役管理器
    功能：
    1. 新增战役（创建战役目录和配置文件）
    2. 编辑战役（修改所有配置）
    3. 删除战役（移动到回收站）
    4. 选择防守方/攻击方游戏IP
    5. 配置难度等级
    6. 上传战役封面图
    """

    def __init__(self, parent: tk.Frame, config_loader, admin_manager):
        """
        初始化战役管理器

        参数:
            parent: 父容器
            config_loader: ConfigLoader实例
            admin_manager: AdminManager实例
        """
        self.parent = parent
        self.config_loader = config_loader
        self.admin_manager = admin_manager
        self.root_dir = Path(config_loader.root_dir)

        # 当前编辑的战役（None表示新建）
        self.current_campaign_id: Optional[str] = None

        # 创建UI
        self._create_ui()

        logger.info("战役管理器初始化完成")

    def _create_ui(self):
        """创建UI组件"""
        # 标题
        title_frame = tk.Frame(self.parent, bg="#f0f0f0")
        title_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(
            title_frame,
            text="战役管理",
            font=('Arial', 18, 'bold'),
            bg="#f0f0f0"
        ).pack(side=tk.LEFT)

        # 工具栏
        toolbar = tk.Frame(self.parent, bg="#f0f0f0")
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(toolbar, text="新增战役", command=self._new_campaign, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="刷新列表", command=self._refresh_list, width=12).pack(side=tk.LEFT, padx=5)

        # 主容器：左侧列表 + 右侧编辑器
        main_container = tk.Frame(self.parent)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧：战役列表
        list_frame = ttk.LabelFrame(main_container, text="已有战役", padding=10)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        # 列表框和滚动条
        list_scroll = ttk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.campaign_listbox = tk.Listbox(
            list_frame,
            width=40,
            yscrollcommand=list_scroll.set
        )
        self.campaign_listbox.pack(fill=tk.BOTH, expand=True)
        list_scroll.config(command=self.campaign_listbox.yview)

        # 绑定选择事件
        self.campaign_listbox.bind('<<ListboxSelect>>', self._on_select_campaign)

        # 列表下方按钮
        list_btn_frame = tk.Frame(list_frame)
        list_btn_frame.pack(fill=tk.X, pady=(10, 0))

        tk.Button(list_btn_frame, text="编辑", command=self._edit_selected, width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(list_btn_frame, text="删除", command=self._delete_selected, width=10).pack(side=tk.LEFT, padx=2)

        # 右侧：编辑器
        editor_frame = ttk.LabelFrame(main_container, text="编辑器", padding=10)
        editor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 创建滚动容器
        canvas = tk.Canvas(editor_frame, bg="white")
        scrollbar = ttk.Scrollbar(editor_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.editor_content = tk.Frame(canvas, bg="white")

        self.editor_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.editor_content, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 编辑器字段
        row = 0

        # 战役ID
        tk.Label(self.editor_content, text="战役ID *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.campaign_id_var = tk.StringVar()
        self.campaign_id_entry = tk.Entry(self.editor_content, textvariable=self.campaign_id_var, width=40)
        self.campaign_id_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            self.editor_content,
            text="(英文字母、数字、下划线)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 战役名称
        tk.Label(self.editor_content, text="战役名称 *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.campaign_name_var = tk.StringVar()
        tk.Entry(self.editor_content, textvariable=self.campaign_name_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 战役描述
        tk.Label(self.editor_content, text="战役描述:", bg="white", anchor=tk.NW).grid(
            row=row, column=0, sticky=tk.NW, padx=5, pady=5
        )
        self.campaign_desc_text = tk.Text(self.editor_content, width=40, height=4)
        self.campaign_desc_text.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 分隔线
        ttk.Separator(self.editor_content, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=3, sticky=tk.EW, pady=10
        )
        row += 1

        # 防守方游戏IP
        tk.Label(self.editor_content, text="防守方游戏IP *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.defender_game_var = tk.StringVar()
        self.defender_combo = ttk.Combobox(
            self.editor_content,
            textvariable=self.defender_game_var,
            state="readonly",
            width=37
        )
        self.defender_combo.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            self.editor_content,
            text="(玩家控制的角色所属游戏)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 攻击方游戏IP
        tk.Label(self.editor_content, text="攻击方游戏IP *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.attacker_game_var = tk.StringVar()
        self.attacker_combo = ttk.Combobox(
            self.editor_content,
            textvariable=self.attacker_game_var,
            state="readonly",
            width=37
        )
        self.attacker_combo.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            self.editor_content,
            text="(敌人角色所属游戏)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 分隔线
        ttk.Separator(self.editor_content, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=3, sticky=tk.EW, pady=10
        )
        row += 1

        # 难度等级
        tk.Label(self.editor_content, text="难度等级:", bg="white", anchor=tk.NW).grid(
            row=row, column=0, sticky=tk.NW, padx=5, pady=5
        )

        difficulty_frame = tk.Frame(self.editor_content, bg="white")
        difficulty_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        self.difficulty_vars = {}
        difficulties = [("简单(easy)", "easy"), ("普通(normal)", "normal"), ("困难(hard)", "hard"), ("噩梦(nightmare)", "nightmare")]
        for idx, (label, value) in enumerate(difficulties):
            var = tk.BooleanVar(value=(value in ["easy", "normal", "hard"]))
            tk.Checkbutton(difficulty_frame, text=label, variable=var, bg="white").grid(
                row=idx // 2, column=idx % 2, sticky=tk.W, padx=5
            )
            self.difficulty_vars[value] = var
        row += 1

        # 分隔线
        ttk.Separator(self.editor_content, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=3, sticky=tk.EW, pady=10
        )
        row += 1

        # 封面图片
        tk.Label(self.editor_content, text="封面图片:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        cover_frame = tk.Frame(self.editor_content, bg="white")
        cover_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        self.cover_image_var = tk.StringVar()
        tk.Entry(cover_frame, textvariable=self.cover_image_var, width=30).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(cover_frame, text="选择图片", command=self._select_cover_image, width=10).pack(side=tk.LEFT)
        row += 1

        # 3D封面模型（可选）
        tk.Label(self.editor_content, text="3D封面模型:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        cover_3d_frame = tk.Frame(self.editor_content, bg="white")
        cover_3d_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        self.cover_3d_var = tk.StringVar()
        tk.Entry(cover_3d_frame, textvariable=self.cover_3d_var, width=30).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(cover_3d_frame, text="选择模型", command=self._select_cover_3d, width=10).pack(side=tk.LEFT)
        tk.Label(
            self.editor_content,
            text="(可选)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 分隔线
        ttk.Separator(self.editor_content, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=3, sticky=tk.EW, pady=20
        )
        row += 1

        # 按钮区域
        btn_frame = tk.Frame(self.editor_content, bg="white")
        btn_frame.grid(row=row, column=0, columnspan=3, pady=10)

        tk.Button(btn_frame, text="保存战役", command=self._save_campaign, width=15, bg="#4CAF50", fg="white").pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="取消", command=self._clear_editor, width=15).pack(side=tk.LEFT, padx=5)

        # 刷新列表
        self._refresh_list()

        # 显示空编辑器
        self._clear_editor()

    def _refresh_list(self):
        """刷新战役列表"""
        try:
            # 触发配置重新扫描
            self.config_loader.scan_all()

            # 清空列表
            self.campaign_listbox.delete(0, tk.END)

            # 更新游戏IP下拉列表
            games = list(self.config_loader.games.keys())
            self.defender_combo['values'] = games
            self.attacker_combo['values'] = games

            # 加载战役
            campaigns = self.config_loader.campaigns
            for campaign_id, campaign_data in campaigns.items():
                campaign_name = campaign_data.get("name", campaign_id)
                defender = campaign_data.get("defender_game", "")
                attacker = campaign_data.get("attacker_game", "")
                self.campaign_listbox.insert(tk.END, f"{campaign_name} ({campaign_id}) - {defender} vs {attacker}")

            logger.info(f"战役列表已刷新: {len(campaigns)}个战役")

        except Exception as e:
            logger.error(f"刷新战役列表失败: {e}")
            messagebox.showerror("错误", f"刷新列表失败:\n{e}")

    def _on_select_campaign(self, event):
        """选择战役时触发"""
        selection = self.campaign_listbox.curselection()
        if not selection:
            return

        # 从列表文本中提取campaign_id
        text = self.campaign_listbox.get(selection[0])
        # 格式: "战役名称 (campaign_id) - defender vs attacker"
        import re
        match = re.search(r'\(([^)]+)\)', text)
        if match:
            campaign_id = match.group(1)
            self._load_campaign(campaign_id)

    def _new_campaign(self):
        """新增战役"""
        self.current_campaign_id = None
        self._clear_editor()
        self.campaign_id_entry.config(state=tk.NORMAL)
        logger.info("准备新增战役")

    def _edit_selected(self):
        """编辑选中的战役"""
        selection = self.campaign_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要编辑的战役")
            return

        self._on_select_campaign(None)

    def _delete_selected(self):
        """删除选中的战役"""
        selection = self.campaign_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的战役")
            return

        # 从列表文本中提取campaign_id
        text = self.campaign_listbox.get(selection[0])
        import re
        match = re.search(r'\(([^)]+)\)', text)
        if not match:
            return

        campaign_id = match.group(1)
        campaign_data = self.config_loader.campaigns.get(campaign_id, {})
        campaign_name = campaign_data.get("name", campaign_id)

        # 确认删除
        if not messagebox.askyesno(
            "确认删除",
            f"确定要删除战役 '{campaign_name}' 吗？\n\n"
            f"这将删除整个战役目录（包括所有关卡）。\n"
            f"删除的内容将移动到回收站，可以恢复。"
        ):
            return

        try:
            # 删除战役目录
            campaign_dir = self.root_dir / "campaigns" / campaign_id
            if campaign_dir.exists():
                self.admin_manager.delete_config(str(campaign_dir), "战役")
                logger.info(f"战役已删除: {campaign_id}")
                messagebox.showinfo("成功", f"战役 '{campaign_name}' 已删除并移动到回收站")

                # 刷新列表
                self._refresh_list()
                self._clear_editor()
            else:
                messagebox.showerror("错误", f"战役目录不存在: {campaign_dir}")

        except Exception as e:
            logger.error(f"删除战役失败: {e}")
            messagebox.showerror("错误", f"删除失败:\n{e}")

    def _load_campaign(self, campaign_id: str):
        """加载战役数据到编辑器"""
        try:
            campaign_data = self.config_loader.campaigns.get(campaign_id)
            if not campaign_data:
                messagebox.showerror("错误", f"战役不存在: {campaign_id}")
                return

            self.current_campaign_id = campaign_id

            # 填充基础信息
            self.campaign_id_var.set(campaign_id)
            self.campaign_id_entry.config(state=tk.DISABLED)
            self.campaign_name_var.set(campaign_data.get("name", ""))

            desc = campaign_data.get("description", "")
            self.campaign_desc_text.delete("1.0", tk.END)
            self.campaign_desc_text.insert("1.0", desc)

            # 填充游戏IP
            self.defender_game_var.set(campaign_data.get("defender_game", ""))
            self.attacker_game_var.set(campaign_data.get("attacker_game", ""))

            # 填充难度等级
            difficulty_levels = campaign_data.get("difficulty_levels", [])
            for key, var in self.difficulty_vars.items():
                var.set(key in difficulty_levels)

            # 填充封面
            self.cover_image_var.set(campaign_data.get("cover_image", ""))
            self.cover_3d_var.set(campaign_data.get("cover_image_3d", ""))

            logger.info(f"已加载战役: {campaign_id}")

        except Exception as e:
            logger.error(f"加载战役失败: {e}")
            messagebox.showerror("错误", f"加载失败:\n{e}")

    def _clear_editor(self):
        """清空编辑器"""
        self.current_campaign_id = None
        self.campaign_id_var.set("")
        self.campaign_id_entry.config(state=tk.NORMAL)
        self.campaign_name_var.set("")
        self.campaign_desc_text.delete("1.0", tk.END)
        self.defender_game_var.set("")
        self.attacker_game_var.set("")

        # 重置难度等级为默认值
        for key, var in self.difficulty_vars.items():
            var.set(key in ["easy", "normal", "hard"])

        self.cover_image_var.set("")
        self.cover_3d_var.set("")

    def _select_cover_image(self):
        """选择封面图片"""
        file_path = filedialog.askopenfilename(
            title="选择封面图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg"), ("所有文件", "*.*")]
        )
        if file_path:
            self.cover_image_var.set(file_path)

    def _select_cover_3d(self):
        """选择3D封面模型"""
        file_path = filedialog.askopenfilename(
            title="选择3D封面模型",
            filetypes=[("模型文件", "*.glb *.fbx"), ("所有文件", "*.*")]
        )
        if file_path:
            self.cover_3d_var.set(file_path)

    def _save_campaign(self):
        """保存战役"""
        try:
            # 验证必填字段
            campaign_id = self.campaign_id_var.get().strip()
            campaign_name = self.campaign_name_var.get().strip()
            defender_game = self.defender_game_var.get().strip()
            attacker_game = self.attacker_game_var.get().strip()

            if not campaign_id:
                messagebox.showwarning("验证失败", "请输入战役ID")
                return

            if not campaign_name:
                messagebox.showwarning("验证失败", "请输入战役名称")
                return

            if not defender_game:
                messagebox.showwarning("验证失败", "请选择防守方游戏IP")
                return

            if not attacker_game:
                messagebox.showwarning("验证失败", "请选择攻击方游戏IP")
                return

            # 验证战役ID格式
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', campaign_id):
                messagebox.showwarning(
                    "验证失败",
                    "战役ID只能包含英文字母、数字和下划线"
                )
                return

            # 验证游戏IP是否存在
            if defender_game not in self.config_loader.games:
                messagebox.showerror("错误", f"防守方游戏IP '{defender_game}' 不存在")
                return

            if attacker_game not in self.config_loader.games:
                messagebox.showerror("错误", f"攻击方游戏IP '{attacker_game}' 不存在")
                return

            # 如果是新增，检查ID是否已存在
            is_new = self.current_campaign_id is None
            if is_new and campaign_id in self.config_loader.campaigns:
                messagebox.showwarning("验证失败", f"战役ID '{campaign_id}' 已存在")
                return

            # 创建战役目录
            campaign_dir = self.root_dir / "campaigns" / campaign_id
            if is_new:
                campaign_dir.mkdir(parents=True, exist_ok=True)
                (campaign_dir / "levels").mkdir(exist_ok=True)
                logger.info(f"创建战役目录: {campaign_dir}")

            # 处理封面图片
            cover_image_path = ""
            cover_file_path = self.cover_image_var.get().strip()
            if cover_file_path and Path(cover_file_path).exists():
                filename = Path(cover_file_path).name
                dest_file = campaign_dir / filename
                shutil.copy2(cover_file_path, dest_file)
                cover_image_path = filename
                logger.info(f"封面图片已复制: {dest_file}")

            # 处理3D封面模型
            cover_3d_path = ""
            cover_3d_file = self.cover_3d_var.get().strip()
            if cover_3d_file and Path(cover_3d_file).exists():
                filename = Path(cover_3d_file).name
                dest_file = campaign_dir / filename
                shutil.copy2(cover_3d_file, dest_file)
                cover_3d_path = f"models/covers/{filename}"
                logger.info(f"3D封面已复制: {dest_file}")

            # 收集难度等级
            difficulty_levels = [key for key, var in self.difficulty_vars.items() if var.get()]

            # 构建配置数据
            campaign_config = {
                "campaign_id": campaign_id,
                "name": campaign_name,
                "description": self.campaign_desc_text.get("1.0", tk.END).strip(),
                "cover_image": cover_image_path,
                "cover_image_3d": cover_3d_path,
                "defender_game": defender_game,
                "attacker_game": attacker_game,
                "difficulty_levels": difficulty_levels,
                "skin_unlocks": [],
                "unlock_conditions": [],
                "global_lighting": {
                    "ambient_light_color": [0.85, 0.85, 0.85],
                    "ambient_light_intensity": 0.6,
                    "directional_light_color": [1.0, 0.95, 0.8],
                    "directional_light_intensity": 1.2,
                    "shadow_quality": "medium"
                },
                "performance_config": {
                    "default_device_profile": "mid_end",
                    "max_entities": 50,
                    "max_particles": 800,
                    "frame_rate_target": 30
                }
            }

            # 保存战役配置文件
            campaign_file = campaign_dir / "campaign.yaml"
            with open(campaign_file, 'w', encoding='utf-8') as f:
                yaml.dump(campaign_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            logger.info(f"战役配置已保存: {campaign_file}")

            # 记录操作日志
            operation = "创建" if is_new else "更新"
            self.admin_manager.log_operation(f"{operation}战役", f"{campaign_name} ({campaign_id})")

            messagebox.showinfo("成功", f"战役 '{campaign_name}' 已{operation}成功！")

            # 刷新列表
            self._refresh_list()

            # 清空编辑器
            self._clear_editor()

        except Exception as e:
            logger.error(f"保存战役失败: {e}")
            messagebox.showerror("错误", f"保存失败:\n{e}")


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    root = tk.Tk()
    root.title("战役管理器测试")
    root.geometry("1100x750")

    from core.config_loader import get_config_loader
    from core.admin_manager import AdminManager

    config_loader = get_config_loader(".")
    admin_manager = AdminManager(".")

    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)

    manager = CampaignManager(frame, config_loader, admin_manager)

    root.mainloop()
