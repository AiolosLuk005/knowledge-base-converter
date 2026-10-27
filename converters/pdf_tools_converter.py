"""
PDF and Archive tools converter module.
Provides functions for merging, compressing, splitting, searching, and converting PDFs and images,
based on PyMuPDF (fitz) and Pillow.
"""
import os
import io
import zipfile
import fitz  # PyMuPDF
from PIL import Image, ImageOps

def merge_pdf_files(file_paths, output_filename=None):
    """
    Merge multiple PDF files into one PDF.
    """
    if not file_paths:
        raise ValueError("文件列表为空")
    if len(file_paths) == 1:
        raise ValueError("至少需要两个 PDF 文件才能合并")

    output_dir = os.path.dirname(file_paths[0])
    if not output_filename:
        first_name = os.path.splitext(os.path.basename(file_paths[0]))[0]
        output_filename = f"{first_name}等{len(file_paths)}份文档合并.pdf"
    output_path = os.path.join(output_dir, output_filename)

    merged_doc = fitz.open()
    for fp in file_paths:
        with fitz.open(fp) as doc:
            merged_doc.insert_pdf(doc)

    merged_doc.save(output_path, garbage=4, deflate=True)
    merged_doc.close()
    return [output_path]


def compress_pdf_file(pdf_path, quality_level="2"):
    """
    Compress PDF by recompressing embedded images and deflating streams.
    quality_level:
      "1": 轻度压缩 (quality 85)
      "2": 中度压缩 (quality 60)
      "3": 高度压缩 (quality 35)
    """
    quality_map = {
        "1": 85,
        "2": 60,
        "3": 35
    }
    target_quality = quality_map.get(str(quality_level), 60)

    base_dir = os.path.dirname(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(base_dir, f"{base_name}_压缩.pdf")

    doc = fitz.open(pdf_path)
    for page in doc:
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                if not base_image:
                    continue
                image_bytes = base_image["image"]
                img = Image.open(io.BytesIO(image_bytes))

                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                compressed_io = io.BytesIO()
                img.save(compressed_io, format="JPEG", quality=target_quality, optimize=True)
                compressed_bytes = compressed_io.getvalue()

                # 仅在体积确实减小时替换
                if len(compressed_bytes) < len(image_bytes):
                    doc.update_stream(xref, compressed_bytes)
            except Exception:
                continue

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return [output_path]


def pdf_to_images(pdf_path, scale=1.5):
    """
    Export each PDF page as an image, and package them into a zip file.
    """
    doc = fitz.open(pdf_path)
    base_dir = os.path.dirname(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    zip_path = os.path.join(base_dir, f"{base_name}_图片.zip")

    try:
        scale_val = float(scale)
    except (ValueError, TypeError):
        scale_val = 1.5

    matrix = fitz.Matrix(scale_val, scale_val)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=matrix)
            img_bytes = pix.tobytes("png")
            zipf.writestr(f"{base_name}_{page_num + 1:03d}.png", img_bytes)

    doc.close()
    return [zip_path]


def images_to_pdf(image_paths, output_filename=None):
    """
    Combine multiple images into a single PDF document.
    """
    if not image_paths:
        raise ValueError("图片列表为空")

    output_dir = os.path.dirname(image_paths[0])
    if not output_filename:
        first_name = os.path.splitext(os.path.basename(image_paths[0]))[0]
        output_filename = f"{first_name}等{len(image_paths)}张图片合成.pdf"
    output_path = os.path.join(output_dir, output_filename)

    doc = fitz.open()
    for img_path in image_paths:
        try:
            img_doc = fitz.open(img_path)
            rect = img_doc[0].rect
            pdf_bytes = img_doc.convert_to_pdf()
            img_doc.close()

            img_pdf = fitz.open("pdf", pdf_bytes)
            page = doc.new_page(width=rect.width, height=rect.height)
            page.show_pdf_page(rect, img_pdf, 0)
            img_pdf.close()
        except Exception:
            # Fallback using PIL
            with Image.open(img_path) as pil_img:
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                pdf_bytes_io = io.BytesIO()
                pil_img.save(pdf_bytes_io, format="PDF")
                pdf_bytes_io.seek(0)
                with fitz.open("pdf", pdf_bytes_io.read()) as pil_doc:
                    doc.insert_pdf(pil_doc)

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return [output_path]


def split_pdf_by_size(pdf_path, max_size_mb=10.0):
    """
    Split a PDF into multiple parts where each part is approximately under max_size_mb.
    """
    try:
        max_size_mb = float(max_size_mb)
    except (ValueError, TypeError):
        max_size_mb = 10.0

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    base_dir = os.path.dirname(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    output_files = []
    current_doc = fitz.open()
    part_idx = 1

    for i in range(total_pages):
        current_doc.insert_pdf(doc, from_page=i, to_page=i)
        # Check buffer size
        temp_bytes = current_doc.tobytes(garbage=4, deflate=True)
        size_mb = len(temp_bytes) / (1024 * 1024)

        if size_mb >= max_size_mb and len(current_doc) > 1:
            # Remove last page, save current part, start new with last page
            current_doc.delete_page(len(current_doc) - 1)
            part_path = os.path.join(base_dir, f"{base_name}_part{part_idx:03d}.pdf")
            current_doc.save(part_path, garbage=4, deflate=True)
            current_doc.close()
            output_files.append(part_path)

            part_idx += 1
            current_doc = fitz.open()
            current_doc.insert_pdf(doc, from_page=i, to_page=i)

    if len(current_doc) > 0:
        part_path = os.path.join(base_dir, f"{base_name}_part{part_idx:03d}.pdf")
        current_doc.save(part_path, garbage=4, deflate=True)
        current_doc.close()
        output_files.append(part_path)

    doc.close()

    # If multiple files generated, package into a zip for easy download
    if len(output_files) > 1:
        zip_path = os.path.join(base_dir, f"{base_name}_按大小拆分.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in output_files:
                zipf.write(f, os.path.basename(f))
        return [zip_path] + output_files
    return output_files


def split_pdf_by_parts(pdf_path, num_parts=2):
    """
    Split a PDF evenly into N parts.
    """
    try:
        num_parts = int(num_parts)
    except (ValueError, TypeError):
        num_parts = 2

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    num_parts = max(1, min(num_parts, total_pages))

    base_dir = os.path.dirname(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    pages_per_part = total_pages // num_parts
    remainder = total_pages % num_parts

    output_files = []
    start_page = 0
    for part_idx in range(1, num_parts + 1):
        count = pages_per_part + (1 if part_idx <= remainder else 0)
        end_page = start_page + count - 1

        part_doc = fitz.open()
        part_doc.insert_pdf(doc, from_page=start_page, to_page=end_page)
        part_path = os.path.join(base_dir, f"{base_name}_份数{part_idx}之{num_parts}.pdf")
        part_doc.save(part_path, garbage=4, deflate=True)
        part_doc.close()
        output_files.append(part_path)

        start_page = end_page + 1

    doc.close()

    if len(output_files) > 1:
        zip_path = os.path.join(base_dir, f"{base_name}_按份数拆分.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in output_files:
                zipf.write(f, os.path.basename(f))
        return [zip_path] + output_files
    return output_files


def extract_or_delete_pages(pdf_path, page_ranges_str, mode="extract"):
    """
    Extract or delete specified page numbers.
    page_ranges_str: e.g. "1-3, 5, 8-10"
    mode: "extract" (保留提取) or "delete" (删除排除)
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    target_pages = set()
    for part in page_ranges_str.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            try:
                s, e = map(int, part.split('-'))
                if s <= e:
                    for p in range(max(1, s), min(total_pages, e) + 1):
                        target_pages.add(p)
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if 1 <= p <= total_pages:
                    target_pages.add(p)
            except ValueError:
                continue

    if not target_pages:
        doc.close()
        raise ValueError(f"输入的页码无效或超出有效范围(1-{total_pages})")

    base_dir = os.path.dirname(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    out_doc = fitz.open()
    for p in range(1, total_pages + 1):
        if mode == "extract" and p in target_pages:
            out_doc.insert_pdf(doc, from_page=p - 1, to_page=p - 1)
        elif mode == "delete" and p not in target_pages:
            out_doc.insert_pdf(doc, from_page=p - 1, to_page=p - 1)

    if len(out_doc) == 0:
        out_doc.close()
        doc.close()
        raise ValueError("处理后没有剩余页面")

    suffix = "提取" if mode == "extract" else "删减"
    out_path = os.path.join(base_dir, f"{base_name}_{suffix}.pdf")
    out_doc.save(out_path, garbage=4, deflate=True)
    out_doc.close()
    doc.close()
    return [out_path]


def highlight_pdf_keywords(pdf_path, keyword):
    """
    Search and highlight keyword in PDF.
    """
    if not keyword or not keyword.strip():
        raise ValueError("请输入要高亮搜索的关键词")

    keyword = keyword.strip()
    doc = fitz.open(pdf_path)
    found = False

    for page in doc:
        text_instances = page.search_for(keyword)
        if text_instances:
            found = True
            for inst in text_instances:
                highlight = page.add_highlight_annot(inst)
                highlight.update()

    base_dir = os.path.dirname(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(base_dir, f"{base_name}_高亮[{keyword}].pdf")

    if not found:
        doc.close()
        raise ValueError(f"未在 PDF 中找到关键词: '{keyword}'")

    doc.save(out_path, garbage=4, deflate=True)
    doc.close()
    return [out_path]


# ---------------------------------------------------------------------------
# PDF 指定页替换（用图片替换源 PDF 中的出错页面）
# ---------------------------------------------------------------------------

REPLACE_FIT_MODES = ("contain", "stretch", "cover")


def get_pdf_page_info(pdf_path):
    """
    返回 PDF 总页数及每页可见尺寸（单位 pt，已考虑 CropBox 与旋转）。
    """
    with fitz.open(pdf_path) as doc:
        pages = []
        for page in doc:
            r = page.rect
            pages.append({
                "width": round(r.width, 2),
                "height": round(r.height, 2),
            })
        return {"page_count": len(doc), "pages": pages}


def get_image_sizes(image_paths):
    """
    返回图片（已按 EXIF 旋转校正后的）像素尺寸列表，用于前端方向提醒。
    """
    sizes = []
    for p in image_paths:
        try:
            with Image.open(p) as im:
                w, h = im.size
                try:
                    orientation = im.getexif().get(0x0112, 1)
                except Exception:
                    orientation = 1
                if orientation in (5, 6, 7, 8):
                    w, h = h, w
                sizes.append({"width": w, "height": h})
        except Exception:
            sizes.append(None)
    return sizes


def parse_ordered_pages(page_spec, total_pages):
    """
    按输入顺序解析页码，例如 "5, 12-13" -> [5, 12, 13]。
    支持中文逗号/顿号/空格分隔，区间可用 '-' 或 '~'。
    页码越界、重复或格式错误时抛出 ValueError。
    """
    if not page_spec or not str(page_spec).strip():
        raise ValueError("请输入要替换的页码")

    spec = str(page_spec)
    for ch in ("，", "、", ";", "；"):
        spec = spec.replace(ch, ",")
    spec = spec.replace("~", "-").replace("～", "-").replace("—", "-").replace("–", "-")

    pages = []
    for part in spec.replace(" ", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                s, e = [int(x) for x in part.split("-", 1)]
                if s > e:
                    raise ValueError
                rng = list(range(s, e + 1))
            else:
                rng = [int(part)]
        except ValueError:
            raise ValueError(f"页码格式错误: '{part}'")
        for p in rng:
            if p < 1 or p > total_pages:
                raise ValueError(f"页码 {p} 超出范围（1-{total_pages}）")
            if p in pages:
                raise ValueError(f"页码 {p} 重复")
            pages.append(p)

    if not pages:
        raise ValueError("请输入要替换的页码")
    return pages


def _prepare_image_bytes(img_path, target_ratio=None):
    """
    用 Pillow 解码图片（支持 WebP/JPG/PNG/BMP/TIF），并：
      - 按 EXIF 方向校正
      - 透明背景合成为白色
      - 统一为 RGB / 灰度
      - target_ratio 不为空时（cover 模式）居中裁切到目标宽高比
    返回高质量 JPEG 字节流。
    """
    with Image.open(img_path) as src:
        try:
            src.seek(0)  # 动图只取第一帧
        except Exception:
            pass
        im = ImageOps.exif_transpose(src)

        has_alpha = im.mode in ("RGBA", "LA", "PA") or (
            im.mode == "P" and "transparency" in im.info
        )
        if has_alpha:
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.getchannel("A"))
            im = bg
        elif im.mode not in ("RGB", "L"):
            im = im.convert("RGB")

        if target_ratio:
            w, h = im.size
            if w / h > target_ratio:
                new_w = max(1, int(round(h * target_ratio)))
                left = (w - new_w) // 2
                im = im.crop((left, 0, left + new_w, h))
            else:
                new_h = max(1, int(round(w / target_ratio)))
                top = (h - new_h) // 2
                im = im.crop((0, top, w, top + new_h))

        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=92, subsampling=0, optimize=True)
        return buf.getvalue()


def _unique_output_path(base_dir, base_name, suffix, ext=".pdf"):
    path = os.path.join(base_dir, f"{base_name}{suffix}{ext}")
    idx = 2
    while os.path.exists(path):
        path = os.path.join(base_dir, f"{base_name}{suffix}({idx}){ext}")
        idx += 1
    return path


def _reset_page_for_image(doc, page, target_w=None, target_h=None):
    """
    就地清空页面内容（保留页面对象本身，使书签/目录跳转仍然有效），
    并将页面规整为：旋转 0、MediaBox = 指定或原可见尺寸。
    返回 (重新加载后的 page, 最终宽, 最终高)。
    """
    vis_w = target_w if target_w is not None else page.rect.width
    vis_h = target_h if target_h is not None else page.rect.height
    pxref = page.xref

    # 新建独立的空内容流，避免误清空与其它页共享的内容流
    new_xref = doc.get_new_xref()
    doc.update_object(new_xref, "<<>>")
    doc.update_stream(new_xref, b" ")
    doc.xref_set_key(pxref, "Contents", f"{new_xref} 0 R")
    doc.xref_set_key(pxref, "Resources", "<<>>")
    doc.xref_set_key(pxref, "Annots", "null")
    for key in ("CropBox", "TrimBox", "BleedBox", "ArtBox"):
        doc.xref_set_key(pxref, key, "null")
    doc.xref_set_key(pxref, "MediaBox", f"[0 0 {vis_w:.4f} {vis_h:.4f}]")
    doc.xref_set_key(pxref, "Rotate", "0")

    page = doc.reload_page(page)
    return page, vis_w, vis_h


def replace_pdf_pages(pdf_path, image_paths, page_spec, fit_mode="contain"):
    """
    用图片替换 PDF 中的指定页面，输出到源文件同目录的新文件，源文件不改动。
      image_paths: 已按用户确认的顺序排列，依次对应 page_spec 中的页码
      fit_mode:
        "contain" 等比适应（居中留白，默认）
        "stretch" 拉伸铺满
        "cover"   等比铺满并居中裁切
    """
    if not image_paths:
        raise ValueError("请选择用于替换的图片")
    if fit_mode not in REPLACE_FIT_MODES:
        fit_mode = "contain"

    doc = fitz.open(pdf_path)
    try:
        total = len(doc)
        pages = parse_ordered_pages(page_spec, total)
        if len(pages) != len(image_paths):
            raise ValueError(
                f"页码数量（{len(pages)}）与图片数量（{len(image_paths)}）不一致"
            )

        for pno, img_path in zip(pages, image_paths):
            page = doc[pno - 1]
            orig_w, orig_h = page.rect.width, page.rect.height

            # 先获取图片的真实像素尺寸和长宽比
            try:
                with Image.open(img_path) as im_check:
                    try:
                        orientation = im_check.getexif().get(0x0112, 1)
                    except Exception:
                        orientation = 1
                    im_w, im_h = im_check.size
                    if orientation in (5, 6, 7, 8):
                        im_w, im_h = im_h, im_w
            except Exception:
                im_w, im_h = orig_w, orig_h

            img_ratio = im_w / im_h
            img_is_land = img_ratio > 1.05
            page_is_land = (orig_w / orig_h) > 1.05

            # 确定最终新页面的目标宽高 (target_w, target_h)
            if img_is_land == page_is_land:
                # 图片方向与当前页方向一致：保持当前页尺寸
                target_w, target_h = orig_w, orig_h
            else:
                # 图片方向与当前页方向相反（例如图片是竖版，原页做成了横版）：
                # 优先寻找与图片方向一致的参考页尺寸（前一页、后一页或全文众数）
                ref_w, ref_h = None, None
                for candidate_pno in (pno - 1, pno + 1):
                    if 1 <= candidate_pno <= total:
                        cp = doc[candidate_pno - 1]
                        if ((cp.rect.width / cp.rect.height) > 1.05) == img_is_land:
                            ref_w, ref_h = cp.rect.width, cp.rect.height
                            break
                
                if ref_w and ref_h:
                    target_w, target_h = ref_w, ref_h
                else:
                    # 若邻页都是同方向，则将当前页宽高对调，使之与图片方向匹配
                    target_w, target_h = orig_h, orig_w

            ratio = (target_w / target_h) if fit_mode == "cover" else None
            try:
                img_bytes = _prepare_image_bytes(img_path, target_ratio=ratio)
            except Exception as e:
                raise ValueError(f"无法读取图片 {os.path.basename(img_path)}: {e}")

            try:
                page, w, h = _reset_page_for_image(doc, page, target_w=target_w, target_h=target_h)
            except Exception:
                # 回退：删除旧页，在原位置插入目标尺寸新页
                doc.delete_page(pno - 1)
                page = doc.new_page(pno - 1, width=target_w, height=target_h)
                w, h = target_w, target_h

            page.insert_image(
                fitz.Rect(0, 0, w, h),
                stream=img_bytes,
                keep_proportion=(fit_mode == "contain"),
            )

        base_dir = os.path.dirname(pdf_path)
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        out_path = _unique_output_path(base_dir, base_name, "_替换页")
        doc.save(out_path, garbage=4, deflate=True)
    finally:
        doc.close()
    return [out_path]
