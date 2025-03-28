import os
import re
import fitz  # PyMuPDF
from openpyxl import Workbook
from openpyxl.styles import Font


def find_section_pages(doc):
    """
    查找包含"释义"或"释 义"的页面和下一个章节的页面
    :param doc: PDF文档对象
    :return: (释义页码, 下一章节页码)
    """
    definition_page = None
    next_section_page = None

    # 首先尝试通过书签查找
    toc = doc.get_toc()
    for i, item in enumerate(toc):
        # 使用正则表达式匹配"释义"或"释 义"
        if re.search(r'释\s*义', item[1]):
            definition_page = item[2] - 1  # 转为0-based
            # 查找下一个章节
            for next_item in toc[i + 1:]:
                if next_item[0] <= item[0]:  # 同级或更高级别的标题
                    next_section_page = next_item[2] - 1
                    return definition_page, next_section_page
            break

    # 如果没有找到匹配的书签，则逐页搜索文本
    if definition_page is None:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if re.search(r'释\s*义', text):
                definition_page = page_num
                break

    # 如果找到释义页面但没找到下一章节，则设置到文档末尾
    if definition_page is not None and next_section_page is None:
        next_section_page = len(doc) - 1

    return definition_page, next_section_page


def extract_report_period_lines(doc, start_page, end_page):
    """
    提取指定页面范围内包含"报告期"的行内容
    :param doc: PDF文档对象
    :param start_page: 起始页码(0-based)
    :param end_page: 结束页码(0-based)
    :return: 包含"报告期"的行列表
    """
    report_lines = []
    for page_num in range(start_page, end_page + 1):
        page = doc.load_page(page_num)
        text = page.get_text("text")

        pattern = r'报告期(?:、\s*最近[一二两三]年)?\s*指\s*(?:\d{4}\s*年度)(?:\s*[、,]\s*\d{4}\s*年度)*(?:\s*(?:和|及)\s*\d{4}\s*年\s*\d{1,2}\s*[-~至]\s*\d{1,2}\s*月)?'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            report_lines.append(match.group(0))

    return report_lines


def process_pdf_file(filepath):
    """
    处理单个PDF文件
    :param filepath: PDF文件路径
    :return: (文件名, 释义页码, 下一章节页码, 报告期行内容)
    """
    try:
        doc = fitz.open(filepath)
        definition_page, next_section_page = find_section_pages(doc)

        if definition_page is None:
            return (os.path.basename(filepath), "未找到", "N/A", [])

        report_lines = extract_report_period_lines(doc, definition_page, next_section_page)

        # 页码转为1-based显示
        return (os.path.basename(filepath),
                definition_page + 1,
                next_section_page + 1 if next_section_page is not None else "文档末尾",
                report_lines)
    except Exception as e:
        print(f"处理文件 {filepath} 时出错: {e}")
        return (os.path.basename(filepath), "错误", "N/A", [str(e)])
    finally:
        if 'docs' in locals():
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
    ws.title = "PDF内容提取结果"

    # 写入表头并设置样式
    headers = ["文件名", "释义页码", "下一章节页码", "包含'报告期'的行内容"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # 遍历文件夹中的PDF文件
    for filename in sorted(os.listdir(folder_path)):
        if filename.lower().endswith('.pdf'):
            filepath = os.path.join(folder_path, filename)
            print(f"正在处理文件: {filename}...")

            # 处理PDF文件
            result = process_pdf_file(filepath)

            # 将结果写入Excel
            ws.append([
                result[0],  # 文件名
                result[1],  # 释义页码
                result[2],  # 下一章节页码
                "\n".join(result[3]) if result[3] else "未找到"  # 报告期行内容
            ])

    # 调整列宽
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2) * 1.2
        ws.column_dimensions[column].width = adjusted_width

    # 冻结首行
    ws.freeze_panes = "A2"

    # 保存Excel文件
    wb.save(output_excel)
    print(f"结果已保存到 {output_excel}")


if __name__ == "__main__":
    # 设置文件夹路径和输出Excel文件名
    pdf_folder = '../../result/report'
    excel_output = "../../result/getReportDate.xlsx"

    # 检查文件夹是否存在
    if not os.path.isdir(pdf_folder):
        print(f"错误: 文件夹 {pdf_folder} 不存在!")
    else:
        process_pdf_folder(pdf_folder, excel_output)