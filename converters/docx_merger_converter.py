"""
DOCX文档合并转换器模块
将多个DOCX文件合并为一个文件，文件之间自动插入分页符
"""
import os
import zipfile
from copy import deepcopy
from docx import Document


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


def copy_element(element):
    """深拷贝一个XML元素，避免直接引用导致原文档结构被破坏"""
    return deepcopy(element._element)


def merge_docx_files(file_list, output_path):
    """
    合并多个 DOCX 文件为一个文件
    
    Args:
        file_list: 要合并的文件路径列表
        output_path: 输出文件路径
    
    Returns:
        生成文件路径列表 [output_path]
    """
    try:
        if not file_list:
            raise ValueError("文件列表为空")
        
        # 验证所有文件
        for file_path in file_list:
            if not is_valid_docx(file_path):
                raise ValueError(f"文件不是有效的 DOCX 格式: {os.path.basename(file_path)}")
        
        # 创建新文档，使用第一个文件作为基础
        merged_doc = Document(file_list[0])
        print(f"✅ 正在合并：{os.path.basename(file_list[0])} (1/{len(file_list)})")
        
        # 从第二个文件开始合并
        for idx, file_path in enumerate(file_list[1:], start=2):
            # 在合并前添加分页符
            merged_doc.add_page_break()
            
            # 读取要合并的文档
            source_doc = Document(file_path)
            
            # 复制所有段落
            for paragraph in source_doc.paragraphs:
                # 复制段落
                new_para = merged_doc.add_paragraph()
                new_para._element = copy_element(paragraph)
            
            # 复制所有表格
            for table in source_doc.tables:
                # 复制表格
                new_table_element = copy_element(table)
                merged_doc._element.body.append(new_table_element)
            
            # 复制所有节（sections）的设置，但只保留最后一个
            if source_doc.sections:
                last_section = source_doc.sections[-1]
                merged_section = merged_doc.add_section()
                # 复制页面设置
                merged_section.page_height = last_section.page_height
                merged_section.page_width = last_section.page_width
                merged_section.left_margin = last_section.left_margin
                merged_section.right_margin = last_section.right_margin
                merged_section.top_margin = last_section.top_margin
                merged_section.bottom_margin = last_section.bottom_margin
            
            print(f"✅ 正在合并：{os.path.basename(file_path)} ({idx}/{len(file_list)})")
        
        # 保存合并后的文档
        merged_doc.save(output_path)
        print(f"✅ 合并完成！输出文件：{os.path.basename(output_path)}")
        
        return [output_path]
        
    except Exception as e:
        print(f"❌ 合并文件时出错: {str(e)}")
        raise


def process_merge_docx(file_paths):
    """
    处理多个DOCX文件的合并
    
    Args:
        file_paths: DOCX文件路径列表
        
    Returns:
        生成文件路径列表
    """
    if not file_paths:
        raise ValueError("没有提供要合并的文件")
    
    if len(file_paths) == 1:
        raise ValueError("至少需要两个文件才能进行合并")
    
    # 生成输出文件名：(第一个文档名称)等(文档总数)份文档合并.docx
    first_file_name = os.path.splitext(os.path.basename(file_paths[0]))[0]
    total_count = len(file_paths)
    output_filename = f"{first_file_name}等{total_count}份文档合并.docx"
    output_path = os.path.join(os.path.dirname(file_paths[0]), output_filename)
    
    # 执行合并
    return merge_docx_files(file_paths, output_path)
