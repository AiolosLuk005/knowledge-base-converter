import os
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Inches
from copy import deepcopy


def is_valid_docx(file_path):
    """验证文件是否为有效的 DOCX 文件"""
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return False
        # 检查文件大小（空文件或过小的文件不是有效的 DOCX）
        if os.path.getsize(file_path) < 100:
            return False
        # 尝试作为 ZIP 文件打开
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # 检查是否包含 DOCX 必需的文件
            namelist = zip_ref.namelist()
            return '[Content_Types].xml' in namelist and 'word/document.xml' in namelist
    except (zipfile.BadZipFile, OSError, PermissionError):
        return False


def adjust_table_width(table, section=None):
    """
    调整表格宽度以适应A4纸张
    A4纸张宽度：
    - 竖向：8.27英寸，减去左右边距（各1英寸），有效宽度约6.5英寸
    - 横向：11.69英寸，减去左右边距（各1英寸），有效宽度约9.5英寸
    """
    try:
        # 确定有效宽度
        # 如果提供了section，根据页面方向判断
        if section:
            from docx.enum.section import WD_ORIENT
            # 检查是否为横向
            if section.orientation == WD_ORIENT.LANDSCAPE:
                effective_width = Inches(9.5)  # 横向
            else:
                effective_width = Inches(6.5)  # 竖向
        else:
            effective_width = Inches(6.5)  # 默认竖向
        
        # 设置表格总宽度
        table.width = effective_width
        
        # 如果表格有列宽设置，平均分配
        if table.columns:
            col_count = len(table.columns)
            col_width = effective_width / col_count
            for column in table.columns:
                column.width = col_width
                
        # 设置表格自动适应内容
        tbl_pr = table._element.find(qn('w:tblPr'))
        if tbl_pr is not None:
            # 检查是否已有tblLayout元素
            tbl_layout = tbl_pr.find(qn('w:tblLayout'))
            if tbl_layout is None:
                # 创建新的tblLayout元素
                tbl_layout = OxmlElement('w:tblLayout')
                tbl_layout.set(qn('w:type'), 'autofit')
                tbl_pr.append(tbl_layout)
            else:
                # 更新已有的tblLayout
                tbl_layout.set(qn('w:type'), 'autofit')
    except Exception as e:
        # 如果调整失败，忽略错误继续
        pass





def merge_docx_files(file_list, output_path, progress_callback=None):
    """
    合并多个 DOCX 文件为一个文件
    保持每个源文件的页面设置（横向/竖向）
    
    Args:
        file_list: 要合并的文件路径列表
        output_path: 输出文件路径
        progress_callback: 进度回调函数
    
    Returns:
        bool: 是否成功
    """
    try:
        if not file_list:
            raise ValueError("文件列表为空")
        
        # 创建新文档，使用第一个文件作为基础
        merged_doc = Document(file_list[0])
        
        # 调整第一个文档中的所有表格（根据第一个文档的section）
        if merged_doc.sections:
            first_section = merged_doc.sections[0]
            for table in merged_doc.tables:
                adjust_table_width(table, first_section)
        
        # 更新进度
        if progress_callback:
            progress_callback(1, len(file_list), os.path.basename(file_list[0]))
        
        # 从第二个文件开始合并
        for idx, file_path in enumerate(file_list[1:], start=2):
            # 读取要合并的文档
            source_doc = Document(file_path)
            
            # 获取源文档的section属性（页面设置）
            source_sections = source_doc.sections
            if not source_sections:
                continue
                
            # 在merged_doc中添加一个新section，复制源文档第一个section的设置
            # 这样可以保持页面方向（横向/竖向）
            source_first_section = source_sections[0]
            new_section = merged_doc.add_section()
            
            # 复制页面设置
            new_section.orientation = source_first_section.orientation
            new_section.page_width = source_first_section.page_width
            new_section.page_height = source_first_section.page_height
            new_section.left_margin = source_first_section.left_margin
            new_section.right_margin = source_first_section.right_margin
            new_section.top_margin = source_first_section.top_margin
            new_section.bottom_margin = source_first_section.bottom_margin
            
            # 复制源文档的所有内容元素（段落、表格等）
            for element in source_doc.element.body:
                # 跳过sectPr元素，因为我们已经通过add_section处理了
                if element.tag == qn('w:sectPr'):
                    continue
                
                # 深拷贝元素
                element_copy = deepcopy(element)
                
                # 将拷贝的元素插入到新section之前
                # merged_doc.element.body的最后一个元素是sectPr，我们要在它之前插入
                merged_doc.element.body.insert(-1, element_copy)
            
            # 调整所有表格的宽度（根据当前section的方向）
            for table in merged_doc.tables:
                adjust_table_width(table, new_section)

            
            # 更新进度
            if progress_callback:
                progress_callback(idx, len(file_list), os.path.basename(file_path))
        
        # 保存合并后的文档
        merged_doc.save(output_path)
        return True

        
    except Exception as e:
        print(f"❌ 合并文件时出错: {str(e)}")
        raise


