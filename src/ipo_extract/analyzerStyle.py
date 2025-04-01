import pdfplumber
import re
from collections import defaultdict


class PDFTitleExtractor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.size_distribution = defaultdict(int)
        self.page_layouts = []

    def _collect_font_metrics(self):
        """收集全文字号统计和页面布局特征"""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                page_data = {
                    "width": page.width,
                    "height": page.height,
                    "text_blocks": []
                }

                # 提取字符级信息
                chars = page.chars
                current_line = []
                prev_y = None

                for char in sorted(chars, key=lambda c: (c["y0"], c["x0"])):
                    # 统计字号分布
                    self.size_distribution[round(char["size"], 1)] += 1

                    # 按行聚合文本
                    if prev_y is None or abs(char["y0"] - prev_y) < 2:
                        current_line.append(char)
                    else:
                        self._analyze_line(current_line, page_data)
                        current_line = [char]
                    prev_y = char["y0"]

                if current_line:
                    self._analyze_line(current_line, page_data)

                self.page_layouts.append(page_data)

    def _analyze_line(self, chars, page_data):
        """分析单行文本特征"""
        line_size = max(c["size"] for c in chars)
        line_text = "".join(c["text"] for c in chars)
        x0 = min(c["x0"] for c in chars)
        y0 = min(c["y0"] for c in chars)

        block = {
            "text": line_text.strip(),
            "size": line_size,
            "x": x0,
            "y": y0,
            "length": len(line_text),
            "center_aligned": self._check_alignment(chars, page_data["width"])
        }
        page_data["text_blocks"].append(block)

    def _check_alignment(self, chars, page_width):
        """检测文本是否居中"""
        first_char = chars[0]
        last_char = chars[-1]
        left_margin = first_char["x0"]
        right_margin = page_width - last_char["x1"]
        return abs(left_margin - right_margin) < 10

    def _determine_title_size(self):
        """自动识别标题字号特征"""
        sizes = sorted(self.size_distribution.keys(), reverse=True)
        body_size = max(
            [s for s in sizes if 8 < s < 14],
            key=lambda x: self.size_distribution[x]
        )
        return [s for s in sizes if s > body_size + 1]

    def _is_title_candidate(self, block):
        """标题候选条件"""
        return (
                block["length"] < 50 and  # 排除长段落
                not re.search(r"[.,;!?]$", block["text"]) and  # 排除段落结尾
                block["center_aligned"] or block["x"] < 50  # 居中或左侧对齐
        )

    def extract_structure(self):
        """执行结构提取"""
        self._collect_font_metrics()
        title_sizes = self._determine_title_size()
        hierarchy = {s: f"标题{idx + 1}级" for idx, s in enumerate(title_sizes)}

        results = []
        for page in self.page_layouts:
            page_titles = []
            for block in sorted(page["text_blocks"], key=lambda b: -b["y"]):
                if block["size"] in hierarchy and self._is_title_candidate(block):
                    level = hierarchy[block["size"]]
                    page_titles.append((level, block["text"]))
                else:
                    results.append({
                        "type": "body",
                        "content": block["text"],
                        "page_layout": (block["x"], block["y"])
                    })
            # 按视觉顺序保留标题
            results.extend(reversed([
                {"type": "title", "level": level, "content": text}
                for level, text in page_titles
            ]))

        return results



if __name__ == "__main__":
    # 使用示例
    extractor = PDFTitleExtractor("../../result/annual_report/TCL科技集团股份有限公司.pdf")
    structure = extractor.extract_structure()

    # 输出结果
    current_section = []
    for item in structure:
        if item["type"] == "title":
            print(f"\n【{item['level']}】{item['content']}")
            current_section = []
        else:
            current_section.append(item["content"])

    print("\n正文内容：")
    print("\n".join(current_section))