// ============================================================
// PDF 指定页替换工具（pdf-replace-pages）
// 依赖 app.js 中的: optionsContainer, convertBtn, formatSize, showResult
// ============================================================

const replaceState = {
    pdf: null,        // { isLocal, name, path?, file?, size }
    pdfInfo: null,    // { page_count, pages: [{width, height}] }
    images: []        // { isLocal, name, path?, file?, size, width?, height? }
};

const REPLACE_IMG_EXTS = ['.webp', '.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff'];

function escHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function naturalCompare(a, b) {
    return a.name.localeCompare(b.name, 'zh-CN', { numeric: true, sensitivity: 'base' });
}

function initReplaceTool() {
    replaceState.pdf = null;
    replaceState.pdfInfo = null;
    replaceState.images = [];

    optionsContainer.innerHTML = `
        <div class="replace-panel">
            <div class="replace-step">
                <div class="step-head"><span class="step-no">1</span>源 PDF 文件</div>
                <div class="replace-zone" id="replace-pdf-zone">
                    <span class="material-icons-outlined">picture_as_pdf</span>
                    <div class="zone-text">
                        <b>点击选择出错的 PDF 文件</b>
                        <span>或将 PDF 拖放到此处 · 新文件将保存在源文件同一目录</span>
                    </div>
                </div>
                <div id="replace-pdf-card"></div>
            </div>

            <div class="replace-step">
                <div class="step-head"><span class="step-no">2</span>替换用图片</div>
                <div class="replace-zone" id="replace-img-zone">
                    <span class="material-icons-outlined">add_photo_alternate</span>
                    <div class="zone-text">
                        <b>点击选择图片（可多选）</b>
                        <span>支持 WebP / JPG / PNG / BMP / TIF · 按文件名自然排序，可在下方调整顺序</span>
                    </div>
                </div>
            </div>

            <div class="replace-step">
                <div class="step-head"><span class="step-no">3</span>页码与放置方式</div>
                <div class="replace-options">
                    <div class="option-group">
                        <label for="replace-page-spec">要替换的页码（按顺序依次对应图片）：</label>
                        <input type="text" id="replace-page-spec" placeholder="例如: 5, 12-13">
                        <span class="option-desc" id="replace-page-hint">支持单页与区间，多个用逗号分隔</span>
                    </div>
                    <div class="option-group">
                        <label for="replace-fit-mode">图片放置方式：</label>
                        <select id="replace-fit-mode">
                            <option value="contain" selected>等比适应（完整显示，居中留白）- 推荐</option>
                            <option value="stretch">拉伸铺满（可能变形）</option>
                            <option value="cover">等比铺满（居中裁切超出部分）</option>
                        </select>
                        <span class="option-desc">页面尺寸始终与原页完全一致，此选项仅决定图片如何放入页面</span>
                    </div>
                </div>
            </div>

            <div class="replace-step">
                <div class="step-head"><span class="step-no">4</span>对应关系预览</div>
                <div id="replace-preview"></div>
            </div>
        </div>
    `;
    optionsContainer.classList.remove('hidden');

    const pdfZone = document.getElementById('replace-pdf-zone');
    const imgZone = document.getElementById('replace-img-zone');
    pdfZone.addEventListener('click', () => pickReplaceFiles('pdf'));
    imgZone.addEventListener('click', () => pickReplaceFiles('images'));
    [pdfZone, imgZone].forEach(zone => {
        zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
        zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
        zone.addEventListener('drop', e => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            handleReplaceDroppedFiles(e.dataTransfer.files);
        });
    });
    document.getElementById('replace-page-spec').addEventListener('input', updateReplacePreview);
    document.getElementById('replace-fit-mode').addEventListener('change', updateReplacePreview);

    updateReplacePreview();
}

// ---------- 文件选择 ----------
async function pickReplaceFiles(kind) {
    const toolKey = kind === 'pdf' ? 'pdf-replace-pdf' : 'pdf-replace-images';
    try {
        const resp = await fetch('/api/pick-local-files', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool: toolKey })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || 'picker failed');
        const files = (data.files || []).map(f => ({ isLocal: true, name: f.name, path: f.path, size: f.size }));
        if (!files.length) return;
        if (kind === 'pdf') {
            const pdf = files.find(f => f.name.toLowerCase().endsWith('.pdf'));
            if (!pdf) return alert('请选择 PDF 文件');
            await setReplacePdf(pdf);
        } else {
            await addReplaceImages(files.filter(f => isReplaceImageName(f.name)));
        }
    } catch (err) {
        console.error('Native picker failed, fallback to browser input:', err);
        document.getElementById(kind === 'pdf' ? 'replace-pdf-input' : 'replace-img-input').click();
    }
}

