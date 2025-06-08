# visualizer/calculator_spread.py
# 负责计算股债利差及其历史百分位。

import os
import sys
import pandas as pd

# 将项目根目录添加到Python路径，以便跨目录调用模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import config

def calculate_spread():
    """
    读取股票和国债数据，计算股债性价比及其历史百分位（温度计）。
    """
    print("\n--- 开始执行股债性价比计算任务 ---")

    # 1. 加载数据
    try:
        stock_df = pd.read_csv(config.get_stock_history_csv())
        treasury_df = pd.read_csv(config.TREASURY_BOND_CSV)
    except FileNotFoundError as e:
        print(f"[错误] 计算所需的数据文件不存在: {e}。请先运行数据更新脚本。")
        return

    # 2. 数据预处理和合并
    print("正在进行数据预处理和合并...")
    stock_df.rename(columns={'交易日期': 'date'}, inplace=True)
    treasury_df.rename(columns={'日期': 'date'}, inplace=True)
    stock_df['date'] = pd.to_datetime(stock_df['date'])
    treasury_df['date'] = pd.to_datetime(treasury_df['date'])
    
    # --- 核心修改1：智能单位修正 ---
    # 检查国债利率 '十年' 列是否是小数形式 (如 0.025)
    # 如果最大值小于1，我们有理由相信它是小数，需要乘以100来匹配股息率的百分比形式 (如 2.5)
    if not treasury_df['十年'].empty and treasury_df['十年'].max() < 1:
        print("检测到国债利率为小数格式，将自动乘以100进行单位统一...")
        treasury_df['十年'] = treasury_df['十年'] * 100

    stock_cols_to_keep = ['date', '收盘价(前复权)(元)', '股息率(Tushare)(%)']
    merged_df = pd.merge(stock_df[stock_cols_to_keep], treasury_df[['date', '十年']], on='date', how='inner')
    
    # 过滤掉无法计算性价比的数据
    merged_df = merged_df[(merged_df['股息率(Tushare)(%)'] > 0) & (merged_df['十年'] > 0)].copy()
    if merged_df.empty:
        print("[错误] 数据过滤后为空，无法进行计算。请检查数据源。")
        return

    # 3. 计算核心指标
    print("正在计算股债性价比和反转温度计...")
    
    # --- 核心修改2：计算股债性价比 ---
    merged_df['股债性价比'] = merged_df['股息率(Tushare)(%)'] / merged_df['十年']

    # --- 核心修改3：基于性价比，计算反转温度计 ---
    # 性价比越高，吸引力越大，温度越低 (ascending=False)
    merged_df['温度计'] = merged_df['股债性价比'].rank(pct=True, ascending=False) * 100
    
    # 4. 保存结果
    output_path = config.get_spread_analysis_csv()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    merged_df.sort_values(by='date', inplace=True)
    merged_df.to_csv(output_path, index=False, encoding='utf-8-sig', float_format='%.4f')

    print("-" * 30)
    print("股债性价比计算完成！")
    print(f"分析结果已保存至: {output_path}")
    print("-" * 30)

if __name__ == '__main__':
    calculate_spread() 