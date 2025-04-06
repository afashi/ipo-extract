from enum import Enum

class Table(Enum):
    ENTRUSTED_FINANCIAL_SITUATION = ("委托理财情况","1")
    TRADING_FINANCIAL_ASSETS = ("理财产品明细",)
    OTHER_CURRENT_ASSETS = ("理财产品明细",)
    DIFF_CTL_ORG_MG_CUR_PRD = ("非同一控制下企业合并-本期发生的非同一控制下企业合并",)
    DIFF_CTL_ORG_MG_COST_GW = ("非同一控制下企业合并-合并成本及商誉",)
    CIP_IMPT_PROJECT_CHANGE = ("在建工程-重要在建工程项目变动",)
    OVERDUE_LOAN = ("逾期借款情况",)
    CONTRACT_ASSET_DTL = ("合同资产",)
    S_ADVANCE_PAY_TOP_FIVE_EB = ("预付款项-期末余额前几名单位情况",)
    S_RELATED_PARTY = ("其他关联方",)

    def __init__(self, cn_name, description):
        self.name = cn_name          # 状态码
        self.description = description  # 状态描述

    @classmethod
    def get_by_code(cls, code):
        """根据状态码获取枚举成员"""
        for status in cls:
            if status.code == code:
                return status
        raise ValueError(f"无效的状态码: {code}")

    def __str__(self):
        return f"{self.name} (code={self.code}, desc={self.description})"

# 使用示例
if __name__ == "__main__":
    # 访问枚举成员
    print(Table.FINANCIAL_PRODUCT)                # Status.SUCCESS
    print(Table.SUCCESS.code)           # 200
    print(Table.SUCCESS.description)    # 操作成功

    # 通过方法获取枚举
    print(Table.get_by_code(404))       # Status.NOT_FOUND

    # 遍历所有枚举成员
    for status in Status:
        print(f"{status.name}: {status.code} - {status.description}")

    # 格式化输出
    print(str(Status.SERVER_ERROR))      # SERVER_ERROR (code=500, desc=服务器错误)