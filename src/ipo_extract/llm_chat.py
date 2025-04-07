from openai import OpenAI

from src.ipo_extract import prompt_constants

client = OpenAI(
    # 如果没有配置环境变量，请用百炼API Key替换：api_key="sk-xxx"
    api_key="sk-22",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)


def chat_completion(message, prompt):
    # 初始化OpenAI客户端
    reasoning_content = ""  # 定义完整思考过程
    answer_content = ""  # 定义完整回复
    completion_tokens = 0  # 定义完整回复
    prompt_tokens = 0  # 定义完整回复
    last = None  # 定义完整回复
    is_answering = False  # 判断是否结束思考过程并开始回复
    # 创建聊天完成请求
    completion = client.chat.completions.create(
        model="qwq-32b",  # 此处以 qwq-32b 为例，可按需更换模型名称
        messages=[
            {"role": "user", "content": prompt + message + prompt_constants.prompt2}
        ],
        # QwQ 模型仅支持流式输出方式调用
        stream=True,
        # 解除以下注释会在最后一个chunk返回Token使用量
        stream_options={
            "include_usage": True
        }
    )
    for chunk in completion:
        # 如果chunk.choices为空，则打印usage
        if not chunk.choices:
            last = chunk.usage
            completion_tokens, prompt_tokens = last.completion_tokens, last.prompt_tokens
        else:
            delta = chunk.choices[0].delta
            # 打印思考过程
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content is not None:
                reasoning_content += delta.reasoning_content
            else:
                # 开始回复
                if delta.content != "" and is_answering is False:
                    is_answering = True
                # 打印回复过程
                answer_content += delta.content
    return reasoning_content, answer_content, completion_tokens, prompt_tokens

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
