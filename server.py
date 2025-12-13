import os
import shutil
import tempfile
import uuid
from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename

# Import converters
from converters.excel_converter import process_excel_file
from converters.pdf_converter import process_pdf_full
from converters.word_converter import extract_from_docx
from converters.doc_converter import convert_doc_to_docx

app = Flask(__name__, static_folder='web', static_url_path='')

# Configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'temp_data')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB limit

# Routes
@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('web', path)

@app.route('/api/convert/<convert_type>', methods=['POST'])
def convert_file(convert_type):
    if 'files' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No selected file'}), 400

    batch_id = str(uuid.uuid4())
    batch_dir = os.path.join(app.config['UPLOAD_FOLDER'], batch_id)
    os.makedirs(batch_dir)

    result_files = []
    
    try:
        for file in files:
            if file.filename == '':
                continue
                
            filename = secure_filename(file.filename)
            file_path = os.path.join(batch_dir, filename)
            file.save(file_path)
            
            generated_paths = []
            
            try:
                if convert_type == 'excel':
                    generated_paths = process_excel_file(file_path)
                elif convert_type == 'pdf':
                    generated_paths = process_pdf_full(file_path)
                elif convert_type == 'word':
                    generated_paths = extract_from_docx(file_path)
                elif convert_type == 'doc2docx':
                    generated_paths = convert_doc_to_docx(file_path)
                else:
                    return jsonify({'error': 'Invalid conversion type'}), 400
            except Exception as e:
                return jsonify({'error': f"Error converting {filename}: {str(e)}"}), 500

            # Collect results
            for path in generated_paths:
                rel_path = os.path.relpath(path, app.config['UPLOAD_FOLDER'])
                # Windows path separators fix for URL
                rel_path = rel_path.replace('\\', '/')
                result_files.append({
                    'name': os.path.basename(path),
                    'url': f'/download/{rel_path}'
                })

        return jsonify({'files': result_files})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    print("Starting Knowledge Base Converter Server...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
