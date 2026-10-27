import os
import shutil
import tempfile
import uuid
import sys
import subprocess
import json
from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename

# Import converters
from converters.excel_converter import process_excel_file
from converters.pdf_converter import process_pdf_full
from converters.word_converter import extract_from_docx
from converters.doc_converter import convert_doc_to_docx
from converters.word_to_md_converter import extract_from_docx as word_to_md_extract
from converters.docx_merger_converter import process_merge_docx
from converters.pdf_to_docx_converter import convert_pdf_to_docx
from converters.pdf_tools_converter import (
    merge_pdf_files,
    compress_pdf_file,
    pdf_to_images,
    images_to_pdf,
    split_pdf_by_size,
    split_pdf_by_parts,
    extract_or_delete_pages,
    highlight_pdf_keywords,
    replace_pdf_pages,
    get_pdf_page_info,
    get_image_sizes,
)

app = Flask(__name__, static_folder='web', static_url_path='')

# Configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'temp_data')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 512 * 1024 * 1024  # 512MB limit

# Routes
@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('web', path)

@app.route('/api/pick-local-files', methods=['POST'])
def pick_local_files():
    """打开原生文件选择器，返回带有本地绝对路径的文件列表"""
    data = request.get_json() or {}
    tool = data.get('tool', '')
    
    desc_map = {
        'excel': ('Excel 表格', '*.xlsx;*.xlsm;*.xls'),
        'pdf': ('PDF 文档', '*.pdf'),
        'pdf2docx': ('PDF 文档', '*.pdf'),
        'doc2docx': ('旧版 Word', '*.doc'),
        'word-to-md': ('Word 文档', '*.docx'),
        'merge-docx': ('Word 文档', '*.docx'),
        'pdf-merge': ('PDF 文档', '*.pdf'),
        'pdf-compress': ('PDF 文档', '*.pdf'),
        'pdf-to-images': ('PDF 文档', '*.pdf'),
        'images-to-pdf': ('图片文件', '*.png;*.jpg;*.jpeg;*.bmp;*.webp'),
        'pdf-split-size': ('PDF 文档', '*.pdf'),
        'pdf-split-parts': ('PDF 文档', '*.pdf'),
        'pdf-split-pages': ('PDF 文档', '*.pdf'),
        'pdf-highlight': ('PDF 文档', '*.pdf'),
        'pdf-replace-pdf': ('PDF 文档', '*.pdf'),
        'pdf-replace-images': ('图片文件', '*.webp;*.jpg;*.jpeg;*.png;*.bmp;*.tif;*.tiff'),
    }
    desc, exts = desc_map.get(tool, ('所有支持的文件', '*.*'))

    try:
        script_path = os.path.join(os.path.dirname(__file__), 'choose_dialog.py')
        proc = subprocess.run([sys.executable, script_path, desc, exts], capture_output=True, text=True, encoding='utf-8', check=True)
        raw_output = proc.stdout.strip()
        file_paths = json.loads(raw_output) if raw_output else []
        
        files_info = []
        for fp in file_paths:
            if os.path.exists(fp):
                files_info.append({
                    'name': os.path.basename(fp),
                    'path': fp,
                    'size': os.path.getsize(fp)
                })
        return jsonify({'files': files_info})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/open-folder', methods=['POST'])