class DocxMergerGUI:
    """DOCX 文件合并工具 GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("DOCX 文件合并工具")
        self.root.geometry("700x500")
        
        # 文件列表（存储完整路径）
        self.file_paths = []
        
        self.create_widgets()
    
    def create_widgets(self):
        """创建GUI组件"""
        # 标题
        title_label = tk.Label(
            self.root, 
            text="DOCX 文件合并工具",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=10)
        
        # 说明文字
        info_label = tk.Label(
            self.root,
            text="选择多个 DOCX 文件，调整顺序后合并成一个文件\n文件之间将自动插入分页符",
            font=("Arial", 9),
            fg="gray"
        )
        info_label.pack(pady=5)
        
        # 文件列表框架
        list_frame = tk.Frame(self.root)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 滚动条
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 列表框
        self.file_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Arial", 10),
            selectmode=tk.SINGLE
        )
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # 按钮框架
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        # 添加文件按钮
        add_btn = tk.Button(
            button_frame,
            text="➕ 添加文件",
            command=self.add_files,
            width=12,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold")
        )
        add_btn.grid(row=0, column=0, padx=5)
        
        # 删除文件按钮
        remove_btn = tk.Button(
            button_frame,
            text="🗑️ 删除选中",
            command=self.remove_file,
            width=12,
            bg="#f44336",
            fg="white",
            font=("Arial", 10, "bold")
        )
        remove_btn.grid(row=0, column=1, padx=5)
        
        # 上移按钮
        up_btn = tk.Button(
            button_frame,
            text="⬆️ 上移",
            command=self.move_up,
            width=12,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold")
        )
        up_btn.grid(row=0, column=2, padx=5)
        
        # 下移按钮
        down_btn = tk.Button(
            button_frame,
            text="⬇️ 下移",
            command=self.move_down,
            width=12,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold")
        )
        down_btn.grid(row=0, column=3, padx=5)
        
        # 合并按钮
        merge_btn = tk.Button(
            self.root,
            text="✅ 开始合并",
            command=self.merge_files,
            width=20,
            height=2,
            bg="#FF9800",
            fg="white",
            font=("Arial", 12, "bold")
        )
        merge_btn.pack(pady=10)
        
        # 状态栏
        self.status_label = tk.Label(
            self.root,
            text="准备就绪",
            font=("Arial", 9),
            fg="gray",
            anchor=tk.W
        )
        self.status_label.pack(fill=tk.X, padx=20, pady=5)
    
    def add_files(self):
        """添加文件到列表"""
        files = filedialog.askopenfilenames(
            title="选择 DOCX 文件",
            filetypes=[("Word 文档", "*.docx"), ("所有文件", "*.*")]
        )
        
        if not files:
            return
        
        # 验证并添加文件
        added_count = 0
        invalid_count = 0
        
        for file_path in files:
            # 验证文件
            if not is_valid_docx(file_path):
                invalid_count += 1
                continue
            
            # 避免重复添加
            if file_path in self.file_paths:
                continue
            
            # 添加到列表
            self.file_paths.append(file_path)
            # 显示文件名（带序号）
            display_name = f"{len(self.file_paths)}. {os.path.basename(file_path)}"
            self.file_listbox.insert(tk.END, display_name)
            added_count += 1
        
        # 更新状态
        status_msg = f"已添加 {added_count} 个文件"
        if invalid_count > 0:
            status_msg += f"，跳过 {invalid_count} 个无效文件"
        self.status_label.config(text=status_msg)
    
    def remove_file(self):
        """删除选中的文件"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的文件")
            return
        
        index = selection[0]
        # 从列表中删除
        self.file_listbox.delete(index)
        self.file_paths.pop(index)
        
        # 重新编号
        self.refresh_list()
        self.status_label.config(text=f"已删除文件，当前文件数: {len(self.file_paths)}")
    
    def move_up(self):
        """上移选中的文件"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要移动的文件")
            return
        
        index = selection[0]
        if index == 0:
            return  # 已经在顶部
        
        # 交换位置
        self.file_paths[index], self.file_paths[index - 1] = \
            self.file_paths[index - 1], self.file_paths[index]
        
        # 刷新显示
        self.refresh_list()
        # 保持选中状态
        self.file_listbox.selection_set(index - 1)
        self.status_label.config(text="已上移文件")
    
    def move_down(self):
        """下移选中的文件"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要移动的文件")
            return
        
        index = selection[0]
        if index >= len(self.file_paths) - 1:
            return  # 已经在底部
        
        # 交换位置
        self.file_paths[index], self.file_paths[index + 1] = \
            self.file_paths[index + 1], self.file_paths[index]
        
        # 刷新显示
        self.refresh_list()
        # 保持选中状态
        self.file_listbox.selection_set(index + 1)
        self.status_label.config(text="已下移文件")
    
    def refresh_list(self):
        """刷新文件列表显示"""
        self.file_listbox.delete(0, tk.END)
        for idx, file_path in enumerate(self.file_paths, start=1):
            display_name = f"{idx}. {os.path.basename(file_path)}"
            self.file_listbox.insert(tk.END, display_name)
    
    def merge_files(self):
        """执行文件合并"""
        if not self.file_paths:
            messagebox.showwarning("提示", "请先添加至少一个文件")
            return
        
        # 生成默认文件名：(第一个文档名称)等(文档总数)份文档合并.docx
        first_file_name = os.path.splitext(os.path.basename(self.file_paths[0]))[0]
        total_count = len(self.file_paths)
        default_filename = f"{first_file_name}等{total_count}份文档合并.docx"
        
        # 选择保存位置
        output_path = filedialog.asksaveasfilename(
            title="选择保存位置",
            defaultextension=".docx",
            filetypes=[("Word 文档", "*.docx")],
            initialfile=default_filename
        )
        
        if not output_path:
            return
        
        # 创建进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("合并进度")
        progress_window.geometry("400x150")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # 进度标签
        progress_label = tk.Label(
            progress_window,
            text="正在合并文件...",
            font=("Arial", 10)
        )
        progress_label.pack(pady=20)
        
        # 进度条
        progress_bar = ttk.Progressbar(
            progress_window,
            length=300,
            mode='determinate'
        )
        progress_bar.pack(pady=10)
        
        # 文件名标签
        file_label = tk.Label(
            progress_window,
            text="",
            font=("Arial", 9),
            fg="gray"
        )
        file_label.pack(pady=10)
        
        def update_progress(current, total, filename):
            """更新进度"""
            progress = (current / total) * 100
            progress_bar['value'] = progress
            file_label.config(text=f"正在处理: {filename}")
            progress_window.update()
        
        try:
            # 执行合并
            merge_docx_files(self.file_paths, output_path, update_progress)
            
            # 关闭进度窗口
            progress_window.destroy()
            
            # 显示成功消息
            messagebox.showinfo(
                "成功",
                f"文件合并完成！\n\n"
                f"合并文件数: {len(self.file_paths)}\n"
                f"输出位置: {output_path}"
            )
            
            self.status_label.config(text=f"✅ 合并成功: {os.path.basename(output_path)}")
            
        except Exception as e:
            # 关闭进度窗口
            progress_window.destroy()
            
            # 显示错误消息
            messagebox.showerror("错误", f"合并失败:\n{str(e)}")
            self.status_label.config(text="❌ 合并失败")


def main():
    """主函数"""
    root = tk.Tk()
    app = DocxMergerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
