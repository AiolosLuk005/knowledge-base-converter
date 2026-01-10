import os
from pdf2docx import Converter


def convert_pdf_to_docx(pdf_path):
    """
    将PDF转换为DOCX，保留图片、表格和格式
    使用pdf2docx库进行转换，可以保留：
    - 文本格式（字体、大小、颜色等）
    - 图片和图形
    - 表格（结构和内容）
    - 页面布局
    
    Args:
        pdf_path: PDF文件的完整路径
        
    Returns:
        list: 包含生成的DOCX文件路径的列表
    """
    try:
        # 生成输出文件名
        base_name = os.path.splitext(pdf_path)[0]
        docx_path = base_name + ".docx"
        
        # 创建转换器
        cv = Converter(pdf_path)
        
        # 转换PDF到DOCX
        # start: 起始页（默认0）
        # end: 结束页（默认None，表示所有页）
        cv.convert(docx_path, start=0, end=None)
        
        # 关闭转换器
        cv.close()
        
        print(f"✅ PDF转DOCX成功：{os.path.basename(pdf_path)}")
        print(f"   ➤ 输出文件：{docx_path}")
        
        return [docx_path]
        
    except Exception as e:
        print(f"❌ PDF转DOCX失败：{os.path.basename(pdf_path)}")
        print(f"   ➤ 错误：{str(e)}")
        raise Exception(f"PDF转DOCX转换失败: {str(e)}")
