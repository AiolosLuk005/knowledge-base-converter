import os
import csv
from docx import Document as DocxDocument
from docx2python import docx2python

def flatten_docx2_text(nested_list):
    flat = []
    for item in nested_list:
        if isinstance(item, list):
            flat.extend(flatten_docx2_text(item))
        elif isinstance(item, str) and item.strip():
            flat.append(item.strip())
    return flat

def format_markdown_table(table_rows, title=None):
    """格式化为 Markdown 表格"""
    if not table_rows or len(table_rows) < 2:
        return ""
    header = table_rows[0]
    data_rows = table_rows[1:]

    md_lines = []
    if title:
        md_lines.append(f"### {title}\n\n")
    md_lines.append("| " + " | ".join(header) + " |")
    md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for row in data_rows:
        md_lines.append("| " + " | ".join(row) + " |")
    md_lines.append("\n")
    return "\n".join(md_lines)

def extract_from_docx(docx_path):
    print(f"Processing Word file: {docx_path}")
    md_lines = []
    generated_files = []
    base_name = os.path.splitext(os.path.basename(docx_path))[0]
    output_dir = os.path.dirname(docx_path)

    # 提取正文段落
    try:
        with docx2python(docx_path) as doc:
            paragraphs = flatten_docx2_text(doc.body)
            if paragraphs:
                md_lines.append("## 正文内容\n\n")
                for para in paragraphs:
                    md_lines.append(para + "\n\n")
    except Exception as e:
        print(f"Error extracting text with docx2python: {e}")

    # 提取表格内容
    try:
        docx = DocxDocument(docx_path)
        for idx, table in enumerate(docx.tables):
            rows = []
            max_cols = 0
            for row in table.rows:
                cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
                max_cols = max(max_cols, len(cells))
                rows.append(cells)

            # 补齐每行列数
            for row in rows:
                while len(row) < max_cols:
                    row.append("")

            # 添加 Markdown 表格
            table_title = f"表格 {idx + 1}"
            md_table = format_markdown_table(rows, table_title)
            md_lines.append(md_table)

            # 输出 CSV 文件
            csv_filename = f"{base_name}_table{idx+1}.csv"
            csv_path = os.path.join(output_dir, csv_filename)
            
            with open(csv_path, "w", newline='', encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                for row in rows:
                    writer.writerow(row)
            generated_files.append(csv_path)

    except Exception as e:
        print(f"Error extracting tables with python-docx: {e}")

    # 保存 Markdown 文件
    md_path = os.path.join(output_dir, f"{base_name}.md")
    try:
        with open(md_path, "w", encoding="utf-8") as md_file:
            md_file.writelines(md_lines)
        generated_files.append(md_path)
    except Exception as e:
        print(f"Error writing markdown file: {e}")

    return generated_files
