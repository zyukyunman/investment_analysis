# main/main_spread_analysis.py
# "股债利差分析"功能的总执行入口。
# 负责按顺序调用数据更新、分析计算和可视化模块。

import os
import sys
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# 将项目根目录添加到Python路径，以便跨目录调用模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入需要调用的模块
from updater import updater_treasury
from updater import updater_stock
from visualizer import calculator_spread
from visualizer import visualizer_spread
from common import config
from common import utils_ts

def run_spread_analysis_pipeline(stock_code=None):
    """
    执行完整的股债利差分析流程。
    
    参数:
        stock_code (str, optional): 要分析的股票代码。如果为None，则使用配置文件中的默认值。
    """
    # 设置当前分析的股票信息
    config.set_stock_info(stock_code)
    
    # 获取实际使用的股票代码和名称（可能是默认值）
    current_stock_code = config.get_stock_code()
    current_stock_name = config.get_stock_name()
    
    print("==========================================")
    print(f"=   开始执行 {current_stock_name}({current_stock_code}) 股债利差分析流程...      =")
    print("==========================================")

    # --- 第1步: 更新数据 ---
    try:
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
    print(f"=   {current_stock_name}({current_stock_code}) 股债利差分析流程执行完毕！     =")
    print("==========================================")

def load_stocks_from_json(json_file=None):
    """
    从JSON文件加载股票列表
    
    参数:
        json_file (str): JSON文件路径
        
    返回:
        dict: 股票代码和名称的映射字典
    """
    if json_file is None:
        json_file = config.STOCKS_JSON_PATH
        
    try:
        if not os.path.exists(json_file):
            print(f"股票JSON文件 {json_file} 不存在")
            return {}
            
        with open(json_file, 'r', encoding='utf-8') as f:
            stocks_dict = json.load(f)
        
        print(f"从 {json_file} 加载了 {len(stocks_dict)} 支股票")
        return stocks_dict
    except Exception as e:
        print(f"加载股票JSON文件失败: {e}")
        return {}

def filter_stocks_by_json(stocks_list, json_file=None):
    """
    根据JSON文件过滤股票列表
    
    参数:
        stocks_list (list): 股票列表，格式为 [(stock_code, stock_name), ...]
        json_file (str): JSON文件路径
        
    返回:
        list: 过滤后的股票列表
    """
    if json_file is None:
        json_file = config.STOCKS_JSON_PATH

    # 加载JSON文件中的股票
    json_stocks = load_stocks_from_json(json_file)
    if not json_stocks:
        return stocks_list
    
    # 过滤股票列表，只保留在JSON文件中的股票
    filtered_list = []
    for stock_code, stock_name in stocks_list:
        if stock_code in json_stocks:
            filtered_list.append((stock_code, stock_name))
    
    print(f"过滤后剩余 {len(filtered_list)} 支股票")
    return filtered_list

def run_batch_analysis(stocks_list, max_workers=1):
    """
    批量执行多个股票的股债利差分析
    
    参数:
        stocks_list (list): 股票列表，格式为 [(stock_code, stock_name), ...]
        max_workers (int): 并行执行的最大线程数
    """
    print(f"开始批量分析 {len(stocks_list)} 支股票...")
    
    # 串行执行
    if max_workers <= 1:
        for stock_code, stock_name in stocks_list:
            print(f"\n{'='*50}")
            print(f"开始分析 {stock_name}({stock_code})...")
            print(f"{'='*50}")
            run_spread_analysis_pipeline(stock_code)
        return
    
    # 并行执行
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 创建未来任务字典
        future_to_stock = {
            executor.submit(run_spread_analysis_pipeline, stock_code): (stock_code)
            for stock_code, stock_name in stocks_list
        }
        
        # 获取结果
        for future in as_completed(future_to_stock):
            stock_code, stock_name = future_to_stock[future]
            try:
                future.result()  # 获取函数返回值，如果有异常则抛出
                print(f"股票 {stock_name}({stock_code}) 分析完成")
            except Exception as e:
                print(f"股票 {stock_name}({stock_code}) 分析失败: {e}")

