#!/usr/bin/env python
# coding=utf-8
'''
Author: chenym loseyyou@gmail.com
Date: 2024-02-20 10:09:11
LastEditors: chenym loseyyou@gmail.com
LastEditTime: 2024-02-20 10:35:45
FilePath: \JIA\src\5.yearreport.py
Description: 
Copyright (c) 2024 by loseyyou@gmail.com, All Rights Reserved. 
'''
import datetime
from loguru import logger
import os
import sqlite3
import sys
import json
import requests
import pandas as pd
import paramiko
import psycopg2
from tqdm import tqdm
import zipfile
import shutil
# 初始化全局变量
# 设置日志级别
DATA_END_TS = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')  # 含微秒的日期时间，来源 比特量化
SCHEDULE_ID = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:18]
# 初始化全局变量
PARENTDIRNAME, SCRIPT_NAME = os.path.split(os.path.abspath(sys.argv[0]))
CURRENT_TIME = datetime.datetime.now().strftime('%Y%m%d')


# 自定义日志格式
logger.add(f"check_{CURRENT_TIME}.log", format="{time} {level} {message}")
logger.level("INFO")
# 数据库日志
def connect_database(dbpath):
    conn = sqlite3.connect(dbpath)
    return conn


def etl_log_crt(conn):
    cur = conn.cursor()
    sql_create_table = '''CREATE TABLE IF NOT EXISTS b_ctl_schedule
                            (
                                id            varchar(32),
                                flow_name     varchar(200),
                                data_start_ts timestamp without time zone,
                                data_end_ts   timestamp without time zone,
                                start_ts      timestamp without time zone,
                                end_ts        timestamp without time zone,
                                create_ts     timestamp without time zone,
                                row_cnt       integer,
                                run_state     varchar(2)
                            );'''
    # 执行sql语句
    cur.execute(sql_create_table)
    sql_create_table = '''CREATE TABLE   IF NOT EXISTS check_pdf_rslt
                        (

                            schedule_id      varchar(256),
                            seq_no           INTEGER,
                            is_exist         varchar(1),
                            rep_date         date,
                            server_path      varchar(256),
                            local_path       varchar(256),
                            rep_title        varchar(256),
                            rep_year         INTEGER,
                            data_id          INTEGER,
                            company_name     varchar(256),
                            file_name         varchar(256),
                            announ_orig_link varchar(256),
                            create_ts        timestamp without time zone,
                            export_time      timestamp without time zone,
                            etl_load_time    timestamp without time zone,
                            message varchar(256),
                            success varchar(10) 
                        );'''
    # 执行sql语句
    cur.execute(sql_create_table)
    cur.close()
    conn.commit()

def load_check_rslt(conn):
    cur = conn.cursor()
    sql_insert = f'''insert into check_pdf_rslt
        (schedule_id, seq_no, is_exist, rep_date, server_path, local_path, rep_title, rep_year, data_id, company_name, announ_orig_link, create_ts
        , etl_load_time,file_name )
        select  t.schedule_id, t.seq_no, t.is_exist, t.rep_date, t.server_path, t.local_path, t.rep_title, t.rep_year, t.data_id, t.company_name, t.announ_orig_link, t.create_ts, t.etl_load_time ,t.file_name from tmp_check_pdf_rslt t
        left join check_pdf_rslt t2 on t.data_id = t2.data_id
        where t2.data_id is null  and  t.schedule_id = {SCHEDULE_ID}'''
    # 执行sql语句
    cur.execute(sql_insert)
    # var_cnt = cur.rowcount
    sql_update = f''' UPDATE b_ctl_schedule SET end_ts= current_timestamp
     ,run_state='02'
              WHERE ID = {SCHEDULE_ID}'''
    cur.execute(sql_update)
    cur.close()
    conn.commit()
# 获取ETL创建时间 Intelli_collect.py
def get_data_start_ts(conn, flow_name):
    cur = conn.cursor()
    # 上次跑批时间
    sql_create_table = f"select coalesce((select max(data_end_ts) FROM  " \
                       f"b_ctl_schedule where run_state='02' and flow_name = '{flow_name}'),'2025-01-01') "
    cur.execute(sql_create_table)
    (data_start_ts,) = cur.fetchone()
    cur.close()
    conn.commit()
    return data_start_ts

