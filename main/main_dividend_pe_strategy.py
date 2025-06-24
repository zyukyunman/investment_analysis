"""
main/main_dividend_pe_strategy.py
基于最新成分股，运行PE和股息率综合排名选股策略的主流程。
"""
import os
import sys
import pandas as pd
import argparse

# 将项目根目录添加到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import common.config as config
from updater import updater_stock, updater_index_constituents
from visualizer import calculator_dividend_pe

def find_latest_constituents_file(index_code):
    """在数据目录中查找最新的指数成分股文件"""
    data_dir = os.path.join(config.DATA_AUTO_UPDATE_DIR, 'index_constituents', index_code)
    if not os.path.exists(data_dir):
        print(f"错误：找不到指数 {index_code} 的成分股数据目录: {data_dir}")
        return None

    files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    if not files:
        print(f"错误：在目录 {data_dir} 中没有找到任何成分股文件。")
        return None

    # 文件名即为日期，直接排序即可找到最新的
    latest_file = sorted(files, reverse=True)[0]
    return os.path.join(data_dir, latest_file)

def get_stock_codes_from_file(file_path):
    """从给定的CSV文件中读取成分股代码列表"""
    try:
        df = pd.read_csv(file_path)
        if 'con_code' not in df.columns:
            print(f"错误：文件 {file_path} 中缺少 'con_code' 列。")
            return []
        return df['con_code'].tolist()
    except Exception as e:
        print(f"读取文件 {file_path} 时发生错误: {e}")
        return []

def main():
    """主流程函数"""
    parser = argparse.ArgumentParser(description='运行基于最新成分股的PE和股息率选股策略')
    parser.add_argument('--index_code', type=str, default='h30269.CSI', help='要分析的目标指数代码')
    parser.add_argument('--force', action='store_true', help='强制全量更新所有成分股的股票数据')
    parser.add_argument('--force_index', action='store_true', help='强制更新指数成分股数据')
    args = parser.parse_args()

    # 如果指定了force参数，临时覆盖配置文件中的设置
    if args.force:
        config.FORCE_FULL_DATA_REFRESH = True
    if args.force_index:
        # 如果强制更新指数，也需要将主刷新开关打开
        config.FORCE_FULL_DATA_REFRESH = True

    print(f"--- 开始执行 {args.index_code} 指数的双因子选股策略 ---")

    # 0. 首先更新指数成分股数据
    print("\n--- (步骤 0/3) 更新指数成分股列表 ---")
    updater_index_constituents.fetch_and_save_constituents_by_year(args.index_code)
    print("--- 指数成分股列表更新完成 ---")

    # 1. 找到并读取最新的成分股文件
    print("\n--- (步骤 1/3) 查找并读取最新的成分股文件 ---")
    latest_file = find_latest_constituents_file(args.index_code)
    if not latest_file:
        print("任务终止，因为找不到最新的成分股文件。")
        return
    print(f"使用最新的成分股文件: {latest_file}")
    
    stock_codes = get_stock_codes_from_file(latest_file)
    if not stock_codes:
        print("任务终止，因为无法从文件中获取成分股列表。")
        return
    print(f"成功从文件中获取 {len(stock_codes)} 只成分股。")

    # 2. 更新所有成分股的股票数据
    print("\n--- (步骤 2/3) 批量更新成分股的股票数据 ---")
    total_stocks = len(stock_codes)
    for i, code in enumerate(stock_codes):
        # 核心修正：在传入config前，去除代码自身的后缀
        code_numeric = str(code).split('.')[0]
        
        print(f"  ({i + 1}/{total_stocks}) 准备更新股票: {code} (使用纯数字ID: {code_numeric})")
        # 通过config模块设置当前要处理的股票代码
        config.set_stock_info(stock_code=code_numeric)
        # 调用不带参数的更新函数
        updater_stock.update_stock_data()
    print("--- 所有成分股数据更新完成 ---")

    # 3. 执行分析和筛选
    print("\n--- (步骤 3/3) 调用分析脚本，传入最新的成分股文件 ---")
    # 直接将最新的成分股文件路径传递给分析器，不指定日期，让其使用默认的最新日期
    calculator_dividend_pe.analyze_constituents_from_file(latest_file)

    print(f"\n--- {args.index_code} 指数的策略流程执行完毕 ---")

if __name__ == '__main__':
    main() 