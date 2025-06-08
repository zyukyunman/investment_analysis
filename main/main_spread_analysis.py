# main/main_spread_analysis.py
# "股债利差分析"功能的总执行入口。
# 负责按顺序调用数据更新、分析计算和可视化模块。

import os
import sys

# 将项目根目录添加到Python路径，以便跨目录调用模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入需要调用的模块
from updater import updater_treasury
from updater import updater_stock
from visualizer import calculator_spread
from visualizer import visualizer_spread

def run_spread_analysis_pipeline():
    """
    执行完整的股债利差分析流程。
    """
    print("==========================================")
    print("=   开始执行股债利差分析流程...      =")
    print("==========================================")

    # --- 第1步: 更新数据 ---
    try:
        # 1.1 更新国债数据
        updater_treasury.update_treasury_bond_data()
        
        # 1.2 更新个股数据 (股价和股息率等)
        updater_stock.update_stock_data()
    except Exception as e:
        print(f"\n[错误] 在数据更新阶段发生错误: {e}")
        # 根据需要，可以选择在这里中断流程
        return

    # --- 第2步: 分析计算 ---
    try:
        calculator_spread.calculate_spread()
    except Exception as e:
        print(f"\n[错误] 在分析计算阶段发生错误: {e}")
        return

    # --- 第3步: 生成可视化图表 ---
    try:
        visualizer_spread.visualize_spread()
    except Exception as e:
        print(f"\n[错误] 在可视化阶段发生错误: {e}")
        return

    print("\n==========================================")
    print("=   股债利差分析流程执行完毕！     =")
    print("==========================================")

if __name__ == '__main__':
    run_spread_analysis_pipeline() 