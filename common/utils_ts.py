# common/utils_ts.py
# 封装所有与 Tushare API 相关的通用函数

import tushare as ts
from common import config

def initialize_tushare():
    """使用config中的token初始化tushare并返回pro_api实例"""
    if config.TUSHARE_TOKEN == 'YOUR_REAL_TOKEN_HERE' or not config.TUSHARE_TOKEN:
        raise ValueError("Tushare token 未在 config.py 中配置。请前往 https://tushare.pro/user/token 获取。")
    ts.set_token(config.TUSHARE_TOKEN)
    return ts.pro_api() 