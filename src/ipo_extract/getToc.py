import os
import fitz  # PyMuPDF
from openpyxl import Workbook


def get_pdf_bookmarks(pdf_path):
    """
    使用 PyMuPDF 获取 PDF 书签
    返回格式: [(level, title, page), ...]
    """
    try:
        doc = fitz.open(pdf_path)
        toc = doc.get_toc()
        return toc if toc else [(1, "无书签", 0)]
    except Exception as e:
        return [(1, f"读取错误: {str(e)}", 0)]


def process_pdf_folder(folder_path, output_excel="../../result/toc_list.xlsx"):
    """
    处理文件夹中的所有 PDF 文件
    """
    # 创建 Excel 工作簿
    wb = Workbook()
    ws = wb.active
    ws.title = "PDF书签"

    # 写入表头
    ws.append(["文件名", "层级", "书签标题", "页码"])

    # 遍历文件夹中的 PDF 文件
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.pdf'):
            filepath = os.path.join(folder_path, filename)
            print(f"正在处理: {filename}")

            # 获取书签
            bookmarks = get_pdf_bookmarks(filepath)

            # 将书签信息写入 Excel
            for level, title, page in bookmarks:
                ws.append([filename, level, title, page])

    # 调整列宽
    ws.column_dimensions['A'].width = 30  # 文件名列
    ws.column_dimensions['C'].width = 50  # 书签标题列

    # 保存 Excel 文件
    wb.save(output_excel)
    print(f"处理完成，结果已保存到: {output_excel}")


if __name__ == "__main__":
    # 设置 PDF 文件夹路径
    pdf_folder = 'report'

    # 检查路径是否存在
    process_pdf_folder(pdf_folder)