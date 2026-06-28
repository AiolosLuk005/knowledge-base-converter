import os
import sys
import shutil
import urllib.request
import zipfile
import subprocess

# Config - Using Python 3.13 to match the host system interpreter
PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.13.0/python-3.13.0-embed-amd64.zip"
PYTHON_ZIP_NAME = "python-3.13.0-embed-amd64.zip"
PYTHON_VERSION_MAJOR_MINOR = "313"  # for python313._pth and DLLs

# Poppler Windows x64.
POPPLER_URL = "https://github.com/oschwartz10612/poppler-windows/releases/download/24.08.0-0/Release-24.08.0-0-x64.zip"
POPPLER_ZIP_NAME = "poppler-24.08.0-0-x64.zip"

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT_DIR, "dist_portable")
PYTHON_EMBED_DIR = os.path.join(DIST_DIR, "python_embeded")
UTILS_DIR = os.path.join(DIST_DIR, "utils")
POPPLER_DIR = os.path.join(UTILS_DIR, "poppler")

def download_file(url, filepath):
    print(f"Downloading from {url} ...")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response, open(filepath, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print(f"Successfully downloaded to {filepath}")
    except Exception as e:
        print(f"Download failed: {e}")
        raise e

def setup_directories():
    print("Creating output directory structure...")
    if os.path.exists(DIST_DIR):
        print(f"Cleaning existing directory {DIST_DIR}...")
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(PYTHON_EMBED_DIR, exist_ok=True)
    os.makedirs(UTILS_DIR, exist_ok=True)
    os.makedirs(os.path.join(DIST_DIR, "temp_data"), exist_ok=True)

def deploy_python():
    zip_path = os.path.join(ROOT_DIR, PYTHON_ZIP_NAME)
    if not os.path.exists(zip_path):
        download_file(PYTHON_EMBED_URL, zip_path)
    
    print("Extracting Python embeddable zip...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(PYTHON_EMBED_DIR)
    
    # Patch python313._pth
    pth_file = os.path.join(PYTHON_EMBED_DIR, f"python{PYTHON_VERSION_MAJOR_MINOR}._pth")
    if os.path.exists(pth_file):
        print(f"Configuring python{PYTHON_VERSION_MAJOR_MINOR}._pth for site-packages support...")
        with open(pth_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        for line in lines:
            if line.strip() == "#import site":
                new_lines.append("import site\n")
            else:
                new_lines.append(line)
        
        # 显式追加 Lib/site-packages 以及上级目录 ..
        new_lines.append("Lib/site-packages\n")
        new_lines.append("..\n")
        
        with open(pth_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

def deploy_poppler():
    zip_path = os.path.join(ROOT_DIR, POPPLER_ZIP_NAME)
    if not os.path.exists(zip_path):
        try:
            download_file(POPPLER_URL, zip_path)
        except Exception:
            print("==========================================================")
            print("Warning: Automatic Poppler download failed.")
            print("You can manually download Poppler (Windows x64) from:")
            print("https://github.com/oschwartz10612/poppler-windows/releases")
            print(f"And extract it to: {POPPLER_DIR}")
            print("==========================================================")
            return
            
    print("Extracting Poppler package...")
    temp_extract_dir = os.path.join(UTILS_DIR, "poppler_temp")
    os.makedirs(temp_extract_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
        
        inner_dirs = os.listdir(temp_extract_dir)
        if inner_dirs:
            inner_dir = inner_dirs[0]
            full_inner_path = os.path.join(temp_extract_dir, inner_dir)
            if os.path.exists(POPPLER_DIR):
                shutil.rmtree(POPPLER_DIR)
            shutil.move(full_inner_path, POPPLER_DIR)
            print("Poppler deployed successfully.")
    except Exception as e:
        print(f"Failed to extract Poppler: {e}")
    finally:
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)

def install_dependencies():
    print("Injecting dependencies into site-packages...")
    site_packages_dir = os.path.join(PYTHON_EMBED_DIR, "Lib", "site-packages")
    os.makedirs(site_packages_dir, exist_ok=True)
    
    requirements_path = os.path.join(ROOT_DIR, "requirements.txt")
    
    # Try using uv first
    try:
        print("Attempting to install dependencies using 'uv'...")
        cmd = [
            "uv", "pip", "install", 
            "-r", requirements_path, 
            "waitress", 
            "--target", site_packages_dir
        ]
        print(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print("Dependencies installed successfully using uv!")
        else:
            raise RuntimeError(f"uv failed: {result.stderr}")
    except Exception as e:
        print(f"uv installation fell back/failed: {e}")
        print("Attempting standard pip install via sys.executable...")
        cmd = [
            sys.executable, "-m", "pip", "install", 
            "-r", requirements_path, 
            "waitress", 
            "--target", site_packages_dir
        ]
        print(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Standard pip installation failed: {result.stderr}")
            raise RuntimeError("Dependency injection failed completely")
        print("Dependencies installed successfully using standard pip!")
    
    # Process pywin32 DLLs
    print("Processing pywin32 DLLs...")
    pywin32_system_dir = os.path.join(site_packages_dir, "pywin32_system32")
    if os.path.exists(pywin32_system_dir):
        for dll_name in [f"pywintypes{PYTHON_VERSION_MAJOR_MINOR}.dll", f"pythoncom{PYTHON_VERSION_MAJOR_MINOR}.dll"]:
            dll_src = os.path.join(pywin32_system_dir, dll_name)
            dll_dst = os.path.join(PYTHON_EMBED_DIR, dll_name)
            if os.path.exists(dll_src):
                shutil.copy2(dll_src, dll_dst)
                print(f"Copied: {dll_name} -> python_embeded root")
            else:
                print(f"Not found: {dll_src}")

def copy_source_code():
    print("Copying project source files...")
    items_to_copy = ["converters", "web", "server.py"]
    for item in items_to_copy:
        src = os.path.join(ROOT_DIR, item)
        dst = os.path.join(DIST_DIR, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
            print(f"Copied directory: {item}")
        elif os.path.isfile(src):
            shutil.copy2(src, dst)
            print(f"Copied file: {item}")

def generate_bat_launcher():
    bat_path = os.path.join(DIST_DIR, "start_app.bat")
    content = """@echo off
title Knowledge Base Converter - Portable
set WORK_DIR=%~dp0
cd /d "%WORK_DIR%"

:: Add Poppler bin to PATH
set PATH=%WORK_DIR%utils\\poppler\\bin;%PATH%

:: Set PYTHONPATH
set PYTHONPATH=%WORK_DIR%

echo Starting Knowledge Base Converter Server...
echo Open http://localhost:5000 in your browser.
echo.

"%WORK_DIR%python_embeded\\python.exe" "%WORK_DIR%server.py"
pause
"""
    with open(bat_path, "w", encoding="gbk") as f:
        f.write(content)
    print("Successfully generated start_app.bat launcher!")

def main():
    try:
        setup_directories()
        deploy_python()
        deploy_poppler()
        install_dependencies()
        copy_source_code()
        generate_bat_launcher()
        print("\n==========================================")
        print("Packaging complete! Run the app using:")
        print(f"{os.path.join(DIST_DIR, 'start_app.bat')}")
        print("==========================================\n")
    except Exception as e:
        print(f"Error during packaging: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
