# updater/updater_stock.py
# 负责使用 Tushare 更新个股每日历史行情及财务指标。

import os
import sys
import pandas as pd
from datetime import datetime
import argparse
import talib
import subprocess

# 将项目根目录添加到Python路径，以便跨目录调用模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import utils_ts
import common.config as config
from common.utils import check_if_update_should_be_skipped

def _get_tushare_data(pro, ts_code, start_date):
    """从Tushare获取所有需要的原始数据"""
    print(f"正在通过 Tushare 获取 {ts_code} 的各项数据...")
    
    end_date = datetime.now().strftime('%Y%m%d')
    ma_params = [20, 51, 120, 250]

    df_daily = utils_ts.get_pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, asset='E', freq='D', ma=ma_params)
    df_qfq = utils_ts.get_pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, asset='E', freq='D', adj='qfq')
    df_hfq = utils_ts.get_pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, asset='E', freq='D', adj='hfq')
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
    """获取并处理分红数据，返回聚合后的年度数据、年度定稿标记和季度数据。"""
    print("  - 正在通过 Tushare SDK 获取原始分红数据...")
    try:
        # 尝试获取所有历史分红数据
        dividend_df = pro.dividend(ts_code=ts_code)
        print(f"  - 成功获取 {len(dividend_df)} 条原始分红记录。")
    except Exception as e:
        print(f"  - 调用 Tushare dividend 接口失败: {e}")
        return {}, {}, {}

    if dividend_df.empty:
        print("未找到该股票的任何分红数据。")
        return {}, {}, {}

    # --- 核心整合逻辑 ---
    # 1. 筛选和清洗
    # 只保留必要的字段，并过滤掉没有实际分红或送转的记录
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
    
    # 2. 按方案进度设置优先级 (重要逻辑)
    proc_priority = ['实施', '股东大会通过', '预案', '预披露']
    # 将div_proc转换为带有优先级的分类类型
    dividend_df['div_proc'] = pd.Categorical(dividend_df['div_proc'], categories=proc_priority, ordered=True)

    # 按end_date和方案进度排序，然后对每个end_date保留优先级最高的记录
    dividend_df.sort_values(by=['end_date', 'div_proc'], inplace=True)
    unique_dividend_df = dividend_df.drop_duplicates(subset='end_date', keep='first').copy()
    print(f"按优先级['实施' > '股东大会通过' > '预案' > '预披露']去重后，剩余 {len(unique_dividend_df)} 条有效分红方案。")

    if unique_dividend_df.empty:
        print("在所有记录中未找到可用的分红方案。")
        return {}, {}, {}
    
    # --- 检查每个分红年度是否包含年末(12-30或12-31)的记录，这标志着年报分红 ---
    has_year_end_dividend = {}
    # 先将end_date转为datetime，以提取年份
    unique_dividend_df['end_date_dt'] = pd.to_datetime(unique_dividend_df['end_date'])
    unique_dividend_df['year'] = unique_dividend_df['end_date_dt'].dt.year

    # 检查每个年份是否有以 '1231' 或 '1230' 结尾的end_date (Tushare返回的是YYYYMMDD字符串)
    year_end_records = unique_dividend_df[
        unique_dividend_df['end_date'].str.endswith('1231') |
        unique_dividend_df['end_date'].str.endswith('1230')
    ]
    finalized_years = set(year_end_records['year'].unique())

    all_years = unique_dividend_df['year'].unique()
    for year in all_years:
        has_year_end_dividend[year] = year in finalized_years

    # 3. 年度聚合：将同一年份的多次分红（如中报、年报）合并
    # 将end_date转换为datetime对象，以便按年份分组
    unique_dividend_df['end_date'] = pd.to_datetime(unique_dividend_df['end_date'])
    
    # 按年份对所有数据进行聚合
    # 每个字段都取当年的总和
    annual_data = unique_dividend_df.groupby(unique_dividend_df['end_date'].dt.year).agg({
        'cash_div_tax': 'sum',
        'stk_bo_rate': 'sum',
        'stk_co_rate': 'sum'
    }).to_dict('index') # 'index'使得结果是 {year: {field: value}} 的形式
    
    # --- 为方法二准备数据：按年和季度聚合，保留最高优先级的记录 ---
    # 1. 识别季度
    # Tushare的end_date月份通常是 03, 06, 09, 12，分别对应Q1, Q2, Q3, Q4(年报)
    unique_dividend_df['quarter'] = unique_dividend_df['end_date_dt'].dt.month.apply(lambda m: m // 3)
    
    # 2. 按年、季度、优先级排序，然后为每个季度保留唯一记录
    quarterly_unique_df = unique_dividend_df.sort_values(
        by=['year', 'quarter', 'div_proc'], 
        ascending=[True, True, True] # proc的category类型已定义优先级
    ).drop_duplicates(subset=['year', 'quarter'], keep='first')

    # 3. 转换为更易于查询的字典格式: {year: {quarter: data}}
    quarterly_data = {}
    for _, row in quarterly_unique_df.iterrows():
        year = row['year']
        quarter = row['quarter']
        if year not in quarterly_data:
            quarterly_data[year] = {}
        quarterly_data[year][quarter] = {
            'cash_div_tax': row['cash_div_tax'],
            'stk_bo_rate': row['stk_bo_rate'],
            'stk_co_rate': row['stk_co_rate']
        }
    
    print("年度和季度分红数据聚合完成。")
    return annual_data, has_year_end_dividend, quarterly_data

def update_stock_data():
    """主函数：更新个股历史数据"""
    print("\n--- 开始使用 Tushare 更新个股每日历史数据 ---")
    stock_code = config.get_stock_code()
    output_file = config.get_stock_history_csv()
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # --- 调用通用工具函数检查是否需要更新 ---
    if check_if_update_should_be_skipped(
        file_path=output_file,
        date_column_name='交易日期',
        force_refresh_flag=config.FORCE_FULL_DATA_REFRESH
    ):
        return # 如果通用函数决定跳过，则直接退出

    pro = utils_ts.initialize_tushare()
    if not pro:
        print("Tushare 初始化失败，更新任务终止。")
        return
        
    # 使用utils_ts中的函数将股票代码转换为Tushare格式
    ts_code = utils_ts.convert_to_ts_code(stock_code)
    
    # 从配置的起始日期开始获取
    start_date = config.DATA_START_DATE.replace('-', '')
    
    try:
        # 获取原始数据和均线参数
        print(f"将使用股票代码: {ts_code} 获取历史行情数据")
        df, ma_params = _get_tushare_data(pro, ts_code, start_date)

        print("正在处理和丰富数据...")
        
        # --- 第一步：列重命名与选择 (先塑形) ---
        rename_map = {
            # 核心行情数据 (来自pro_bar)
            'trade_date': '交易日期', 'open': '开盘价(元)', 'high': '最高价(元)', 'low': '最低价(元)',
            'close_daily': '收盘价(元)', 
            'change': '涨跌(元)',
            'pct_chg': '涨跌幅(%)',
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
        # 仅计算均线，股息率计算已移至 calculator_dividend.py
        print("正在计算技术指标：MA均线...")
        for p in ma_params:
            df[f'MA{p}'] = talib.MA(df['收盘价(元)'], timeperiod=p)
            df[f'MA{p}'] = df[f'MA{p}'].round(4)
        print("均线计算完成。")

        # --- 第三步：最终列选择与排序 (定型) ---
        # 按照逻辑关系重新组织所有列的顺序，方便查看
        final_columns = [
            # 核心行情
            '交易日期', '开盘价(元)', '最高价(元)', '最低价(元)', '收盘价(元)', 
            '涨跌(元)', '涨跌幅(%)',
            '成交量(手)', '成交额(千元)',
            '收盘价(前复权)(元)', '收盘价(后复权)(元)',
            
            # 换手率与量比
            '换手率(%)', '换手率(自由流通)(%)', '量比',

            # 估值指标
            'PE市盈率', 'PE市盈率(TTM)', 'PB市净率', 'PS市销率', 'PS市销率(TTM)',

            # 股本与市值
            '总股本(万股)', '流通股本(万股)', '自由流通股本(万股)',
            '总市值(万元)', '流通市值(万元)',

            # 分红与股息率 (自定义的股息率将由 calculator_dividend.py 添加)
            '股息率(Tushare)(%)',
            '股息率(TTM,Tushare)(%)',
        ]
        
        # 将均线列加入到最终列名列表
        ma_cols = [f'MA{p}' for p in ma_params]
        final_columns.extend(ma_cols)

        # 整理最终列顺序
        final_df = df[[col for col in final_columns if col in df.columns]]
        
        final_df.to_csv(output_file, index=False, encoding='utf-8-sig', float_format='%.4f')

        print("-" * 30)
        print(f"个股基础历史数据更新完成！总共 {len(final_df)} 条记录。")
        print(f"数据已保存至: {output_file}")
        print("-" * 30)

        # --- 第四步：调用独立脚本计算股息率 ---
        print("\n--- 开始调用独立脚本计算自定义股息率 ---")
        script_path = os.path.join(os.path.dirname(__file__), 'calculator_dividend.py')
        try:
            # 使用 subprocess.run 来执行脚本，并捕获输出
            result = subprocess.run(
                ['python', script_path, '--code', stock_code],
                check=True, # 如果脚本返回非0退出码，则抛出异常
                capture_output=True, # 捕获标准输出和标准错误
                text=True, # 以文本模式处理输出
                encoding='utf-8'
            )
            print("股息率计算脚本执行成功。")
            print("脚本输出:\n" + result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"股息率计算脚本执行失败，返回码: {e.returncode}")
            print("错误信息:\n" + e.stderr)
        except FileNotFoundError:
            print(f"错误：找不到股息率计算脚本: {script_path}")

    except Exception as e:
        print(f"更新股票 {stock_code} 数据失败: {e}")
        print("请检查股票代码是否正确，以及Tushare接口是否正常。")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='单独更新某支股票的历史数据')
    parser.add_argument('--code', type=str, help='需要更新的股票代码, 例如: 600036')
    parser.add_argument('--force', action='store_true', help='强制刷新，忽略已有的数据和更新日期检查')
    args = parser.parse_args()
    
    # 如果命令行提供了强制刷新标志，则设置全局配置
    if args.force:
        config.FORCE_FULL_DATA_REFRESH = True
        print("--- 检测到 --force 参数，将强制刷新全部数据 ---")

    # 如果命令行提供了股票代码，则使用该代码
    if args.code:
        # 在独立运行时，强制设置当前股票代码，以便config能正确返回路径
        config.set_stock_info(stock_code=args.code)
        update_stock_data()
    else:
        # 否则，使用默认配置运行
        print("未指定股票代码，将使用 config.py 中的默认设置。")
        update_stock_data() 