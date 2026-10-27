# 知识库文档转换工具 (Knowledge Base Converter)

这是一个全能的文档转换工具，旨在将各种常见文档格式（Excel, PDF, Word）转换为知识库系统（如 RAG 应用）常用的 Markdown, CSV 和 JSON 格式。

项目提供了现代化的 **Web 界面**，同时也保留了 Python 脚本作为底层模块。

## ✨ 功能特性

- **Excel 转换**: 自动处理合并单元格，导出为 CSV, JSON 和格式化的 Markdown 表格。
- **PDF 转换**: 集成 PaddleOCR，支持扫描版 PDF，智能识别分栏，导出为 Markdown 和 CSV。
- **Word 转换**: 提取 Word 文档中的正文和表格，转换为 Markdown 和 CSV。
- **Doc 转 Docx**: 批量将旧版 .doc 文件转换为 .docx (仅限 Windows)。
- **Word 多文档合并**: 将多个 .docx 文档按顺序自动分页拼接为一个完整文档。
- **PDF 文档合并**: 将多个 PDF 文档按顺序无缝合并为一个文件。
- **PDF 文件压缩**: 重采样优化内部高分辨率图片并流压缩，提供轻度/中度/高度压缩选项。
- **PDF 导出图片**: 将 PDF 每一页渲染为高清 PNG 图片，自动打包为 ZIP 供一键下载。
- **图片合成 PDF**: 将 PNG、JPG、JPEG、BMP、WEBP 等多图按顺序排版并合成单个 PDF。
- **PDF 智能拆分**: 支持按文件大小上限（MB）拆分、按份数均等拆分。
- **PDF 页面提取与删减**: 支持按指定页码（如 `1-3, 5, 8-10`）保留提取或剔除废页。
- **PDF 关键词检索高亮**: 在 PDF 中检索特定关键词并自动生成带有醒目高亮标注的 PDF。
- **Web 界面**: 简洁美观的 Google Play 风格界面，支持拖拽上传、参数配置与批量处理。

## 🚀 快速开始

### 1. 安装依赖

确保已安装 Python 3.8+。

```bash
pip install -r requirements.txt
```

> **注意**: 
> - 如果需要 Doc 转 Docx 功能，必须在 Windows 上运行且安装了 Microsoft Word。
> - PDF OCR 功能首次运行会自动下载 PaddleOCR 模型，请保持网络连接。

### 2. 启动 Web 服务

```bash
python server.py
```

启动后，浏览器会自动打开 `http://localhost:5000`。

### 3. 使用方法

1. 在首页选择需要转换的文档类型。
2. 将文件拖入上传区域，或点击选择文件。
3. 点击“开始转换”。
4. 转换完成后，下载生成的文件。

## 📂 项目结构

```
knowledge-base-converter/
├── web/                  # 前端资源 (HTML, CSS, JS)
├── converters/           # 核心转换逻辑模块
│   ├── excel_converter.py
│   ├── pdf_converter.py
│   ├── word_converter.py
│   └── doc_converter.py
├── server.py             # Flask Web 服务器
├── requirements.txt      # 项目依赖
└── README.md             # 项目说明
```

## ⚠️ 常见问题

- **PaddleOCR 报错**: 请确保安装了 C++ 运行库，并检查网络连接是否能下载模型。
- **Doc 转换失败**: 请确保 Word 已激活且未在后台卡死。

## 📝 原始脚本
原始的独立运行脚本已保留在项目根目录下，但建议使用新的 Web 界面或导入 `converters` 模块使用。