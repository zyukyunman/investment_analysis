# common/utils_ts.py
# 封装所有与 Tushare API 相关的通用函数

import tushare as ts
import pandas as pd
import time
from common import config

def initialize_tushare():
    """使用config中的token初始化tushare并返回pro_api实例"""
    if config.TUSHARE_TOKEN == 'YOUR_REAL_TOKEN_HERE' or not config.TUSHARE_TOKEN:
        raise ValueError("Tushare token 未在 config.py 中配置。请前往 https://tushare.pro/user/token 获取。")
    ts.set_token(config.TUSHARE_TOKEN)
    return ts.pro_api()

# 获取股票信息
def get_stock_info(ts_code):
    pro = initialize_tushare()
    df = pro.stock_basic(ts_code=convert_to_ts_code(ts_code))
    return df

def get_sw_industry_list(level='L1'):
    """
    获取申万行业列表
    
    参数:
        level (str): 行业级别，L1-一级，L2-二级，L3-三级
    
    返回:
        list: 包含行业信息的列表，每个元素为 (行业代码, 行业名称)
    """
    pro = initialize_tushare()
    try:
        # 获取申万行业列表
        df = pro.index_classify(level=level, src='SW2021')
        
        # 构建行业信息列表
        industries = []
        for _, row in df.iterrows():
            industries.append((row['index_code'], row['industry_name']))
        
        # 按行业代码排序
        industries.sort(key=lambda x: x[0])
        
        return industries
    except Exception as e:
        print(f"获取申万行业列表失败: {e}")
        return []

def get_sw_industry_members(industry_code):
    """
    获取申万行业成分股
    
    参数:
        industry_code (str): 申万行业代码，例如：801780.SI
    
    返回:
        pandas.DataFrame: 包含成分股信息的DataFrame
    """
    pro = initialize_tushare()
    try:
        # 确保行业代码有正确的后缀
        if not industry_code.endswith('.SI'):
            industry_code = f"{industry_code}.SI"
        
        # 获取行业基本信息
        industries_df = pro.index_classify(src='SW2021')
        industry_info = industries_df[industries_df['index_code'] == industry_code]
        
        if industry_info.empty:
            print(f"找不到行业 {industry_code} 的基本信息")
            return pd.DataFrame()
        
        # 获取行业成分股
        df = pro.index_weight(index_code=industry_code)
        if df.empty:
            print(f"行业 {industry_code} 没有成分股信息")
            return pd.DataFrame()
            
        # 获取股票名称
        stock_codes = df['con_code'].tolist()
        # 将列表分块，避免一次查询太多股票
        batch_size = 100
        stock_info_list = []
        
        for i in range(0, len(stock_codes), batch_size):
            batch_codes = stock_codes[i:i+batch_size]
            batch_str = ','.join(batch_codes)
            try:
                stock_info = pro.stock_basic(ts_code=batch_str, fields='ts_code,name')
                stock_info_list.append(stock_info)
                # 加入短暂延迟，避免请求频率过高
                time.sleep(0.5)
            except Exception as e:
                print(f"获取股票批次 {i//batch_size + 1} 信息失败: {e}")
        
        if not stock_info_list:
            return pd.DataFrame()
            
        # 合并所有批次的结果
        stock_info_df = pd.concat(stock_info_list, ignore_index=True)
        
        # 合并成分股权重和股票信息
        result = pd.merge(df, stock_info_df, on='ts_code', how='left')
        
        return result
    except Exception as e:
        print(f"获取行业 {industry_code} 成分股失败: {e}")
        return pd.DataFrame()

def get_sw_industry_stocks_by_code(industry_code):
    """
    根据申万行业代码获取成分股（使用index_member_all接口）
    
    参数:
        industry_code (str): 申万行业代码，格式如"801780.SI"
    
    返回:
        list: 股票列表，格式为 [(stock_code, stock_name), ...]
    """
    pro = initialize_tushare()
    try:
        # 确保行业代码有正确的后缀
        if not industry_code.endswith('.SI'):
            industry_code = f"{industry_code}.SI"
            
        # 获取行业基本信息，确定是一级、二级还是三级行业
        industry_info = get_industry_info(industry_code)
        if not industry_info:
            print(f"无法确定行业 {industry_code} 的级别")
            return []
            
        level = industry_info['level']
        level_code = f"l{level[1:]}_code"  # L1 -> l1_code, L2 -> l2_code, L3 -> l3_code
            
        # 获取行业成分股
        params = {level_code: industry_code, 'is_new': 'Y'}
        try:
            df = pro.index_member_all(**params)
        except Exception as e:
            print(f"使用index_member_all获取行业 {industry_code} 成分股失败: {e}")
            # 如果权限不足，使用index_weight接口
            print("尝试使用index_weight接口...")
            df_result = get_sw_industry_members(industry_code)
            if df_result.empty:
                return []
                
            # 提取股票代码和名称
            stocks_list = []
            for _, row in df_result.iterrows():
                stock_code = row['ts_code'].split('.')[0]
                stock_name = row['name']
                stocks_list.append((stock_code, stock_name))
            
            return stocks_list
        
        # 如果为空，返回空列表
        if df.empty:
            print(f"行业 {industry_code} 没有成分股")
            return []
            
        # 提取股票代码和名称
        stocks_list = []
        for _, row in df.iterrows():
            # 确保股票代码格式正确（去掉后缀）
            stock_code = row['ts_code'].split('.')[0]
            stock_name = row['name']
            stocks_list.append((stock_code, stock_name))
        
        return stocks_list
    except Exception as e:
        print(f"获取行业 {industry_code} 成分股失败: {e}")
        return []

