let currentTool = null;
let selectedFiles = [];

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

// Tool Selection
function selectTool(type) {
    currentTool = type;
    const titles = {
        'excel': 'Excel 转换',
        'pdf': 'PDF 转换',
        'word': 'Word 转换',
        'doc2docx': 'Doc 转 Docx'
    };
    
    // Update UI
    toolTitle.textContent = titles[type] || '上传文件';
    
    // Accept types
    let accept = '';
    if(type === 'excel') accept = '.xlsx, .xlsm';
    else if(type === 'pdf') accept = '.pdf';
    else if(type === 'word') accept = '.docx';
    else if(type === 'doc2docx') accept = '.doc';
    
    fileInput.accept = accept;
    
    // Switch views
    toolsGrid.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    
    // Clear previous files
    selectedFiles = [];
    renderFileList();
}

function backToTools() {
    uploadSection.classList.add('hidden');
    toolsGrid.classList.remove('hidden');
    currentTool = null;
    selectedFiles = [];
}

// File Handling
dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
    fileInput.value = ''; // Reset
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
});

function handleFiles(files) {
    if (!currentTool) return;
    
    const validExtensions = {
        'excel': ['.xlsx', '.xlsm'],
        'pdf': ['.pdf'],
        'word': ['.docx'],
        'doc2docx': ['.doc']
    };

    const allowed = validExtensions[currentTool];

    for (let file of files) {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (allowed.includes(ext)) {
            selectedFiles.push(file);
        } else {
            alert(`文件 ${file.name} 格式不正确，仅支持 ${allowed.join(', ')}`);
        }
    }
    renderFileList();
}

function renderFileList() {
    fileList.innerHTML = '';
    selectedFiles.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <div class="file-info">
                <span class="material-icons-outlined" style="color:#5F6368">insert_drive_file</span>
                <div>
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatSize(file.size)}</div>
                </div>
            </div>
            <span class="material-icons-outlined remove-file" onclick="removeFile(${index})">close</span>
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

// API Interaction
async function startConversion() {
    if (selectedFiles.length === 0) return;

    convertBtn.disabled = true;
    convertBtn.textContent = '处理中...';
    
    const formData = new FormData();
    selectedFiles.forEach(file => {
        formData.append('files', file);
    });
    
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
            alert('转换失败: ' + (result.error || '未知错误'));
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
            const link = document.createElement('a');
            link.href = file.url;
            link.className = 'download-link';
            link.textContent = `⬇️ 下载 ${file.name}`;
            link.download = '';
            downloadLinks.appendChild(link);
        });
    } else {
        downloadLinks.innerHTML = '<p>没有生成输出文件</p>';
    }
    
    modal.classList.remove('hidden');
}

function closeModal() {
    modal.classList.add('hidden');
    // Optional: Clear files after successful conversion
    // selectedFiles = [];
    // renderFileList();
}
