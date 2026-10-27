let currentTool = null;
let selectedFiles = []; // 支持 { file: File } 或 { isLocal: true, name: string, path: string, size: number }

// DOM Elements
const toolsGrid = document.querySelector('.tools-grid');
const uploadSection = document.getElementById('upload-section');
const toolTitle = document.getElementById('current-tool-title');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const convertBtn = document.getElementById('convert-btn');
const modal = document.getElementById('result-modal');
const downloadLinks = document.getElementById('download-links');
const optionsContainer = document.getElementById('tool-options-container');

// Tool Selection
function selectTool(type) {
    currentTool = type;
    const titles = {
        'excel': 'Excel 转换',
        'pdf': 'PDF 转换 (OCR)',
        'pdf2docx': 'PDF 转 DOCX',
        'doc2docx': 'Doc 转 Docx',
        'word-to-md': 'Word 转 Markdown',
        'merge-docx': '多 Word 文档合并',
        'pdf-merge': 'PDF 文档合并',
        'pdf-compress': 'PDF 文件压缩',
        'pdf-to-images': 'PDF 导出图片',
        'images-to-pdf': '图片合成 PDF',
        'pdf-split-size': '按大小拆分 PDF',
        'pdf-split-parts': '按份数拆分 PDF',
        'pdf-split-pages': '指定页码提取/删除',
        'pdf-highlight': 'PDF 关键词高亮',
        'pdf-replace-pages': 'PDF 指定页替换'
    };

    // Update UI
    toolTitle.textContent = titles[type] || '上传文件';

    // Accept types
    let accept = '';
    if (type === 'excel') accept = '.xlsx, .xlsm, .xls';
    else if (type === 'doc2docx') accept = '.doc';
    else if (type === 'word-to-md' || type === 'merge-docx') accept = '.docx';
    else if (type === 'images-to-pdf') accept = '.png, .jpg, .jpeg, .bmp, .webp';
    else accept = '.pdf';

    fileInput.accept = accept;

    // Render tool dynamic options
    renderToolOptions(type);

    // 指定页替换工具使用专属面板，隐藏通用上传区
    const isReplace = type === 'pdf-replace-pages';
    dropZone.classList.toggle('hidden', isReplace);
    fileList.classList.toggle('hidden', isReplace);
    convertBtn.textContent = isReplace ? '开始替换' : '开始转换';

    // Switch views
    toolsGrid.classList.add('hidden');
    uploadSection.classList.remove('hidden');

    // Clear previous files
    selectedFiles = [];
    renderFileList();
}

function renderToolOptions(type) {
    optionsContainer.innerHTML = '';
    optionsContainer.classList.add('hidden');

    if (type === 'pdf-compress') {
        optionsContainer.innerHTML = `
            <div class="option-group">
                <label for="compress-quality">选择压缩级别：</label>
                <select id="compress-quality">
                    <option value="1">轻度压缩 (图片质量 85%，日常使用)</option>
                    <option value="2" selected>中度压缩 (图片质量 60%，体积明显减小)</option>
                    <option value="3">高度压缩 (图片质量 35%，体积大幅减小)</option>
                </select>
                <span class="option-desc">通过重采样压缩 PDF 内部高分辨率位图以节省存储</span>
            </div>
        `;
        optionsContainer.classList.remove('hidden');
    } else if (type === 'pdf-to-images') {
        optionsContainer.innerHTML = `
            <div class="option-group">
                <label for="export-scale">导出图片清晰度 (缩放比例)：</label>
                <select id="export-scale">
                    <option value="1.0">原始分辨率 (1.0x)</option>
                    <option value="1.5" selected>超清高画质 (1.5x - 推荐)</option>
                    <option value="2.0">原尺寸 2.0x (高精度打印级)</option>
                    <option value="0.5">缩略图级别 (0.5x)</option>
                </select>
                <span class="option-desc">每页将渲染为高清 PNG，并自动打包为 ZIP 供一键下载</span>
            </div>
        `;
        optionsContainer.classList.remove('hidden');
    } else if (type === 'pdf-split-size') {
        optionsContainer.innerHTML = `
            <div class="option-group">
                <label for="split-max-size">每个分卷的最大体积 (MB)：</label>
                <input type="number" id="split-max-size" value="10" min="1" max="500" step="1">
                <span class="option-desc">系统将在不超过该文件大小的整页边界处智能拆分</span>
            </div>
        `;
        optionsContainer.classList.remove('hidden');
    } else if (type === 'pdf-split-parts') {
        optionsContainer.innerHTML = `
            <div class="option-group">
                <label for="split-num-parts">均等拆分的份数：</label>
                <input type="number" id="split-num-parts" value="2" min="2" max="100" step="1">
                <span class="option-desc">按页数均等切分为多份 PDF 文件</span>
            </div>
        `;
        optionsContainer.classList.remove('hidden');
    } else if (type === 'pdf-split-pages') {
        optionsContainer.innerHTML = `
            <div class="option-group">
                <label for="split-page-mode">处理操作：</label>
                <select id="split-page-mode">
                    <option value="extract" selected>提取指定页码 (仅保留这些页)</option>
                    <option value="delete">删除指定页码 (排除这些页)</option>
                </select>
            </div>
            <div class="option-group">
                <label for="split-page-ranges">页码范围：</label>
                <input type="text" id="split-page-ranges" placeholder="例如: 1-3, 5, 8-10">
                <span class="option-desc">支持单页（如 5）与连续区间（如 1-3），多个请用英文逗号分隔</span>
            </div>
        `;
        optionsContainer.classList.remove('hidden');
    } else if (type === 'pdf-highlight') {
        optionsContainer.innerHTML = `
            <div class="option-group">
                <label for="highlight-keyword">要搜索高亮的关键词：</label>
                <input type="text" id="highlight-keyword" placeholder="输入要高亮搜索的词汇（如：档案、合同）">
                <span class="option-desc">系统将在全文检索该词并自动添加黄色高亮标注</span>
            </div>
        `;
        optionsContainer.classList.remove('hidden');
    } else if (type === 'pdf-replace-pages') {
        initReplaceTool();
    }
}