def get_sw_industry_stocks(industry_code):
    """
    获取指定申万行业的成分股
    
    参数:
        industry_code (str): 申万行业代码
    
    返回:
        list: 股票列表，格式为 [(stock_code, stock_name), ...]
    """
    # 首先使用index_member_all接口
    stocks_list = get_sw_industry_stocks_by_code(industry_code)
    if stocks_list:
        return stocks_list
        
    # 如果index_member_all接口失败，尝试使用index_weight接口获取成分股
    try:
        df_result = get_sw_industry_members(industry_code)
        if df_result.empty:
            return []
            
        # 提取股票代码和名称
        stocks_list = []
        for _, row in df_result.iterrows():
            stock_code = row['ts_code'].split('.')[0]
            stock_name = row['name']
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
        dict: 行业信息，包括名称等
    """
    # 确保行业代码格式正确
    original_code = industry_code
    if not industry_code.endswith('.SI'):
        industry_code = f"{industry_code}.SI"
        
    pro = initialize_tushare()
    
    # 尝试从index_classify获取信息
    try:
        # 获取行业信息
        df = pro.index_classify(src='SW2021')
        industry_row = df[df['index_code'] == industry_code]
        
        if industry_row.empty:
            industry_row = df[df['index_code'] == original_code]
            
        if industry_row.empty:
            print(f"未找到行业代码 {original_code} 的信息")
            return None
        
        # 获取行业信息
        industry_info = {
            'code': industry_code,  # 使用带后缀的完整代码
            'name': industry_row['industry_name'].values[0],
            'level': industry_row['level'].values[0],
            'src': industry_row['src'].values[0],
            'stock_count': 0
        }
        
        # 获取成分股数量
        try:
            df_weight = pro.index_weight(index_code=industry_code)
            industry_info['stock_count'] = len(df_weight) if not df_weight.empty else 0
        except Exception as e:
            print(f"获取行业 {industry_code} 成分股数量失败: {e}")
            industry_info['stock_count'] = 0
        
        return industry_info
    except Exception as e:
        print(f"获取行业 {original_code} 信息失败: {e}")
        return None

def convert_to_ts_code(stock_code):
    """
    将股票代码转换为 Tushare 格式（带交易所后缀）
    
    参数:
        stock_code (str): 股票代码，如 "600000"
        
    返回:
        str: 带交易所后缀的 Tushare 格式代码，如 "600000.SH"
    """
    pro = initialize_tushare()
    
    # 更准确地判断股票所属交易所
    # 沪市股票：以60、68开头（主板、科创板）
    # 深市股票：以00、30、301开头（主板、创业板）
    if stock_code.startswith(('6')):
        ts_code = f"{stock_code}.SH"
    elif stock_code.startswith(('0', '3')):
        ts_code = f"{stock_code}.SZ"
    else:
        # 如果无法确定，尝试查询股票基本信息
        try:
            stock_info = pro.stock_basic(ts_code=f"{stock_code}.*")
            if not stock_info.empty:
                ts_code = stock_info.iloc[0]['ts_code']
            else:
                print(f"无法确定股票 {stock_code} 的交易所，将尝试使用默认规则...")
                ts_code = f"{stock_code}.SH" if stock_code.startswith('6') else f"{stock_code}.SZ"
        except Exception as e:
            print(f"查询股票信息失败: {e}，将使用默认规则...")
            ts_code = f"{stock_code}.SH" if stock_code.startswith('6') else f"{stock_code}.SZ"
    
    print(f"将使用股票代码: {ts_code}")
    return ts_code

def get_pro_bar(ts_code, start_date, end_date, asset='E', freq='D', adj=None, ma=None):
    """
    Tushare pro_bar 接口的封装，解决 pro.pro_bar 不可用的问题。
    pro_bar 是一个独立的函数，不依赖于 pro_api 实例。
    只要 initialize_tushare 被调用过一次，token 就会被设置。
    """
    return ts.pro_bar(
        ts_code=ts_code, 
        start_date=start_date, 
        end_date=end_date, 
        asset=asset, 
        freq=freq, 
        adj=adj, 
        ma=ma
    ) 