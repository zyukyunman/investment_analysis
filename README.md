# 投资分析套件 (Investment Analysis Suite)

本项目是一个灵活、可扩展的投资分析工具集，旨在利用模块化的设计，为不同的投资分析策略提供支持。当前版本实现了**股债利差**分析的核心功能。

## 核心功能

- **数据自动更新**:
  - `updater_stock.py`: 从网络获取并更新指定股票的历史股价、股息率等信息。
  - `updater_treasury.py`: 获取并更新中国国债收益率曲线数据。
- **核心分析计算**:
  - `calculator_spread.py`: 基于最新的股票和国债数据，计算二者之间的利差（风险溢价）。
- **数据可视化**:
  - `visualizer_spread.py`: 将计算出的利差、股价等信息生成清晰的可视化图表。

## 快速开始

#### 1. 环境准备

确保您的电脑已安装 `Python 3` 和 `pip` 包管理工具。

#### 2. 安装

```bash
# 1. 克隆本项目到本地
git clone <your_repository_url>
cd investment_analysis

# 2. 安装项目所需的依赖库
pip install -r requirements.txt
```

#### 3. 参数配置

项目的所有配置项都集中在 `common/config.py` 文件中。在运行前，**请务必进行以下配置**：

1.  **设置API Token**:
    打开 `common/config.py` 文件，找到 `TUSHARE_TOKEN` 配置项，并替换为您自己的 [Tushare Pro](https://tushare.pro/) 的真实 Token。Tushare 用于获取准确的股票股息率数据。

    ```python
    # common/config.py

    # [updater_stock] tushare Pro 的 API token，用于获取分红等数据。请替换为自己的真实token。
    TUSHARE_TOKEN = 'YOUR_REAL_TOKEN_HERE' 
    ```

2.  **修改分析对象 (可选)**:
    您可以修改 `STOCK_CODE` 和 `STOCK_NAME` 来分析不同的股票。

    ```python
    # common/config.py

    STOCK_CODE = "002807"         # 要分析的股票代码 (例如: "600519" 对应贵州茅台)
    STOCK_NAME = "江阴银行"        # 股票中文名 (用于图表标题)
    ```

3.  **其他配置**:
    - `FORCE_FULL_DATA_REFRESH`: 默认为 `False`，使用增量更新模式，高效地获取最新数据。如果发现本地数据有损坏或缺失，可以将其设置为 `True`，程序将强制从网络下载全量历史数据并与本地合并。
    - `DATA_START_DATE`: 数据获取的起始日期，默认为 "1998-01-01"。

#### 4. 运行分析

完成配置后，直接运行主程序即可：

```bash
python main/main_spread_analysis.py
```

程序会自动执行数据更新、分析计算和图表生成的全过程。

#### 5. 查看结果

分析完成后，所有的产出文件都保存在 `visualizer/results/` 目录下：

-   `{stock_code}_spread_analysis.csv`: 详细的股债利差计算数据。
-   `{stock_code}_spread_plot_with_price.png`: 包含股价走势和股债利差的综合图表。
-   `{stock_code}_spread_plot_standalone.png`: 独立的股债利差走势图。

## 项目结构与数据流

#### 目录结构

```
investment_analysis/
│
├── main/
│   └── main_spread_analysis.py   # <--- 股债利差分析的总入口
│
├── updater/
│   ├── updater_treasury.py       # <--- 负责更新国债数据
│   └── updater_stock.py          # <--- 负责更新股票数据
│
├── data/
│   ├── auto/                     # <--- 存放由 updater 脚本自动下载和更新的数据
│   │   ├── treasury_bond_rates.csv
│   │   └── 002807_history.csv
│   └── hand/                     # <--- 用于存放需要手动添加的原始数据 (当前为空)
│
├── visualizer/
│   ├── calculator_spread.py      # <--- 股债利差计算器
│   ├── visualizer_spread.py      # <--- 股债利差可视化工具
│   └── results/                  # <--- 存放所有分析和可视化的结果
│       ├── 002807_spread_analysis.csv
│       └── 002807_spread_plot_with_price.png
│
├── common/
│   ├── config.py                 # <--- 所有模块的统一配置文件
│   └── utils.py                  # <--- 通用工具函数
│
├── requirements.txt              # <--- 项目依赖
└── README.md                     # <--- 项目说明书 (本文件)
```

#### 数据流

1.  **数据获取**: `main` 脚本首先调用 `updater/` 中的脚本。这些脚本会从网络（如 `akshare`, `tushare`）获取最新的国债和股票数据，并将其保存到 `data/auto/` 目录中。
2.  **数据读取**: `visualizer/calculator_spread.py` 从 `data/auto/` 读取上一步生成的数据文件。
3.  **分析计算**: 计算器完成利差分析后，将结果（一个 `.csv` 文件）保存到 `visualizer/results/` 目录。
4.  **可视化**: `visualizer/visualizer_spread.py` 读取 `visualizer/results/` 中的分析数据，生成图表（`.png` 文件），并再次保存到该目录。

## 开发者指南：如何扩展新功能

本项目的设计鼓励进行功能扩展。例如，要新增一个 "市盈率（PE）分析" 功能，您可以遵循以下步骤：

1.  **创建执行入口**: 在 `main/` 目录下创建 `main_pe_analysis.py`。
2.  **创建数据获取器**: 如果需要新的数据源（例如获取PE数据），在 `updater/` 下创建对应的 `updater_pe_data.py`。
3.  **创建分析器与可视化工具**: 在 `visualizer/` 目录下创建 `calculator_pe_analysis.py` 和 `visualizer_pe.py`。
4.  **更新配置**: 在 `common/config.py` 中为新功能添加所需的所有配置项（如文件路径、参数等），并写好注释。
5.  **编写调度逻辑**: 在 `main_pe_analysis.py` 中，按顺序调用您新创建的 `updater`, `calculator` 和 `visualizer` 模块。
6.  **运行**: `python main/main_pe_analysis.py`。
