# updater/updater_stock.py
# 负责使用 Tushare 更新个股每日历史行情及财务指标。

import os
import sys
import pandas as pd
from datetime import datetime
import tushare as ts
import common.config as config
from common.utils import check_if_update_should_be_skipped

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _initialize_tushare():
    """使用config中的token初始化tushare"""
    if config.TUSHARE_TOKEN == 'your_token_here' or not config.TUSHARE_TOKEN:
        raise ValueError("Tushare token 未在 config.py 中配置。请前往 https://tushare.pro/user/token 获取。")
    ts.set_token(config.TUSHARE_TOKEN)
    return ts.pro_api()

def _get_tushare_data(pro, ts_code, start_date):
    """从Tushare获取所有需要的原始数据"""
    print(f"正在通过 Tushare 获取 {ts_code} 的各项数据...")
    
    end_date = datetime.now().strftime('%Y%m%d')
    ma_params = [20, 51, 120, 250]

    df_daily = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, asset='E', freq='D', ma=ma_params)
    df_qfq = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, asset='E', freq='D', adj='qfq')
    df_hfq = ts.pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, asset='E', freq='D', adj='hfq')
    df_basic = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)

    print("正在合并 Tushare 数据...")
    
    # --- 核心修复：在合并前，预先重命名有冲突的列 ---
    df_daily.rename(columns={'close': 'close_daily'}, inplace=True)
    df_qfq.rename(columns={'close': 'close_qfq'}, inplace=True)
    df_hfq.rename(columns={'close': 'close_hfq'}, inplace=True)

    # 合并复权价格
    merged_df = pd.merge(df_daily, 
                         df_qfq[['trade_date', 'close_qfq']], 
                         on='trade_date')
    merged_df = pd.merge(merged_df, 
                         df_hfq[['trade_date', 'close_hfq']], 
                         on='trade_date')

    # --- 最终修复：在合并财务数据前，删除df_basic中会引起冲突的多余列 ---
    if 'close' in df_basic.columns and 'ts_code' in df_basic.columns:
        df_basic.drop(columns=['close', 'ts_code'], inplace=True)

    # 合并财务指标
    merged_df = pd.merge(merged_df, df_basic, on='trade_date')
    
    merged_df['trade_date'] = pd.to_datetime(merged_df['trade_date'])
    # 返回原始数据和均线参数，以便后续使用
    return merged_df.sort_values(by='trade_date').reset_index(drop=True), ma_params

def _get_dividend_data(pro, ts_code):
    """获取指定股票代码的分红和送转股数据，并处理成年度映射字典"""
    print(f"正在获取 {ts_code} 的分红及送转股数据...")
    # 请求包含分红、送股、转股以及【实施进度】的字段
    dividend_df = pro.dividend(ts_code=ts_code, fields='end_date,cash_div_tax,stk_bo_rate,stk_co_rate,div_proc')
    
    # --- 核心修改：只保留已经"实施"的分红方案 ---
    print(f"获取到 {len(dividend_df)} 条分红记录，将按'实施'状态进行过滤...")
    dividend_df = dividend_df[dividend_df['div_proc'] == '实施'].copy()
    print(f"过滤后剩余 {len(dividend_df)} 条已实施记录。")

    dividend_df.dropna(subset=['end_date', 'cash_div_tax'], inplace=True)
    
    if dividend_df.empty:
        print("未找到该股票【已实施】的分红数据。")
        return {}

    # 将所有缺失的送转股比例填充为0
    dividend_df[['stk_bo_rate', 'stk_co_rate']] = dividend_df[['stk_bo_rate', 'stk_co_rate']].fillna(0)
    
    # 将end_date转换为datetime对象，以便按年份分组
    dividend_df['end_date'] = pd.to_datetime(dividend_df['end_date'])
    
    # 按年份对所有数据进行聚合
    # 每个字段都取当年的总和（对于分红和送转，通常一年只有一次，sum是安全的）
    annual_data = dividend_df.groupby(dividend_df['end_date'].dt.year).agg({
        'cash_div_tax': 'sum',
        'stk_bo_rate': 'sum',
        'stk_co_rate': 'sum'
    }).to_dict('index') # 'index'使得结果是 {year: {field: value}} 的形式
    
    return annual_data