function backToTools() {
    uploadSection.classList.add('hidden');
    toolsGrid.classList.remove('hidden');
    currentTool = null;
    selectedFiles = [];
    dropZone.classList.remove('hidden');
    fileList.classList.remove('hidden');
    convertBtn.textContent = '开始转换';
}

// 弹出原生 Windows 文件选择器，直接获取绝对路径
async function openNativeFilePicker(event) {
    if (event) event.stopPropagation();
    try {
        const resp = await fetch('/api/pick-local-files', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool: currentTool })
        });
        const data = await resp.json();
        if (data.files && data.files.length > 0) {
            for (let f of data.files) {
                selectedFiles.push({
                    isLocal: true,
                    name: f.name,
                    path: f.path,
                    size: f.size
                });
            }
            renderFileList();
        }
    } catch (err) {
        console.error('Error opening native file picker:', err);
        // 如果失败，回退触发传统 input 选择
        fileInput.click();
    }
}

// File Handling
dropZone.addEventListener('click', (e) => {
    // 默认点击进入原生文件选择器，便于获取真实路径保存回原目录
    openNativeFilePicker(e);
});

fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    handleFiles(e.dataTransfer.files);
});

function handleFiles(files) {
    for (let file of files) {
        if (isValidFile(file, currentTool)) {
            selectedFiles.push({
                isLocal: false,
                file: file,
                name: file.name,
                size: file.size
            });
        } else {
            alert(`文件 ${file.name} 格式不符合当前工具要求。`);
        }
    }
    renderFileList();
    fileInput.value = '';
}

function isValidFile(file, tool) {
    const name = file.name.toLowerCase();
    if (tool === 'excel') return name.endsWith('.xlsx') || name.endsWith('.xlsm') || name.endsWith('.xls');
    if (tool === 'doc2docx') return name.endsWith('.doc');
    if (tool === 'word-to-md' || tool === 'merge-docx') return name.endsWith('.docx');
    if (tool === 'images-to-pdf') return name.endsWith('.png') || name.endsWith('.jpg') || name.endsWith('.jpeg') || name.endsWith('.bmp') || name.endsWith('.webp');
    return name.endsWith('.pdf');
}

function renderFileList() {
    if (currentTool === 'pdf-replace-pages') {
        updateReplacePreview();
        return;
    }
    fileList.innerHTML = '';
    selectedFiles.forEach((itemData, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';

        let pathBadge = '';
        if (itemData.isLocal && itemData.path) {
            pathBadge = `<span class="file-path-badge">📍 原路径: ${itemData.path} (新文件将自动存回此目录)</span>`;
        } else {
            pathBadge = `<span class="file-path-badge warn">⚠️ 浏览器拖拽模式无法获取电脑原路径，处理后只能通过网页下载备份。如需自动存回源目录，请点击上方“选择电脑本地文件”。</span>`;
        }

        item.innerHTML = `
            <div class="file-info" style="max-width: 85%;">
                <span class="material-icons-outlined file-icon">insert_drive_file</span>
                <div>
                    <span class="file-name" title="${itemData.name}">${itemData.name}</span>
                    <span class="file-size" style="margin-left: 8px;">${formatSize(itemData.size)}</span>
                    ${pathBadge}
                </div>
            </div>
            <button class="remove-btn" onclick="removeFile(${index})">
                <span class="material-icons-outlined">close</span>
            </button>
        `;

        fileList.appendChild(item);
    });

    convertBtn.disabled = selectedFiles.length === 0;
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
}

