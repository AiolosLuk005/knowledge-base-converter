# BUILD_SPEC.md：知识库文档转换工具便携式打包方案

本文档定义了将 `knowledge-base-converter` 从“依赖本地 Python 环境”转变为“独立运行的便携式软件包（Portable Package）”的完整方案和执行规范。

---

## 核心架构设计

1. **引擎隔离**：
   - 基础 Python 解释器：官方 Windows x64 Embeddable Package（例如 Python 3.10.x 嵌入式版本）。
   - 主程序启动入口：在 `dist_portable` 根目录部署 `start_app.bat`，自动注入环境变量（`PYTHONPATH`、`PATH` 等），并调用自带的 `python_embeded\python.exe`。

2. **库与依赖注入**：
   - 使用 pip 将 `requirements.txt` 中声明的依赖以及生产级服务网关（如 `waitress`）安装至 `dist_portable\python_embeded\Lib\site-packages`。
   - **关键适配：由于嵌入式环境默认不加载 `site-packages`，需修改嵌入式 Python 目录下的 `python310._pth`（或对应版本的 `._pth` 文件），解除 `import site` 的注释或新增 `Lib/site-packages` 路径。**

3. **二进制与外部工具（Poppler & pywin32）适配**：
   - **pywin32**：在嵌入式环境中，需要将 `pywin32` 相关的 DLL 文件（如 `pywintypes310.dll`、`pythoncom310.dll`）手动拷贝至 `python_embeded\` 根目录或系统的 System 查找路径下，以防 COM 接口（如 Word 转换器）调用报错。
   - **pdf2image (Poppler)**：需要下载 Windows 版本的 Poppler 二进制包，并解压存放在 `dist_portable\utils\poppler\bin`，在 `start_app.bat` 中将其添加至临时 `PATH` 环境变量中。

---

## 执行步骤与阶段划分

### 第一阶段：开发与验证环境 (Dev & Test Phase)
在此阶段，我们在本地隔离的虚拟环境中验证代码与依赖在 Windows 下的正确性：
1. 在项目根目录使用 `uv` 创建一个标准的本地虚拟环境：
   ```bash
   uv venv .venv
   .venv\Scripts\activate
   ```
2. 安装所有依赖包：
   ```bash
   uv pip install -r requirements.txt waitress
   ```
3. 启动 `server.py` 并通过转换测试验证功能：
   ```bash
   python server.py
   ```
   *验证项目：Excel 转换、PDF 转换（包含 OCR）、Word/Doc 转换。*

### 第二阶段：自动构建流水线 (Build & Packaging Phase)
自动化打包脚本 `build_portable.py` 将自动完成以下工作：

1. **创建输出结构**：
   - 创建 `dist_portable\` 文件夹。
   - 创建 `dist_portable\python_embeded\`。
   - 创建 `dist_portable\utils\`。

2. **部署 Python 引擎**：
   - 从 Python 官网自动下载（或从缓存中读取） `python-3.10.11-embed-amd64.zip`。
   - 解压至 `dist_portable\python_embeded\`。
   - 修改 `dist_portable\python_embeded\python310._pth`：
     - 追加 `Lib/site-packages`
     - 启用 `import site`

3. **依赖库注入**：
   - 提取临时的 `pip` 引导脚本（`get-pip.py`）或利用本地虚拟环境的 pip，在 `dist_portable\python_embeded` 中安装依赖：
     ```bash
     .\dist_portable\python_embeded\python.exe -m pip install -r requirements.txt waitress --target .\dist_portable\python_embeded\Lib\site-packages
     ```
   - 针对 `pywin32` 的特殊处理：
     - 将 `Lib\site-packages\pywin32_system32\` 下的 `pywintypes310.dll` 和 `pythoncom310.dll` 拷贝至 `dist_portable\python_embeded\`。

4. **第三方二进制集成**：
   - 下载 Windows 版 Poppler 工具链。
   - 解压至 `dist_portable\utils\poppler\`。

5. **部署源码**：
   - 将 `converters\`、`web\`、`server.py` 等项目文件复制到 `dist_portable\`。
   - 创建空的 `dist_portable\temp_data\` 目录。

6. **生成启动脚本 `dist_portable\start_app.bat`** :
   - 写入以下内容：
     ```bat
     @echo off
     title Knowledge Base Converter - Portable
     set WORK_DIR=%~dp0
     cd /d "%WORK_DIR%"
     
     :: 注入 Poppler 路径到 PATH 环境变量
     set PATH=%WORK_DIR%utils\poppler\bin;%PATH%
     
     :: 设置 Python 环境变量
     set PYTHONPATH=%WORK_DIR%
     
     echo Starting Knowledge Base Converter Server...
     echo Open http://localhost:5000 in your browser.
     
     "%WORK_DIR%python_embeded\python.exe" "%WORK_DIR%server.py"
     pause
     ```

### 第三阶段：最终校验 (Final Verification)
1. 双击运行 `dist_portable\start_app.bat`，观察控制台是否有加载报错或 DLL 缺失报错。
2. 验证浏览器是否可打开 `http://localhost:5000` 并成功进行至少一次 Word、PDF（OCR）或 Excel 的转换。
