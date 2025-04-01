import os
import re
import pdfplumber
import pandas as pd

# 中文数字映射字典
chinese_num_map = {
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7,
    '八': 8, '九': 9, '十': 10, '十一': 11, '十二': 12, '十三': 13,
    '十四': 14, '十五': 15, '十六': 16
}

# 正则表达式模式
main_pattern = re.compile(
    r'^([一二三四五六七八九十十一十二十三十四十五十六])、\s*'
    r'(重要会计政策及会计估计|税项|会计政策和会计估计变更以及前期差错更正的说明|'
    r'(合并)?财务报表(主要)?项目(注释|附注)|研发支出|合并范围的(变更|变动)|'
    r'在其他主体中的权益)$'
)
target_pattern = re.compile(r'^(合并)?财务报表(主要)?项目(注释|附注)$')


def process_pdf(pdf_path):
    """处理单个PDF文件"""
    filename = os.path.basename(pdf_path)
    all_titles = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            current_page = page_num + 1  # 转换为1-based页码
            text = page.extract_text()
            if text:
                # 清理文本并匹配标题
                text_clean = re.sub(r'\s+', ' ', text).strip()
                matches = main_pattern.finditer(text_clean)
                for match in matches:
                    num_str = match.group(1)
                    title = match.group(2).strip()
                    is_target = bool(target_pattern.match(title))
                    all_titles.append({
                        'num_str': num_str,
                        'title': title,
                        'page': current_page,
                        'is_target': is_target
                    })

    # 处理序号连续性
    nums = []
    for title in all_titles:
        num = chinese_num_map.get(title['num_str'], None)
        if num is not None:
            nums.append(num)

    is_continuous = True
    if len(nums) < 1:
        is_continuous = False  # 无标题视为不连续
    else:
        for i in range(1, len(nums)):
            if nums[i] != nums[i - 1] + 1:
                is_continuous = False
                break

    # 获取目标标题页码
    target_page = None
    next_page = None
    target_indices = [i for i, t in enumerate(all_titles) if t['is_target']]
    if target_indices:
        first_target_idx = target_indices[0]
        target_page = all_titles[first_target_idx]['page']
        if first_target_idx + 1 < len(all_titles):
            next_page = all_titles[first_target_idx + 1]['page']

    return {
        '文件名': filename,
        '所有标题': '，'.join([t['title'] for t in all_titles]),
        '是否连续': '是' if is_continuous else '否',
        '财务报表项目注释页码': target_page,
        '下一个标题的页码': next_page
    }


def main(folder_path, output_file):
    """主处理函数"""
    results = []

    for file_name in os.listdir(folder_path):
        if file_name.lower().endswith('.pdf'):
            pdf_path = os.path.join(folder_path, file_name)
            results.append(process_pdf(pdf_path))

    # 创建DataFrame并保存Excel
    df = pd.DataFrame(results)
    df.to_excel(output_file, index=False)


if __name__ == '__main__':
    folder_path = input("请输入PDF文件夹路径：").strip()
    output_file = '分析结果.xlsx'
    main(folder_path, output_file)
    print(f"处理完成，结果已保存至：{output_file}")