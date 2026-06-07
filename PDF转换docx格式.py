import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

from pdf2docx import Converter

# Force UTF-8 encoding for stdout and stderr to prevent UnicodeEncodeError on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")



def select_path():
    """选择文件或文件夹路径"""
    root = tk.Tk()
    root.withdraw()
    choice = messagebox.askyesno("选择方式", "是否处理整个文件夹？\n是 = 文件夹，否 = 单个文件")
    if choice:
        folder = filedialog.askdirectory(title="选择包含 PDF 文件的文件夹")
        return "folder", folder if folder else None
    file_path = filedialog.askopenfilename(title="选择 PDF 文件", filetypes=[("PDF 文件", "*.pdf")])
    return "file", file_path if file_path else None


def convert_pdf_to_docx(pdf_path):
    """
    将PDF转换为DOCX，保留图片、表格和格式
    使用pdf2docx库进行转换，可以保留：
    - 文本格式（字体、大小、颜色等）
    - 图片和图形
    - 表格（结构和内容）
    - 页面布局
    """
    try:
        docx_path = os.path.splitext(pdf_path)[0] + ".docx"
        
        # 创建转换器
        cv = Converter(pdf_path)
        
        # 转换PDF到DOCX
        # start: 起始页（默认0）
        # end: 结束页（默认None，表示所有页）
        cv.convert(docx_path, start=0, end=None)
        
        # 关闭转换器
        cv.close()
        
        print(f"✅ 已处理：{os.path.basename(pdf_path)}")
        print(f"   ➤ DOCX 输出：{docx_path}")
        
    except Exception as e:
        print(f"❌ 转换失败：{os.path.basename(pdf_path)}")
        print(f"   ➤ 错误信息：{str(e)}")


def main():
    """主函数"""
    print("=" * 60)
    print("PDF 转 DOCX 工具（保留图片、表格和格式）")
    print("=" * 60)
    
    mode, path = select_path()
    if not path:
        print("❌ 未选择路径。")
        return

    if mode == "file":
        print(f"\n📄 处理单个文件...")
        convert_pdf_to_docx(path)
    elif mode == "folder":
        print(f"\n📁 处理文件夹：{path}")
        files = [f for f in os.listdir(path) if f.lower().endswith(".pdf")]
        if not files:
            print("❌ 文件夹中无 .pdf 文件。")
            return
        
        print(f"找到 {len(files)} 个 PDF 文件\n")
        for index, file in enumerate(files, 1):
            print(f"[{index}/{len(files)}] 处理中...")
            full_path = os.path.join(path, file)
            convert_pdf_to_docx(full_path)
            print()
    
    print("=" * 60)
    print("✨ 转换完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
