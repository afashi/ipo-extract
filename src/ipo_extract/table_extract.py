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
                # 处理序号连续性,只判断需要提取的标题的前后连续性
                is_continuous = check_continuity(all_titles)
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
                        '路径': os.path.abspath(pdf_path),
                        '所有标题': second_all_title[config.second_title_all]["all_titles"],
                        '是否连续': '否',
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
            '路径': os.path.abspath(pdf_path),
            '所有标题': second_all_title[config.second_title_all]["all_titles"],
            '出错': error_msg
        }
        return table_result


def check_continuity(all_titles):
    is_continuous = True
    if(len(all_titles) == 0):
        return False
    for i in range(len(all_titles)):
        current_obj = all_titles[i]
        if current_obj['target_title'] is not None:
            current_num = common_constants.CHINESE_NUM_MAP.get((all_titles[i]['num_str']), None)
            has_prev = i > 0
            has_next = i < len(all_titles) - 1

            # 如果没有相邻元素，判定为不连续
            if not has_prev and not has_next:
                return False

            # 检查前一个和后一个的连续性
            prev_ok = True
            next_ok = True

            if has_prev:
                prev_num = common_constants.CHINESE_NUM_MAP.get((all_titles[i - 1]['num_str']), None)
                prev_ok = (prev_num == current_num - 1)

            if has_next:
                next_num = common_constants.CHINESE_NUM_MAP.get((all_titles[i + 1]['num_str']), None)
                next_ok = (next_num == current_num + 1)

            # 综合判断存在的相邻元素是否连续
            result = True
            if has_prev:
                is_continuous = result and prev_ok
            if has_next:
                is_continuous = result and next_ok
            if not is_continuous:
                return False
        else:
            # 如果不需要检查，可以忽略或设为None
            return False
    return is_continuous


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
                if not any(item['num_str'] == num_str for item in all_titles) and not any(item['title'] == num_str for item in all_titles):
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
        if len(table_start_pages) < 1 and len(table_start2_pages) < 1 and table_parent_pattern_start is not None:
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
        if len(table_parent_start_pages) > 0 and table_end_page:
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
    pdf_files = list(
        filter(lambda s:
               "珠海华发实业股份有限公司_2024-12-31_年度报告_2025-03-18.pdf" in s or
               "中国南方航空股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "中国冶金科工股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中国农业银行股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中国光大银行股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中国人民保险集团股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "中国交通建设股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "中国中铁股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中国中煤能源股份有限公司_2024-12-31_年度报告_2025-03-22.pdf" in s or
               "中国东方航空股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中原证券股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中信银行股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "中信证券股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "中国人寿保险股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "烟台民士达特种纸业股份有限公司_2024-12-31_年度报告_2025-03-19.pdf" in s or
               "中信建投证券股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "湖南惠同新材料股份有限公司_2024-12-31_年度报告_2025-03-31.pdf" in s or
               "东方证券股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "湖南华菱钢铁股份有限公司_2024-12-31_年度报告_2025-03-22.pdf" in s or
               "东兴证券股份有限公司_2024-12-31_年度报告_2025-04-04.pdf" in s or
               "上海飞乐音响股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "湖北宏裕新型包材股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "东莞发展控股股份有限公司_2024-12-31_年度报告_2025-04-08.pdf" in s or
               "深圳高速公路集团股份有限公司_2024-12-31_年度报告_2025-03-22.pdf" in s or
               "上海电气集团股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "上海申通地铁股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "上海浦东发展银行股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "上海机电股份有限公司_2024-12-31_年度报告_2025-03-22.pdf" in s or
               "上海张江高科技园区开发股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "蓝星安迪苏股份有限公司_2024-12-31_年度报告_2025-02-28.pdf" in s or
               "中船海洋与防务装备股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "苏州轴承厂股份有限公司_2024-12-31_年度报告_2025-04-07.pdf" in s or
               "中航富士达科技股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "苏州太湖雪丝绸股份有限公司_2024-12-31_年度报告_2025-04-01.pdf" in s or
               "中科星图测控技术股份有限公司_2024-12-31_年度报告_2025-03-03.pdf" in s or
               "苏宁易购集团股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中石化石油工程技术服务股份有限公司_2024-12-31_年度报告_2025-03-19.pdf" in s or
               "航天长征化学工程股份有限公司_2024-12-31_年度报告_2025-04-01.pdf" in s or
               "中泰证券股份有限公司_2024-12-31_年度报告_2025-03-22.pdf" in s or
               "中材节能股份有限公司_2024-12-31_年度报告_2025-04-02.pdf" in s or
               "胜业电气股份有限公司_2023-12-31_年度报告_2024-04-22.pdf" in s or
               "聚辰半导体股份有限公司_2024-12-31_年度报告_2025-03-25.pdf" in s or
               "翱捷科技股份有限公司_2024-12-31_年度报告_2025-04-08.pdf" in s or
               "美的集团股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中国银行股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "绿色动力环保集团股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "统一低碳科技(新疆)股份有限公司_2024-12-31_年度报告_2025-02-28.pdf" in s or
               "中国铝业股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "中国铁路物资股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "红塔证券股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中国铁建重工集团股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中国银河证券股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中国邮政储蓄银行股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "中国联合网络通信股份有限公司_2024-12-31_年度报告_2025-03-19.pdf" in s or
               "中国神华能源股份有限公司_2024-12-31_年度报告_2025-03-22.pdf" in s or
               "中国石油集团资本股份有限公司_2024-12-31_年度报告_2025-04-03.pdf" in s or
               "中国石油天然气股份有限公司_2024-12-31_年度报告_2025-03-31.pdf" in s or
               "中国石油化工股份有限公司_2024-12-31_年度报告_2025-03-24.pdf" in s or
               "中国石化上海石油化工股份有限公司_2024-12-31_年度报告_2025-03-20.pdf" in s or
               "中国电信股份有限公司_2024-12-31_年度报告_2025-03-26.pdf" in s or
               "中国海洋石油有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "中国民生银行股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中国建设银行股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中国工商银行股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中国太平洋保险(集团)股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "中国外运股份有限公司_2024-12-31_年度报告_2025-03-26.pdf" in s or
               "中国平安保险(集团)股份有限公司_2024-12-31_年度报告_2025-03-20.pdf" in s or
               "中国国际金融股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "中国国际贸易中心股份有限公司_2024-12-31_年度报告_2025-04-01.pdf" in s or
               "中国国际货运航空股份有限公司_2024-12-31_年度报告_2025-04-09.pdf" in s or
               "中国国际航空股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "中国国际海运集装箱(集团)股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "长虹美菱股份有限公司_2024-12-31_年度报告_2025-04-03.pdf" in s or
               "北京天坛生物制品股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "长城汽车股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "上海复旦张江生物医药股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "北京北辰实业股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "上海博迅医疗生物仪器股份有限公司_2024-12-31_年度报告_2025-04-07.pdf" in s or
               "上海华鑫股份有限公司_2024-12-31_年度报告_2025-03-31.pdf" in s or
               "上海医药集团股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "上海光明肉业集团股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "上海世茂股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "上海交运集团股份有限公司_2024-12-31_年度报告_2025-04-02.pdf" in s or
               "创元科技股份有限公司_2024-12-31_年度报告_2025-04-08.pdf" in s or
               "凯盛科技股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "万科企业股份有限公司_2024-12-31_年度报告_2025-04-01.pdf" in s or
               "重庆银行股份有限公司_2024-12-31_年度报告_2025-03-22.pdf" in s or
               "重庆钢铁股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "重庆美心翼申机械股份有限公司_2024-12-31_年度报告_2025-03-31.pdf" in s or
               "兴业银行股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "光大证券股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "信达证券股份有限公司_2024-12-31_年度报告_2025-03-26.pdf" in s or
               "重庆农村商业银行股份有限公司_2024-12-31_年度报告_2025-03-26.pdf" in s or
               "郑州银行股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "黄山永新股份有限公司_2024-12-31_年度报告_2025-03-21.pdf" in s or
               "万泽实业股份有限公司_2024-12-31_年度报告_2025-03-07.pdf" in s or
               "顺丰控股股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "鞍钢股份有限公司_2024-12-31_年度报告_2025-03-31.pdf" in s or
               "青岛银行股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "贵州贵航汽车零部件股份有限公司_2024-12-31_年度报告_2025-03-15.pdf" in s or
               "丽珠医药集团股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "陕西科隆新材料科技股份有限公司_2023-12-31_年度报告_2024-04-24.pdf" in s or
               "陕西省国际信托股份有限公司_2024-12-31_年度报告_2025-03-18.pdf" in s or
               "中集车辆(集团)股份有限公司_2024-12-31_年度报告_2025-03-26.pdf" in s or
               "中铝国际工程股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "日照港股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "无锡农村商业银行股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "方正证券股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "南华期货股份有限公司_2024-12-31_年度报告_2025-03-11.pdf" in s or
               "南京证券股份有限公司_2024-12-31_年度报告_2025-03-22.pdf" in s or
               "华电国际电力股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "华润博雅生物制药集团股份有限公司_2024-12-31_年度报告_2025-03-19.pdf" in s or
               "招商银行股份有限公司_2024-12-31_年度报告_2025-03-26.pdf" in s or
               "招商证券股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "华泰证券股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "招商局蛇口工业区控股股份有限公司_2024-12-31_年度报告_2025-03-18.pdf" in s or
               "华林证券股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "招商局积余产业运营服务股份有限公司_2024-12-31_年度报告_2025-03-17.pdf" in s or
               "招商局港口集团股份有限公司_2024-12-31_年度报告_2025-04-03.pdf" in s or
               "招商局公路网络科技控股股份有限公司_2024-12-31_年度报告_2025-04-03.pdf" in s or
               "华安证券股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "成都长城开发科技股份有限公司_2023-12-31_年度报告_2024-04-10.pdf" in s or
               "北新集团建材股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "成都成电光信科技股份有限公司_2023-12-31_年度报告_2024-03-19.pdf" in s or
               "成都银河磁体股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "恒生电子股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "弘业期货股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "开滦能源化工股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "北京威卡威汽车零部件股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "宁夏银星能源股份有限公司_2024-12-31_年度报告_2025-03-25.pdf" in s or
               "江苏张家港农村商业银行股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "江苏农华智慧农业科技股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "江苏万达特种轴承股份有限公司_2023-12-31_年度报告_2024-03-29.pdf" in s or
               "奇精机械股份有限公司_2024-12-31_年度报告_2025-03-22.pdf" in s or
               "天虹数科商业股份有限公司_2024-12-31_年度报告_2025-03-15.pdf" in s or
               "武汉三镇实业控股股份有限公司_2023-12-31_年度报告_2024-04-29.pdf" in s or
               "步步高商业连锁股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "基康仪器股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "国联民生证券股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "国海证券股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "国泰海通证券股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "杭州天目山药业股份有限公司_2024-12-31_年度报告_2025-04-01.pdf" in s or
               "合肥科拜尔新材料股份有限公司_2023-12-31_年度报告_2024-03-11.pdf" in s or
               "浙江久立特材科技股份有限公司_2024-12-31_年度报告_2025-03-25.pdf" in s or
               "浙商银行股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "洛阳栾川钼业集团股份有限公司_2024-12-31_年度报告_2025-03-22.pdf" in s or
               "深圳市中科蓝讯科技股份有限公司_2024-12-31_年度报告_2025-04-09.pdf" in s or
               "河南硅烷科技发展股份有限公司_2024-12-31_年度报告_2025-03-20.pdf" in s or
               "深圳华侨城股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "杭州朗鸿科技股份有限公司_2024-12-31_年度报告_2025-03-25.pdf" in s or
               "深圳赛格股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "海通证券股份有限公司_2024-12-31_年度报告_2025-04-01.pdf" in s or
               "沙河实业股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "海尔智家股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "沪士电子股份有限公司_2024-12-31_年度报告_2025-03-26.pdf" in s or
               "申万宏源集团股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "江铃汽车股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "海信家电集团股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "浪潮电子信息产业股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "浙江航民股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "浙江绍兴瑞丰农村商业银行股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "江苏江阴农村商业银行股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "重庆宗申动力机械股份有限公司_2024-12-31_年度报告_2025-04-01.pdf" in s or
               "浙江华康药业股份有限公司_2024-12-31_年度报告_2025-02-28.pdf" in s or
               "江苏常熟农村商业银行股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "江苏宁沪高速公路股份有限公司_2024-12-31_年度报告_2025-03-27.pdf" in s or
               "山东海化股份有限公司_2024-12-31_年度报告_2025-03-22.pdf" in s or
               "山东新华制药股份有限公司_2024-12-31_年度报告_2025-03-31.pdf" in s or
               "广州越秀资本控股集团股份有限公司_2024-12-31_年度报告_2025-04-03.pdf" in s or
               "山东胜利股份有限公司_2024-12-31_年度报告_2025-03-22.pdf" in s or
               "广州白云山医药集团股份有限公司_2024-12-31_年度报告_2025-03-14.pdf" in s or
               "广发证券股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "安徽海螺水泥股份有限公司_2024-12-31_年度报告_2025-03-25.pdf" in s or
               "广东电力发展股份有限公司_2024-12-31_年度报告_2025-03-29.pdf" in s or
               "广东奥迪威传感科技股份有限公司_2024-12-31_年度报告_2025-03-25.pdf" in s or
               "平安银行股份有限公司_2024-12-31_年度报告_2025-03-15.pdf" in s or
               "常州瑞华化工工程技术股份有限公司_2023-12-31_年度报告_2024-04-26.pdf" in s or
               "宁波球冠电缆股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "宁波太平鸟时尚服饰股份有限公司_2024-12-31_年度报告_2025-03-28.pdf" in s or
               "山东高速股份有限公司_2024-12-31_年度报告_2025-04-04.pdf" in s or
               "爱玛科技集团股份有限公司.pdf" in s or
               "111.pdf" in s, pdf_files))

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
    main(folder_path, output_file, False)
    end_time = time.time()  # 记录结束时间
    print(f"全部文件处理完成，结果已保存至：{output_file}，耗时: {end_time - start_time:.6f}秒")