function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 在资源管理器中定位打开文件夹
async function locateFileInExplorer(filePath) {
    try {
        const resp = await fetch('/api/open-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: filePath })
        });
        const res = await resp.json();
        if (!resp.ok) {
            alert('定位文件夹失败: ' + (res.error || '未知错误'));
        }
    } catch (e) {
        alert('无法定位文件夹: ' + e.message);
    }
}

// API Interaction
async function startConversion() {
    if (currentTool === 'pdf-replace-pages') return startReplaceConversion();
    if (selectedFiles.length === 0) return;

    // 参数校验
    if (currentTool === 'pdf-split-pages') {
        const pagesInput = document.getElementById('split-page-ranges');
        if (!pagesInput || !pagesInput.value.trim()) {
            alert('请输入要处理的页码范围（例如 1-3, 5）');
            return;
        }
    } else if (currentTool === 'pdf-highlight') {
        const kwInput = document.getElementById('highlight-keyword');
        if (!kwInput || !kwInput.value.trim()) {
            alert('请输入要高亮的关键词');
            return;
        }
    }

    convertBtn.disabled = true;
    convertBtn.textContent = '处理中...';

    const formData = new FormData();
    selectedFiles.forEach(item => {
        if (item.isLocal) {
            formData.append('local_paths', item.path);
        } else {
            formData.append('files', item.file);
        }
    });

    // 附加额外参数
    if (currentTool === 'pdf-compress') {
        const q = document.getElementById('compress-quality');
        if (q) formData.append('quality', q.value);
    } else if (currentTool === 'pdf-to-images') {
        const s = document.getElementById('export-scale');
        if (s) formData.append('scale', s.value);
    } else if (currentTool === 'pdf-split-size') {
        const ms = document.getElementById('split-max-size');
        if (ms) formData.append('max_size', ms.value);
    } else if (currentTool === 'pdf-split-parts') {
        const np = document.getElementById('split-num-parts');
        if (np) formData.append('num_parts', np.value);
    } else if (currentTool === 'pdf-split-pages') {
        const pr = document.getElementById('split-page-ranges');
        const md = document.getElementById('split-page-mode');
        if (pr) formData.append('page_ranges', pr.value.trim());
        if (md) formData.append('mode', md.value);
    } else if (currentTool === 'pdf-highlight') {
        const kw = document.getElementById('highlight-keyword');
        if (kw) formData.append('keyword', kw.value.trim());
    }

    try {
        const endpoint = `/api/convert/${currentTool}`;
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            showResult(result);
        } else {
            alert('处理失败: ' + (result.error || '未知错误'));
        }
    } catch (error) {
        alert('网络错误: ' + error.message);
    } finally {
        convertBtn.disabled = false;
        convertBtn.textContent = '开始转换';
    }
}

function showResult(result) {
    downloadLinks.innerHTML = '';

    if (result.files && result.files.length > 0) {
        result.files.forEach(file => {
            const card = document.createElement('div');
            card.className = 'result-item-card';

            let savedNotice = '';
            let openBtn = '';
            if (file.saved_in_source_dir && file.path) {
                savedNotice = `<div class="result-path-hint">📁 已保存至源目录: <b>${file.path}</b></div>`;
                openBtn = `
                    <button type="button" class="open-folder-btn" onclick="locateFileInExplorer('${file.path.replace(/\\/g, '\\\\')}')">
                        <span class="material-icons-outlined" style="font-size:16px;">folder_open</span>
                        在文件夹中显示
                    </button>
                `;
            }

            card.innerHTML = `
                <div class="result-item-header">
                    <span>📄 ${file.name}</span>
                </div>
                ${savedNotice}
                <div class="result-actions">
                    <a href="${file.url}" class="download-link" download style="flex: 1; text-align: center;">⬇️ 浏览器下载备份</a>
                    ${openBtn}
                </div>
            `;
            downloadLinks.appendChild(card);
        });
    } else {
        downloadLinks.innerHTML = '<p>没有生成输出文件</p>';
    }

    modal.classList.remove('hidden');
}

function closeModal() {
    modal.classList.add('hidden');
}