def update_stock_data():
    """主函数：更新个股历史数据"""
    print("\n--- 开始使用 Tushare 更新个股每日历史数据 ---")
    stock_code = config.STOCK_CODE
    output_file = config.STOCK_HISTORY_CSV
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # --- 调用通用工具函数检查是否需要更新 ---
    if check_if_update_should_be_skipped(
        file_path=output_file,
        date_column_name='交易日期',
        force_refresh_flag=config.FORCE_FULL_DATA_REFRESH
    ):
        return # 如果通用函数决定跳过，则直接退出

    pro = _initialize_tushare()
    if not pro:
        print("Tushare 初始化失败，更新任务终止。")
        return
        
    ts_code = f"{stock_code}.SH" if stock_code.startswith('6') else f"{stock_code}.SZ"
    
    # 从配置的起始日期开始获取
    start_date = config.DATA_START_DATE.replace('-', '')
    
    # 获取原始数据和均线参数
    df, ma_params = _get_tushare_data(pro, ts_code, start_date)
    dividend_map = _get_dividend_data(pro, ts_code)

    print("正在处理和丰富数据...")
    
    # --- 第一步：列重命名与选择 (先塑形) ---
    rename_map = {
        # 核心行情数据 (来自pro_bar)
        'trade_date': '交易日期', 'open': '开盘价(元)', 'high': '最高价(元)', 'low': '最低价(元)',
        'close_daily': '收盘价(元)', 
        'close_qfq': '收盘价(前复权)(元)', 
        'close_hfq': '收盘价(后复权)(元)',
        'vol': '成交量(手)', 'amount': '成交额(千元)',
        
        # 每日基本指标 (来自daily_basic)
        'turnover_rate': '换手率(%)',
        'turnover_rate_f': '换手率(自由流通)(%)',
        'volume_ratio': '量比',
        'pe': 'PE市盈率', 
        'pe_ttm': 'PE市盈率(TTM)',
        'pb': 'PB市净率', 
        'ps': 'PS市销率',
        'ps_ttm': 'PS市销率(TTM)',
        'dv_ratio': '股息率(Tushare)(%)',
        'dv_ttm': '股息率(TTM,Tushare)(%)',
        'total_share': '总股本(万股)',
        'float_share': '流通股本(万股)',
        'free_share': '自由流通股本(万股)',
        'total_mv': '总市值(万元)',
        'circ_mv': '流通市值(万元)'
    }
    df.rename(columns=rename_map, inplace=True)

    # --- 第二步：数据计算与衍生 (再创造) ---
    print("正在计算动态股息率...")
    df['year'] = df['交易日期'].dt.year
    
    def calculate_dynamic_dividend(row):
        # 查找上一年的分红和送转股数据
        last_year_data = dividend_map.get(row['year'] - 1)
        if not last_year_data:
            return 0
            
        # --- 数据提取 (根据Tushare官方文档的正确单位) ---
        cash_div_for_10_shares = last_year_data.get('cash_div_tax', 0)
        bonus_rate_per_share = last_year_data.get('stk_bo_rate', 0)
        conversion_rate_per_share = last_year_data.get('stk_co_rate', 0)
        current_price = row['收盘价(前复权)(元)']
        
        if current_price <= 0:
            return 0

        # --- 核心计算 (严格按照您提供的公式结构) ---
        # 公式: 股息率 = 每股分红 / (10 + 10 * (赠股比例 + 转股比例)) / 股价
        
        # 1. 计算 "每股分红"
        dividend_per_share = cash_div_for_10_shares * 10

        # 2. 计算公式中的分母部分: (10 + 10 * (赠股比例 + 转股比例))
        #    这里 `bonus_rate_per_share` 是每股赠股, `conversion_rate_per_share` 是每股转股
        denominator_part = 10 + 10 * (bonus_rate_per_share + conversion_rate_per_share)
        
        if denominator_part <= 0:
            return 0

        # 3. 严格按照您的公式进行计算
        #    注意: A / B / C 在数学上等于 A / (B * C)
        yield_ratio = (dividend_per_share / denominator_part) / current_price
        
        # 返回百分比
        return yield_ratio * 100

    df['股息率(%)'] = df.apply(calculate_dynamic_dividend, axis=1)

    # 计算涨跌幅
    df['涨跌(元)'] = df['收盘价(元)'].diff()
    df['涨跌幅(%)'] = df['收盘价(元)'].pct_change() * 100

    # --- 第三步：最终列选择与排序 (定型) ---
    # 按照逻辑关系重新组织所有列的顺序，方便查看
    final_columns = [
        # 核心行情
        '交易日期', '开盘价(元)', '最高价(元)', '最低价(元)', '收盘价(元)', '成交量(手)', '成交额(千元)',
        '收盘价(前复权)(元)', '收盘价(后复权)(元)',
        
        # 换手率与量比
        '换手率(%)', '换手率(自由流通)(%)', '量比',

        # 估值指标
        'PE市盈率', 'PE市盈率(TTM)', 'PB市净率', 'PS市销率', 'PS市销率(TTM)',

        # 股本与市值
        '总股本(万股)', '流通股本(万股)', '自由流通股本(万股)',
        '总市值(万元)', '流通市值(万元)',

        # 分红与股息率
        '股息率(Tushare)(%)',
        '股息率(TTM,Tushare)(%)',
        '股息率(%)',
    ]
    
    # 将均线列加入到最终列名列表
    ma_cols = [f'MA{p}' for p in ma_params]
    final_columns.extend(ma_cols)

    # 整理最终列顺序
    final_df = df[[col for col in final_columns if col in df.columns]]
    
    final_df.to_csv(output_file, index=False, encoding='utf-8-sig', float_format='%.4f')

    print("-" * 30)
    print(f"个股历史数据更新完成！总共 {len(final_df)} 条记录。")
    print(f"数据已保存至: {output_file}")
    print("-" * 30)

if __name__ == '__main__':
    update_stock_data() 