# 数据更新模块

本目录包含所有用于获取和更新金融市场数据的脚本。

## 现有更新器

- `updater_stock.py`: 更新个股的每日行情、基本面指标和复权数据。
- `updater_treasury.py`: 更新中美十年期国债收益率数据。
- `updater_sw_industry.py`: 更新申万一级行业指数的行情和估值数据。

所有更新器都设计为可以独立运行。详细的参数和使用说明，请直接查阅对应脚本文件顶部的注释。

## 开发框架与规范

为了保持项目代码的一致性和可维护性，开发新的更新器或修改现有更新器时，请遵循以下框架和规范：

1.  **优先使用公共模块**:
    在编写任何新功能之前，请首先检查 `common/` 目录。该目录提供了项目通用的配置 (`config.py`)、工具函数 (`utils.py`) 和 Tushare 接口封装 (`utils_ts.py`)。
    - **目标**：避免重复造轮子，实现代码复用。
    - **实践**: 如果发现需要一个在多处可能都会用到的功能（如日期处理、文件查找、API 初始化等），请优先在 `common/utils.py` 中寻找是否已有实现。如果没有，请将你的实现添加到 `common/` 目录下的相应模块中，并确保其通用性。

2.  **独立可执行**:
    每个更新器脚本都应该是一个独立的可执行单元，可以通过 `python -m updater.your_updater_name` 或 `python updater/your_updater_name.py` 的方式直接运行。

3.  **清晰的日志输出**:
    在数据获取、处理和保存的各个关键步骤，都应有清晰的 `print()` 日志输出，方便用户了解脚本执行的当前状态和结果。

4.  **增量更新与强制刷新**:
    所有更新器都应具备智能的增量更新能力，即只获取最新缺失的数据，避免重复下载。同时，也需要提供一个 `--force` 或类似的命令行参数，允许用户强制执行全量数据刷新。可以参考 `common/utils.py` 中的 `check_if_update_should_be_skipped` 函数。

5.  **统一的数据出口**:
    所有由更新器自动获取的数据都应保存在 `data/auto/` 目录下的相应子目录中。文件路径的管理应通过 `common/config.py` 统一进行，而不是在更新器脚本中硬编码。

遵循以上规范，可以帮助我们构建一个更加健壮和易于扩展的数据更新系统。

## 可用的更新器

### 1. 股票数据更新器 (`updater_stock.py`)

从Tushare获取个股的历史数据，包括：
- 日线行情（前复权、后复权）
- 基本面指标（PE、PB等）
- 分红数据

```bash
# 更新指定股票的数据
python updater_stock.py --code 600036

# 强制全量更新
python updater_stock.py --code 600036 --force
```

#### 特色功能

- **智能分红处理**：自动处理多种分红方案，按优先级选择最终方案
- **动态股息率**：基于历史分红数据计算动态股息率
- **数据完整性检查**：自动检查和补充缺失数据

### 2. 国债数据更新器 (`updater_treasury.py`)

从中国债券信息网获取国债收益率数据：

```bash
# 更新国债收益率数据
python updater_treasury.py

# 强制全量更新
python updater_treasury.py --force
```

### 3. 申万行业数据更新器 (`updater_sw_industry.py`)

获取申万一级行业指数数据：

```bash
# 更新所有行业数据
python updater_sw_industry.py

# 更新特定行业数据
python updater_sw_industry.py --code 801780

# 强制全量更新
python updater_sw_industry.py --force
```

## 数据源说明

1. **Tushare**
   - 用途：股票数据、行业数据
   - 需要配置：`TUSHARE_TOKEN`
   - 数据质量：高
   - 访问限制：按积分计费

2. **AKShare**
   - 用途：作为Tushare的备选数据源
   - 无需配置
   - 数据质量：中
   - 访问限制：较少

3. **中国债券信息网**
   - 用途：国债收益率数据
   - 无需配置
   - 数据质量：高
   - 访问限制：需要遵守爬虫规则

## 通用参数说明

所有更新器都支持以下通用参数：

- `--force`: 强制全量更新数据
- `--help`: 显示帮助信息
- `--debug`: 启用调试模式，显示详细日志

## 输出说明

所有数据文件都保存在 `data/auto/` 目录下：

```
data/auto/
├── stock/                    # 股票数据
│   └── {股票代码}_history.csv
├── treasury/                 # 国债数据
│   └── treasury_rates.csv
└── sw_industry/             # 申万行业数据
    └── {行业代码}.csv
```

## 开发新的更新器

1. **基本要求**
   - 必须支持命令行参数
   - 必须实现增量更新
   - 必须处理异常情况
   - 必须提供详细的日志

2. **代码模板**
```python
import argparse
from common import config

def update_data(force=False):
    """数据更新主函数"""
    pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    
    update_data(force=args.force)

if __name__ == '__main__':
    main()
```

3. **测试要求**
   - 编写单元测试
   - 验证数据格式
   - 测试异常处理
   - 检查增量更新逻辑 