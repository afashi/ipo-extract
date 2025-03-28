import os
import requests
import openpyxl
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# 全局配置
MAX_RETRIES = 1  # 最大重试次数
TIMEOUT = 30  # 单次请求超时时间（秒）
THREADS = 5  # 线程数


def sanitize_filename(filename):
    """清理文件名中的非法字符"""
    keep_chars = (' ', '.', '_', '-')
    return "".join(c for c in str(filename)
                   if c.isalnum() or c in keep_chars).strip()


def download_file(url, filename, folder):
    """带重试逻辑的文件下载函数"""
    if not url.lower().startswith(('http://', 'https://')):
        print(f"无效URL: {url}")
        return False

    filename = sanitize_filename(filename)
    if not filename:
        print(f"无效文件名，URL: {url}")
        return False

    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'

    filepath = os.path.join(folder, filename)

    # 如果文件已存在，跳过下载
    if os.path.exists(filepath):
        print(f"文件已存在，跳过: {filename}")
        return True

    for attempt in range(MAX_RETRIES):
        try:
            print(f"尝试 {attempt + 1}/{MAX_RETRIES}: 下载 {filename}")
            response = requests.get(
                url,
                stream=True,
                timeout=TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Referer": "http://www.sse.com.cn/",
                    "cookie": "acw_tc=751b942017431517124033439e92e3c0161f948fe3843f874a4aa84259; cdn_sec_tc=751b942017431517124033439e92e3c0161f948fe3843f874a4aa84259; ssxmod_itna=eqAxRi0=0Qi=DQeGHKGdXLCmYLruwAExYvxEExD//mDnqD=GFDK40ooO4DCzAzil0w3YdnD4G=fYhlxdzMWcuoa3bDCPGnDB94qW/4YYkDt4DTD34DYDixibkxi5GRD0KDFWqvz19Dm4GWWdQDmqG27qDfDAoxowiD4qDBGodqx7U9zDDlz0u5bDD+Kr0iu+0gQQUP41GxWqDMUeGX8795WTb86Zhl4paHxWPRDB=+xBjSITX6Qj+99utDEGDaii4sKDo3W2dmYGDiohmolAeb80DqlDPix8hz4HqjvVxDGRAjcAoo3KOpOIum0tBKaWrabDb92StDxi+DD=; ssxmod_itna2=eqAxRi0=0Qi=DQeGHKGdXLCmYLruwAExYvxo4G9bTbDBk0De7pvgFypOwg7DCR=qidlQQGW3DwZ0PGcDY9qxD===; acw_sc__v2=67e66d1a085d1ad21012f21e6ee1f6de57239f23"
                }
            )
            response.raise_for_status()

            # 检查内容类型是否为PDF
            content_type = response.headers.get('Content-Type', '').lower()
            if 'pdf' not in content_type:
                print(f"警告: {url} 可能不是PDF文件 (Content-Type: {content_type})")
                return False
            else:
                # 保存文件
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return True

        except requests.exceptions.RequestException as e:
            print(f"下载失败 (尝试 {attempt + 1}): {filename} - 错误: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)  # 重试前等待
        except Exception as e:
            print(f"未知错误: {filename} - {str(e)}")
            break

    # 所有重试都失败
    print(f"全部 {MAX_RETRIES} 次尝试失败: {filename}")
    return False


def process_excel(excel_path):
    """处理Excel文件并返回下载任务列表"""
    try:
        workbook = openpyxl.load_workbook(excel_path, data_only=True)
        sheet = workbook.worksheets[0]

        downloads = []
        for row in sheet.iter_rows(min_row=2):  # 从第二行开始
            if len(row) >= 21:  # 确保有U列
                name = row[2].value  # C列
                announce_date = row[3].value  # D列
                url = row[20].value  # U列

                if url and name:
                    downloads.append((url.strip(), str(name + '_招股说明书' + '_' + announce_date).strip()))

        return downloads

    except Exception as e:
        print(f"Excel处理错误: {str(e)}")
        return []


def main():
    excel_path = "../../docs/IpoFileList.xlsx"
    save_folder = "../../result/report"

    if not os.path.exists(excel_path):
        print("错误: Excel文件不存在")
        return

    os.makedirs(save_folder, exist_ok=True)

    downloads = process_excel(excel_path)
    if not downloads:
        print("没有找到可下载的链接")
        return

    print(f"找到 {len(downloads)} 个下载任务，使用 {THREADS} 个线程...")

    success = 0
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(download_file, url, name, save_folder): (url, name)
                   for url, name in downloads}

        for future in as_completed(futures):
            url, name = futures[future]
            try:
                if future.result():
                    success += 1
            except Exception as e:
                print(f"任务异常: {name} - {str(e)}")

    print("\n下载完成:")
    print(f"成功: {success}/{len(downloads)}")
    print(f"失败: {len(downloads) - success}/{len(downloads)}")


if __name__ == "__main__":
    main()
