"""
visualizer/calculator_dividend_pe.py
负责基于PE和股息率对股票进行排名和筛选。
"""
import os
import sys
import pandas as pd
import argparse

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import common.config as config
from common import utils_ts

def get_stock_data_by_date(stock_code, date_str):
    """根据给定的日期，读取单个股票当天的或最近一个交易日的数据"""
    code_numeric = str(stock_code).split('.')[0]
    stock_info = utils_ts.get_stock_info(code_numeric)
    if stock_info.empty:
        print(f"警告：无法找到 {code_numeric} 的信息。")
        return None, None
    
    stock_name = stock_info['name'].iloc[0]
    file_path = os.path.join(config.DATA_AUTO_UPDATE_DIR, f"{code_numeric}_{stock_name}_history.csv")
    
    if not os.path.exists(file_path):
        print(f"警告：找不到数据文件: {file_path}")
        return None, None
    
    try:
        df = pd.read_csv(file_path, parse_dates=['交易日期'])
        if df.empty:
            return None, None
        
        target_date = pd.to_datetime(date_str)
        df_filtered = df[df['交易日期'] <= target_date]
        
        if df_filtered.empty:
            return None, None
        
        return df_filtered.iloc[-1], stock_name
    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        return None, None

def analyze_constituents_from_file(constituent_file_path, date_str=None):
    """
    从成分股列表文件中读取股票，查找它们各自的数据，并根据指定日期进行排名。
    """
    print(f"\\n--- 开始从成分股文件 {constituent_file_path} 中进行策略分析 ---")
    
    try:
        constituent_df = pd.read_csv(constituent_file_path)
        if 'con_code' not in constituent_df.columns:
            print(f"错误: 成分股文件 {constituent_file_path} 中缺少 'con_code' 列。")
            return
        stock_codes = constituent_df['con_code'].tolist()
    except Exception as e:
        print(f"读取成分股文件 {constituent_file_path} 失败: {e}")
        return

    if not date_str:
        date_str = pd.Timestamp.now().strftime('%Y%m%d')
        print(f"未指定日期，将使用默认最新日期 {date_str} 进行分析。")
    else:
        print(f"将使用指定日期 {date_str} 或之前最近的交易日数据进行分析。")
        
    all_stocks_data = []
    for code in stock_codes:
        data_on_date, stock_name = get_stock_data_by_date(code, date_str)
        
        if (data_on_date is not None and 
            pd.notna(data_on_date['PE市盈率(TTM)']) and 
            pd.notna(data_on_date['股息率(%)'])):
            
            data_dict = data_on_date.to_dict()
            data_dict['ts_code'] = code
            data_dict['名称'] = stock_name
            all_stocks_data.append(data_dict)

    if not all_stocks_data:
        print("错误：未能从任何成分股中收集到有效的基本面数据。")
        return

    df_final = pd.DataFrame(all_stocks_data)
    
    # --- 后续的打分、排名逻辑，都基于 df_final 进行 ---
    # 1. PE市盈率(TTM)排名
    df_pe_positive = df_final[df_final['PE市盈率(TTM)'] > 0].copy()
    df_pe_positive = df_pe_positive.sort_values(by='PE市盈率(TTM)', ascending=False)
    df_pe_positive['pe_score'] = range(1, len(df_pe_positive) + 1)

    # 2. 股息率(%)排名
    df_dividend = df_final.copy()
    df_dividend = df_dividend.sort_values(by='股息率(%)', ascending=True)
    df_dividend['dividend_score'] = range(1, len(df_dividend) + 1)
    
    # 3. 合并分数
    df_final = pd.merge(df_final, df_pe_positive[['ts_code', 'pe_score']], on='ts_code', how='left')
    df_final = pd.merge(df_final, df_dividend[['ts_code', 'dividend_score']], on='ts_code', how='left')
    df_final['pe_score'].fillna(0, inplace=True)
    
    # 4. 计算总分并排序
    df_final['total_score'] = df_final['pe_score'] + df_final['dividend_score']
    df_sorted = df_final.sort_values(by='total_score', ascending=False)
    
    # 核心修改：不再只选取前10名，而是使用完整的、排序后的DataFrame
    full_ranked_portfolio = df_sorted
    
    # 6. 保存结果
    output_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'portfolio_dividend_pe_full_rank.csv')
    
    # 选择要输出的列
    output_columns = [
        'ts_code', '名称', '交易日期', 'PE市盈率(TTM)', '股息率(%)', 
        'pe_score', 'dividend_score', 'total_score'
    ]
    
    # 核心修改：确保使用完整的DataFrame进行输出
    full_ranked_portfolio_output = full_ranked_portfolio[[col for col in output_columns if col in full_ranked_portfolio.columns]]
    full_ranked_portfolio_output.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"--- 分析完成！所有股票的完整排名已保存至: {output_file} ---")
    print("最终股票组合完整排名如下:")
    print(full_ranked_portfolio_output.to_string(index=False))

def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='从成分股列表文件筛选股票组合')
    parser.add_argument('--file', type=str, required=True, help='包含成分股列表的CSV文件路径')
    parser.add_argument('--date', type=str, help='可选的分析日期 (YYYYMMDD)，如果未提供，则使用最新日期。')
    args = parser.parse_args()

    analyze_constituents_from_file(args.file, args.date)

if __name__ == '__main__':
    main() 