# --- 项目全局配置文件 ---
# 是否强制刷新所有历史数据。如果设为True，则会无视本地文件的新旧，强制从网络下载全部数据并合并。
# 日常使用时建议设为False以提高效率。
FORCE_FULL_DATA_REFRESH = False 

# 是否开启调试日志。如果设为True，在更新数据时会打印详细的计算过程。
DEBUG_LOG_ENABLED = False

# --- 数据获取网络配置 ---
# [通用] 每次从网上抓取数据时的通用延迟时间（秒），防止IP被封
FETCH_DELAY_SECONDS = 1
# [通用] 网络请求的通用超时时间（秒）
REQUESTS_TIMEOUT = 30

# [updater_stock] tushare Pro 的 API token，用于获取分红等数据。请替换为自己的真实token。
TUSHARE_TOKEN = '4a66c02af10f90745639ec22611a03cc4ceca5ca65877e2c201e9f81'

# --- 数据获取日期配置 ---
# 首次运行时，数据获取的起始日期
# 对于国债，最早的数据在 2002 年左右
# 对于股票，akshare 会获取上市以来的所有数据，此配置主要用于国债
DATA_START_DATE = "1998-01-01"


# ----------------------------------------------------------------

# --- 股票与市场配置 ---
# 默认股票配置，可以被程序调用时的参数覆盖
DEFAULT_STOCK_CODE = "002807"  # 默认分析的股票代码 (jiangyin_bank)
BENCHMARK_INDEX = "000300"  # 对比基准指数 (e.g., 沪深300)

# 当前分析的股票代码和名称，可以通过main函数传入覆盖默认值
_CURRENT_STOCK_CODE = DEFAULT_STOCK_CODE
_CURRENT_STOCK_NAME = ""

from common import utils_ts
def set_stock_info(stock_code=None):
    """设置当前分析的股票信息"""
    global _CURRENT_STOCK_CODE, _CURRENT_STOCK_NAME
    if stock_code:
        _CURRENT_STOCK_CODE = stock_code
    stock_info = utils_ts.get_stock_info(_CURRENT_STOCK_CODE)
    _CURRENT_STOCK_NAME = stock_info['name'].iloc[0]

def get_stock_code():
    """获取当前分析的股票代码"""
    return _CURRENT_STOCK_CODE

def get_stock_name():
    """获取当前分析的股票名称"""
    return _CURRENT_STOCK_NAME

# ----------------------------------------------------------------

# --- 文件路径配置 (通常无需修改) ---
import os

# 基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))+"/.."
# 核心数据目录
DATA_DIR = os.path.join(BASE_DIR, "data")               # 统一的数据根目录
DATA_AUTO_UPDATE_DIR = os.path.join(DATA_DIR, "auto") # updater脚本自动更新的数据存放处
DATA_HAND_UPDATE_DIR = os.path.join(DATA_DIR, "hand") # 手动更新数据存放处

# 由 updater 脚本产出的数据文件路径
TREASURY_BOND_CSV = os.path.join(DATA_AUTO_UPDATE_DIR, "treasury_bond_rates.csv")

# 动态生成的文件路径，基于当前选择的股票代码
def get_stock_history_csv():
    """获取股票历史数据CSV文件路径"""
    return os.path.join(DATA_AUTO_UPDATE_DIR, f"{get_stock_code()}_history.csv")

def get_spread_analysis_csv():
    """获取股债利差分析结果CSV文件路径"""
    return os.path.join(VISUALIZER_RESULTS_DIR, f"{get_stock_code()}_spread_analysis.csv")

def get_spread_plot_image_path():
    """获取带股价的股债利差图表文件路径"""
    return os.path.join(VISUALIZER_RESULTS_DIR, f"{get_stock_code()}_spread_plot_with_price.png")

def get_spread_plot_image_standalone_path():
    """获取独立的股债利差图表文件路径"""
    return os.path.join(VISUALIZER_RESULTS_DIR, f"{get_stock_code()}_spread_plot_standalone.png")

def get_plot_image_path():
    """获取通用图表文件路径"""
    return os.path.join(VISUALIZER_RESULTS_DIR, f"{get_stock_code()}_plot.png")

# 分析工具模块的产出路径 (由 visualizer/ 目录下的脚本使用)
VISUALIZER_RESULTS_DIR = os.path.join(BASE_DIR, "visualizer", "results")