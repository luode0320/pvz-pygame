"""
配置浏览器 - 树形结构显示所有配置文件
支持搜索、筛选、状态显示
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable
import yaml

logger = logging.getLogger(__name__)


class ConfigBrowser:
    """
    配置浏览器类
    功能：
    1. 树形视图显示所有配置
    2. 配置分类（游戏IP/角色/技能/皮肤/战役/关卡）
    3. 搜索和筛选
    4. 状态显示（有效/无效/缺少资源）
    5. 双击打开编辑器
    """

    def __init__(self, parent: tk.Frame, config_loader, admin_manager):
        """
        初始化配置浏览器

        参数:
            parent: 父容器
            config_loader: ConfigLoader实例
            admin_manager: AdminManager实例
        """
        self.parent = parent
        self.config_loader = config_loader
        self.admin_manager = admin_manager

        # 配置数据缓存
        self.config_data: Dict = {}

        # 编辑器回调
        self.editor_callbacks: Dict[str, Callable] = {}

        # 创建UI
        self._create_ui()

        # 加载配置数据
        self.refresh()

        logger.info("配置浏览器初始化完成")

    def _create_ui(self):
        """创建UI组件"""
        # 顶部工具栏
        toolbar = tk.Frame(self.parent, bg="#f0f0f0")
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        # 搜索框
        tk.Label(toolbar, text="搜索:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search)
        search_entry = tk.Entry(toolbar, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)

        # 筛选下拉框
        tk.Label(toolbar, text="类型:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.filter_var = tk.StringVar(value="全部")
        filter_combo = ttk.Combobox(
            toolbar,
            textvariable=self.filter_var,
            values=["全部", "游戏IP", "角色", "技能", "皮肤", "战役", "关卡"],
            state="readonly",
            width=12
        )
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind('<<ComboboxSelected>>', self._on_filter)

        # 刷新按钮
        refresh_btn = tk.Button(toolbar, text="刷新", command=self.refresh)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # 展开/折叠按钮
        expand_btn = tk.Button(toolbar, text="展开全部", command=self._expand_all)
        expand_btn.pack(side=tk.LEFT, padx=2)
        collapse_btn = tk.Button(toolbar, text="折叠全部", command=self._collapse_all)
        collapse_btn.pack(side=tk.LEFT, padx=2)

        # 树形视图和滚动条
        tree_frame = tk.Frame(self.parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 垂直滚动条
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 水平滚动条
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # 树形视图
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("type", "status", "path"),
            show="tree headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        self.tree.pack(fill=tk.BOTH, expand=True)

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # 配置列
        self.tree.heading("#0", text="名称")
        self.tree.heading("type", text="类型")
        self.tree.heading("status", text="状态")
        self.tree.heading("path", text="路径")

        self.tree.column("#0", width=250, minwidth=150)
        self.tree.column("type", width=100, minwidth=80)
        self.tree.column("status", width=80, minwidth=60)
        self.tree.column("path", width=300, minwidth=200)

        # 绑定双击事件
        self.tree.bind("<Double-Button-1>", self._on_double_click)

        # 右键菜单
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="编辑", command=self._edit_selected)
        self.context_menu.add_command(label="删除", command=self._delete_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="刷新", command=self.refresh)

        self.tree.bind("<Button-3>", self._show_context_menu)

        # 底部状态栏
        status_frame = tk.Frame(self.parent, bg="#f0f0f0")
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = tk.Label(
            status_frame,
            text="就绪",
            bg="#f0f0f0",
            anchor=tk.W
        )
        self.status_label.pack(fill=tk.X, padx=5)

    def refresh(self):
        """刷新配置数据"""
        try:
            self.status_label.config(text="正在扫描配置...")

            # 触发配置重新扫描
            self.config_loader.scan_all()

            # 收集配置数据
            self.config_data = {
                "games": self.config_loader.games,
                "characters": self.config_loader.characters,
                "skins": self.config_loader.skins,
                "campaigns": self.config_loader.campaigns,
                "levels": self.config_loader.levels,
            }

            # 重建树
            self._rebuild_tree()

            # 更新状态
            total = sum(len(items) for items in self.config_data.values())
            self.status_label.config(text=f"共加载 {total} 个配置")

            logger.info(f"配置刷新完成: {total}个配置")

        except Exception as e:
            logger.error(f"刷新配置失败: {e}")
            messagebox.showerror("错误", f"刷新配置失败:\n{e}")
            self.status_label.config(text="刷新失败")

    def _rebuild_tree(self):
        """重建树形视图（层级结构）"""
        # 清空树
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 获取搜索和筛选条件
        search_text = self.search_var.get().lower()
        filter_type = self.filter_var.get()

        # 构建游戏IP层级结构（游戏IP -> 角色、皮肤）
        if filter_type in ["全部", "游戏IP", "角色", "皮肤"]:
            games_node = self.tree.insert("", tk.END, text="游戏IP", tags=("category",))

            # 按游戏名称排序
            sorted_games = sorted(
                self.config_data.get("games", {}).items(),
                key=lambda x: x[1].get("name", x[0])
            )

            for game_id, game_data in sorted_games:
                game_name = game_data.get("name", game_id)

                # 搜索过滤
                if search_text and search_text not in game_name.lower():
                    # 检查该游戏下的角色和皮肤是否匹配搜索
                    has_match = False
                    if filter_type in ["全部", "角色"]:
                        for char_id, char_data in self.config_data.get("characters", {}).items():
                            if char_data.get("game_id") == game_id:
                                if search_text in char_data.get("name", "").lower():
                                    has_match = True
                                    break
                    if not has_match and filter_type in ["全部", "皮肤"]:
                        for skin_id, skin_data in self.config_data.get("skins", {}).items():
                            if skin_data.get("game_id") == game_id:
                                if search_text in skin_data.get("name", "").lower():
                                    has_match = True
                                    break
                    if not has_match:
                        continue

                # 添加游戏IP节点
                status = self._check_game_status(game_id, game_data)
                game_node = self.tree.insert(
                    games_node,
                    tk.END,
                    text=game_name,
                    values=("游戏IP", status, f"games/{game_id}"),
                    tags=(f"game:{game_id}", status.lower())
                )

                # 添加该游戏下的角色
                if filter_type in ["全部", "角色"]:
                    # 收集该游戏的角色
                    game_characters = {
                        char_id: char_data
                        for char_id, char_data in self.config_data.get("characters", {}).items()
                        if char_data.get("game_id") == game_id
                    }

                    if game_characters:
                        characters_subnode = self.tree.insert(
                            game_node, tk.END, text="角色", tags=("subcategory",)
                        )

                        # 按角色名称排序
                        sorted_chars = sorted(
                            game_characters.items(),
                            key=lambda x: x[1].get("name", x[0])
                        )

                        for char_id, char_data in sorted_chars:
                            char_name = char_data.get("name", char_id)
                            if search_text and search_text not in char_name.lower():
                                # 检查该角色的技能是否匹配搜索
                                has_skill_match = False
                                if filter_type in ["全部", "技能"]:
                                    for skill in char_data.get("skills", []):
                                        if search_text in skill.get("name", "").lower():
                                            has_skill_match = True
                                            break
                                if not has_skill_match:
                                    continue

                            status = self._check_character_status(char_id, char_data)
                            # 创建角色节点
                            char_node = self.tree.insert(
                                characters_subnode,
                                tk.END,
                                text=char_name,
                                values=("角色", status, f"games/{game_id}/characters/{char_id}"),
                                tags=(f"character:{char_id}", status.lower())
                            )

                            # 添加该角色的技能
                            if filter_type in ["全部", "角色", "技能"]:
                                skills = char_data.get("skills", [])
                                if skills:
                                    skills_subnode = self.tree.insert(
                                        char_node, tk.END, text="技能", tags=("subcategory",)
                                    )

                                    # 按技能顺序显示（保持配置文件中的顺序）
                                    for skill in skills:
                                        skill_name = skill.get("name", skill.get("skill_id", "未知技能"))
                                        skill_id = skill.get("skill_id", "")

                                        # 搜索过滤
                                        if search_text and search_text not in skill_name.lower():
                                            continue

                                        # 检查技能状态
                                        skill_status = self._check_skill_status(skill)

                                        # 技能类型和冷却时间
                                        skill_type = skill.get("type", "unknown")
                                        cooldown = skill.get("cooldown", 0)
                                        skill_info = f"{skill_name} ({skill_type}, CD:{cooldown}s)"

                                        self.tree.insert(
                                            skills_subnode,
                                            tk.END,
                                            text=skill_info,
                                            values=("技能", skill_status, f"games/{game_id}/characters/{char_id}/skills/{skill_id}"),
                                            tags=(f"skill:{char_id}:{skill_id}", skill_status.lower())
                                        )

                # 添加该游戏下的皮肤
                if filter_type in ["全部", "皮肤"]:
                    # 收集该游戏的皮肤
                    game_skins = {
                        skin_id: skin_data
                        for skin_id, skin_data in self.config_data.get("skins", {}).items()
                        if skin_data.get("game_id") == game_id
                    }

                    if game_skins:
                        skins_subnode = self.tree.insert(
                            game_node, tk.END, text="皮肤", tags=("subcategory",)
                        )

                        # 按皮肤名称排序
                        sorted_skins = sorted(
                            game_skins.items(),
                            key=lambda x: x[1].get("name", x[0])
                        )

                        for skin_id, skin_data in sorted_skins:
                            skin_name = skin_data.get("name", skin_id)
                            if search_text and search_text not in skin_name.lower():
                                continue

                            status = self._check_skin_status(skin_id, skin_data)
                            char_name = self.config_data.get("characters", {}).get(
                                skin_data.get("character_id"),
                                {}
                            ).get("name", "未知角色")

                            self.tree.insert(
                                skins_subnode,
                                tk.END,
                                text=f"{skin_name} ({char_name})",
                                values=("皮肤", status, f"games/{game_id}/skins/{skin_id}"),
                                tags=(f"skin:{skin_id}", status.lower())
                            )

        # 构建战役层级结构（战役 -> 关卡）
        if filter_type in ["全部", "战役", "关卡"]:
            campaigns_node = self.tree.insert("", tk.END, text="战役", tags=("category",))

            # 按战役名称排序
            sorted_campaigns = sorted(
                self.config_data.get("campaigns", {}).items(),
                key=lambda x: x[1].get("name", x[0])
            )

            for campaign_id, campaign_data in sorted_campaigns:
                campaign_name = campaign_data.get("name", campaign_id)

                # 搜索过滤
                if search_text and search_text not in campaign_name.lower():
                    # 检查该战役下的关卡是否匹配搜索
                    has_match = False
                    if filter_type in ["全部", "关卡"]:
                        for level_key, level_data in self.config_data.get("levels", {}).items():
                            if level_key.startswith(campaign_id + "/"):
                                if search_text in level_data.get("name", "").lower():
                                    has_match = True
                                    break
                    if not has_match:
                        continue

                # 添加战役节点
                status = self._check_campaign_status(campaign_id, campaign_data)
                campaign_node = self.tree.insert(
                    campaigns_node,
                    tk.END,
                    text=campaign_name,
                    values=("战役", status, f"campaigns/{campaign_id}"),
                    tags=(f"campaign:{campaign_id}", status.lower())
                )

                # 添加该战役下的关卡
                if filter_type in ["全部", "关卡"]:
                    # 收集该战役的关卡
                    campaign_levels = {
                        level_key: level_data
                        for level_key, level_data in self.config_data.get("levels", {}).items()
                        if level_key.startswith(campaign_id + "/")
                    }

                    if campaign_levels:
                        levels_subnode = self.tree.insert(
                            campaign_node, tk.END, text="关卡", tags=("subcategory",)
                        )

                        # 按关卡ID排序（保持level_01, level_02的顺序）
                        sorted_levels = sorted(campaign_levels.items(), key=lambda x: x[0])

                        for level_key, level_data in sorted_levels:
                            level_name = level_data.get("name", level_key)
                            if search_text and search_text not in level_name.lower():
                                continue

                            status = self._check_level_status(level_key, level_data)
                            # 只显示关卡名称，不显示战役ID（因为已经在层级中体现）
                            self.tree.insert(
                                levels_subnode,
                                tk.END,
                                text=level_name,
                                values=("关卡", status, f"campaigns/{level_key}"),
                                tags=(f"level:{level_key}", status.lower())
                            )

        # 配置标签样式
        self.tree.tag_configure("category", font=("Arial", 10, "bold"))
        self.tree.tag_configure("subcategory", font=("Arial", 9, "bold"), foreground="#333")
        self.tree.tag_configure("有效", foreground="green")
        self.tree.tag_configure("警告", foreground="orange")
        self.tree.tag_configure("无效", foreground="red")

    def _check_game_status(self, game_id: str, game_data: Dict) -> str:
        """检查游戏IP状态"""
        # 简单检查：是否有必需字段
        if not game_data.get("name"):
            return "无效"
        if not game_data.get("type"):
            return "警告"
        return "有效"

    def _check_character_status(self, char_id: str, char_data: Dict) -> str:
        """检查角色状态"""
        # 检查游戏IP是否存在
        game_id = char_data.get("game_id")
        if not game_id or game_id not in self.config_data.get("games", {}):
            return "无效"

        # 检查必需字段
        if not char_data.get("name"):
            return "无效"
        if not char_data.get("base_stats"):
            return "警告"

        return "有效"

    def _check_skin_status(self, skin_id: str, skin_data: Dict) -> str:
        """检查皮肤状态"""
        # 检查角色是否存在
        char_id = skin_data.get("character_id")
        if not char_id or char_id not in self.config_data.get("characters", {}):
            return "无效"

        # 检查必需字段
        if not skin_data.get("name"):
            return "无效"

        return "有效"

    def _check_campaign_status(self, campaign_id: str, campaign_data: Dict) -> str:
        """检查战役状态"""
        # 检查必需字段
        if not campaign_data.get("name"):
            return "无效"

        # 检查游戏IP
        defender = campaign_data.get("defender_game")
        attacker = campaign_data.get("attacker_game")
        games = self.config_data.get("games", {})

        if defender not in games or attacker not in games:
            return "警告"

        return "有效"

    def _check_level_status(self, level_key: str, level_data: Dict) -> str:
        """检查关卡状态"""
        # 检查必需字段
        if not level_data.get("name"):
            return "无效"
        if not level_data.get("waves"):
            return "警告"

        return "有效"

    def _check_skill_status(self, skill_data: Dict) -> str:
        """检查技能状态"""
        # 检查必需字段
        if not skill_data.get("name"):
            return "无效"
        if not skill_data.get("skill_id"):
            return "无效"
        if not skill_data.get("type"):
            return "警告"
        if skill_data.get("cooldown") is None:
            return "警告"

        return "有效"

    def _on_search(self, *args):
        """搜索框变化时触发"""
        self._rebuild_tree()

    def _on_filter(self, event):
        """筛选器变化时触发"""
        self._rebuild_tree()

    def _expand_all(self):
        """展开所有节点"""
        def expand_node(node):
            self.tree.item(node, open=True)
            for child in self.tree.get_children(node):
                expand_node(child)

        for item in self.tree.get_children():
            expand_node(item)

    def _collapse_all(self):
        """折叠所有节点"""
        for item in self.tree.get_children():
            self.tree.item(item, open=False)

    def _on_double_click(self, event):
        """双击打开编辑器"""
        self._edit_selected()

    def _show_context_menu(self, event):
        """显示右键菜单"""
        # 选中点击的项
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _edit_selected(self):
        """编辑选中的配置"""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        tags = self.tree.item(item, "tags")

        # 跳过分类节点
        if "category" in tags:
            return

        # 解析标签获取类型和ID
        for tag in tags:
            if ":" in tag:
                config_type, config_id = tag.split(":", 1)
                self._open_editor(config_type, config_id)
                break

    def _delete_selected(self):
        """删除选中的配置"""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        tags = self.tree.item(item, "tags")

        # 跳过分类节点
        if "category" in tags:
            return

        # 确认删除
        if not messagebox.askyesno("确认删除", "确定要删除选中的配置吗？\n删除的配置将移动到回收站。"):
            return

        try:
            # 获取配置路径
            path = self.tree.item(item, "values")[2]
            config_path = self.config_loader.root_dir / path

            # 删除配置（移动到回收站）
            self.admin_manager.delete_config(str(config_path))

            # 刷新树
            self.refresh()

            messagebox.showinfo("成功", "配置已删除并移动到回收站")

        except Exception as e:
            logger.error(f"删除配置失败: {e}")
            messagebox.showerror("错误", f"删除失败:\n{e}")

    def _open_editor(self, config_type: str, config_id: str):
        """打开配置编辑器"""
        # 查找对应的编辑器回调
        callback = self.editor_callbacks.get(config_type)
        if callback:
            callback(config_id)
        else:
            messagebox.showinfo(
                "提示",
                f"{config_type} 编辑器尚未实现\n将在后续Phase中完成"
            )

    def register_editor(self, config_type: str, callback: Callable):
        """
        注册配置编辑器回调

        参数:
            config_type: 配置类型（game/character/skill/skin/campaign/level）
            callback: 编辑器回调函数，接收config_id参数
        """
        self.editor_callbacks[config_type] = callback
        logger.info(f"注册编辑器: {config_type}")


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 创建测试窗口
    root = tk.Tk()
    root.title("配置浏览器测试")
    root.geometry("900x600")

    from core.config_loader import get_config_loader
    from core.admin_manager import AdminManager

    config_loader = get_config_loader(".")
    admin_manager = AdminManager(".")

    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True)

    browser = ConfigBrowser(frame, config_loader, admin_manager)

    root.mainloop()
