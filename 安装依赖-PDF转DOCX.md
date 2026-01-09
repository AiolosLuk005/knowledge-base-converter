# PDF转DOCX工具 - 依赖安装说明

## 重要改进说明

原来的脚本使用 `PyMuPDF (fitz)` 只提取纯文本，导致丢失了：
- ❌ 图片和图形
- ❌ 表格结构
- ❌ 文本格式（字体、大小、颜色等）
- ❌ 页面布局

**新版本使用 `pdf2docx` 库，可以保留：**
- ✅ 图片和图形
- ✅ 表格（结构和内容）
- ✅ 文本格式（字体、大小、颜色等）
- ✅ 页面布局
- ✅ 段落格式

## 安装依赖

### 方法1：使用pip安装

```bash
pip install pdf2docx
```

### 方法2：如果有requirements.txt

将以下内容添加到 `requirements.txt`：

```
pdf2docx
```

然后运行：

```bash
pip install -r requirements.txt
```

## 使用说明

1. 运行脚本：
   ```bash
   python PDF转换docx格式.py
   ```

2. 选择处理方式：
   - 点击"是"：处理整个文件夹中的所有PDF文件
   - 点击"否"：只处理单个PDF文件

3. 等待转换完成，DOCX文件将保存在原PDF文件的同一目录下

## 注意事项

1. **pdf2docx** 库依赖于 `PyMuPDF (fitz)` 和 `python-docx`，安装时会自动安装这些依赖
2. 转换复杂PDF可能需要较长时间，请耐心等待
3. 转换效果取决于PDF的复杂度和格式，扫描版PDF效果可能不如原生PDF
4. 如果PDF包含特殊字体，确保系统已安装相应字体

## 卸载旧依赖（可选）

如果不再需要单独的 `PyMuPDF`，可以卸载：

```bash
pip uninstall PyMuPDF
```

但注意 `pdf2docx` 依赖它，所以卸载后会被重新安装。

## 可能的错误及解决方案

### 错误1：ModuleNotFoundError: No module named 'pdf2docx'
**解决方案**：运行 `pip install pdf2docx`

### 错误2：转换失败或崩溃
**解决方案**：
- 检查PDF文件是否损坏
- 确保有足够的内存和磁盘空间
- 尝试转换单个文件而非整个文件夹

### 错误3：转换后格式不完美
**说明**：这是正常现象。PDF到DOCX的转换是复杂的过程：
- 扫描版PDF（图片）转换效果较差
- 复杂布局可能需要手动调整
- 某些特殊效果可能无法完全保留
