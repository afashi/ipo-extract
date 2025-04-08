import concurrent
import logging
import os
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from datetime import datetime
from multiprocessing import Value, Lock

import pandas as pd
import pdfplumber

import common_constants, llm_chat
import table_config


class TableResult:
    full_text = ""
    reasoning_content = ""
    answer_content = ""
    completion_usage = ""
    completion_tokens = 0
    prompt_tokens = 0

    def __init__(self, table_name, table_start_pages, table_start2_pages, table_end_page):
        self.table_name = table_name
        self.table_start_pages = table_start_pages
        self.table_start2_pages = table_start2_pages
        self.table_end_page = table_end_page


def process_pdf(pdf_path, enable_llm):
    """处理单个PDF文件（含异常处理）"""
    start_time1 = time.time()  # 记录开始时间
    filename = os.path.basename(pdf_path)
    second_all_title = {}
    try:
        # 1、遍历表格配置
        # 2、获取所有二级标题，如果没有就添加，页码和目标的标题
        # 3、判断二级标题是否连续
        # 4、如果连续获取表格所在的二级标题页码和二级标题下一级的页码
        with pdfplumber.open(pdf_path) as pdf:
            for key, value in table_config.second_title_all_map.items():
                if second_all_title.get(key) is None:
                    all_titles = get_all_titles(pdf, value)
                # 处理序号连续性
                is_continuous = is_num_continuous(all_titles)
                second_all_title[key] = {"is_continuous": is_continuous, "all_titles": all_titles}
            table_result = {}
            for config in table_config.TableConfigEnum:
                if second_all_title[config.second_title_all]["is_continuous"]:
                    target_page, next_page = get_target_page(second_all_title[config.second_title_all]["all_titles"],
                                                             config.second_title)
                    if config.strategy == "1":
                        table_start_pages, table_parent_start_pages, table_end_page = get_table(pdf, target_page,
                                                                                                next_page,
                                                                                                config.start_pattern,
                                                                                                config.parent_start_pattern,
                                                                                                config.end_pattern)
                    if config.strategy == "2":
                        table_start_pages, table_parent_start_pages, table_end_page = get_table1(pdf, target_page,
                                                                                                 next_page,
                                                                                                 config.start_pattern,
                                                                                                 config.parent_start_pattern,
                                                                                                 config.end_pattern)
                    full_text = get_full_text(pdf, table_start_pages, table_parent_start_pages, table_end_page)
                    if enable_llm and len(full_text) > 0:
                        reasoning_content, answer_content, completion_tokens, prompt_tokens = llm_chat.chat_completion(
                            full_text,
                            config.prompt)
                    else:
                        reasoning_content, answer_content, completion_tokens, prompt_tokens = "", "", 0, 0
                    result = {
                        '文件名': filename,
                        '路径': os.path.abspath(pdf_path),
                        '所有标题': '，'.join([t['title'] for t in all_titles]),
                        '是否连续': '是' if is_continuous else '否',
                        '财务报表项目注释页码': target_page,
                        '下一个标题的页码': next_page,
                        '开始页码': table_start_pages,
                        '父标题开始页码': table_parent_start_pages,
                        '结束页码': table_end_page,
                        '引用全文': full_text,
                        '思考过程': reasoning_content,
                        '大模型回答': answer_content,
                        '大模型输入tokens': completion_tokens,
                        '大模型输出tokens': prompt_tokens
                    }
                else:
                    result = {
                        '文件名': filename,
                        '全部二级标题': second_all_title[config.second_title_all]["all_titles"],
                        '是否连续': '否'
                    }
                table_result[config.cn_name] = result
            end_time1 = time.time()  # 记录结束时间
            with lock:
                counter.value += 1
                print(f"{counter.value}.{filename}，耗时: {end_time1 - start_time1:.6f}秒")
            return table_result
    except Exception as e:
        error_msg = traceback.format_exc()
        print(f'{os.path.basename(pdf_path)}出错了:{e},{error_msg}')
        table_result[config.cn_name] = {
            '文件名': filename,
            '全部二级标题': second_all_title[config.second_title_all]["all_titles"],
            '出错': error_msg
        }
        return table_result


def is_num_continuous(all_titles):
    nums = []
    for title in all_titles:
        num = common_constants.CHINESE_NUM_MAP.get(title['num_str'], None)
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
    return is_continuous


def get_all_titles(pdf, all_title_pattern):
    all_titles = []
    for page_num, page in enumerate(pdf.pages):
        current_page = page_num + 1
        words = page.extract_words(keep_blank_chars=True, x_tolerance=40)
        for word in words:
            # 提取文案
            word_text = word.get('text').replace(" ", "")
            text_clean = re.sub(r'\s+', ' ', word_text).strip()
            matches = all_title_pattern.finditer(text_clean)
            for match in matches:
                num_str = match.group(1)
                title = match.group(2).strip()
                target_title = None
                for title_key, title_pattern in table_config.second_title_map.items():
                    if bool(title_pattern.match(title)):
                        target_title = title_key
                # 标题编号去重
                if not any(item['num_str'] == num_str for item in all_titles):
                    all_titles.append({
                        'num_str': num_str,
                        'title': title,
                        'page': current_page,
                        'target_title': target_title
                    })
    return all_titles


# 过滤到2级标题
def get_target_page(all_titles, target_name):
    target_page = None
    next_page = None
    target_indices = [i for i, t in enumerate(all_titles) if t["target_title"] == target_name]
    if target_indices:
        first_target_idx = target_indices[0]
        target_page = all_titles[first_target_idx]['page']
        if first_target_idx + 1 < len(all_titles):
            next_page = all_titles[first_target_idx + 1]['page']
    return target_page, next_page


