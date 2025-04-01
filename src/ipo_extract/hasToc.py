import os
import fitz  # PyMuPDF
from openpyxl import Workbook


def check_pdf_bookmarks(pdf_path):
    """
    使用PyMuPDF检查PDF文件是否有书签
    :param pdf_path: PDF文件路径
    :return: True(有书签)或False(无书签)
    """
    try:
        doc = fitz.open(pdf_path)
        if doc.get_toc():  # 获取目录(书签)
            return True
        return False
    except Exception as e:
        print(f"处理文件 {pdf_path} 时出错: {e}")
        return False
    finally:
        if 'doc' in locals():
            doc.close()


def process_pdf_folder(folder_path, output_excel):
    """
    处理文件夹中的PDF文件并将结果写入Excel
    :param folder_path: 包含PDF文件的文件夹路径
    :param output_excel: 输出的Excel文件名
    """
    # 创建Excel工作簿
    wb = Workbook()
    ws = wb.active
    ws.title = "PDF书签检查结果"

    # 写入表头
    ws.append(["文件名", "是否有书签", "书签数量"])

    # 遍历文件夹中的PDF文件
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.pdf'):
            filepath = os.path.join(folder_path, filename)
            try:
                doc = fitz.open(filepath)
                toc = doc.get_toc()  # 获取书签
                has_bookmarks = bool(toc)
                bookmark_count = len(toc) if has_bookmarks else 0

                # 将结果写入Excel
                ws.append([filename, "是" if has_bookmarks else "否", bookmark_count])
                print(f"处理文件: {filename} - 书签: {'有' if has_bookmarks else '无'} ({bookmark_count}个)")
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")
                ws.append([filename, "错误", "N/A"])
            finally:
                if 'doc' in locals():
                    doc.close()

    # 保存Excel文件
    wb.save(output_excel)
    print(f"结果已保存到 {output_excel}")


if __name__ == "__main__":
    # 设置文件夹路径和输出Excel文件名
    pdf_folder = '../../result/annual_report'
    excel_output = "../../result/has_toc_list.xlsx"

    # 检查文件夹是否存在
    if not os.path.isdir(pdf_folder):
        print(f"错误: 文件夹 {pdf_folder} 不存在!")
    else:
        process_pdf_folder(pdf_folder, excel_output)