function isReplaceImageName(name) {
    const n = name.toLowerCase();
    return REPLACE_IMG_EXTS.some(ext => n.endsWith(ext));
}

function handleReplaceDroppedFiles(fileListObj) {
    const files = Array.from(fileListObj || []);
    const pdf = files.find(f => f.name.toLowerCase().endsWith('.pdf'));
    const imgs = files.filter(f => isReplaceImageName(f.name));
    const rejected = files.filter(f => f !== pdf && !imgs.includes(f));
    if (pdf) setReplacePdf({ isLocal: false, name: pdf.name, file: pdf, size: pdf.size });
    if (imgs.length) addReplaceImages(imgs.map(f => ({ isLocal: false, name: f.name, file: f, size: f.size })));
    if (rejected.length) alert(`以下文件格式不支持，已忽略：\n${rejected.map(f => f.name).join('\n')}`);
}

document.getElementById('replace-pdf-input').addEventListener('change', e => {
    handleReplaceDroppedFiles(e.target.files);
    e.target.value = '';
});
document.getElementById('replace-img-input').addEventListener('change', e => {
    handleReplaceDroppedFiles(e.target.files);
    e.target.value = '';
});

async function setReplacePdf(pdf) {
    replaceState.pdf = pdf;
    replaceState.pdfInfo = null;
    renderReplacePdfCard();
    updateReplacePreview();
    if (pdf.isLocal) {
        try {
            const resp = await fetch('/api/replace-info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pdf_path: pdf.path })
            });
            const data = await resp.json();
            if (resp.ok && data.pdf && replaceState.pdf === pdf) {
                replaceState.pdfInfo = data.pdf;
            } else if (!resp.ok) {
                alert('读取 PDF 信息失败: ' + (data.error || '未知错误'));
            }
        } catch (e) {
            console.error(e);
        }
        renderReplacePdfCard();
        updateReplacePreview();
    }
}

async function addReplaceImages(items) {
    if (!items.length) return;
    // 去重（同一路径/同名同大小）
    const key = it => it.isLocal ? 'L:' + it.path : 'U:' + it.name + ':' + it.size;
    const existing = new Set(replaceState.images.map(key));
    items = items.filter(it => !existing.has(key(it)));
    items.sort(naturalCompare);

    // 读取图片尺寸（用于方向提醒）
    const local = items.filter(i => i.isLocal);
    if (local.length) {
        try {
            const resp = await fetch('/api/replace-info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_paths: local.map(i => i.path) })
            });
            const data = await resp.json();
            (data.images || []).forEach((s, idx) => {
                if (s && local[idx]) { local[idx].width = s.width; local[idx].height = s.height; }
            });
        } catch (e) { console.error(e); }
    }
    for (const it of items.filter(i => !i.isLocal)) {
        try {
            const bmp = await createImageBitmap(it.file);
            it.width = bmp.width; it.height = bmp.height;
            bmp.close();
        } catch (e) { /* 浏览器无法解码时跳过尺寸检查 */ }
    }

    replaceState.images = replaceState.images.concat(items);
    replaceState.images.sort(naturalCompare);
    updateReplacePreview();
}

// ---------- 渲染 ----------
function renderReplacePdfCard() {
    const box = document.getElementById('replace-pdf-card');
    if (!box) return;
    const pdf = replaceState.pdf;
    if (!pdf) { box.innerHTML = ''; return; }

    let infoText = '';
    const info = replaceState.pdfInfo;
    if (info) {
        const sizes = {};
        info.pages.forEach(p => {
            const k = `${Math.round(p.width)}×${Math.round(p.height)}`;
            sizes[k] = (sizes[k] || 0) + 1;
        });
        const sizeDesc = Object.entries(sizes).slice(0, 3)
            .map(([k, n]) => `${describePageSize(k)}${Object.keys(sizes).length > 1 ? ` ×${n}页` : ''}`).join('，');
        infoText = `共 <b>${info.page_count}</b> 页 · ${sizeDesc}${Object.keys(sizes).length > 3 ? ' 等' : ''}`;
    } else if (pdf.isLocal) {
        infoText = '正在读取页面信息…';
    } else {
        infoText = '拖拽上传模式：无法读取源路径，结果只能通过浏览器下载（推荐点击上方按钮选择本地文件）';
    }

    box.innerHTML = `
        <div class="replace-file-card">
            <span class="material-icons-outlined">description</span>
            <div class="rf-main">
                <div class="rf-name" title="${escHtml(pdf.name)}">${escHtml(pdf.name)} <span class="file-size">${formatSize(pdf.size)}</span></div>
                <div class="rf-sub">${infoText}</div>
                ${pdf.isLocal ? `<div class="file-path-badge">📍 ${escHtml(pdf.path)}</div>` : ''}
            </div>
            <button class="remove-btn" title="移除" onclick="clearReplacePdf()"><span class="material-icons-outlined">close</span></button>
        </div>`;
}