def open_folder():
    """在文件资源管理器中定位并选中生成的文件"""
    data = request.get_json() or {}
    target_path = data.get('path', '')
    if not target_path or not os.path.exists(target_path):
        return jsonify({'error': '路径不存在'}), 404
    
    try:
        target_path = os.path.normpath(target_path)
        subprocess.run(f'explorer /select,"{target_path}"', shell=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/replace-info', methods=['POST'])
def replace_info():
    """返回源 PDF 页面尺寸与替换图片尺寸，供前端预览对应关系与方向提醒"""
    data = request.get_json() or {}
    pdf_path = data.get('pdf_path', '')
    image_paths = data.get('image_paths', []) or []
    result = {}
    try:
        if pdf_path:
            if not os.path.exists(pdf_path):
                return jsonify({'error': 'PDF 文件不存在'}), 404
            result['pdf'] = get_pdf_page_info(pdf_path)
        if image_paths:
            result['images'] = get_image_sizes([p for p in image_paths if os.path.exists(p)])
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert/<convert_type>', methods=['POST'])
def convert_file(convert_type):
    # 支持两种模式：1. 本地源路径直接处理（直接存回源目录） 2. HTTP 上传文件
    local_paths = request.form.getlist('local_paths')
    is_local_mode = len(local_paths) > 0
    # PDF 指定页替换：源 PDF 与图片分别传入
    is_replace = convert_type == 'pdf-replace-pages'
    if is_replace:
        is_local_mode = bool(request.form.get('pdf_path'))

    batch_dir = None
    if is_replace:
        if not is_local_mode and 'pdf_file' not in request.files:
            return jsonify({'error': '请选择源 PDF 文件'}), 400
        batch_id = str(uuid.uuid4())
        batch_dir = os.path.join(app.config['UPLOAD_FOLDER'], batch_id)
        os.makedirs(batch_dir)
    elif not is_local_mode:
        if 'files' not in request.files:
            return jsonify({'error': 'No files part'}), 400
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No selected file'}), 400
        batch_id = str(uuid.uuid4())
        batch_dir = os.path.join(app.config['UPLOAD_FOLDER'], batch_id)
        os.makedirs(batch_dir)

    result_files = []
    
    def process_saved_outputs(generated_paths, source_original_dir=None):
        out_list = []
        for path in generated_paths:
            # 如果是本地源路径模式且指定了原目录，确保文件保存在源目录中
            if is_local_mode and source_original_dir and os.path.abspath(os.path.dirname(path)) != os.path.abspath(source_original_dir):
                target_dest = os.path.join(source_original_dir, os.path.basename(path))
                if os.path.abspath(path) != os.path.abspath(target_dest):
                    shutil.copy2(path, target_dest)
                    path = target_dest
            
            # 同时复制一份到 temp_data 供网页端下载与预览
            rel_name = os.path.basename(path)
            temp_copy_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'recent_outputs')
            os.makedirs(temp_copy_dir, exist_ok=True)
            temp_copy_path = os.path.join(temp_copy_dir, rel_name)
            if os.path.abspath(path) != os.path.abspath(temp_copy_path):
                shutil.copy2(path, temp_copy_path)

            rel_url = f'/download/recent_outputs/{rel_name}'
            out_list.append({
                'name': os.path.basename(path),
                'path': os.path.abspath(path),
                'saved_in_source_dir': is_local_mode,
                'source_dir': os.path.dirname(os.path.abspath(path)),
                'url': rel_url
            })
        return out_list

    try:
        # 多文件合并类：merge-docx, pdf-merge, images-to-pdf
        if convert_type == 'merge-docx':
            if is_local_mode:
                file_paths = [p for p in local_paths if os.path.exists(p)]
            else:
                file_paths = []
                for file in files:
                    if file.filename == '':
                        continue
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(batch_dir, filename)
                    file.save(file_path)
                    file_paths.append(file_path)
            
            if len(file_paths) < 2:
                return jsonify({'error': '至少需要两个文件才能进行合并'}), 400
            
            try:
                generated_paths = process_merge_docx(file_paths)
                source_dir = os.path.dirname(file_paths[0]) if is_local_mode else None
                result_files.extend(process_saved_outputs(generated_paths, source_dir))
            except Exception as e:
                return jsonify({'error': f"Error merging files: {str(e)}"}), 500

        elif convert_type == 'pdf-merge':
            if is_local_mode:
                file_paths = [p for p in local_paths if os.path.exists(p)]
            else:
                file_paths = []
                for file in files:
                    if file.filename == '':
                        continue
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(batch_dir, filename)
                    file.save(file_path)
                    file_paths.append(file_path)

            if len(file_paths) < 2:
                return jsonify({'error': '至少需要两个 PDF 文件才能合并'}), 400

            try:
                generated_paths = merge_pdf_files(file_paths)
                source_dir = os.path.dirname(file_paths[0]) if is_local_mode else None
                result_files.extend(process_saved_outputs(generated_paths, source_dir))
            except Exception as e:
                return jsonify({'error': f"Error merging PDFs: {str(e)}"}), 500

        elif convert_type == 'images-to-pdf':
            if is_local_mode:
                file_paths = [p for p in local_paths if os.path.exists(p)]
            else:
                file_paths = []
                for file in files:
                    if file.filename == '':
                        continue
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(batch_dir, filename)
                    file.save(file_path)
                    file_paths.append(file_path)

            if len(file_paths) < 1:
                return jsonify({'error': '请选择至少一张图片'}), 400

            try:
                generated_paths = images_to_pdf(file_paths)
                source_dir = os.path.dirname(file_paths[0]) if is_local_mode else None
                result_files.extend(process_saved_outputs(generated_paths, source_dir))
            except Exception as e:
                return jsonify({'error': f"Error creating PDF from images: {str(e)}"}), 500

        elif convert_type == 'pdf-replace-pages':
            # 源 PDF
            if is_local_mode:
                pdf_path = request.form.get('pdf_path')
                if not os.path.exists(pdf_path):
                    return jsonify({'error': '源 PDF 文件不存在'}), 400
            else:
                pdf_file = request.files['pdf_file']
                pdf_name = os.path.basename((pdf_file.filename or '').replace('\\', '/')) or 'source.pdf'
                if not pdf_name.lower().endswith('.pdf'):
                    pdf_name += '.pdf'
                pdf_path = os.path.join(batch_dir, pdf_name)
                pdf_file.save(pdf_path)

            # 图片（顺序即前端确认的对应顺序；本地路径与上传文件可混合）
            image_paths = []
            order = request.form.getlist('image_order')  # 'L:<path>' 或 'U:<index>'
            uploaded = request.files.getlist('image_files')
            for idx, token in enumerate(order):
                kind, _, val = token.partition(':')
                if kind == 'L':
                    if not os.path.exists(val):
                        return jsonify({'error': f'图片不存在: {val}'}), 400
                    image_paths.append(val)
                elif kind == 'U':
                    f = uploaded[int(val)]
                    ext = os.path.splitext(f.filename)[1] or '.img'
                    save_path = os.path.join(batch_dir, f'img_{idx:04d}{ext}')
                    f.save(save_path)
                    image_paths.append(save_path)

            try:
                generated_paths = replace_pdf_pages(
                    pdf_path,
                    image_paths,
                    request.form.get('page_spec', ''),
                    fit_mode=request.form.get('fit_mode', 'contain'),
                )
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': f"替换页面失败: {str(e)}"}), 500
            source_dir = os.path.dirname(pdf_path) if is_local_mode else None
            result_files.extend(process_saved_outputs(generated_paths, source_dir))

        # 单文件或逐个转换类
        else:
            items_to_process = []
            if is_local_mode:
                for lp in local_paths:
                    if os.path.exists(lp):
                        items_to_process.append((lp, os.path.basename(lp), os.path.dirname(lp)))
            else:
                for file in files:
                    if file.filename == '':
                        continue
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(batch_dir, filename)
                    file.save(file_path)
                    items_to_process.append((file_path, filename, None))

            for file_path, filename, original_dir in items_to_process:
                generated_paths = []
                try:
                    if convert_type == 'excel':
                        generated_paths = process_excel_file(file_path)
                    elif convert_type == 'pdf':
                        generated_paths = process_pdf_full(file_path)
                    elif convert_type == 'pdf2docx':
                        generated_paths = convert_pdf_to_docx(file_path)
                    elif convert_type == 'word':
                        generated_paths = extract_from_docx(file_path)
                    elif convert_type == 'doc2docx':
                        generated_paths = convert_doc_to_docx(file_path)
                    elif convert_type == 'word-to-md':
                        generated_paths = word_to_md_extract(file_path)
                    elif convert_type == 'pdf-compress':
                        quality = request.form.get('quality', '2')
                        generated_paths = compress_pdf_file(file_path, quality_level=quality)
                    elif convert_type == 'pdf-to-images':
                        scale = request.form.get('scale', '1.5')
                        generated_paths = pdf_to_images(file_path, scale=scale)
                    elif convert_type == 'pdf-split-size':
                        max_size = request.form.get('max_size', '10')
                        generated_paths = split_pdf_by_size(file_path, max_size_mb=max_size)
                    elif convert_type == 'pdf-split-parts':
                        num_parts = request.form.get('num_parts', '2')
                        generated_paths = split_pdf_by_parts(file_path, num_parts=num_parts)
                    elif convert_type == 'pdf-split-pages':
                        page_ranges = request.form.get('page_ranges', '')
                        mode = request.form.get('mode', 'extract')
                        generated_paths = extract_or_delete_pages(file_path, page_ranges, mode=mode)
                    elif convert_type == 'pdf-highlight':
                        keyword = request.form.get('keyword', '')
                        generated_paths = highlight_pdf_keywords(file_path, keyword=keyword)
                    else:
                        return jsonify({'error': 'Invalid conversion type'}), 400
                except Exception as e:
                    return jsonify({'error': f"Error converting {filename}: {str(e)}"}), 500

                result_files.extend(process_saved_outputs(generated_paths, original_dir))

        return jsonify({'files': result_files})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('web', 'favicon.ico', mimetype='image/x-icon')

if __name__ == '__main__':
    # 通过环境变量控制 debug 模式，默认为关闭（生产模式）
    # 开发时可设置: set FLASK_DEBUG=1 (Windows) 或 export FLASK_DEBUG=1 (Linux/Mac)
    debug_mode = os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true', 'yes')
    
    print("Starting Knowledge Base Converter Server...")
    print(f"Debug mode: {'ON' if debug_mode else 'OFF'}")
    print("Open http://localhost:5000 in your browser")
    
    if debug_mode:
        print("TIP: To disable debug mode, unset FLASK_DEBUG environment variable")
        app.run(debug=True, port=5000)
    else:
        # 生产模式：使用 Waitress 服务器（如果已安装），否则使用 Flask 内置服务器
        try:
            from waitress import serve
            print("Using Waitress production server")
            serve(app, host='127.0.0.1', port=5000)
        except ImportError:
            print("TIP: Install 'waitress' for better production performance: pip install waitress")
            app.run(debug=False, port=5000)
