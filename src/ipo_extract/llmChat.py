from openai import OpenAI

prompt1 = """
#### 定位
- 智能助手名称 ：数据采集员
- 主要任务 ：对任务材料中的上市公司年度财报的内容进行分析，判断该内容片段是否披露《重要在建工程项目本期变动情况》的表格。

#### 能力
- 文本分析 ：
  - 能够准确识别《重要在建工程项目本期变动情况》的章节，不受其他章节干扰。
  - 能够准确识别《重要在建工程项目本期变动情况》的章节下，是否存在相应表格。
  - 能够准确分辨《重要在建工程项目本期变动情况》下的表格是否有被拆分成多个表格的情况，能结合被拆分的表格统一进行分析。
  - 能够准确分析《重要在建工程项目本期变动情况》下的表格，是否披露相应表格，分析是否包含表头和数据，都包含则视为披露，如果只有表头没有任何数据则视为未披露。
  - 能够准确分析《重要在建工程项目本期变动情况》的章节下，如没有表格则需要判断是否标注不适用，未披露情况下一般会标注不适用。披露情况下一般会不标注或标注适用。
  - 能够分析出自己是否能对这次任务做出准确判断，如数据披露过少，表头部分确实等无法做出准确判断则该认为需要人工介入

#### 知识储备
- 财务知识 ：《重要在建工程项目本期变动情况》一般包含以下内容，部分情况下也可能没有
  - 项目名称
  - 预算数
  - 期初余额
  - 本期增加额
  - 本期转入固定资产金额
  - 本期其他减少金额
  - 期末余额
  - 工程累计投入占比
  - 工程进度
  - 利息资本化累计金额
  - 资金来源

#### 任务材料
"""

prompt2 = """
#### 输出说明
- 输出 ：最后根据思考过程得出结论。结论只输出“是”来表示披露或“否”来表示不披露。如无法判断则输出“需要人工介入”，不需要额外解释。
"""

client = OpenAI(
    # 如果没有配置环境变量，请用百炼API Key替换：api_key="sk-xxx"
    api_key="sk-622c6d00c975492786eba2e6a2a93ec4",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

def chat_completion(message):
    # 初始化OpenAI客户端
    try:
        reasoning_content = ""  # 定义完整思考过程
        answer_content = ""  # 定义完整回复
        last = ""
        is_answering = False  # 判断是否结束思考过程并开始回复
        # 创建聊天完成请求
        completion = client.chat.completions.create(
            model="qwq-32b",  # 此处以 qwq-32b 为例，可按需更换模型名称
            messages=[
                {"role": "user", "content": prompt1 + message + prompt2}
            ],
            # QwQ 模型仅支持流式输出方式调用
            stream=True,
            # 解除以下注释会在最后一个chunk返回Token使用量
            stream_options={
                "include_usage": True
            }
        )
        print("\n" + "=" * 20 + "思考过程" + "=" * 20 + "\n")
        for chunk in completion:
            # 如果chunk.choices为空，则打印usage
            if not chunk.choices:
                last = chunk.usage
            else:
                delta = chunk.choices[0].delta
                # 打印思考过程
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                    reasoning_content += delta.reasoning_content
                else:
                    # 开始回复
                    if delta.content != "" and is_answering is False:
                        print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
                        is_answering = True
                    # 打印回复过程
                    answer_content += delta.content
    except Exception as error:
        print(error)
    return reasoning_content, answer_content,last

#
# if __name__ == '__main__':
#     reasoning_content, answer_content,completion_usage = chat_completion("""
#     项目  账面价值  未办妥产权证书的原因
# 研发大楼  65,147,832.91 尚在办理房产证
# 研发辅楼  4,793,123.98 尚在办理房产证
# 其他说明：
#   报告期末固定资产抵押情况详见本附注五、19所有权或使用权受到限制的资产。
# （5） 固定资产的减值测试情况
# □适用 不适用
# 14、在建工程
# 单位：元
# 项目  期末余额  期初余额
# 在建工程  977,781.49  3,935,928.50
# 合计  977,781.49  3,935,928.50
# （1） 在建工程情况
# 单位：元
# 期末余额  期初余额
# 项目
# 账面余额 减值准备 账面价值 账面余额 减值准备 账面价值
# 中型高档公商
#      3,615,928.50   3,615,928.50
# 务车项目
# 其他  977,781.49   977,781.49 320,000.00   320,000.00
# 合计  977,781.49   977,781.49 3,935,928.50   3,935,928.50
# （2） 在建工程的减值测试情况
# □适用 不适用
# 15、无形资产
# （1） 无形资产情况
# 单位：元
# 项目  土地使用权 专利权 非专利技术 软件及其他  合计
# 一、账面原值
# 1.期初余额  220,280,035.42     34,622,456.87 254,902,492.29
# 2.本期增加金额       1,987,880.14 1,987,880.14
# （1）购置       1,156,653.72 1,156,653.72
# （2）内部研
#
# 发
# （3）企业合
#
# 并增加
#        （4）在建工程      831,226.42 831,226.42
#     """)
#     print("=" * 20 + "完整思考过程" + "=" * 20 + "\n")
#     print(reasoning_content)
#     print("=" * 20 + "完整回复" + "=" * 20 + "\n")
#     print(answer_content)
