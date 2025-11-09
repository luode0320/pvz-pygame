"""
游戏IP管理器 - 游戏IP的完整CRUD操作
支持创建、编辑、删除游戏IP，自动生成目录结构和配置文件
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from pathlib import Path
from typing import Dict, Optional
import yaml
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)


class GameManager:
    """
    游戏IP管理器
    功能：
    1. 新增游戏IP（创建目录结构、生成meta.yaml）
    2. 编辑游戏IP（修改meta.yaml）
    3. 删除游戏IP（移动到回收站）
    4. 上传游戏图标
    5. 验证（名称唯一性、路径合法性）
    """

    # 游戏玩法类型映射：中文显示 -> 英文存储
    # 注意：游戏IP本身没有"防守方/攻击方"的固定身份
    # "防守方/攻击方"是在战役配置中定义的，不是游戏IP的属性
    GAME_TYPE_MAP = {
        "塔防": "tower_defense",
        "动作": "action",
        "角色扮演": "rpg",
        "策略": "strategy",
        "MOBA": "moba",
        "格斗": "fighting",
        "冒险": "adventure",
        "益智": "puzzle"
    }

    # 反向映射：英文 -> 中文
    GAME_TYPE_REVERSE_MAP = {v: k for k, v in GAME_TYPE_MAP.items()}

    def __init__(self, parent: tk.Frame, config_loader, admin_manager):
        """
        初始化游戏IP管理器

        参数:
            parent: 父容器
            config_loader: ConfigLoader实例
            admin_manager: AdminManager实例
        """
        self.parent = parent
        self.config_loader = config_loader
        self.admin_manager = admin_manager
        self.root_dir = Path(config_loader.root_dir)

        # 当前编辑的游戏IP（None表示新建）
        self.current_game_id: Optional[str] = None

        # 创建UI
        self._create_ui()

        logger.info("游戏IP管理器初始化完成")

    def _create_ui(self):
        """创建UI组件"""
        # 标题
        title_frame = tk.Frame(self.parent, bg="#f0f0f0")
        title_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(
            title_frame,
            text="游戏IP管理",
            font=('Arial', 18, 'bold'),
            bg="#f0f0f0"
        ).pack(side=tk.LEFT)

        # 工具栏
        toolbar = tk.Frame(self.parent, bg="#f0f0f0")
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(toolbar, text="新增游戏IP", command=self._new_game, width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="刷新列表", command=self._refresh_list, width=12).pack(side=tk.LEFT, padx=5)

        # 主容器：左侧列表 + 右侧编辑器
        main_container = tk.Frame(self.parent)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧：游戏IP列表
        list_frame = ttk.LabelFrame(main_container, text="已有游戏IP", padding=10)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))

        # 列表框和滚动条
        list_scroll = ttk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.game_listbox = tk.Listbox(
            list_frame,
            width=30,
            yscrollcommand=list_scroll.set
        )
        self.game_listbox.pack(fill=tk.BOTH, expand=True)
        list_scroll.config(command=self.game_listbox.yview)

        # 绑定选择事件
        self.game_listbox.bind('<<ListboxSelect>>', self._on_select_game)

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

        # 游戏ID
        tk.Label(self.editor_content, text="游戏ID *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.game_id_var = tk.StringVar()
        self.game_id_entry = tk.Entry(self.editor_content, textvariable=self.game_id_var, width=40)
        self.game_id_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(
            self.editor_content,
            text="(英文字母、数字、下划线，如: dnf, league_of_legends)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 游戏名称
        tk.Label(self.editor_content, text="游戏名称 *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.game_name_var = tk.StringVar()
        tk.Entry(self.editor_content, textvariable=self.game_name_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        tk.Label(
            self.editor_content,
            text="(显示在游戏中的名称，如: 地下城与勇士)",
            font=('Arial', 8),
            bg="white",
            fg="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 游戏类型
        tk.Label(self.editor_content, text="游戏类型 *:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.game_type_var = tk.StringVar(value="动作")
        type_combo = ttk.Combobox(
            self.editor_content,
            textvariable=self.game_type_var,
            values=list(self.GAME_TYPE_MAP.keys()),  # 使用中文选项
            state="readonly",
            width=37
        )
        type_combo.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 游戏描述
        tk.Label(self.editor_content, text="游戏描述:", bg="white", anchor=tk.NW).grid(
            row=row, column=0, sticky=tk.NW, padx=5, pady=5
        )
        self.game_desc_text = tk.Text(self.editor_content, width=40, height=4)
        self.game_desc_text.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1

        # 作者
        tk.Label(self.editor_content, text="作者:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.game_author_var = tk.StringVar()
        tk.Entry(self.editor_content, textvariable=self.game_author_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 版本
        tk.Label(self.editor_content, text="版本:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.game_version_var = tk.StringVar(value="1.0.0")
        tk.Entry(self.editor_content, textvariable=self.game_version_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 图标路径
        tk.Label(self.editor_content, text="游戏图标:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        icon_frame = tk.Frame(self.editor_content, bg="white")
        icon_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        self.game_icon_var = tk.StringVar()
        tk.Entry(icon_frame, textvariable=self.game_icon_var, width=30).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(icon_frame, text="选择图标", command=self._select_icon, width=10).pack(side=tk.LEFT)
        row += 1

        # 标签
        tk.Label(self.editor_content, text="标签:", bg="white", anchor=tk.W).grid(
            row=row, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.game_tags_var = tk.StringVar()
        tk.Entry(self.editor_content, textvariable=self.game_tags_var, width=40).grid(
            row=row, column=1, sticky=tk.W, padx=5, pady=5
        )
        tk.Label(
            self.editor_content,
            text="(多个标签用逗号分隔，如: 动作,格斗,横版)",
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

        tk.Button(btn_frame, text="保存", command=self._save_game, width=15, bg="#4CAF50", fg="white").pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="取消", command=self._clear_editor, width=15).pack(side=tk.LEFT, padx=5)

        # 刷新列表
        self._refresh_list()

        # 显示空编辑器
        self._clear_editor()

    def _refresh_list(self):
        """刷新游戏IP列表"""
        try:
            # 触发配置重新扫描
            self.config_loader.scan_all()

            # 清空列表
            self.game_listbox.delete(0, tk.END)

            # 加载游戏IP
            games = self.config_loader.games
            for game_id, game_data in games.items():
                game_name = game_data.get("name", game_id)
                self.game_listbox.insert(tk.END, f"{game_name} ({game_id})")

            logger.info(f"游戏IP列表已刷新: {len(games)}个游戏")

        except Exception as e:
            logger.error(f"刷新游戏IP列表失败: {e}")
            messagebox.showerror("错误", f"刷新列表失败:\n{e}")

    def _on_select_game(self, event):
        """选择游戏IP时触发"""
        selection = self.game_listbox.curselection()
        if not selection:
            return

        # 从列表文本中提取game_id
        text = self.game_listbox.get(selection[0])
        # 格式: "游戏名称 (game_id)"
        import re
        match = re.search(r'\(([^)]+)\)$', text)
        if match:
            game_id = match.group(1)
            self._load_game(game_id)

    def _new_game(self):
        """新增游戏IP"""
        self.current_game_id = None
        self._clear_editor()
        self.game_id_entry.config(state=tk.NORMAL)
        logger.info("准备新增游戏IP")

    def _edit_selected(self):
        """编辑选中的游戏IP"""
        selection = self.game_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要编辑的游戏IP")
            return

        self._on_select_game(None)

    def _delete_selected(self):
        """删除选中的游戏IP"""
        selection = self.game_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的游戏IP")
            return

        # 从列表文本中提取game_id
        text = self.game_listbox.get(selection[0])
        import re
        match = re.search(r'\(([^)]+)\)$', text)
        if not match:
            return

        game_id = match.group(1)
        game_name = self.config_loader.games.get(game_id, {}).get("name", game_id)

        # 确认删除
        if not messagebox.askyesno(
            "确认删除",
            f"确定要删除游戏IP '{game_name}' 吗？\n\n"
            f"这将删除整个游戏目录（包括所有角色、技能、皮肤）。\n"
            f"删除的内容将移动到回收站，可以恢复。"
        ):
            return

        try:
            # 删除游戏目录
            game_dir = self.root_dir / "games" / game_id
            if game_dir.exists():
                self.admin_manager.delete_config(str(game_dir))
                logger.info(f"游戏IP已删除: {game_id}")
                messagebox.showinfo("成功", f"游戏IP '{game_name}' 已删除并移动到回收站")

                # 刷新列表
                self._refresh_list()
                self._clear_editor()
            else:
                messagebox.showerror("错误", f"游戏目录不存在: {game_dir}")

        except Exception as e:
            logger.error(f"删除游戏IP失败: {e}")
            messagebox.showerror("错误", f"删除失败:\n{e}")

    def _load_game(self, game_id: str):
        """加载游戏IP数据到编辑器"""
        try:
            game_data = self.config_loader.games.get(game_id)
            if not game_data:
                messagebox.showerror("错误", f"游戏IP不存在: {game_id}")
                return

            self.current_game_id = game_id

            # 填充字段
            self.game_id_var.set(game_id)
            self.game_id_entry.config(state=tk.DISABLED)  # 禁止修改ID（作为主键，应保持不变）

            self.game_name_var.set(game_data.get("name", ""))
            # 将英文类型转换为中文显示
            game_type_en = game_data.get("type", "action")
            game_type_cn = self.GAME_TYPE_REVERSE_MAP.get(game_type_en, "动作")
            self.game_type_var.set(game_type_cn)

            desc = game_data.get("description", "")
            self.game_desc_text.delete("1.0", tk.END)
            self.game_desc_text.insert("1.0", desc)

            self.game_author_var.set(game_data.get("author", ""))
            self.game_version_var.set(game_data.get("version", "1.0.0"))
            self.game_icon_var.set(game_data.get("icon", ""))

            tags = game_data.get("tags", [])
            self.game_tags_var.set(", ".join(tags) if tags else "")

            logger.info(f"已加载游戏IP: {game_id}")

        except Exception as e:
            logger.error(f"加载游戏IP失败: {e}")
            messagebox.showerror("错误", f"加载失败:\n{e}")

    def _clear_editor(self):
        """清空编辑器"""
        self.current_game_id = None
        self.game_id_var.set("")
        self.game_id_entry.config(state=tk.NORMAL)
        self.game_name_var.set("")
        self.game_type_var.set("动作")  # 使用中文默认值
        self.game_desc_text.delete("1.0", tk.END)
        self.game_author_var.set("")
        self.game_version_var.set("1.0.0")
        self.game_icon_var.set("")
        self.game_tags_var.set("")

    def _select_icon(self):
        """选择游戏图标"""
        file_path = filedialog.askopenfilename(
            title="选择游戏图标",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg"), ("所有文件", "*.*")]
        )
        if file_path:
            self.game_icon_var.set(file_path)

    def _save_game(self):
        """保存游戏IP"""
        try:
            # 验证必填字段
            game_id = self.game_id_var.get().strip()
            game_name = self.game_name_var.get().strip()
            game_type = self.game_type_var.get().strip()

            if not game_id:
                messagebox.showwarning("验证失败", "请输入游戏ID")
                return

            if not game_name:
                messagebox.showwarning("验证失败", "请输入游戏名称")
                return

            # 验证游戏ID格式（只允许字母、数字、下划线）
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', game_id):
                messagebox.showwarning(
                    "验证失败",
                    "游戏ID只能包含英文字母、数字和下划线"
                )
                return

            # 如果是新增，检查ID是否已存在
            is_new = self.current_game_id is None
            if is_new and game_id in self.config_loader.games:
                messagebox.showwarning("验证失败", f"游戏ID '{game_id}' 已存在")
                return

            # 创建游戏目录
            game_dir = self.root_dir / "games" / game_id
            if is_new:
                game_dir.mkdir(parents=True, exist_ok=True)

                # 创建子目录
                (game_dir / "characters").mkdir(exist_ok=True)
                (game_dir / "skins").mkdir(exist_ok=True)
                (game_dir / "models").mkdir(exist_ok=True)
                (game_dir / "materials").mkdir(exist_ok=True)
                (game_dir / "assets").mkdir(exist_ok=True)

                logger.info(f"创建游戏目录结构: {game_dir}")

            # 处理图标（如果选择了新图标）
            icon_path = self.game_icon_var.get().strip()
            icon_relative_path = ""

            # 如果是编辑模式，先获取原有的图标路径
            if not is_new:
                icon_relative_path = self.config_loader.games.get(game_id, {}).get("icon", "")

            # 如果选择了新图标，则上传并更新路径
            if icon_path and Path(icon_path).exists():
                # 复制图标到游戏目录的 assets/icons/ 子目录
                icon_filename = Path(icon_path).name
                icons_dir = game_dir / "assets" / "icons"
                icons_dir.mkdir(parents=True, exist_ok=True)  # 创建 icons 子目录
                dest_icon = icons_dir / icon_filename
                shutil.copy2(icon_path, dest_icon)
                icon_relative_path = f"games/{game_id}/assets/icons/{icon_filename}"
                logger.info(f"图标已复制: {dest_icon}")

            # 处理标签
            tags_text = self.game_tags_var.get().strip()
            tags = [tag.strip() for tag in tags_text.split(",")] if tags_text else []

            # 将中文类型转换为英文存储
            game_type_en = self.GAME_TYPE_MAP.get(game_type, "action")

            # 构建配置数据
            game_config = {
                "game_id": game_id,
                "name": game_name,
                "type": game_type_en,  # 保存英文类型
                "description": self.game_desc_text.get("1.0", tk.END).strip(),
                "author": self.game_author_var.get().strip(),
                "version": self.game_version_var.get().strip(),
                "icon": icon_relative_path,
                "tags": tags,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if is_new else self.config_loader.games.get(game_id, {}).get("created_at", ""),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            # 保存meta.yaml
            meta_file = game_dir / "meta.yaml"
            with open(meta_file, 'w', encoding='utf-8') as f:
                yaml.dump(game_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            logger.info(f"游戏IP配置已保存: {meta_file}")

            # 记录操作日志
            operation = "创建" if is_new else "更新"
            self.admin_manager.log_operation(f"{operation}游戏IP", f"{game_name} ({game_id})")

            messagebox.showinfo("成功", f"游戏IP '{game_name}' 已{operation}成功！")

            # 刷新列表
            self._refresh_list()

            # 清空编辑器
            self._clear_editor()

        except Exception as e:
            logger.error(f"保存游戏IP失败: {e}")
            messagebox.showerror("错误", f"保存失败:\n{e}")

# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    root = tk.Tk()
    root.title("游戏IP管理器测试")
    root.geometry("1000x700")

    from core.config_loader import get_config_loader
    from core.admin_manager import AdminManager

    config_loader = get_config_loader(".")
    admin_manager = AdminManager(".")

    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)

    manager = GameManager(frame, config_loader, admin_manager)

    root.mainloop()