def get_user_confirmation(prompt):
    """
    获取用户确认
    
    参数:
        prompt (str): 提示信息
        
    返回:
        bool: 用户是否确认
    """
    while True:
        response = input(f"{prompt} (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("请输入 'y' 或 'n'")

def main():
    """命令行入口函数"""
    parser = argparse.ArgumentParser(description='股债利差分析工具')
    parser.add_argument('--stock_code', type=str, help='要分析的股票代码，例如 002807')
    parser.add_argument('--stock_name', type=str, help='股票名称，例如 江阴银行')
    parser.add_argument('--sw_industry', type=str, help='申万行业代码，用于批量分析特定行业的股票，例如 801780 或 801780.SI')
    parser.add_argument('--list_industries', action='store_true', help='列出所有申万行业')
    parser.add_argument('--industry_level', type=str, default='L1', choices=['L1', 'L2', 'L3'], help='申万行业级别：L1-一级，L2-二级，L3-三级')
    parser.add_argument('--max_workers', type=int, default=1, help='并行执行的最大线程数')
    parser.add_argument('--stocks_json', type=str, default=config.STOCKS_JSON_PATH, help='股票JSON文件路径')
    parser.add_argument('--filter', action='store_true', help='是否过滤股票列表，只分析JSON文件中的股票')
    
    args = parser.parse_args()

    # 设置默认值
    config.set_stock_info(config.DEFAULT_STOCK_CODE)
    
    # 如果请求列出申万行业
    if args.list_industries:
        try:
            industries = utils_ts.get_sw_industry_list(level=args.industry_level)
            print(f"\n申万{args.industry_level}级行业列表:")
            print("-" * 50)
            print("行业代码\t行业名称")
            print("-" * 50)
            for code, name in industries:
                print(f"{code}\t{name}")
            return
        except Exception as e:
            print(f"列出申万行业失败: {e}")
            return
    
    # 如果指定了申万行业
    if args.sw_industry:
        try:
            # 获取行业信息
            industry_info = utils_ts.get_industry_info(args.sw_industry)
            if not industry_info:
                print(f"未找到申万行业代码 {args.sw_industry}")
                return
                
            print(f"获取到行业: {industry_info['name']}({industry_info['code']})")
            print(f"行业基本信息: 级别={industry_info['level']}, 成分股数量={industry_info['stock_count']}")
            
            # 获取行业成分股
            stocks_list = utils_ts.get_sw_industry_stocks(args.sw_industry)
            if not stocks_list:
                print(f"未找到行业 {industry_info['name']} 的成分股")
                return
                
            print(f"获取到 {len(stocks_list)} 支股票")
            
            # 询问是否过滤股票列表
            use_filter = args.filter
            if not use_filter:
                use_filter = get_user_confirmation(f"是否只分析已在 {args.stocks_json} 中的股票？(股票数量可能较多)")

            # --- 第1步: 更新数据 ---
            try:
                # 1.1 更新国债数据
                updater_treasury.update_treasury_bond_data()
            except Exception as e:
                print(f"\n[错误] 在数据更新阶段发生错误: {e}")
                return
            
            # 如果需要过滤
            if use_filter:
                filtered_stocks = filter_stocks_by_json(stocks_list, args.stocks_json)
                if not filtered_stocks:
                    print(f"过滤后没有剩余股票，请检查 {args.stocks_json} 文件")
                    return
                print(f"将分析 {len(filtered_stocks)} 支过滤后的股票")
                run_batch_analysis(filtered_stocks, args.max_workers)
            else:
                print(f"将分析全部 {len(stocks_list)} 支行业股票")
                run_batch_analysis(stocks_list, args.max_workers)
        except Exception as e:
            print(f"申万行业批量分析失败: {e}")
    # 如果指定了单一股票
    elif args.stock_code:
        # --- 第1步: 更新数据 ---
        try:
            # 1.1 更新国债数据
            updater_treasury.update_treasury_bond_data()
        except Exception as e:
            print(f"\n[错误] 在数据更新阶段发生错误: {e}")
            return
        run_spread_analysis_pipeline(args.stock_code)
    # 默认分析配置文件中的股票
    else:
        # --- 第1步: 更新数据 ---
        try:
            # 1.1 更新国债数据
            updater_treasury.update_treasury_bond_data()
        except Exception as e:
            print(f"\n[错误] 在数据更新阶段发生错误: {e}")
            return
        run_spread_analysis_pipeline()

if __name__ == '__main__':
    main() 