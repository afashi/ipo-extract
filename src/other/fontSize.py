import pdfplumber
import fitz  # PyMuPDF


def extract_text_with_fontsize(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num <= 1 or page_num > 50:
                continue
            print(f"\n=== 第 {page_num + 1} 页 ===")

            # 提取文本及其属性
            chars = page.chars

            # 按字号分组文本
            fontsize_groups = {}
            for char in chars:
                size = round(char['size'], 1)  # 四舍五入到小数点后一位
                if size not in fontsize_groups:
                    fontsize_groups[size] = []
                fontsize_groups[size].append(char['text'])

            # 打印每个字号的文本
            for size, texts in sorted(fontsize_groups.items()):
                print(f"\n字号: {size}pt")
                print("内容:", "".join(texts))


def extract_text_with_font_properties(pdf_path):
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        print(f"\n=== 第 {page_num + 1} 页 ===")

        # 获取文本块
        blocks = page.get_text("dict")["blocks"]

        # 按字号分组文本
        fontsize_groups = {}
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        size = round(span['size'], 1)  # 四舍五入到小数点后一位
                        if size > 13:
                            if size not in fontsize_groups:
                                fontsize_groups[size] = []
                            fontsize_groups[size].append((span['font'], span['text']))
        # 打印每个字号的文本
        for size, texts in sorted(fontsize_groups.items()):
            print(f"\n字号: {size}pt")
            print("字体:", texts)


if __name__ == "__main__":
    # 使用示例
    # extract_text_with_fontsize("../../result/annual_report/TCL科技集团股份有限公司.pdf")
    extract_text_with_font_properties("../../result/annual_report/TCL科技集团股份有限公司.pdf")
