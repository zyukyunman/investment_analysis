"""
updater/updater_index_constituents.py
负责按年度获取和保存指数的成分股数据。
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import argparse

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import utils_ts
import common.config as config

def fetch_and_save_constituents_by_year(index_code):
    """
    获取指定指数历年的年终成分股，以及最新一个月的成分股，并保存为CSV文件。
    """
    print(f"--- 开始获取指数 {index_code} 的成分股数据 ---")
    
    # 创建数据输出目录
    output_dir = os.path.join(config.DATA_AUTO_UPDATE_DIR, 'index_constituents', index_code)
    os.makedirs(output_dir, exist_ok=True)
    print(f"数据将保存在: {output_dir}")

    ts_pro = utils_ts.initialize_tushare()
    if not ts_pro:
        print("Tushare API 初始化失败，任务终止。")
        return

    # 1. 获取历年年终的成分股数据
    print("\n--- 开始获取历年年终的成分股数据 ---")
    start_year = int(config.DATA_START_DATE.split('-')[0])
    current_year = datetime.now().year

    for year in range(start_year, current_year): # 循环到去年为止
        # 输出文件名始终是YYYY1231.csv
        output_file = os.path.join(output_dir, f"{year}1231.csv")
        
        # 如果文件已存在且不是强制刷新模式，则跳过
        if not config.FORCE_FULL_DATA_REFRESH and os.path.exists(output_file):
            print(f"数据文件 {output_file} 已存在，跳过。")
            continue

        df = pd.DataFrame()
        # 按照您的要求，优先尝试1231，失败则尝试1230
        dates_to_try = [f"{year}1231", f"{year}1230"]
        
        for trade_date in dates_to_try:
            print(f"正在尝试获取 {trade_date} 的成分股数据...")
            try:
                # Tushare的index_weight接口是月度数据，查询年底日期可以获取到当年12月的成分股情况
                df_temp = ts_pro.index_weight(index_code=index_code, trade_date=trade_date)
                if not df_temp.empty:
                    df = df_temp
                    print(f"成功获取到 {trade_date} 的成分股数据。")
                    break  # 成功获取数据，跳出循环
            except Exception as e:
                print(f"获取 {trade_date} 成分股数据时发生错误: {e}")
        
        if df.empty:
            print(f"在 {year} 年底（1231或1230）未找到 {index_code} 的成分股数据。")
            continue
            
        # 保存数据
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"成功保存 {len(df)} 条成分股数据至: {output_file}")

    # 2. 获取最新一个月的成分股数据
    print("\n--- 开始获取最新月份的成分股数据 ---")
    today = datetime.now()
    first_day_of_current_month = today.replace(day=1)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)

    df_latest = pd.DataFrame()
    # 为应对节假日，从上月末开始往前尝试5天
    for i in range(5):
        date_to_try = last_day_of_previous_month - timedelta(days=i)
        date_str = date_to_try.strftime('%Y%m%d')
        print(f"正在尝试获取最新数据，日期: {date_str}...")
        try:
            df_temp = ts_pro.index_weight(index_code=index_code, trade_date=date_str)
            if not df_temp.empty:
                df_latest = df_temp
                print(f"成功获取到 {date_str} 的最新成分股数据。")
                break
        except Exception as e:
            print(f"获取 {date_str} 成分股数据时发生错误: {e}")

    if not df_latest.empty:
        # 使用数据中真实的交易日期来命名文件，确保准确性
        latest_trade_date = df_latest['trade_date'].iloc[0]
        output_file_latest = os.path.join(output_dir, f"{latest_trade_date}.csv")

        if not config.FORCE_FULL_DATA_REFRESH and os.path.exists(output_file_latest):
            print(f"最新的数据文件 {output_file_latest} 已存在，跳过。")
        else:
            df_latest.to_csv(output_file_latest, index=False, encoding='utf-8-sig')
            print(f"成功保存 {len(df_latest)} 条最新成分股数据至: {output_file_latest}")
    else:
        print("未能获取到最新月份的成分股数据。")

    print(f"\n--- 指数 {index_code} 的成分股更新完成 ---")


def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='获取指数的年度成分股数据')
    parser.add_argument('--index_code', type=str, default='h30269.CSI', help='要获取的目标指数代码')
    parser.add_argument('--force', action='store_true', help='强制全量更新所有数据')
    args = parser.parse_args()

    if args.force:
        config.FORCE_FULL_DATA_REFRESH = True

    fetch_and_save_constituents_by_year(args.index_code)

if __name__ == '__main__':
    main() 