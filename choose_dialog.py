import sys
import os
import json

def choose_files_win32(filetypes_desc="所有文件", extensions="*.*"):
    import win32gui
    import win32con

    # 构造 Filter 字符串，以 \0 分隔，末尾以两个 \0 结尾
    # 例如: "PDF 文档 (*.pdf)\0*.pdf\0所有文件 (*.*)\0*.*\0\0"
    ext_pattern = ";".join(extensions.split(";")) if ";" in extensions else extensions
    filt = f"{filetypes_desc} ({ext_pattern})\0{ext_pattern}\0所有文件 (*.*)\0*.*\0\0"
    
    flags = (
        win32con.OFN_EXPLORER
        | win32con.OFN_FILEMUSTEXIST
        | win32con.OFN_HIDEREADONLY
        | win32con.OFN_ALLOWMULTISELECT
    )
    
    try:
        file_res, _, _ = win32gui.GetOpenFileNameW(
            Title="选择要处理的文件（将直接保存至原目录）",
            Filter=filt,
            Flags=flags,
            MaxFile=65536
        )
        if not file_res:
            return []
        
        # 多选时返回格式为 "目录\0文件1\0文件2\0"；单选时返回直接就是完整路径
        parts = file_res.split('\0')
        if len(parts) <= 1:
            return [parts[0]] if parts and parts[0] else []
        
        folder = parts[0]
        selected_files = [os.path.join(folder, f) for f in parts[1:] if f.strip()]
        return selected_files
    except Exception:
        # 用户取消或选择出错
        return []

def choose_files_tk(filetypes_desc="所有文件", extensions="*.*"):
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.lift()
    root.attributes('-topmost', True)
    
    filetypes = [(filetypes_desc, extensions), ("所有文件", "*.*")]
    selected = filedialog.askopenfilenames(
        title="选择要处理的文件（将直接保存至原目录）",
        filetypes=filetypes
    )
    root.destroy()
    return list(selected)

def choose_files(filetypes_desc="所有文件", extensions="*.*"):
    try:
        return choose_files_win32(filetypes_desc, extensions)
    except Exception:
        return choose_files_tk(filetypes_desc, extensions)

if __name__ == '__main__':
    if sys.stdout.encoding.lower() != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    desc = sys.argv[1] if len(sys.argv) > 1 else "所有文件"
    exts = sys.argv[2] if len(sys.argv) > 2 else "*.*"
    paths = choose_files(desc, exts)
    # Output JSON string to stdout
    print(json.dumps(paths, ensure_ascii=False))
