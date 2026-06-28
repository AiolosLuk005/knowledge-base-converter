# -*- coding: utf-8 -*-
import os
import sys
from tkinter import Tk, filedialog
from win32com.client import Dispatch

# 解决在某些终端（如VS Code）中中文乱码的问题
# 强制标准输出使用UTF-8编码
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def select_folder():
    """
    弹出对话框让用户选择一个文件夹
    """
    root = Tk()
    root.withdraw()  # 隐藏 Tkinter 的主窗口
    folder_path = filedialog.askdirectory(title="请选择要转换文件的文件夹")
    return folder_path

def convert_doc_to_docx(folder_path):
    """
    将指定文件夹中的所有 .doc 文件转换为 .docx 文件。
    新文件与原文件同名，保存在同一文件夹中，且不删除原文件。
    """
    if not folder_path:
        print("未选择任何文件夹，脚本已退出。")
        return

    print("--- 转换开始 ---")
    print(f"正在处理文件夹：{folder_path}\n")

    try:
        word_app = Dispatch("Word.Application")
        word_app.Visible = False  # 在后台运行，不显示 Word 窗口
    except Exception as e:
        print("错误: 无法启动 Microsoft Word。请确保您的电脑上安装了 Word。")
        print(f"详细信息: {e}")
        return

    converted_files = []
    skipped_files = []

    # 遍历文件夹中的所有文件
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".doc"):
            doc_path = os.path.join(folder_path, filename)
            # 构造新的 .docx 文件路径
            docx_path = os.path.join(folder_path, os.path.splitext(filename)[0] + ".docx")

            # 如果同名的 .docx 文件已经存在，就跳过转换
            if os.path.exists(docx_path):
                print(f"✅ 已存在同名文件，跳过：{filename}")
                skipped_files.append(filename)
                continue

            try:
                # 规范化文件路径，解决 Win32COM 在处理复杂路径时可能遇到的问题
                normalized_doc_path = os.path.normpath(doc_path)

                print(f"🔄 正在转换：{filename}")
                # 打开 .doc 文件
                doc = word_app.Documents.Open(normalized_doc_path, False, False, False)
                # 另存为 .docx 格式，参数 16 代表 .docx 文件格式
                doc.SaveAs(docx_path, 16)
                doc.Close()
                print(f"🎉 成功转换：{filename} -> {os.path.basename(docx_path)}\n")
                converted_files.append(filename)
            except Exception as e:
                print(f"❌ 转换文件时出错：{filename}")
                print(f"详细信息: {e}\n")
                skipped_files.append(filename)

    # 转换完成后，关闭 Word 应用程序
    word_app.Quit()

    # 打印转换总结
    print("\n--- 转换完成总结 ---")
    if converted_files:
        print(f"✅ 成功转换了 {len(converted_files)} 个文件:")
        for f in converted_files:
            print(f"   - {f}")
    else:
        print("❌ 未成功转换任何文件。")

    if skipped_files:
        print(f"\n⚠️ 以下 {len(skipped_files)} 个文件被跳过（可能是已存在或转换失败）:")
        for f in skipped_files:
            print(f"   - {f}")

    print("\n[脚本已完成]")

# 运行脚本
if __name__ == "__main__":
    folder_to_convert = select_folder()
    convert_doc_to_docx(folder_to_convert)