function describePageSize(k) {
    const [w, h] = k.split('×').map(Number);
    const near = (a, b) => Math.abs(a - b) <= 3;
    const named = [['A4', 595, 842], ['A3', 842, 1191], ['A5', 420, 595], ['B5', 499, 709], ['Letter', 612, 792]];
    for (const [n, a, b] of named) {
        if (near(w, a) && near(h, b)) return `${n} 纵向`;
        if (near(w, b) && near(h, a)) return `${n} 横向`;
    }
    return `${w}×${h}pt（${w > h ? '横向' : '纵向'}）`;
}

function clearReplacePdf() {
    replaceState.pdf = null;
    replaceState.pdfInfo = null;
    renderReplacePdfCard();
    updateReplacePreview();
}

function removeReplaceImage(idx) {
    replaceState.images.splice(idx, 1);
    updateReplacePreview();
}

function moveReplaceImage(idx, delta) {
    const j = idx + delta;
    const arr = replaceState.images;
    if (j < 0 || j >= arr.length) return;
    [arr[idx], arr[j]] = [arr[j], arr[idx]];
    updateReplacePreview();
}

function clearReplaceImages() {
    replaceState.images = [];
    updateReplacePreview();
}

// 与后端 parse_ordered_pages 保持一致
function parseReplacePages(spec, total) {
    spec = (spec || '').replace(/[，、;；]/g, ',').replace(/[~～—–]/g, '-').replace(/\s+/g, ',');
    const pages = [];
    for (let part of spec.split(',')) {
        part = part.trim();
        if (!part) continue;
        let range;
        const m = part.match(/^(\d+)-(\d+)$/);
        if (m) {
            const s = +m[1], e = +m[2];
            if (s > e) return { error: `页码区间错误: '${part}'` };
            range = [];
            for (let p = s; p <= e; p++) range.push(p);
        } else if (/^\d+$/.test(part)) {
            range = [+part];
        } else {
            return { error: `页码格式错误: '${part}'` };
        }
        for (const p of range) {
            if (p < 1 || (total && p > total)) return { error: `页码 ${p} 超出范围（1-${total}）` };
            if (pages.includes(p)) return { error: `页码 ${p} 重复` };
            pages.push(p);
        }
    }
    return { pages };
}

