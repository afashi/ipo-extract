import concurrent
import logging
import os
import re
import llmChat
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import Value, Lock

import pandas as pd
import pdfplumber

# 中文数字映射字典
chinese_num_map = {
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7,
    '八': 8, '九': 9, '十': 10, '十一': 11, '十二': 12, '十三': 13,
    '十四': 14, '十五': 15, '十六': 16
}

# 正则表达式模式
main_pattern = re.compile(
    r'^\(?(一|二|三|四|五|六|七|八|九|十|十一|十二|十三|十四|十五|十六)、?\)?\s*(重要会计政策及会计估计|税项|会计政策和会计估计变更以及前期差错更正的说明|(合并)?财务报表(主要)?项目(注释|附注)|研发支出|合并范围的(变更|变动)|在其他主体中的权益)$')
target_pattern = re.compile(r'^(合并)?财务报表(主要)?项目(注释|附注)$')
table1_pattern_start = re.compile(r'(重要)?在建工程(项目)?(本期|本年)?变动情况')
table1_pattern2_start = re.compile(r'\d{1,2}、?\s*在建工程')
table1_pattern_end = re.compile(
    r'在建工程减值准备情况|在建工程的减值测试情况|工程物资|生产性生物资产|无形资产|递延所得税资产|使用权资产|长期待摊费用')


def process_pdf(pdf_path):
    """处理单个PDF文件（含异常处理）"""
    try:
        filename = os.path.basename(pdf_path)
        all_titles = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                current_page = page_num + 1
                words = page.extract_words(keep_blank_chars=True, x_tolerance=40)
                for word in words:
                    # 提取文案
                    word_text = word.get('text').replace(" ", "")
                    text_clean = re.sub(r'\s+', ' ', word_text).strip()
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
            is_continuous = False
        else:
            for i in range(1, len(nums)):
                if nums[i] != nums[i - 1] + 1:
                    is_continuous = False
                    break

        # 获取目标页码
        target_page = None
        next_page = None
        target_indices = [i for i, t in enumerate(all_titles) if t['is_target']]
        if target_indices:
            first_target_idx = target_indices[0]
            target_page = all_titles[first_target_idx]['page']
            if first_target_idx + 1 < len(all_titles):
                next_page = all_titles[first_target_idx + 1]['page']

        table1_end_page, table1_start2_pages, table1_start_pages = getTable1(pdf, target_page, next_page)

        full_text = ""
        if len(table1_start_pages) < 1:
            table1_start_pages = table1_start2_pages

        print(f"{table1_start_pages}:{table1_end_page}")

        if table1_end_page is not None and len(table1_start_pages) > 0:
            for page in pdf.pages[table1_start_pages[0] - 1:table1_end_page]:
                text = page.extract_text(keep_blank_chars=True, x_tolerance=40)
                full_text += text
        print(f"full_text:{full_text}")
        reasoning_content, answer_content, completion_usage = llmChat.chat_completion(full_text)
        with lock:
            counter.value += 1
            print(f"{counter.value}.{filename}")
        return {
            '文件名': filename,
            '所有标题': '，'.join([t['title'] for t in all_titles]),
            '是否连续': '是' if is_continuous else '否',
            '财务报表项目注释页码': target_page,
            '下一个标题的页码': next_page,
            '重要在建工程变动情况的开始页码': table1_start_pages,
            '在建工程开始页码': table1_start2_pages,
            '重要在建工程变动情况的结束页码': table1_end_page,
            '引用全文': full_text,
            '思考过程': reasoning_content,
            '大模型回答': answer_content,
            '大模型输入tokens': completion_usage.completion_tokens,
            '大模型输出tokens': completion_usage.prompt_tokens
        }

    except Exception as e:
        return {
            '文件名': os.path.basename(pdf_path),
            '所有标题': f'处理出错：{str(e)}',
            '是否连续': '否',
            '财务报表项目注释页码': None,
            '下一个标题的页码': None,
            '重要在建工程变动情况的页码': None,
            '在建工程开始页码': None,
            '重要在建工程变动情况的结束页码': None
        }


def getTable1(pdf, start_page, end_page):
    table1_start_pages = []
    table1_start2_pages = []
    table1_end_page = None
    if end_page:
        for page_num, page in enumerate(pdf.pages[start_page - 1:end_page - 1]):
            words = page.extract_words(keep_blank_chars=True, x_tolerance=40)
            for word in words:
                # 提取文案
                word_text = word.get('text').replace(" ", "")
                text_clean = re.sub(r'\s+', ' ', word_text).strip()
                matches = table1_pattern_start.findall(text_clean)
                for match in matches:
                    table1_start_pages.append(start_page + page_num)
                if (len(table1_start_pages) > 0
                        and table1_end_page is None
                        and table1_pattern_end.search(text_clean) is not None):
                    table1_end_page = start_page + page_num
    if len(table1_start_pages) < 1 and len(table1_start2_pages) < 1:
        for page_num, page in enumerate(pdf.pages[start_page - 1:end_page - 1]):
            words = page.extract_words(keep_blank_chars=True, x_tolerance=40)
            for word in words:
                # 提取文案
                word_text = word.get('text').replace(" ", "")
                text_clean = re.sub(r'\s+', ' ', word_text).strip()
                matches = table1_pattern2_start.findall(text_clean)
                for match in matches:
                    table1_start2_pages.append(start_page + page_num)
                if (len(table1_start2_pages) > 0
                        and table1_end_page is None
                        and table1_pattern_end.search(text_clean) is not None):
                    table1_end_page = start_page + page_num
    return table1_end_page, table1_start2_pages, table1_start_pages


# 全局变量（子进程中共享）
counter = None
lock = None


def init_worker(c, l):
    global counter, lock
    counter = c  # 继承共享变量
    lock = l  # 继承锁


def main(folder_path, output_file):
    """主处理函数（多线程版）"""
    # 获取所有PDF文件路径
    pdf_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith('.pdf')
    ]
    # pdf_files = list(
    #     filter(lambda s:
    #            "安徽安凯汽车股份有限公司.pdf" in s or
    #            "111.pdf" in s, pdf_files))

    counter = Value("i", 0)  # 主进程创建共享变量
    lock = Lock()  # 主进程创建锁
    # 多线程处理
    results = []

    with ProcessPoolExecutor(max_workers=8, initializer=init_worker, initargs=(counter, lock)) as executor:
        futures = [executor.submit(process_pdf, path) for path in pdf_files]
    for future in concurrent.futures.as_completed(futures):
        results.append(future.result())

    # 创建DataFrame并保存
    df = pd.DataFrame(results)
    df.to_excel(output_file, index=False)


logging.disable(level=logging.WARN)
if __name__ == '__main__':
    folder_path = '../../result/annual_report_test'
    output_file = '../../result/分析结果.xlsx'
    main(folder_path, output_file)
    print(f"处理完成，结果已保存至：{output_file}")
