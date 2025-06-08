# updater/updater_stock.py
# 负责使用 Tushare 更新个股每日历史行情及财务指标。

import os
import sys
import pandas as pd
from datetime import datetime
import argparse

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
    """获取指定股票代码的分红和送转股数据，并处理成年度映射字典"""
    print(f"正在获取 {ts_code} 的分红及送转股数据...")
    # 请求Tushare接口，获取所有分红记录
    dividend_df = pro.dividend(ts_code=ts_code, fields='end_date,cash_div_tax,stk_bo_rate,stk_co_rate,div_proc')
    print(f"获取到 {len(dividend_df)} 条原始分红记录。")

    if dividend_df.empty:
        print("未找到该股票的任何分红数据。")
        return {}

    # --- 核心整合逻辑 ---
    # 1. 数据清洗：删除end_date为空的记录，并将关键数值列的NaN填充为0
    dividend_df.dropna(subset=['end_date'], inplace=True)
    dividend_df[['cash_div_tax', 'stk_bo_rate', 'stk_co_rate']] = dividend_df[['cash_div_tax', 'stk_bo_rate', 'stk_co_rate']].fillna(0)

    # 2. 优先级处理：根据'div_proc'字段确定每个end_date唯一有效的分红方案
    # 定义优先级顺序
    proc_priority = ['实施', '股东大会通过', '预案']
    # 将div_proc转换为带有优先级的分类类型
    dividend_df['div_proc'] = pd.Categorical(dividend_df['div_proc'], categories=proc_priority, ordered=True)

    # 按end_date和方案进度排序，然后对每个end_date保留优先级最高的记录
    dividend_df.sort_values(by=['end_date', 'div_proc'], inplace=True)
    unique_dividend_df = dividend_df.drop_duplicates(subset='end_date', keep='first').copy()
    print(f"按优先级['实施' > '股东大会通过' > '预案']去重后，剩余 {len(unique_dividend_df)} 条有效分红方案。")

    if unique_dividend_df.empty:
        print("在所有记录中未找到可用的分红方案。")
        return {}
    
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
    
    print("年度分红数据聚合完成。")
    return annual_data

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
        # 重新启用分红数据获取
        print(f"将使用股票代码: {ts_code} 获取历史分红数据")
        dividend_map = _get_dividend_data(pro, ts_code)

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
        print("正在计算自定义动态股息率...")
        df['year'] = df['交易日期'].dt.year
        total_rows = len(df) # 获取总行数以便于判断最后一条记录

        def calculate_custom_dividend(row):
            # 只有在启用DEBUG模式且是最后一条记录时才打印详细日志
            is_debug_log_for_this_row = config.DEBUG_LOG_ENABLED and row.name == total_rows - 1

            # 查找上一年的分红和送转股数据
            last_year_data = dividend_map.get(row['year'] - 1)
    
            if not last_year_data:
                if is_debug_log_for_this_row:
                    print(f"  - {row['year'] - 1} 年无分红数据，动态股息率计为 0")
                return 0

            # 使用前复权收盘价作为计算基准，更为稳定
            current_price = row['开盘价(元)']

            if current_price <= 0:
                if is_debug_log_for_this_row:
                    print(f"  - 股价为0或负数，无法计算，返回0")
                return 0

            cash_div_per_share = last_year_data.get('cash_div_tax', 0)
            bonus_rate_per_share = last_year_data.get('stk_bo_rate', 0)
            conversion_rate_per_share = last_year_data.get('stk_co_rate', 0)

            # --- 核心计算 (已修正) ---
            # 静态股息率(%) = ((C / 10) / (1 + S / 10)) / P * 100
            # C (每10股派息) 对应 cash_div_for_10_shares。
            # S (每10股送转) 对应 bonus_rate_per_share + conversion_rate_per_share。
            # P (当前股价) 对应 current_price (使用前复权价)。
            share_adjustment_factor = 1.0 + (bonus_rate_per_share + conversion_rate_per_share) / 10.0
            adjusted_dividend_per_share = cash_div_per_share / share_adjustment_factor
            yield_ratio = adjusted_dividend_per_share / current_price
            final_yield_percentage = yield_ratio * 100

            if is_debug_log_for_this_row:
                print(f"  - 找到 {row['year'] - 1} 年的分红数据: {last_year_data}")
                print(f"  - (修正后)步骤1: 计算 '每股现金分红' = {cash_div_per_share:.4f}")
                print(f"  - (修正后)步骤2: 计算 '股本调整因子' = 1.0 + ({bonus_rate_per_share} + {conversion_rate_per_share}) / 10.0 = {share_adjustment_factor:.4f}")
                print(f"  - (修正后)步骤3: 计算 '调整后每股分红' = {cash_div_per_share:.4f} / {share_adjustment_factor:.4f} = {adjusted_dividend_per_share:.4f}")
                print(f"  - (修正后)步骤4: 最终计算 '自定义股息率(%)' = {adjusted_dividend_per_share:.4f} / {current_price:.2f} * 100 = {final_yield_percentage:.4f}%")
                print(f"  - --- 对比: Tushare (dv_ttm) = {row['股息率(TTM,Tushare)(%)']:.4f}%")

            return final_yield_percentage

        df['股息率(%)'] = df.apply(calculate_custom_dividend, axis=1)

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
    except Exception as e:
        print(f"更新股票 {stock_code} 数据失败: {e}")
        print("请检查股票代码是否正确，以及Tushare接口是否正常。")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='单独更新某支股票的历史数据')
    parser.add_argument('--code', type=str, help='需要更新的股票代码, 例如: 600036')
    args = parser.parse_args()
    
    # 如果命令行提供了股票代码，则使用该代码
    if args.code:
        # 在独立运行时，强制设置当前股票代码，以便config能正确返回路径
        config.set_stock_info(stock_code=args.code)
        update_stock_data()
    else:
        # 否则，使用默认配置运行
        update_stock_data() 