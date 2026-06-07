"""
Hermes ↔ knowledge-base-converter 对接客户端
==============================================
通过本地的 Flask API 调用 knowledge-base-converter 完成文件转换。

用法示例（Hermes 中调用）：
  python /d/Data-Lab/knowledge-base-converter/hermes_api_client.py convert \
    --file /path/to/input.pdf --type pdf --output /path/to/save

支持的转换类型 (--type):
  pdf        - PDF → markdown + csv (OCR + 表格提取)
  pdf2docx   - PDF → Word (docx)
  excel      - Excel → csv
  word       - Word (docx) → txt
  word-to-md - Word (docx) → markdown + csv
  doc2docx   - .doc → .docx
  merge-docx - 合并多个 docx (用 --files 传多个文件)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
import uuid
from pathlib import Path

# Force UTF-8 encoding for stdout and stderr to prevent UnicodeEncodeError on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

API_BASE = os.environ.get("KBC_API_BASE", "http://localhost:5000")



def upload_and_convert(file_paths, convert_type, output_dir=None):
    """
    上传文件到 knowledge-base-converter API 并下载转换结果。

    Args:
        file_paths: 文件路径列表
        convert_type: 转换类型 (pdf, excel, word, word-to-md, pdf2docx, doc2docx, merge-docx)
        output_dir: 输出目录，默认使用当前目录

    Returns:
        下载到本地的文件路径列表
    """
    if output_dir is None:
        output_dir = os.getcwd()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 构建 multipart/form-data 请求
    import http.client
    import mimetypes

    boundary = f"----HermesKBCBoundary{uuid.uuid4().hex[:8]}"

    body_parts = []
    for fpath in file_paths:
        fpath = Path(fpath)
        if not fpath.exists():
            raise FileNotFoundError(f"文件不存在: {fpath}")

        with open(fpath, "rb") as f:
            file_data = f.read()

        filename = fpath.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        part = (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8") + file_data
        body_parts.append(part)

    body_parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(body_parts)

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    }

    api_url = f"{API_BASE}/api/convert/{convert_type}"
    req = urllib.request.Request(api_url, data=body, headers=headers, method="POST")

    print(f"📤 上传 {len(file_paths)} 个文件到 {api_url} ...")
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"❌ API 返回 {e.code}: {body}")
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"❌ 无法连接到 {API_BASE}。请确保 APP 正在运行:\n"
            f"   conda activate StableDiffusion && cd knowledge-base-converter && python server.py\n"
            f"   错误: {e.reason}"
        )

    if "error" in result:
        raise RuntimeError(f"❌ 转换失败: {result['error']}")

    # 下载结果文件
    downloaded = []
    for file_info in result.get("files", []):
        url_path = file_info["url"]
        name = file_info["name"]
        # 修复 URL 中的反斜杠
        url_path = url_path.replace("\\", "/")

        download_url = f"{API_BASE}{url_path}"
        local_path = output_dir / name

        print(f"📥 下载 {name} ...")
        try:
            urllib.request.urlretrieve(download_url, local_path)
            downloaded.append(str(local_path.resolve()))
            print(f"   ✅ 已保存: {local_path}")
        except Exception as e:
            print(f"   ⚠️  下载失败: {e}")

    return downloaded


def convert_file_main(args):
    """单个文件转换"""
    if args.file:
        file_paths = [args.file]
    elif args.files:
        file_paths = args.files
    else:
        print("❌ 请指定 --file 或 --files")
        sys.exit(1)

    output_dir = args.output or os.path.dirname(file_paths[0]) or os.getcwd()
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔄 转换类型: {args.type}")
    print(f"📁 输入文件: {file_paths}")
    print(f"📂 输出目录: {output_dir}")

    try:
        downloaded = upload_and_convert(file_paths, args.type, output_dir)
        if downloaded:
            print(f"\n✅ 转换完成! 生成了 {len(downloaded)} 个文件:")
            for f in downloaded:
                # 尝试读取并预览 markdown 内容
                if f.endswith(".md"):
                    try:
                        with open(f, "r", encoding="utf-8") as fh:
                            content = fh.read()
                        preview = content[:500]
                        print(f"   📄 {f} ({len(content)} 字符)")
                        print(f"      预览: {preview[:120]}...")
                    except:
                        print(f"   📄 {f}")
                else:
                    size = os.path.getsize(f)
                    print(f"   📄 {f} ({size} 字节)")
            return downloaded
        else:
            print("⚠️  没有生成任何文件")
            return []
    except RuntimeError as e:
        print(str(e))
        sys.exit(1)


def health_check(args):
    """检查 APP 是否运行"""
    import urllib.request
    try:
        resp = urllib.request.urlopen(f"{API_BASE}/", timeout=5)
        print(f"✅ knowledge-base-converter 运行中 (HTTP {resp.getcode()})")
        print(f"   API 地址: {API_BASE}")
        return True
    except Exception as e:
        print(f"❌ knowledge-base-converter 未运行: {e}")
        print(f"   请启动: conda activate StableDiffusion && cd D:\\Data-Lab\\knowledge-base-converter && python server.py")
        return False


def list_types(args):
    """列出所有支持的转换类型"""
    types = {
        "pdf": "PDF → markdown + csv (OCR识别、分栏、表格提取)",
        "pdf2docx": "PDF → Word (docx，保留格式)",
        "excel": "Excel → csv",
        "word": "Word (docx) → 提取文本",
        "word-to-md": "Word (docx) → markdown + csv表格",
        "doc2docx": "旧版 .doc → .docx",
        "merge-docx": "合并多个 docx 文件",
    }
    print("📋 支持的转换类型:\n")
    for key, desc in types.items():
        print(f"   {key:15s} {desc}")
    return list(types.keys())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hermes ↔ knowledge-base-converter 对接客户端",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 检查服务状态
  python hermes_api_client.py status

  # PDF → Markdown
  python hermes_api_client.py convert --file document.pdf --type pdf

  # PDF → Markdown，指定输出目录
  python hermes_api_client.py convert --file document.pdf --type pdf --output ./output

  # PDF → DOCX
  python hermes_api_client.py convert --file document.pdf --type pdf2docx

  # Excel → CSV
  python hermes_api_client.py convert --file data.xlsx --type excel

  # Word → Markdown
  python hermes_api_client.py convert --file report.docx --type word-to-md

  # 合并多个 docx
  python hermes_api_client.py convert --files file1.docx file2.docx --type merge-docx
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # convert 子命令
    p_conv = subparsers.add_parser("convert", help="上传文件并转换")
    p_conv.add_argument("--file", "-f", help="输入文件路径")
    p_conv.add_argument("--files", "-F", nargs="+", help="多个输入文件（用于合并）")
    p_conv.add_argument("--type", "-t", required=True,
                        choices=["pdf", "excel", "word", "word-to-md", "pdf2docx", "doc2docx", "merge-docx"],
                        help="转换类型")
    p_conv.add_argument("--output", "-o", default=".", help="输出目录（默认: 当前目录）")

    # status 子命令
    subparsers.add_parser("status", help="检查 APP 运行状态")

    # list-types 子命令
    subparsers.add_parser("list-types", help="列出所有支持的转换类型")

    args = parser.parse_args()

    if args.command == "convert":
        convert_file_main(args)
    elif args.command == "status":
        health_check(args)
    elif args.command == "list-types":
        list_types(args)
    else:
        parser.print_help()
