import os
import sys
import pythoncom
from win32com.client import Dispatch

def convert_doc_to_docx(file_path):
    print(f"Converting DOC to DOCX: {file_path}")
    
    # Ensure absolute path
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    folder_path = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    
    if not filename.lower().endswith(".doc"):
        print(f"Skipping {filename}: Not a .doc file")
        return []

    docx_path = os.path.join(folder_path, os.path.splitext(filename)[0] + ".docx")

    if os.path.exists(docx_path):
        print(f"Skipping: {docx_path} already exists")
        return [docx_path]

    word_app = None
    try:
        # Initialize COM library (needed for threads/web server)
        pythoncom.CoInitialize()
        
        word_app = Dispatch("Word.Application")
        word_app.Visible = False
        
        doc = word_app.Documents.Open(file_path, False, False, False)
        doc.SaveAs(docx_path, 16) # 16 = wdFormatXMLDocument
        doc.Close()
        
        print(f"Converted: {docx_path}")
        return [docx_path]
        
    except Exception as e:
        print(f"Error converting {filename}: {e}")
        raise e
    finally:
        if word_app:
            try:
                word_app.Quit()
            except:
                pass
        pythoncom.CoUninitialize()