# 写入ETL日志
def write_etl_log(conn, data_start_ts, flow_name) -> bool:
    id = SCHEDULE_ID
    data_end_ts = DATA_END_TS
    start_ts = str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'))
    run_state = '01'
    cur = conn.cursor()
    # 上次跑批时间
    sql = f''' insert into b_ctl_schedule 
                (id,flow_name,data_start_ts,data_end_ts,start_ts,create_ts,run_state)
             values ('{id}', '{flow_name}', '{data_start_ts}', '{data_end_ts}', '{start_ts}', '{data_end_ts}', '{run_state}') '''
    cur.execute(sql)
    cnt = cur.rowcount
    cur.close()
    conn.commit()
    if cnt == 1:
        return True
    else:
        return False

def getpdffile(data_start_ts, **dsn):

    logger.info(f'data_start_ts {data_start_ts}')
    conn = psycopg2.connect(**dsn)
    try:
        with conn:
            with conn.cursor() as curs:
                curs.execute("""
                SELECT
          %s as schedule_id  
         , p.rep_date::date
         ,concat('/usb/filebackup/file/ths/announcement_file/'
                 ,to_char(p.announcement_date,'yyyy-mm-dd'),'/'
                 ,p.data_id,'.pdf')
         as source_file
         ,concat('PDFFILE/'
                     ,p.company_name
                     ,'_'
                     ,rep_date,'_'
                     ,rep_type,'_'
                     ,to_char(p.announcement_date,'yyyy-mm-dd')
                     ,'.pdf') as target_file
         ,concat(  
                      p.company_name
                     ,'_'
                     ,rep_date,'_'
                     ,rep_type,'_'
                     ,to_char(p.announcement_date,'yyyy-mm-dd')
                     ) as file_name
         ,rep_type
         ,rep_year
         ,data_id
         ,company_name,announ_orig_link
         ,create_ts
         ,current_timestamp as etl_load_time
     from (
     select
         substring(t1.title from  '(\\d{4}).*?年')||'-12-31'  as rep_date
         ,  '年度报告'  as rep_type
         ,t1.announcement_date,t1.data_id,t2.company_name
         ,substring(t1.title from  '(\\d{4}).*?年')::integer   as rep_year
         ,t1.create_ts
         ,t1.announ_orig_link 
         ,row_number() over (partition by company_id, substring(t1.title from  '(\\d{4}).*?年')::integer
          order by t1.data_source_code,t1.type_code, t1.data_id desc)  as  rn  
     from s_announcement_title t1
     inner join b_bas_company t2
     on t1.company_id = t2.id
     and t2.is_a_share='1'
     where  1=1 
     and type_code IN ('001001003001', '007002', '024004002004')
                             and t1.create_ts>date%s  and t1.create_ts<= %s
     and t1.title ~'\\d{4}.*年度报告'
     and t1.announcement_date>=date '20241201' 
     and t1.title !~ '摘要|更正公告|半年|季度|英文|取消|专项说明|募集资金|业绩|情况|非标|督导|披露|托管|风险控制|净资本|服务报告|提示|风控|问询函|说明|债券担保方|评估|季报|补充公告|专项意见|更正公告|声明|模拟|3月|6月|9月|资产服务机构报告|资产管理报告|资产运营报告|股份变动|中期|保留意见|清算|反馈意见|赎回|诉讼|变更|摊薄|子公司|债权代理事务|一季|三季|Annual Report' AND not (t1.title ~ '担保人' and t1.title !~ '含担保人') AND not (t1.title ~ '母公司' and title !~ '合并及') AND not (t1.title ~ '本部' and t1.title !~ '合并及')
     ) p  where p.rn =1
                """, (SCHEDULE_ID,data_start_ts, DATA_END_TS))
                v_rslt = curs.fetchall()
                v_cnt = curs.rowcount
                return v_rslt, v_cnt
    finally:
        conn.close()

'''
獲取遠程ssh鏈接信息
'''


def getremoteinfo(ip, port, user, password):
    v_client = paramiko.SSHClient()
    v_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    v_client.connect(ip, port, user, password)
    v_transport = v_client.get_transport()
    return v_client, v_transport

