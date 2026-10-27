import os
import cv2
import numpy as np
import pdfplumber
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from PIL import Image
import pandas as pd
import re
from pathlib import Path
import fitz  # PyMuPDF

# Initialize OCR once to avoid reloading model
try:
    ocr = PaddleOCR(use_angle_cls=True, lang='ch')
except Exception as e:
    print(f"Warning: Failed to initialize PaddleOCR. OCR functions will fail. {e}")
    ocr = None

def semantic_split(text):
    return [s.strip() for s in re.split(r'(?<=[。！？!?\.])\s+', text) if s.strip()]

def detect_columns_and_crop(img, min_col_width=300, min_gap=40):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    vertical_proj = np.sum(thresh, axis=0)
    cols = []
    in_col = False
    start = 0
    for i, val in enumerate(vertical_proj):
        if val > 0 and not in_col:
            in_col = True
            start = i
        elif val == 0 and in_col:
            in_col = False
            if i - start > min_col_width:
                cols.append((start, i))
    
    # Merge loose columns
    merged = []
    prev = None
    for c in cols:
        if not prev:
            prev = c
        elif c[0] - prev[1] < min_gap:
            prev = (prev[0], c[1])
        else:
            merged.append(prev)
            prev = c
    if prev:
        merged.append(prev)
    
    crops = [img[:, x0:x1] for x0, x1 in merged]
    return crops

def ocr_image(img):
    if ocr is None:
        return ["OCR not initialized"]
    
    results = ocr.ocr(img, cls=True)
    if not results or results[0] is None:
        return []
        
    lines = []
    for block in results:
        for line in block:
            lines.append(line[1][0])
    return lines

def process_pdf_page_image(img, page_num):
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    columns = detect_columns_and_crop(img_cv)
    full_text = []
    
    if not columns:
        # If no columns detected, try OCR on the whole image
        lines = ocr_image(img_cv)
        full_text.extend(lines)
    else:
        for col_img in columns:
            lines = ocr_image(col_img)
            full_text.extend(lines)
            
    clean_text = " ".join(full_text)
    sentences = semantic_split(clean_text)
    
    md_page = f"## 第 {page_num} 页\n" + "\n\n".join(f"- {s}" for s in sentences)
    csv_data = [{"Page": page_num, "Sentence": s} for s in sentences]
    return md_page, csv_data

def clean_dataframe(df):
    # Replaced applymap with map for newer pandas versions compatibility
    return df.map(lambda x: str(x).replace('\n', '').replace('\r', '').strip() if x else '')

def is_same_table_structure(df1, df2):
    if df1 is None or df2 is None:
        return False
    return list(df1.columns) == list(df2.columns)

def process_pdf_full(pdf_path):
    print(f"Processing PDF: {pdf_path}")
    results_md = []
    results_csv = []
    filename = Path(pdf_path).stem
    base_dir = os.path.dirname(pdf_path)

    try:
        doc = fitz.open(pdf_path)
        # Use PyMuPDF directly to render images in-memory (no Poppler required)
        images = []
        for p in doc:
            pix = p.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        plumber_pdf = pdfplumber.open(pdf_path)
    except Exception as e:
        raise Exception(f"Failed to open PDF or render images: {e}")

    prev_df = None

    for i, (img, page, ppage) in enumerate(zip(images, doc, plumber_pdf.pages), start=1):
        try:
            # Check if page is mostly image/needs OCR or has extractable text
            text_content = page.get_text().strip()
            
            if len(text_content) < 10:
                md_page, csv_page = process_pdf_page_image(img, i)
                results_md.append(md_page)
                results_csv.extend(csv_page)
                prev_df = None
            else:
                tables = ppage.extract_tables()
                if tables and len(tables[0]) > 1:
                    for table in tables:
                        # Handle potential empty tables or rows
                        if not table: continue
                        
                        df = pd.DataFrame(table[1:], columns=table[0])
                        df = clean_dataframe(df)
                        
                        if prev_df is not None and is_same_table_structure(prev_df, df):
                            prev_df = pd.concat([prev_df, df], ignore_index=True)
                        else:
                            if prev_df is not None:
                                md = prev_df.to_markdown(index=False)
                                results_md.append(f"## 表格页\n{md}")
                                for row in prev_df.itertuples(index=False):
                                    joined = " | ".join(str(c) for c in row)
                                    results_csv.append({"Page": i - 1, "Sentence": joined})
                            prev_df = df
                else:
                    if prev_df is not None:
                        md = prev_df.to_markdown(index=False)
                        results_md.append(f"## 表格页\n{md}")
                        for row in prev_df.itertuples(index=False):
                            joined = " | ".join(str(c) for c in row)
                            results_csv.append({"Page": i - 1, "Sentence": joined})
                        prev_df = None

                    # Even if there is some text, we might want to OCR if it's mixed
                    # But the logic here seems to respect text content presence
                    # Here we fallback to OCR if no tables found but we are in this block? 
                    # The original logic falls back to OCR here.
                    md_page, csv_page = process_pdf_page_image(img, i)
                    results_md.append(md_page)
                    results_csv.extend(csv_page)
        except Exception as e:
            print(f"Error processing page {i}: {e}")
            continue

    if prev_df is not None:
        md = prev_df.to_markdown(index=False)
        results_md.append(f"## 表格页\n{md}")
        for row in prev_df.itertuples(index=False):
            joined = " | ".join(str(c) for c in row)
            results_csv.append({"Page": "Last", "Sentence": joined})

    try:
        doc.close()
    except Exception:
        pass
    try:
        plumber_pdf.close()
    except Exception:
        pass

    csv_path = os.path.join(base_dir, f"{filename}.csv")
    md_path = os.path.join(base_dir, f"{filename}.md")
    
    generated_files = []
    
    if results_csv:
        pd.DataFrame(results_csv).to_csv(csv_path, index=False, encoding="utf-8-sig")
        generated_files.append(csv_path)
    
    if results_md:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(results_md))
        generated_files.append(md_path)
        
    return generated_files
