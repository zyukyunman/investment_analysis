"""
独立计算指定股票的自定义股息率指标。

该脚本会读取已有的个股历史数据文件，重新计算或添加自定义的股息率列，
然后覆盖保存原文件。

设计目的：
- 将复杂的股息率计算与基础数据下载解耦。
- 方便针对股息率计算逻辑进行独立的调试、验证和回测，无需每次都重新下载基础行情数据。

用法：
python updater/calculator_dividend.py --code 600036
python updater/calculator_dividend.py --dir ./data/stock/history
"""

import os
import sys
import argparse
import pandas as pd

# 将项目根目录添加到Python路径，以便跨目录调用模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# 确保common目录在路径中，以便导入
from common import utils_ts, config

def _get_dividend_data(pro, ts_code):
    """获取并处理分红数据，返回聚合后的年度数据、年度定稿标记和季度数据。"""
    print("  - 正在通过 Tushare SDK 获取原始分红数据...")
    try:
        dividend_df = pro.dividend(ts_code=ts_code)
        print(f"  - 成功获取 {len(dividend_df)} 条原始分红记录。")
    except Exception as e:
        print(f"  - 调用 Tushare dividend 接口失败: {e}")
        return {}, {}, {}

    if dividend_df.empty:
        print("未找到该股票的任何分红数据。")
        return {}, {}, {}

    required_cols = ['end_date', 'div_proc', 'cash_div_tax', 'stk_bo_rate', 'stk_co_rate']
    dividend_df = dividend_df[required_cols].dropna(subset=['end_date'])
    dividend_df = dividend_df[
        (dividend_df['cash_div_tax'] > 0) | 
        (dividend_df['stk_bo_rate'] > 0) | 
        (dividend_df['stk_co_rate'] > 0)
    ]
    if dividend_df.empty:
        print("过滤后无有效的(有金额/比例的)分红方案。")
        return {}, {}, {}
    
    proc_priority = ['实施', '股东大会通过', '预案', '预披露']
    dividend_df['div_proc'] = pd.Categorical(dividend_df['div_proc'], categories=proc_priority, ordered=True)
    dividend_df.sort_values(by=['end_date', 'div_proc'], inplace=True)
    unique_dividend_df = dividend_df.drop_duplicates(subset='end_date', keep='first').copy()
    
    # --- 数据清洗：将所有分红和送转中的None/NaN值替换为0，避免计算错误 ---
    unique_dividend_df[['cash_div_tax', 'stk_bo_rate', 'stk_co_rate']] = unique_dividend_df[['cash_div_tax', 'stk_bo_rate', 'stk_co_rate']].fillna(0)

    if unique_dividend_df.empty:
        print("在所有记录中未找到可用的分红方案。")
        return {}, {}, {}

    unique_dividend_df['end_date_dt'] = pd.to_datetime(unique_dividend_df['end_date'])
    unique_dividend_df['year'] = unique_dividend_df['end_date_dt'].dt.year

    year_end_records = unique_dividend_df[
        unique_dividend_df['end_date'].str.endswith('1231') |
        unique_dividend_df['end_date'].str.endswith('1230')
    ]
    finalized_years = set(year_end_records['year'].unique())
    has_year_end_dividend = {year: year in finalized_years for year in unique_dividend_df['year'].unique()}

    annual_data = unique_dividend_df.groupby('year').agg({
        'cash_div_tax': 'sum',
        'stk_bo_rate': 'sum',
        'stk_co_rate': 'sum'
    }).to_dict('index')

    unique_dividend_df['quarter'] = unique_dividend_df['end_date_dt'].dt.month.apply(lambda m: (m - 1) // 3 + 1)
    quarterly_unique_df = unique_dividend_df.sort_values(
        by=['year', 'quarter', 'div_proc']
    ).drop_duplicates(subset=['year', 'quarter'], keep='first')
    
    quarterly_data = {}
    for _, row in quarterly_unique_df.iterrows():
        year = row['year']
        quarter = row['quarter']
        if year not in quarterly_data:
            quarterly_data[year] = {}
        # 数据清洗已在上游完成，这里直接赋值
        quarterly_data[year][quarter] = {
            'cash_div_tax': row['cash_div_tax'],
            'stk_bo_rate': row['stk_bo_rate'],
            'stk_co_rate': row['stk_co_rate']
        }
    
    return annual_data, has_year_end_dividend, quarterly_data

def calculate_and_update_dividends(stock_code, history_file):
    """为指定股票代码计算并更新股息率列。"""
    print(f"\n--- 开始为 {stock_code} 计算自定义股息率 (文件: {history_file}) ---")
    
    if not os.path.exists(history_file):
        print(f"错误：历史数据文件不存在: {history_file}")
        return

    df = pd.read_csv(history_file)
    if df.empty:
        print(f"警告: 历史数据文件为空: {history_file}")
        return
        
    df['交易日期'] = pd.to_datetime(df['交易日期'])
    print(f"成功读取 {len(df)} 条历史数据。")

    if '股息率(%)' not in df.columns: df['股息率(%)'] = 0.0
    if '股息率(S2-滚动累计)(%)' not in df.columns: df['股息率(S2-滚动累计)(%)'] = 0.0

    pro = utils_ts.initialize_tushare()
    if not pro: return
        
    ts_code = utils_ts.convert_to_ts_code(stock_code)
    dividend_map, yearly_finalized_flags, quarterly_dividend_map = _get_dividend_data(pro, ts_code)

    if not dividend_map:
        print("未获取到有效分红数据，跳过计算。")
        df.to_csv(history_file, index=False, encoding='utf-8-sig', float_format='%.4f')
        return

    def calculate_yield_core(dividend_data, current_price):
        if not dividend_data or current_price <= 0: return 0
        cash = dividend_data.get('cash_div_tax', 0)
        stk = dividend_data.get('stk_bo_rate', 0) + dividend_data.get('stk_co_rate', 0)
        adj_factor = 1.0 + stk / 10.0
        if adj_factor == 0: return 0
        adj_div = (cash / 10.0) / adj_factor
        return (adj_div / current_price) * 100

    df['year'] = df['交易日期'].dt.year
    TODAY_YEAR = pd.Timestamp.now().year

    def calculate_dynamic_dividend(row):
        """
        方法一 (修正后 - 简单年度):
        严格使用上一年度(Y-1)的全年分红数据。
        如果上一年度无分红数据，则为0。不回溯。
        """
        previous_year = row['year'] - 1
        data_to_use = dividend_map.get(previous_year)
        return calculate_yield_core(data_to_use, row['开盘价(元)'])

    df['股息率(%)'] = df.apply(calculate_dynamic_dividend, axis=1)

    def calculate_dividend_s2(row):
        base_year = row['year'] - 1
        combined_div = {'cash_div_tax': 0, 'stk_bo_rate': 0, 'stk_co_rate': 0}
        latest_q = max(quarterly_dividend_map.get(base_year, {}).keys(), default=0)
        for q in [1, 2, 3, 4]:
            q_data = quarterly_dividend_map.get(base_year, {}).get(q)
            if not q_data and q > latest_q:
                q_data = quarterly_dividend_map.get(base_year - 1, {}).get(q)
            if q_data:
                combined_div['cash_div_tax'] += q_data.get('cash_div_tax', 0)
                combined_div['stk_bo_rate'] += q_data.get('stk_bo_rate', 0)
                combined_div['stk_co_rate'] += q_data.get('stk_co_rate', 0)
        return calculate_yield_core(combined_div, row['开盘价(元)'])
    
    df['股息率(S2-滚动累计)(%)'] = df.apply(calculate_dividend_s2, axis=1)
    
    if '股息率(TTM,Tushare)(%)' in df.columns:
        cols = df.columns.tolist()
        for col in ['股息率(%)', '股息率(S2-滚动累计)(%)']:
            if col in cols: cols.remove(col)
        
        anchor_pos = cols.index('股息率(TTM,Tushare)(%)')
        cols.insert(anchor_pos + 1, '股息率(S2-滚动累计)(%)')
        cols.insert(anchor_pos + 1, '股息率(%)')
        df = df[cols]

    df.drop(columns=['year'], inplace=True, errors='ignore')
    df.to_csv(history_file, index=False, encoding='utf-8-sig', float_format='%.4f')
    
    print("-" * 30)
    print(f"股息率计算完成！数据已更新并保存至: {history_file}")
    if not df.empty:
        last_row = df.iloc[-1]
        tushare_yield_ttm = last_row.get('股息率(TTM,Tushare)(%)')
        
        # 格式化输出，处理可能不存在或为NaN的情况
        tushare_yield_ttm_str = f"{tushare_yield_ttm:.4f}" if pd.notna(tushare_yield_ttm) else "N/A"
            
        print(f"最后一日计算结果:")
        print(f"  - Tushare TTM股息率(%): {tushare_yield_ttm_str}")
        print(f"  - 股息率(%) (方法一: 简单年度): {last_row['股息率(%)']:.4f}")
        print(f"  - S2-滚动累计(%) (方法二: 滚动季度): {last_row['股息率(S2-滚动累计)(%)']:.4f}")
    print("-" * 30)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='独立计算个股或目录中多个个股的自定义股息率',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--code', type=str, help='需要计算的单个股票代码, 例如: 600036')
    parser.add_argument('--dir', type=str, help='包含 `_history.csv` 文件的目录路径。\n脚本将遍历此目录，为所有匹配文件计算股息率。')
    args = parser.parse_args()

    if args.code and args.dir:
        print("错误: --code 和 --dir 参数不能同时使用。请只选择其中一个。")
    
    elif args.code:
        stock_code = args.code
        config.set_stock_info(stock_code=stock_code)
        history_file = config.get_stock_history_csv(stock_code)
        calculate_and_update_dividends(stock_code, history_file)

    elif args.dir:
        target_dir = args.dir
        if not os.path.isdir(target_dir):
            print(f"错误: 提供的路径不是一个有效的目录: {target_dir}")
        else:
            print(f"--- 开始扫描目录 '{target_dir}' 中的历史数据文件 ---")
            found_files = [f for f in os.listdir(target_dir) if f.endswith('_history.csv')]
            
            if not found_files:
                print("未在该目录中找到 `_history.csv` 文件。")
            
            total = len(found_files)
            for i, filename in enumerate(sorted(found_files)):
                stock_code = filename.split('_')[0]
                history_file_path = os.path.join(target_dir, filename)
                
                print(f"\n--- [{i+1}/{total}] 处理: {filename} ---")
                
                try:
                    calculate_and_update_dividends(stock_code, history_file_path)
                except Exception as e:
                    print(f"!!! 处理文件 {filename} 时发生严重错误: {e}")
                    import traceback
                    traceback.print_exc()

    else:
        parser.print_help()
        print("\n错误: 请提供 --code 或 --dir 参数中的一个。")