'''
導出數據pdf路徑信息
'''
def exportcsvfile(v_rslt_list):
    # columns_list = ['is_exist','rep_date', 'server_', '本地地址', "data_id", "company_name", "announcement_date"
    # , "create_ts","report_type"]
    data_raw = pd.DataFrame(data=v_rslt_list)
    data_raw.to_csv("check.csv", header=False, index=False)

'''
获取存在的pdf文件有效数据,下載pdf文件
'''
def getfilepdf(file, v_sftp):
    df = pd.read_csv(file, header=None)
    dataset = df[df[0]]
    total_size = dataset.shape[0]
    with tqdm(total=total_size, desc=f"下载到本地平台报告数[{total_size}家]") as pbar:
        for index, row in dataset.iterrows():
            soucefile = row[3]
            targetfile = row[4]
            #判断文件是否存在
            if os.path.exists(targetfile):
                logger.info(f"{targetfile} 文件已存在")
            else:
                 v_sftp.get(soucefile, targetfile)
            pbar.set_postfix_str(targetfile, True)
            pbar.update(1)

# 下载文件到本地PDF
def expor_pdf_local(target_path):
    conn = connect_database('intelli_collect.db')
    flow_name = 'intelli_collect.py'
    etl_log_crt(conn)
    v_data_start_ts = get_data_start_ts(conn, flow_name)
    write_etl_log(conn, v_data_start_ts, flow_name)

    client, transport = getremoteinfo('192.168.0.50', 22, 'root', "VGp6eEA1MAo=")
    sftp = paramiko.SFTPClient.from_transport(transport)

    pgsql_config = {
        'user': 'tjfj_user',
        'password': 'TJPRDuser#401210xx',
        'host': '192.168.0.90',
        'port': 5432,
        'database': 'tjfj'}
    # 生成结果数据及條數
    pdfpath, cnt = getpdffile(v_data_start_ts, **pgsql_config)
    logger.info(f"当前增量报告数: {cnt}")
    if cnt <= 0:
        logger.info("无新增数据")
    else:
    # 结果数据导出csv
        exportcsvfile(pdfpath)
        # 上传CSV文件列表/脚本
        v_check_file = "/usb/filebackup/file/ths/announcement_file/check.csv"
        v_check_script = "/usb/filebackup/file/ths/announcement_file/checkfile.sh"
        v_check_rslt = "/usb/filebackup/file/ths/announcement_file/check.rslt"
        sftp.put("check.csv", v_check_file)
        sftp.put("checkfile.sh", v_check_script)
        # 调用脚本检查pdf文件是否存在
        exec_arg = f" sh {v_check_script}  {v_check_file} {v_check_rslt}"
        _, stdout, _ = client.exec_command(exec_arg)
        if stdout.readline().strip() == 'success':
            logger.info('报告是否存在服务器校验完成')
        # 下載檢查結果
        sftp.get(v_check_rslt, "check.csv")
        df = pd.read_csv("check.csv", header=None)
        df.columns = ['is_exist', 'schedule_id', 'rep_date', 'server_path', 'local_path','file_name', "rep_title", "rep_year",
                      "data_id",
                      "company_name", "announ_orig_link", "create_ts", "etl_load_time"]
        # df.rename(columns={'a':'A','b':'B'},inplace=True)
        cnt = df.shape[0]
        df.to_sql(name='tmp_check_pdf_rslt', con=conn, index_label='seq_no', if_exists='replace')
        # 獲取有效數據並下載pdf
        getfilepdf("check.csv", sftp)
        load_check_rslt(conn)
        # 关闭链接
        # upload_fintelli_collect(target_path)
        export_error_file()
    client.close()
    conn.close()


