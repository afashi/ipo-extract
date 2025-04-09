from enum import Enum
import re_pattern, prompt_constants


class TableConfigEnum(Enum):
    CIP_IMPT_PROJECT_CHANGE = (
        "在建工程-重要在建工程项目变动", "1",
        "financial_report",
        "note",
        re_pattern.cip_impt_project_change_start_pattern,
        re_pattern.cip_impt_project_change_parent_start_pattern,
        re_pattern.cip_impt_project_change_end_pattern, prompt_constants.prompt11)
    CONTRACT_ASSET_DTL = (
        "合同资产情况", "1",
        "financial_report",
        "note",
        re_pattern.contract_asset_dtl_start_pattern,
        re_pattern.contract_asset_dtl_parent_start_pattern,
        re_pattern.contract_asset_dtl_end_pattern, prompt_constants.prompt12)
    ADVANCE_PAY_TOP_FIVE_EB = (
        "预付款项-期末余额前几名单位情况", "1",
        "financial_report",
        "note",
        re_pattern.advance_pay_top_five_eb_start_pattern,
        re_pattern.advance_pay_top_five_eb_parent_start_pattern,
        re_pattern.advance_pay_top_five_eb_end_pattern, prompt_constants.prompt13)

    DIFF_CTL_ORG_MG_CUR_PRD = (
        "非同一控制下企业合并-本期发生的非同一控制下企业合并", "2",
        "financial_report",
        "scope_change",
        re_pattern.diff_ctl_org_mg_cur_prd_start_pattern,
        re_pattern.diff_ctl_org_mg_cur_prd_parent_start_pattern,
        re_pattern.diff_ctl_org_mg_cur_prd_end_pattern, prompt_constants.prompt14)
    DIFF_CTL_ORG_MG_COST_GW = (
        "非同一控制下企业合并-合并成本及商誉", "2",
        "financial_report",
        "scope_change",
        re_pattern.diff_ctl_org_mg_cost_gw_start_pattern,
        re_pattern.diff_ctl_org_mg_cost_gw_parent_start_pattern,
        re_pattern.diff_ctl_org_mg_cost_gw_end_pattern, prompt_constants.prompt15)
    OTHER_RELATED_PARTY = (
        "其他关联方", "1",
        "financial_report",
        "related_party",
        re_pattern.other_related_party_start_pattern,
        re_pattern.other_related_party_parent_start_pattern,
        re_pattern.other_related_party_end_pattern, prompt_constants.prompt16)

    ENTRUSTED_FINANCIAL_SITUATION = (
        "委托理财情况","1",
        "important_matters",
        "major_contracts",
        re_pattern.entrusted_financial_situation_party_start_pattern,
        re_pattern.entrusted_financial_situation_party_parent_start_pattern,
        re_pattern.entrusted_financial_situation_party_end_pattern,prompt_constants.prompt171)
    TRADING_FINANCIAL_ASSETS = (
        "交易性金融资产","1",
        "financial_report",
        "note",
        re_pattern.trading_financial_assets_party_start_pattern,
        re_pattern.trading_financial_assets_party_parent_start_pattern,
        re_pattern.trading_financial_assets_party_end_pattern,prompt_constants.prompt172)
    OTHER_CURRENT_ASSETS = (
        "其他流动资产","1",
        "financial_report",
        "note",
        re_pattern.other_current_assets_start_pattern,
        re_pattern.other_current_assets_parent_start_pattern,
        re_pattern.other_current_assets_end_pattern,prompt_constants.prompt173)
    SHORT_TERM_BORROWING = (
        "短期借款","1",
        "financial_report",
        "note",
        re_pattern.short_term_borrowing_start_pattern,
        re_pattern.short_term_borrowing_parent_start_pattern,
        re_pattern.short_term_borrowing_end_pattern,prompt_constants.prompt181)
    LONG_TERM_BORROWING = (
        "长期借款","1",
        "financial_report",
        "note",
        re_pattern.long_term_borrowing_start_pattern,
        re_pattern.long_term_borrowing_parent_start_pattern,
        re_pattern.long_term_borrowing_end_pattern,prompt_constants.prompt182)
    INTEREST_PAYABLE = (
        "应付利息","2",
        "financial_report",
        "note",
        re_pattern.interest_payable_start_pattern,
        re_pattern.interest_payable_parent_start_pattern,
        re_pattern.interest_payable_end_pattern,prompt_constants.prompt183)

    def __init__(self, cn_name, strategy,
                 second_title_all,
                 second_title, start_pattern,
                 parent_start_pattern,
                 end_pattern, prompt):
        self.cn_name = cn_name  # 状态码
        self.strategy = strategy
        self.second_title_all = second_title_all  # 所有二级标题
        self.second_title = second_title  # 所在的二级标题
        self.start_pattern = start_pattern  # 表格标题开头
        self.parent_start_pattern = parent_start_pattern  # 表格父级标题开头
        self.end_pattern = end_pattern  # 表格标题开头
        self.prompt = prompt  # 专用提示词

    @classmethod
    def get_by_code(cls, code):
        """根据状态码获取枚举成员"""
        for status in cls:
            if status.code == code:
                return status
        raise ValueError(f"无效的状态码: {code}")

    def __str__(self):
        return f"{self.name} (code={self.code}, desc={self.description})"


second_title_all_map = {
    "important_matters": re_pattern.second_title_important_matters_all_pattern,
    "financial_report": re_pattern.second_title_financial_report_all_pattern,
}

second_title_map = {
    "note": re_pattern.second_title_note_pattern,
    "scope_change": re_pattern.second_title_scope_change_pattern,
    "related_party": re_pattern.second_title_related_party_pattern,
    "major_contracts": re_pattern.second_title_major_contracts_pattern
}