# 获取表格
def get_table(pdf, start_page, end_page, table_pattern_start, table_parent_pattern_start, table_pattern_end):
    table_start_pages = []
    table_start2_pages = []
    table_end_page = None
    if end_page:
        for page_num, page in enumerate(pdf.pages[start_page - 1:end_page - 1]):
            words = page.extract_words(keep_blank_chars=True, x_tolerance=40)
            for word in words:
                # 提取文案
                word_text = word.get('text').replace(" ", "")
                if word_text:
                    text_clean = re.sub(r'\s+', ' ', word_text).strip()
                    matches = table_pattern_start.findall(text_clean)
                    for match in matches:
                        table_start_pages.append(start_page + page_num)
                    if (len(table_start_pages) > 0
                            and table_end_page is None
                            and table_pattern_end.search(text_clean) is not None):
                        table_end_page = start_page + page_num
        if len(table_start_pages) < 1 and len(table_start2_pages) < 1:
            for page_num, page in enumerate(pdf.pages[start_page - 1:end_page - 1]):
                words = page.extract_words(keep_blank_chars=True, x_tolerance=40)
                for word in words:
                    # 提取文案
                    word_text = word.get('text').replace(" ", "")
                    if word_text:
                        text_clean = re.sub(r'\s+', ' ', word_text).strip()
                        matches = table_parent_pattern_start.findall(text_clean)
                        for match in matches:
                            table_start2_pages.append(start_page + page_num)
                        if (len(table_start2_pages) > 0
                                and table_end_page is None
                                and table_pattern_end.search(text_clean) is not None):
                            table_end_page = start_page + page_num
    return table_start_pages, table_start2_pages, table_end_page


def get_table1(pdf, start_page, end_page, table_pattern_start, table_parent_pattern_start, table_pattern_end):
    table_start_pages = []
    table_parent_start_pages = []
    table_end_page = None
    if end_page:
        for page_num, page in enumerate(pdf.pages[start_page - 1:end_page - 1]):
            words = page.extract_words(keep_blank_chars=True, x_tolerance=40)
            for word in words:
                # 提取文案
                word_text = word.get('text').replace(" ", "")
                if word_text:
                    text_clean = re.sub(r'\s+', ' ', word_text).strip()
                    matches = table_parent_pattern_start.findall(text_clean)
                    for match in matches:
                        table_parent_start_pages.append(start_page + page_num)
                    if (len(table_parent_start_pages) > 0
                            and table_end_page is None
                            and table_pattern_end.search(text_clean) is not None):
                        table_end_page = start_page + page_num
        if len(table_parent_start_pages) > 1:
            for page_num, page in enumerate(pdf.pages[table_parent_start_pages[0] - 1:table_end_page - 1]):
                words = page.extract_words(keep_blank_chars=True, x_tolerance=40)
                for word in words:
                    # 提取文案
                    word_text = word.get('text').replace(" ", "")
                    if word_text:
                        text_clean = re.sub(r'\s+', ' ', word_text).strip()
                        matches = table_pattern_start.findall(text_clean)
                        for match in matches:
                            table_start_pages.append(start_page + page_num)
                        if (len(table_start_pages) > 0
                                and table_pattern_end.search(text_clean) is not None):
                            table_end_page = start_page + page_num
    return table_start_pages, table_parent_start_pages, table_end_page


def get_full_text(pdf, table_start_pages, table_start2_pages, table_end_page):
    full_text = ""
    if len(table_start_pages) < 1:
        table_start_pages = table_start2_pages
    if table_end_page is not None and len(table_start_pages) > 0 and table_start_pages[0] - table_end_page < 20:
        for page in pdf.pages[table_start_pages[0] - 1:table_end_page]:
            text = page.extract_text(keep_blank_chars=True, x_tolerance=40)
            full_text += text
    return full_text


# 全局变量（子进程中共享）
counter = None
lock = None


def init_worker(c, l):
    global counter, lock
    counter = c  # 继承共享变量
    lock = l  # 继承锁


def main(folder_path, output_file, enable_llm=True):
    """主处理函数（多线程版）"""
    # 获取所有PDF文件路径
    pdf_files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith('.pdf')
    ]
    # pdf_files = list(
    #     filter(lambda s:
    #            "深圳市智莱科技股份有限公司_2024-12-31_年度报告_2025-04-01.pdf" in s or
    #            "株洲中车时代电气股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
    #            "爱玛科技集团股份有限公司.pdf" in s or
    #            "111.pdf" in s, pdf_files))

    counter = Value("i", 0)  # 主进程创建共享变量
    lock = Lock()  # 主进程创建锁
    # 多线程处理
    results = []

    with ProcessPoolExecutor(max_workers=8, initializer=init_worker, initargs=(counter, lock)) as executor:
        futures = [executor.submit(process_pdf, path, enable_llm) for path in pdf_files]
    for future in concurrent.futures.as_completed(futures):
        results.append(future.result())
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        for config in table_config.TableConfigEnum:
            table_result = []
            for result in results:
                table_result.append(result.get(config.cn_name))
            df = pd.DataFrame(table_result)
            df.to_excel(writer, sheet_name=config.cn_name, index=False)

logging.disable(level=logging.WARN)
if __name__ == '__main__':
    current_time = datetime.now()
    start_time = time.time()  # 记录开始时间
    folder_path = '../../result/annual_report_test'
    output_file = '../../result/分析结果_' + current_time.strftime("%Y%m%d%H%M%S") + '.xlsx'
    main(folder_path, output_file, True)
    end_time = time.time()  # 记录结束时间
    print(f"全部文件处理完成，结果已保存至：{output_file}，耗时: {end_time - start_time:.6f}秒")