def upload_fintelli_collect(target_path):
    headers_data = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"
        ,
        "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJlc19zdXBlcmFkbWluIiwicGFzc3dvcmQiOiI4OWMzMTQ0Yjc0NzQyNThhN2NmNjRhNDFhZWZhODViOSIsImlkIjoiU1VQRVJNQU4wMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAiLCJ1c2VyTmFtZSI6ImVzX3N1cGVyYWRtaW4iLCJleHAiOjQ4MTI1MDYwNTcsImlhdCI6MTY1ODkwNjA1NywianRpIjoiY2FkNjMyMTc1OWU3NDczM2JlNmY1YjI1YzRmMzA4MTgifQ.PL2GG3XLMTExilU7Z2_LT0WdS1SvKeKQplrBmjSLS-w"
    }
    file_list = os.listdir(target_path)
    print(target_path)
    print(file_list)
    post_date ={"sourceType":2}
    upload_file_list = []
    conn = connect_database('intelli_collect.db')
    cur = conn.cursor()

    with tqdm(total=len(file_list), desc=f"上传到采集平台报告数[{len(file_list)}家]") as pbar:
        for v_file in file_list:
            if os.path.splitext(v_file)[1] in ('.pdf', '.PDF'):
                upload_file_list.append(os.path.splitext(v_file)[0])
                absut_file_path = os.path.join(target_path, v_file)
                url = 'http://192.168.0.44:8582/api/doc/upload'
                file = {'file': open(absut_file_path, 'rb')}
                response = requests.post(url, headers=headers_data, files=file,data=post_date)
                rslt = json.loads(response.text)
                logger.info(f"{v_file} : {rslt}")
                cur.execute("update check_pdf_rslt set export_time = current_timestamp,success=?,message=? "
                            " where file_name =? ",(rslt.get('success'),rslt.get('message'),os.path.splitext(v_file)[0],))
                pbar.set_postfix_str(v_file, True)
                pbar.update(1)
    cur.close()
    conn.commit()
    conn.close()
def get_absulote_path(filepath):
    path = os.path.expanduser("~")
    if os.name in ("nt", "dos", "ce"):  # DOS/Windows
        # os.system("CLS")
        path = os.path.join(path, PARENTDIRNAME)
        # logger.debug(f"{SCRIPT_NAME} 程序执行路径 {path}")
    filepath = os.path.join(path, filepath)
    return filepath
def export_error_file():
    conn = connect_database('intelli_collect.db')
    cur = conn.cursor()
    cur.execute("select local_path from check_pdf_rslt where success ='0' and message<>'已上传过相同文件' "
                " and etl_load_time >= current_date")
    rslt = cur.fetchall()

    filepath = f"报告未上传_{CURRENT_TIME}.xlsx"
    cur.execute("select * from check_pdf_rslt where export_time is null "
                " and etl_load_time >= current_date" )
    records = cur.fetchall()
    data_raw = pd.DataFrame(data=records)
    data_raw.to_excel(filepath,index = False,header=None)
    conn.close()
    if len(rslt)> 0 and len(records) >0:
        current_time = datetime.datetime.now().strftime('%Y%m%d')
        tar_zip = f"error_{current_time}.zip"
        f = zipfile.ZipFile(tar_zip, 'w',zipfile.ZIP_DEFLATED)
        try:
            for v_file in rslt:
                f.write(get_absulote_path(v_file[0]),os.path.split(v_file[0])[1])
            f.write(filepath)
        finally:
            f.close()

# def upload_tmpl_file():
#     download_file = '智能采集数据下载模板.xlsx'
#     left = pd.read_excel(download_file,usecols=["库表名称"])
#     left.dropna(subset=["库表名称"], axis=0, inplace=True)
#     conn = connect_database('intelli_collect.db')
#     cur = conn.cursor()
#     cur.execute("select file_name from check_pdf_rslt where export_time is null")
#     rslt = cur.fetchall()
#     right = pd.DataFrame(data=rslt, columns={"文件名"})
#     all = left.join(right,how='outer')
#     all.to_excel('当前上传模板.xlsx', index_label='序号')
#     conn.close()
if __name__ == '__main__':
    file_dir_path = 'PDFFILE'
    target_path = os.path.join(PARENTDIRNAME, file_dir_path)
    print(target_path)
    if os.path.exists(target_path):
        print("文件夹存在")

    else:
        print("文件夹不存在")
        os.makedirs(target_path)
    shutil.rmtree(target_path)
    os.makedirs(target_path)
    expor_pdf_local(target_path)


#
# select concat(data_id,',',announcement_date)  from s_announcement_title sat
