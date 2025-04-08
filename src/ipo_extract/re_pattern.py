import re

# 重要事项的二级标题
second_title_important_matters_all_pattern = re.compile(
    r'^\(?(一|二|三|四|五|六|七|八|九|十|十一|十二|十三|十四|十五|十六)、?\)?\s*(重大关联交易|重大合同及其履行情况|其他.{0,30}重大事项的说明|募集资金使用进展说明)$')
# 财务报告的二级标题
second_title_financial_report_all_pattern = re.compile(
    r'^\(?(一|二|三|四|五|六|七|八|九|十|十一|十二|十三|十四|十五|十六|十七)、?\)?\s*(重要会计政策及会计估计|税项|会计政策和会计估计变更以及前期差错更正的说明|(合并)?财务报表(主要)?项目(注释|附注)|研发支出|合并范围的(变更|变动)|在其他主体中的权益|政府补助|与金融工具相关的风险|金融工具的分类及其公允价值|公允价值的披露|关联方及关联方?交易|关联方关系及其交易|承诺及或有事项|期后事项|股份支付|其他重要事项|资产负债表日后事项)$')
# 合并财务报表项目注释
second_title_note_pattern = re.compile(r'^(合并)?财务报表(主要)?项目(注释|附注)$')
# 合并范围的变更
second_title_scope_change_pattern = re.compile(r'^合并范围的(变更|变动)$')
# 关联方及关联交易
second_title_related_party_pattern = re.compile(r'^关联方及关联方?交易|关联方关系及其交易$')
# 重大合同及其履行情况
second_title_major_contracts_pattern = re.compile(r'^重大合同及其履行情况$')
# 重要在建工程项目本期变动情况
cip_impt_project_change_start_pattern = re.compile(r'(重要)?在建工程(项目)?(本期|本年)?变动情况')
cip_impt_project_change_parent_start_pattern = re.compile(r'\d{1,2}、?\s*在建工程')
cip_impt_project_change_end_pattern = re.compile(
    r'在建工程减值准备情况|在建工程的减值测试情况|工程物资|生产性生物资产|无形资产|递延所得税资产|使用权资产|长期待摊费用')
# 合同资产情况
contract_asset_dtl_start_pattern = re.compile(r'^.{0,5}\s*(合同资产情况|合同资产分类如下)')
contract_asset_dtl_parent_start_pattern = re.compile(r'\d{1,2}、?\s*合同资产')
contract_asset_dtl_end_pattern = re.compile(
    r'报告期内账面价值发生重大变动的金额和原因|持有待售资产|应收款项融资|应收款项融资分类列示|预付款项|其他应收款')
# 预付款项--按预付对象归集的期末余额前五名的预付款情况
advance_pay_top_five_eb_start_pattern = re.compile(
    r'按预付对象归集的(期末|年末)余额前五名的预付款项?情况|余额前五名的预付款项')
advance_pay_top_five_eb_parent_start_pattern = re.compile(r'\d{1,2}、?\s*预付款项')
advance_pay_top_five_eb_end_pattern = re.compile(
    r'其他说明|其他应收款|存货')
# 非同一控制下企业合并--本期发生的非同一控制下企业合并
diff_ctl_org_mg_cur_prd_start_pattern = re.compile(
    r'本期发生的非同一控制下企业合并(交易)?')
diff_ctl_org_mg_cur_prd_parent_start_pattern = re.compile(r'\d{1,2}、?\s*非同一控制下企业合并')
diff_ctl_org_mg_cur_prd_end_pattern = re.compile(
    r'其他说明|合并成本及商誉|同一控制下企业合并')
# 非同一控制下企业合并--合并成本及商誉
diff_ctl_org_mg_cost_gw_start_pattern = re.compile(
    r'合并成本及商誉')
diff_ctl_org_mg_cost_gw_parent_start_pattern = re.compile(r'\d{1,2}、?\s*非同一控制下企业合并')
diff_ctl_org_mg_cost_gw_end_pattern = re.compile(
    r'其他说明|被购买方于购买日可辨认资产、负债|同一控制下企业合并')
# 关联方及关联交易-其他关联方情况
other_related_party_start_pattern = re.compile(
    r'其他关联方情况|不存在控制关系的关联方性质')
other_related_party_parent_start_pattern = re.compile(
    r'^\(?(十一|十二|十三|十四|十五|十六)、?\)?\s*(关联方及关联方?交易|关联方关系及其交易)$')
other_related_party_end_pattern = re.compile(
    r'关联方?交易情况|关联方应收应付款项|其他说明|本公司与关联方主要关联交易')
# 委托理财情况
entrusted_financial_situation_party_start_pattern = re.compile(
    r'按预付对象归集的(期末|年末)余额前五名的预付款项?情况|余额前五名的预付款项')
entrusted_financial_situation_party_parent_start_pattern = re.compile(r'\d{1,2}、?\s*预付款项')
entrusted_financial_situation_party_end_pattern = re.compile(
    r'其他说明|其他应收款|存货')
# 交易性金融资产
trading_financial_assets_party_start_pattern = re.compile(
    r'按预付对象归集的(期末|年末)余额前五名的预付款项?情况|余额前五名的预付款项')
trading_financial_assets_party_parent_start_pattern = re.compile(r'\d{1,2}、?\s*预付款项')
trading_financial_assets_party_end_pattern = re.compile(
    r'其他说明|其他应收款|存货')
# 其他流动资产
other_current_assets_start_pattern = re.compile(
    r'按预付对象归集的(期末|年末)余额前五名的预付款项?情况|余额前五名的预付款项')
other_current_assets_parent_start_pattern = re.compile(r'\d{1,2}、?\s*预付款项')
other_current_assets_end_pattern = re.compile(
    r'其他说明|其他应收款|存货')
# 短期借款
short_term_borrowing_start_pattern = re.compile(
    r'按预付对象归集的(期末|年末)余额前五名的预付款项?情况|余额前五名的预付款项')
short_term_borrowing_parent_start_pattern = re.compile(r'\d{1,2}、?\s*预付款项')
short_term_borrowing_end_pattern = re.compile(
    r'其他说明|其他应收款|存货')
# 长期借款
long_term_borrowing_start_pattern = re.compile(
    r'按预付对象归集的(期末|年末)余额前五名的预付款项?情况|余额前五名的预付款项')
long_term_borrowing_parent_start_pattern = re.compile(r'\d{1,2}、?\s*预付款项')
long_term_borrowing_end_pattern = re.compile(
    r'其他说明|其他应收款|存货')
# 应付利息
interest_payable_start_pattern = re.compile(
    r'按预付对象归集的(期末|年末)余额前五名的预付款项?情况|余额前五名的预付款项')
interest_payable_parent_start_pattern = re.compile(r'\d{1,2}、?\s*预付款项')
interest_payable_end_pattern = re.compile(
    r'其他说明|其他应收款|存货')

