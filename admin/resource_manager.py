"""
资源管理器 - Phase 11
提供资源浏览、上传、删除、预览功能
支持图片、音频、模型等多种资源类型
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import shutil
import os
from typing import Dict, List, Optional
from logger_config import logger


class ResourceManager:
    """资源管理器"""

    def __init__(self, parent, config_loader, admin_manager):
        self.parent = parent
        self.config_loader = config_loader
        self.admin_manager = admin_manager
        self.root_dir = Path(__file__).parent.parent

        # 资源类型配置
        self.resource_types = {
            "images": {
                "name": "图片资源",
                "extensions": [".png", ".jpg", ".jpeg"],
                "folders": ["assets/images", "games/*/assets/sprites", "campaigns/*/assets"],
                "max_size": 2048 * 2048  # 2MB
            },
            "audio": {
                "name": "音频资源",
                "extensions": [".wav", ".ogg", ".mp3"],
                "folders": ["assets/sounds", "games/*/assets/sounds"],
                "max_size": 5 * 1024 * 1024  # 5MB
            },
            "models": {
                "name": "模型资源",
                "extensions": [".fbx", ".glb"],
                "folders": ["assets/models", "games/*/assets/models"],
                "max_size": 50 * 1024 * 1024  # 50MB
            },
            "maps": {
                "name": "地图资源",
                "extensions": [".png", ".json"],
                "folders": ["campaigns/*/levels/maps"],
                "max_size": 2048 * 2048
            }
        }

        # 当前选择
        self.current_type = "images"
        self.current_files = []
        self.selected_file = None

        # 创建主布局
        self._create_layout()

        # 加载资源列表
        self._load_resources()

    def _create_layout(self):
        """创建主布局"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(toolbar, text="资源管理器", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="上传文件", command=self._upload_file).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="批量上传", command=self._batch_upload).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="删除选中", command=self._delete_selected).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="刷新", command=self._load_resources).pack(side=tk.RIGHT, padx=5)

        # 分隔线
        ttk.Separator(self.parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # 主内容区域
        main_pane = ttk.Frame(self.parent)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧：资源类型
        left_frame = ttk.Frame(main_pane, width=150)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="资源类型", font=("Arial", 10, "bold")).pack(pady=5)

        self.type_listbox = tk.Listbox(left_frame, font=("Arial", 9))
        self.type_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.type_listbox.bind("<<ListboxSelect>>", self._on_type_selected)

        for type_key, type_info in self.resource_types.items():
            self.type_listbox.insert(tk.END, type_info["name"])

        self.type_listbox.selection_set(0)

        # 中间：文件列表
        middle_frame = ttk.Frame(main_pane)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # 搜索框
        search_frame = ttk.Frame(middle_frame)
        search_frame.pack(fill=tk.X, pady=5)

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._filter_files())
        ttk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)

        # 文件列表
        list_frame = ttk.Frame(middle_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview显示文件列表
        columns = ("name", "size", "path")
        self.file_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_tree.configure(yscrollcommand=scrollbar.set)

        # 列标题
        self.file_tree.heading("name", text="文件名")
        self.file_tree.heading("size", text="大小")
        self.file_tree.heading("path", text="路径")

        # 列宽
        self.file_tree.column("name", width=200)
        self.file_tree.column("size", width=100)
        self.file_tree.column("path", width=300)

        self.file_tree.bind("<<TreeviewSelect>>", self._on_file_selected)

        # 右侧：预览和详情
        right_frame = ttk.Frame(main_pane, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5)
        right_frame.pack_propagate(False)

        ttk.Label(right_frame, text="文件详情", font=("Arial", 10, "bold")).pack(pady=5)

        # 详情显示区域
        details_frame = ttk.LabelFrame(right_frame, text="基本信息")
        details_frame.pack(fill=tk.X, padx=5, pady=5)

        self.detail_labels = {}

        detail_items = [
            ("文件名:", "name"),
            ("文件类型:", "type"),
            ("文件大小:", "size"),
            ("完整路径:", "path"),
            ("修改时间:", "mtime")
        ]

        for i, (label_text, key) in enumerate(detail_items):
            ttk.Label(details_frame, text=label_text, font=("Arial", 8, "bold")).grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            label = ttk.Label(details_frame, text="-", font=("Arial", 8), wraplength=250)
            label.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
            self.detail_labels[key] = label

        # 预览区域（仅用于图片）
        preview_frame = ttk.LabelFrame(right_frame, text="预览")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.preview_label = ttk.Label(preview_frame, text="选择图片文件以预览", foreground="gray", anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 统计信息
        stats_frame = ttk.LabelFrame(right_frame, text="统计信息")
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        self.stats_label = ttk.Label(stats_frame, text="", font=("Arial", 8), justify=tk.LEFT)
        self.stats_label.pack(padx=10, pady=5)

    def _on_type_selected(self, event):
        """资源类型选择"""
        selection = self.type_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        type_keys = list(self.resource_types.keys())
        self.current_type = type_keys[idx]

        self._load_resources()

    def _load_resources(self):
        """加载资源列表"""
        self.current_files = []
        type_info = self.resource_types[self.current_type]

        # 扫描文件夹
        for folder_pattern in type_info["folders"]:
            # 处理通配符
            if "*" in folder_pattern:
                # 分割路径
                parts = folder_pattern.split("*")
                base_dir = self.root_dir / parts[0].strip("/")

                if base_dir.exists():
                    # 查找匹配的子目录
                    for subdir in base_dir.iterdir():
                        if subdir.is_dir():
                            full_path = subdir / parts[1].strip("/")
                            if full_path.exists():
                                self._scan_folder(full_path, type_info["extensions"])
            else:
                folder_path = self.root_dir / folder_pattern
                if folder_path.exists():
                    self._scan_folder(folder_path, type_info["extensions"])

        # 显示文件列表
        self._filter_files()

        # 更新统计
        self._update_stats()

    def _scan_folder(self, folder: Path, extensions: List[str]):
        """扫描文件夹"""
        try:
            for file_path in folder.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in extensions:
                    self.current_files.append(file_path)
        except Exception as e:
            logger.error(f"扫描文件夹失败 {folder}: {e}")

    def _filter_files(self):
        """筛选文件列表"""
        # 清空列表
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        # 获取搜索关键词
        search_term = self.search_var.get().lower()

        # 过滤和显示
        for file_path in self.current_files:
            if search_term and search_term not in file_path.name.lower():
                continue

            # 获取文件信息
            try:
                file_size = file_path.stat().st_size
                size_str = self._format_size(file_size)

                # 相对路径
                try:
                    rel_path = file_path.relative_to(self.root_dir)
                except ValueError:
                    rel_path = file_path

                self.file_tree.insert("", "end", values=(
                    file_path.name,
                    size_str,
                    str(rel_path)
                ))
            except Exception as e:
                logger.error(f"获取文件信息失败 {file_path}: {e}")

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def _on_file_selected(self, event):
        """文件选择"""
        selection = self.file_tree.selection()
        if not selection:
            return

        item = selection[0]
        values = self.file_tree.item(item, "values")

        if not values:
            return

        file_name = values[0]
        rel_path = values[2]

        # 查找完整路径
        full_path = self.root_dir / rel_path
        self.selected_file = full_path

        # 更新详情
        self._update_details(full_path)

        # 更新预览（仅图片）
        self._update_preview(full_path)

    def _update_details(self, file_path: Path):
        """更新文件详情"""
        try:
            stat = file_path.stat()

            self.detail_labels["name"].config(text=file_path.name)
            self.detail_labels["type"].config(text=file_path.suffix.upper()[1:])
            self.detail_labels["size"].config(text=self._format_size(stat.st_size))

            # 相对路径
            try:
                rel_path = file_path.relative_to(self.root_dir)
            except ValueError:
                rel_path = file_path

            self.detail_labels["path"].config(text=str(rel_path))

            # 修改时间
            import datetime
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
            self.detail_labels["mtime"].config(text=mtime.strftime("%Y-%m-%d %H:%M:%S"))

        except Exception as e:
            logger.error(f"更新文件详情失败: {e}")

    def _update_preview(self, file_path: Path):
        """更新预览（仅图片）"""
        # 清空预览
        self.preview_label.config(image="", text="")

        if self.current_type == "images" and file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            try:
                from PIL import Image, ImageTk

                # 加载图片
                img = Image.open(file_path)

                # 缩放到合适大小
                max_size = (250, 250)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

                # 转换为Tkinter格式
                photo = ImageTk.PhotoImage(img)

                self.preview_label.config(image=photo, text="")
                self.preview_label.image = photo  # 保持引用

            except ImportError:
                self.preview_label.config(text="需要安装Pillow库\n才能预览图片", foreground="orange")
            except Exception as e:
                self.preview_label.config(text=f"预览失败:\n{e}", foreground="red")
        else:
            self.preview_label.config(text=f"{file_path.suffix.upper()[1:]} 文件\n不支持预览", foreground="gray")

    def _update_stats(self):
        """更新统计信息"""
        total_files = len(self.current_files)
        total_size = sum(f.stat().st_size for f in self.current_files if f.exists())

        stats_text = f"文件数量: {total_files}\n"
        stats_text += f"总大小: {self._format_size(total_size)}"

        self.stats_label.config(text=stats_text)

    def _upload_file(self):
        """上传文件"""
        type_info = self.resource_types[self.current_type]

        # 文件选择对话框
        file_types = [(type_info["name"], " ".join(f"*{ext}" for ext in type_info["extensions"]))]

        file_path = filedialog.askopenfilename(
            title=f"选择{type_info['name']}",
            filetypes=file_types
        )

        if not file_path:
            return

        file_path = Path(file_path)

        # 验证文件类型
        if file_path.suffix.lower() not in type_info["extensions"]:
            messagebox.showerror("错误", f"不支持的文件类型: {file_path.suffix}")
            return

        # 验证文件大小
        file_size = file_path.stat().st_size
        if file_size > type_info["max_size"]:
            messagebox.showerror("错误", f"文件太大，最大允许: {self._format_size(type_info['max_size'])}")
            return

        # 选择目标目录
        dest_dir = self._select_destination()
        if not dest_dir:
            return

        # 复制文件
        try:
            dest_path = dest_dir / file_path.name

            # 检查重名
            if dest_path.exists():
                if not messagebox.askyesno("确认", f"文件已存在:\n{dest_path.name}\n是否覆盖？"):
                    return

            # 确保目录存在
            dest_dir.mkdir(parents=True, exist_ok=True)

            # 复制
            shutil.copy2(file_path, dest_path)

            logger.info(f"上传文件: {file_path.name} -> {dest_path}")
            messagebox.showinfo("成功", f"文件已上传:\n{dest_path}")

            # 刷新列表
            self._load_resources()

        except Exception as e:
            logger.error(f"上传文件失败: {e}")
            messagebox.showerror("错误", f"上传文件失败:\n{e}")

    def _batch_upload(self):
        """批量上传"""
        type_info = self.resource_types[self.current_type]

        # 文件选择对话框（多选）
        file_types = [(type_info["name"], " ".join(f"*{ext}" for ext in type_info["extensions"]))]

        file_paths = filedialog.askopenfilenames(
            title=f"选择多个{type_info['name']}",
            filetypes=file_types
        )

        if not file_paths:
            return

        # 选择目标目录
        dest_dir = self._select_destination()
        if not dest_dir:
            return

        # 批量复制
        success_count = 0
        fail_count = 0

        for file_path_str in file_paths:
            file_path = Path(file_path_str)

            # 验证
            if file_path.suffix.lower() not in type_info["extensions"]:
                fail_count += 1
                continue

            if file_path.stat().st_size > type_info["max_size"]:
                fail_count += 1
                continue

            # 复制
            try:
                dest_path = dest_dir / file_path.name

                # 确保目录存在
                dest_dir.mkdir(parents=True, exist_ok=True)

                # 复制（覆盖）
                shutil.copy2(file_path, dest_path)
                success_count += 1

            except Exception as e:
                logger.error(f"上传文件失败 {file_path.name}: {e}")
                fail_count += 1

        # 结果
        messagebox.showinfo("批量上传完成", f"成功: {success_count}\n失败: {fail_count}")

        # 刷新
        self._load_resources()

    def _select_destination(self) -> Optional[Path]:
        """选择目标目录"""
        type_info = self.resource_types[self.current_type]

        # 获取可用目录
        available_dirs = []
        for folder_pattern in type_info["folders"]:
            if "*" not in folder_pattern:
                folder_path = self.root_dir / folder_pattern
                available_dirs.append((folder_pattern, folder_path))

        if not available_dirs:
            messagebox.showerror("错误", "没有可用的目标目录")
            return None

        # 简单选择对话框
        dialog = tk.Toplevel()
        dialog.title("选择目标目录")
        dialog.geometry("400x300")
        dialog.transient(self.parent)
        dialog.grab_set()

        ttk.Label(dialog, text="选择目标目录:", font=("Arial", 10, "bold")).pack(pady=10)

        listbox = tk.Listbox(dialog, font=("Arial", 9))
        listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        for folder_pattern, _ in available_dirs:
            listbox.insert(tk.END, folder_pattern)

        listbox.selection_set(0)

        selected_dir = [None]

        def on_ok():
            selection = listbox.curselection()
            if selection:
                selected_dir[0] = available_dirs[selection[0]][1]
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)

        dialog.wait_window()

        return selected_dir[0]

    def _delete_selected(self):
        """删除选中文件"""
        if not self.selected_file:
            messagebox.showwarning("警告", "请先选择要删除的文件")
            return

        if not messagebox.askyesno("确认删除", f"确定要删除文件吗？\n{self.selected_file.name}\n将移动到回收站"):
            return

        try:
            # 移动到回收站
            self.admin_manager.move_to_recycle_bin(self.selected_file, f"resource_{self.selected_file.name}")

            logger.info(f"删除资源文件: {self.selected_file}")
            messagebox.showinfo("成功", "文件已删除")

            self.selected_file = None
            self._load_resources()

        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            messagebox.showerror("错误", f"删除文件失败:\n{e}")
