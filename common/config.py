# --- 项目全局配置文件 ---
# 是否强制刷新所有历史数据。如果设为True，则会无视本地文件的新旧，强制从网络下载全部数据并合并。
# 日常使用时建议设为False以提高效率。
FORCE_FULL_DATA_REFRESH = False 

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
STOCK_CODE = "002807"         # 要分析的股票代码 (jiangyin_bank)
STOCK_NAME = "江阴银行"        # 股票中文名 (用于图表标题)
BENCHMARK_INDEX = "000300"  # 对比基准指数 (e.g., 沪深300)

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
STOCK_HISTORY_CSV = os.path.join(DATA_AUTO_UPDATE_DIR, f"{STOCK_CODE}_history.csv")

# 分析工具模块的产出路径 (由 visualizer/ 目录下的脚本使用)
VISUALIZER_RESULTS_DIR = os.path.join(BASE_DIR, "visualizer", "results")
# [calculator_spread] 由股债利差计算器生成的分析结果文件
SPREAD_ANALYSIS_CSV = os.path.join(VISUALIZER_RESULTS_DIR, f"{STOCK_CODE}_spread_analysis.csv")
# [visualizer_spread] 由股债利差可视化工具生成的图表文件
SPREAD_PLOT_IMAGE_PATH = os.path.join(VISUALIZER_RESULTS_DIR, f"{STOCK_CODE}_spread_plot_with_price.png")
SPREAD_PLOT_IMAGE_STANDALONE_PATH = os.path.join(VISUALIZER_RESULTS_DIR, f"{STOCK_CODE}_spread_plot_standalone.png")
PLOT_IMAGE_PATH = os.path.join(VISUALIZER_RESULTS_DIR, f"{STOCK_CODE}_plot.png")