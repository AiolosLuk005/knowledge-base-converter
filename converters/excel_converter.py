import os
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import range_boundaries
from openpyxl.styles.numbers import is_date_format
from datetime import datetime

def format_cell(cell):
    if cell.value is None:
        return ""
    fmt = cell.number_format
    val = cell.value
    try:
        if is_date_format(fmt) and isinstance(val, datetime):
            return val.strftime("%Y-%m-%d")
        elif "%" in fmt:
            # Handle percentage formatting manually if needed, or rely on string conversion
            return f"{val * 100:.2f}%" if isinstance(val, (int, float)) else str(val)
        elif isinstance(val, float):
            if "." in fmt:
                try:
                    # Attempt to find decimal precision from format string like '0.00'
                    decimals = 0
                    if '.' in fmt:
                        decimals = len(fmt.split('.')[1].replace('0', '').replace('#', ''))
                        # Simple heuristic, might need adjustment for complex formats
                        # Actually, a safer way for simple floats is just to round
                    return f"{val:.2f}" 
                except:
                    return str(round(val, 2))
            else:
                return str(round(val, 2))
        else:
            return str(val)
    except Exception as e:
        print(f"Error formatting cell {cell.coordinate}: {e}")
        return str(val)

def unmerge_and_fill_preserve_format(sheet):
    # Copy merged cells to a list to avoid issues while modifying
    merged_ranges = list(sheet.merged_cells.ranges)
    for merge_range in merged_ranges:
        min_col, min_row, max_col, max_row = range_boundaries(str(merge_range))
        value = sheet.cell(row=min_row, column=min_col).value
        sheet.unmerge_cells(str(merge_range))
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                cell = sheet.cell(row=row, column=col)
                if cell.value is None:
                    cell.value = value
    
    formatted_data = []
    for row in sheet.iter_rows():
        formatted_row = [format_cell(cell) for cell in row]
        formatted_data.append(formatted_row)
    return formatted_data

def process_excel_file(file_path):
    print(f"Processing Excel file: {file_path}")
    try:
        wb = load_workbook(file_path, data_only=True)
    except Exception as e:
        raise Exception(f"Failed to load Excel file: {e}")

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = os.path.dirname(file_path)
    exported_files = []
    md_lines = []

    for i, sheetname in enumerate(wb.sheetnames):
        try:
            sheet = wb[sheetname]
            formatted_data = unmerge_and_fill_preserve_format(sheet)
            
            # CSV Output
            output_file = os.path.join(output_dir, f"{base_name}_Sheet{i+1}.csv")
            df = pd.DataFrame(formatted_data)
            df.to_csv(output_file, index=False, header=False, encoding='utf-8-sig')
            exported_files.append(output_file)

            # JSON Output
            safe_sheetname = "".join(c if c not in r'\\/:"*?<>|' else "_" for c in sheetname)
            if formatted_data:
                headers = [str(h) for h in formatted_data[0]]
                # Handle empty data
                if len(formatted_data) > 1:
                    json_df = pd.DataFrame(formatted_data[1:], columns=headers)
                else:
                    json_df = pd.DataFrame(columns=headers)
            else:
                headers = []
                json_df = pd.DataFrame()
            
            json_file = os.path.join(output_dir, f"{base_name}_{safe_sheetname}.json")
            json_df.to_json(json_file, orient="records", force_ascii=False)
            exported_files.append(json_file)

            # Markdown Content
            md_lines.append(f"### Sheet{i+1}: {sheetname}")
            if formatted_data:
                # Ensure all cells are strings for join
                header_row = [str(h) for h in headers]
                md_lines.append("| " + " | ".join(header_row) + " |")
                md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                for row in formatted_data[1:]:
                    row_str = [str(cell) for cell in row]
                    md_lines.append("| " + " | ".join(row_str) + " |")
            md_lines.append("")
        except Exception as e:
            print(f"Error processing sheet {sheetname}: {e}")
            continue

    # Write Markdown file
    md_file = os.path.join(output_dir, f"{base_name}.md")
    try:
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
        exported_files.append(md_file)
    except Exception as e:
        print(f"Failed to write markdown file: {e}")

    return exported_files
