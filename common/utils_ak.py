# common/utils_ak.py
# 封装与akshare API相关的工具函数

import os
import sys
import pandas as pd

# 将项目根目录添加到Python路径，以便跨目录调用模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入申万行业获取模块
try:
    import akshare as ak
except ImportError:
    print("未安装akshare库，无法使用申万行业功能")
    print("请执行: pip install akshare")

def get_sw_industry_list():
    """
    获取申万一级行业列表
    
    返回:
        list: 包含行业信息的列表，每个元素为 (行业代码, 行业名称, 成分股数量)
    """
    try:
        # 获取申万一级行业列表
        industry_df = ak.sw_index_first_info()
        
        # 构建行业信息列表
        industries = []
        for _, row in industry_df.iterrows():
            industries.append((row['行业代码'], row['行业名称'], row.get('成份个数', 0)))
        
        # 按行业代码排序
        industries.sort(key=lambda x: x[0])
        
        return industries
    except Exception as e:
        print(f"获取申万行业列表失败: {e}")
        return []

def get_sw_industry_stocks(industry_code):
    """
    获取指定申万行业的成分股
    
    参数:
        industry_code (str): 申万行业代码
    
    返回:
        list: 股票列表，格式为 [(stock_code, stock_name), ...]
    """
    try:
        # 获取指定行业的成分股
        stocks_df = ak.sw_index_cons(index_code=industry_code)
        
        # 提取股票代码和名称
        stocks_list = []
        for _, stock_row in stocks_df.iterrows():
            # 确保股票代码格式正确（去掉可能的后缀）
            stock_code = stock_row['股票代码'].split('.')[0]
            stock_name = stock_row['股票名称']
            stocks_list.append((stock_code, stock_name))
        
        return stocks_list
    except Exception as e:
        print(f"获取行业 {industry_code} 成分股失败: {e}")
        return []

def get_industry_info(industry_code):
    """
    获取指定申万行业的信息
    
    参数:
        industry_code (str): 申万行业代码
    
    返回:
        dict: 行业信息，包括名称、PE、PB等
    """
    try:
        industry_df = ak.sw_index_first_info()
        industry_row = industry_df[industry_df['行业代码'] == industry_code]
        
        if industry_row.empty:
            print(f"未找到行业代码 {industry_code} 的信息")
            return None
        
        # 获取行业信息
        industry_info = {
            'code': industry_code,
            'name': industry_row['行业名称'].values[0],
            'stock_count': industry_row.get('成份个数', pd.Series([0])).values[0],
            'pe_static': industry_row.get('静态市盈率', pd.Series([None])).values[0],
            'pe_ttm': industry_row.get('TTM(滚动)市盈率', pd.Series([None])).values[0],
            'pb': industry_row.get('市净率', pd.Series([None])).values[0],
            'dividend_yield': industry_row.get('静态股息率', pd.Series([None])).values[0]
        }
        
        return industry_info
    except Exception as e:
        print(f"获取行业 {industry_code} 信息失败: {e}")
        return None

def is_akshare_available():
    """
    检查akshare库是否可用
    
    返回:
        bool: 如果akshare可用返回True，否则返回False
    """
    try:
        import akshare
        return True
    except ImportError:
        return False

if __name__ == '__main__':
    # 测试代码
    print("申万一级行业列表:")
    industries = get_sw_industry_list()
    for code, name, count in industries[:5]:  # 只显示前5个行业
        print(f"{code}\t{name}\t\t{count}")
    
    print("\n银行业成分股:")
    bank_stocks = get_sw_industry_stocks('850831')  # 银行业代码
    for code, name in bank_stocks[:5]:  # 只显示前5支股票
        print(f"{code}\t{name}")
    
    print("\n银行业信息:")
    bank_info = get_industry_info('850831')
    if bank_info:
        for key, value in bank_info.items():
            print(f"{key}: {value}")
