"""
回收站与日志管理器 - Phase 12
提供回收站浏览、恢复、永久删除功能
提供操作日志查看、筛选、导出功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from pathlib import Path
import shutil
import datetime
from typing import List, Dict
from logger_config import logger


class RecycleLogManager:
    """回收站与日志管理器"""

    def __init__(self, parent, config_loader, admin_manager):
        self.parent = parent
        self.config_loader = config_loader
        self.admin_manager = admin_manager
        self.root_dir = Path(__file__).parent.parent

        # 回收站路径
        self.recycle_bin_path = self.root_dir / "admin" / "recycle_bin"
        self.log_file_path = self.root_dir / "admin" / "admin_log.txt"

        # 创建主布局
        self._create_layout()

        # 加载数据
        self._load_recycle_bin()
        self._load_logs()

    def _create_layout(self):
        """创建主布局"""
        # 标签页
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: 回收站
        self.recycle_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.recycle_tab, text="回收站")

        # Tab 2: 操作日志
        self.log_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.log_tab, text="操作日志")

        self._create_recycle_tab()
        self._create_log_tab()

    def _create_recycle_tab(self):
        """创建回收站标签页"""
        # 工具栏
        toolbar = ttk.Frame(self.recycle_tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(toolbar, text="回收站管理", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="恢复选中", command=self._restore_item).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="永久删除", command=self._permanently_delete).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="清空回收站", command=self._empty_recycle_bin).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="刷新", command=self._load_recycle_bin).pack(side=tk.RIGHT, padx=5)

        # 分隔线
        ttk.Separator(self.recycle_tab, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # 说明
        info_frame = ttk.Frame(self.recycle_tab)
        info_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(info_frame, text="💡 回收站说明:", font=("Arial", 9, "bold")).pack(anchor=tk.W)
        ttk.Label(info_frame, text="• 删除的配置文件和资源会暂时保存在回收站", foreground="gray", font=("Arial", 8)).pack(anchor=tk.W, padx=20)
        ttk.Label(info_frame, text="• 可以恢复误删的文件，或永久删除不需要的文件", foreground="gray", font=("Arial", 8)).pack(anchor=tk.W, padx=20)
        ttk.Label(info_frame, text="• 清空回收站将永久删除所有文件，无法恢复", foreground="red", font=("Arial", 8)).pack(anchor=tk.W, padx=20)

        # 文件列表
        list_frame = ttk.Frame(self.recycle_tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview
        columns = ("name", "type", "delete_time", "size")
        self.recycle_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        self.recycle_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.recycle_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.recycle_tree.configure(yscrollcommand=scrollbar.set)

        # 列标题
        self.recycle_tree.heading("name", text="文件名")
        self.recycle_tree.heading("type", text="类型")
        self.recycle_tree.heading("delete_time", text="删除时间")
        self.recycle_tree.heading("size", text="大小")

        # 列宽
        self.recycle_tree.column("name", width=300)
        self.recycle_tree.column("type", width=100)
        self.recycle_tree.column("delete_time", width=150)
        self.recycle_tree.column("size", width=100)

        # 统计信息
        self.recycle_stats_label = ttk.Label(self.recycle_tab, text="", font=("Arial", 8))
        self.recycle_stats_label.pack(pady=5)

    def _create_log_tab(self):
        """创建操作日志标签页"""
        # 工具栏
        toolbar = ttk.Frame(self.log_tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(toolbar, text="操作日志", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="导出日志", command=self._export_log).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="清空日志", command=self._clear_log).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="刷新", command=self._load_logs).pack(side=tk.RIGHT, padx=5)

        # 分隔线
        ttk.Separator(self.log_tab, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # 筛选栏
        filter_frame = ttk.Frame(self.log_tab)
        filter_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(filter_frame, text="筛选:").pack(side=tk.LEFT, padx=5)

        self.log_filter_var = tk.StringVar()
        self.log_filter_var.trace_add("write", lambda *args: self._filter_logs())
        ttk.Entry(filter_frame, textvariable=self.log_filter_var, width=30).pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="级别:").pack(side=tk.LEFT, padx=10)
        self.log_level_var = tk.StringVar(value="全部")
        level_combo = ttk.Combobox(filter_frame, textvariable=self.log_level_var, state="readonly", width=10)
        level_combo['values'] = ["全部", "INFO", "WARNING", "ERROR"]
        level_combo.pack(side=tk.LEFT, padx=5)
        level_combo.bind("<<ComboboxSelected>>", lambda e: self._filter_logs())

        # 日志文本框
        log_frame = ttk.Frame(self.log_tab)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置颜色标签
        self.log_text.tag_config("INFO", foreground="blue")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")

        # 统计信息
        self.log_stats_label = ttk.Label(self.log_tab, text="", font=("Arial", 8))
        self.log_stats_label.pack(pady=5)

    def _load_recycle_bin(self):
        """加载回收站"""
        # 清空列表
        for item in self.recycle_tree.get_children():
            self.recycle_tree.delete(item)

        if not self.recycle_bin_path.exists():
            self.recycle_bin_path.mkdir(parents=True, exist_ok=True)

        # 扫描回收站
        total_size = 0
        file_count = 0

        for item_path in self.recycle_bin_path.iterdir():
            if item_path.is_file():
                try:
                    stat = item_path.stat()
                    size = stat.st_size
                    total_size += size

                    # 删除时间
                    mtime = datetime.datetime.fromtimestamp(stat.st_mtime)

                    # 文件类型
                    if item_path.suffix:
                        file_type = item_path.suffix.upper()[1:]
                    else:
                        file_type = "文件"

                    self.recycle_tree.insert("", "end", values=(
                        item_path.name,
                        file_type,
                        mtime.strftime("%Y-%m-%d %H:%M:%S"),
                        self._format_size(size)
                    ))

                    file_count += 1

                except Exception as e:
                    logger.error(f"读取回收站文件失败 {item_path}: {e}")

        # 更新统计
        stats_text = f"文件数量: {file_count}  |  总大小: {self._format_size(total_size)}"
        self.recycle_stats_label.config(text=stats_text)

    def _restore_item(self):
        """恢复选中项"""
        selection = self.recycle_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要恢复的文件")
            return

        item = selection[0]
        values = self.recycle_tree.item(item, "values")
        file_name = values[0]

        file_path = self.recycle_bin_path / file_name

        if not file_path.exists():
            messagebox.showerror("错误", "文件不存在")
            return

        # 让用户选择恢复位置
        dest_dir = filedialog.askdirectory(title="选择恢复位置", initialdir=self.root_dir)
        if not dest_dir:
            return

        dest_path = Path(dest_dir) / file_name

        # 检查重名
        if dest_path.exists():
            if not messagebox.askyesno("确认", f"目标位置已有同名文件:\n{file_name}\n是否覆盖？"):
                return

        try:
            shutil.move(str(file_path), str(dest_path))
            logger.info(f"恢复文件: {file_name} -> {dest_path}")
            messagebox.showinfo("成功", f"文件已恢复到:\n{dest_path}")

            self._load_recycle_bin()

        except Exception as e:
            logger.error(f"恢复文件失败: {e}")
            messagebox.showerror("错误", f"恢复文件失败:\n{e}")

    def _permanently_delete(self):
        """永久删除选中项"""
        selection = self.recycle_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的文件")
            return

        item = selection[0]
        values = self.recycle_tree.item(item, "values")
        file_name = values[0]

        if not messagebox.askyesno("确认永久删除", f"确定要永久删除吗？\n{file_name}\n此操作无法撤销！"):
            return

        file_path = self.recycle_bin_path / file_name

        try:
            file_path.unlink()
            logger.info(f"永久删除文件: {file_name}")
            messagebox.showinfo("成功", "文件已永久删除")

            self._load_recycle_bin()

        except Exception as e:
            logger.error(f"永久删除文件失败: {e}")
            messagebox.showerror("错误", f"永久删除文件失败:\n{e}")

    def _empty_recycle_bin(self):
        """清空回收站"""
        if not messagebox.askyesno("确认清空", "确定要清空回收站吗？\n所有文件将被永久删除，无法恢复！"):
            return

        try:
            count = 0
            for item_path in self.recycle_bin_path.iterdir():
                if item_path.is_file():
                    item_path.unlink()
                    count += 1

            logger.info(f"清空回收站，删除 {count} 个文件")
            messagebox.showinfo("成功", f"已清空回收站，删除 {count} 个文件")

            self._load_recycle_bin()

        except Exception as e:
            logger.error(f"清空回收站失败: {e}")
            messagebox.showerror("错误", f"清空回收站失败:\n{e}")

    def _load_logs(self):
        """加载日志"""
        self.all_logs = []

        if not self.log_file_path.exists():
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, "日志文件不存在")
            return

        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                self.all_logs = f.readlines()

            self._filter_logs()

        except Exception as e:
            logger.error(f"加载日志失败: {e}")
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"加载日志失败:\n{e}")

    def _filter_logs(self):
        """筛选日志"""
        # 清空
        self.log_text.delete(1.0, tk.END)

        # 获取筛选条件
        search_term = self.log_filter_var.get().lower()
        level_filter = self.log_level_var.get()

        # 筛选和显示
        displayed_count = 0

        for line in self.all_logs:
            # 关键词筛选
            if search_term and search_term not in line.lower():
                continue

            # 级别筛选
            if level_filter != "全部":
                if level_filter not in line:
                    continue

            # 显示
            self.log_text.insert(tk.END, line)

            # 颜色标记
            if "ERROR" in line:
                # 查找行号
                line_num = self.log_text.index(tk.INSERT).split('.')[0]
                self.log_text.tag_add("ERROR", f"{line_num}.0", f"{line_num}.end")
            elif "WARNING" in line:
                line_num = self.log_text.index(tk.INSERT).split('.')[0]
                self.log_text.tag_add("WARNING", f"{line_num}.0", f"{line_num}.end")
            elif "INFO" in line:
                line_num = self.log_text.index(tk.INSERT).split('.')[0]
                self.log_text.tag_add("INFO", f"{line_num}.0", f"{line_num}.end")

            displayed_count += 1

        # 更新统计
        stats_text = f"总日志数: {len(self.all_logs)}  |  显示: {displayed_count}"
        self.log_stats_label.config(text=stats_text)

        # 滚动到底部
        self.log_text.see(tk.END)

    def _export_log(self):
        """导出日志"""
        file_path = filedialog.asksaveasfilename(
            title="导出日志",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )

        if not file_path:
            return

        try:
            # 获取当前显示的内容
            content = self.log_text.get(1.0, tk.END)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"导出日志: {file_path}")
            messagebox.showinfo("成功", f"日志已导出到:\n{file_path}")

        except Exception as e:
            logger.error(f"导出日志失败: {e}")
            messagebox.showerror("错误", f"导出日志失败:\n{e}")

    def _clear_log(self):
        """清空日志"""
        if not messagebox.askyesno("确认清空", "确定要清空操作日志吗？\n此操作无法撤销！"):
            return

        try:
            # 备份
            backup_path = self.log_file_path.with_suffix('.txt.bak')
            shutil.copy2(self.log_file_path, backup_path)

            # 清空
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                f.write("")

            logger.info("清空操作日志")
            messagebox.showinfo("成功", f"操作日志已清空\n备份保存在:\n{backup_path}")

            self._load_logs()

        except Exception as e:
            logger.error(f"清空日志失败: {e}")
            messagebox.showerror("错误", f"清空日志失败:\n{e}")

    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