function updateReplacePreview() {
    const box = document.getElementById('replace-preview');
    if (!box) return;
    const specInput = document.getElementById('replace-page-spec');
    const hint = document.getElementById('replace-page-hint');
    const fitMode = document.getElementById('replace-fit-mode').value;
    const info = replaceState.pdfInfo;
    const imgs = replaceState.images;

    const parsed = parseReplacePages(specInput.value, info ? info.page_count : 0);
    const pages = parsed.pages || [];
    if (parsed.error) {
        hint.textContent = '⚠️ ' + parsed.error;
        hint.classList.add('hint-error');
        specInput.classList.add('input-error');
    } else {
        hint.textContent = pages.length ? `已识别 ${pages.length} 页：${pages.join(', ')}` : '支持单页与区间，多个用逗号分隔';
        hint.classList.remove('hint-error');
        specInput.classList.remove('input-error');
    }

    const rows = Math.max(pages.length, imgs.length);
    let html = '';
    if (rows === 0) {
        html = '<div class="replace-empty">选择图片并输入页码后，这里会显示「第几页 ← 哪张图片」的对应关系</div>';
    } else {
        html += `<div class="replace-toolbar">
            <span>图片 ${imgs.length} 张 · 页码 ${pages.length} 个</span>
            ${imgs.length ? '<button type="button" class="text-btn" onclick="clearReplaceImages()">清空图片</button>' : ''}
        </div>`;
        html += '<table class="replace-table"><thead><tr><th>页码</th><th>原页尺寸</th><th></th><th>替换图片</th><th>提示</th><th>顺序</th></tr></thead><tbody>';
        for (let i = 0; i < rows; i++) {
            const p = pages[i];
            const img = imgs[i];
            const pageSize = (p && info) ? info.pages[p - 1] : null;
            let tip = '';
            let rowCls = '';
            if (!p) { tip = '<span class="tag tag-error">缺少页码</span>'; rowCls = 'row-error'; }
            else if (!img) { tip = '<span class="tag tag-error">缺少图片</span>'; rowCls = 'row-error'; }
            else if (pageSize && img.width && img.height) {
                const pr = pageSize.width / pageSize.height;
                const ir = img.width / img.height;
                const pLand = pr > 1.02, pPort = pr < 0.98;
                const iLand = ir > 1.02, iPort = ir < 0.98;
                if ((pLand && iPort) || (pPort && iLand)) {
                    tip = '<span class="tag tag-info">自动纠正为图片版式</span>';
                } else if (Math.abs(ir - pr) / pr > 0.03) {
                    const t = { contain: '比例不同，将留白', stretch: '比例不同，将拉伸', cover: '比例不同，将裁切' }[fitMode];
                    tip = `<span class="tag tag-info">${t}</span>`;
                } else {
                    tip = '<span class="tag tag-ok">比例匹配</span>';
                }
            } else {
                tip = '<span class="tag tag-ok">就绪</span>';
            }
            const pageSizeTxt = pageSize ? `${Math.round(pageSize.width)}×${Math.round(pageSize.height)}pt` : '—';
            const imgCell = img
                ? `<div class="img-cell"><span class="img-name" title="${escHtml(img.isLocal ? img.path : img.name)}">${escHtml(img.name)}</span>
                     <span class="img-meta">${img.width ? `${img.width}×${img.height}px · ` : ''}${formatSize(img.size)}</span></div>`
                : '<span class="muted">—</span>';
            const orderCell = img ? `
                <div class="order-btns">
                    <button type="button" title="上移" onclick="moveReplaceImage(${i},-1)" ${i === 0 ? 'disabled' : ''}><span class="material-icons-outlined">arrow_upward</span></button>
                    <button type="button" title="下移" onclick="moveReplaceImage(${i},1)" ${i === imgs.length - 1 ? 'disabled' : ''}><span class="material-icons-outlined">arrow_downward</span></button>
                    <button type="button" title="移除" onclick="removeReplaceImage(${i})"><span class="material-icons-outlined">close</span></button>
                </div>` : '';
            html += `<tr class="${rowCls}">
                <td class="page-no">${p ? `第 ${p} 页` : '<span class="muted">—</span>'}</td>
                <td class="muted">${pageSizeTxt}</td>
                <td class="arrow"><span class="material-icons-outlined">west</span></td>
                <td>${imgCell}</td>
                <td>${tip}</td>
                <td>${orderCell}</td>
            </tr>`;
        }
        html += '</tbody></table>';
    }
    box.innerHTML = html;

    const ready = !!replaceState.pdf && imgs.length > 0 && !parsed.error
        && pages.length > 0 && pages.length === imgs.length;
    convertBtn.disabled = !ready;
    convertBtn.textContent = ready ? `替换 ${pages.length} 页并生成新文件` : '开始替换';
}

// ---------- 提交 ----------
async function startReplaceConversion() {
    const pdf = replaceState.pdf;
    const imgs = replaceState.images;
    const spec = document.getElementById('replace-page-spec').value.trim();
    const fitMode = document.getElementById('replace-fit-mode').value;

    const hasWarn = document.querySelector('.replace-table .row-warn');
    if (hasWarn && !confirm('部分图片与原页面方向不一致（横版/竖版），仍要继续替换吗？')) return;

    const formData = new FormData();
    if (pdf.isLocal) formData.append('pdf_path', pdf.path);
    else formData.append('pdf_file', pdf.file);

    let uploadIdx = 0;
    imgs.forEach(img => {
        if (img.isLocal) {
            formData.append('image_order', 'L:' + img.path);
        } else {
            formData.append('image_files', img.file);
            formData.append('image_order', 'U:' + (uploadIdx++));
        }
    });
    formData.append('page_spec', spec);
    formData.append('fit_mode', fitMode);

    convertBtn.disabled = true;
    convertBtn.textContent = '处理中...';
    try {
        const response = await fetch('/api/convert/pdf-replace-pages', { method: 'POST', body: formData });
        const result = await response.json();
        if (response.ok) showResult(result);
        else alert('处理失败: ' + (result.error || '未知错误'));
    } catch (error) {
        alert('网络错误: ' + error.message);
    } finally {
        updateReplacePreview();
    }
}
