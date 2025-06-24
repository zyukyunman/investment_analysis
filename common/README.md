# 通用工具与配置

本目录包含项目中共用的工具函数和配置文件。

## 目录说明

- `config.py`: 主配置文件，包含所有可配置项
- `config.template.py`: 配置文件模板，首次使用时复制为config.py
- `utils.py`: 通用工具函数，如日期处理、数据验证等
- `utils_ts.py`: Tushare相关的工具函数

## 首次使用

```bash
# 在项目根目录下执行
cp common/config.template.py common/config.py

# 然后修改config.py中的必要配置项（具体见文件注释）
```

## 配置管理

### 1. 配置文件

首次使用时，需要从模板创建配置文件：

```bash
# 在项目根目录下执行
cp common/config.template.py common/config.py
```

### 2. 必需配置项

```python
# Tushare API配置
TUSHARE_TOKEN = 'your_token_here'  # Tushare Pro的API token

# 数据获取配置
DATA_START_DATE = '1998-01-01'     # 数据获取的起始日期
FORCE_FULL_DATA_REFRESH = False    # 是否强制全量更新数据

# 数据目录配置
DATA_AUTO_DIR = 'data/auto'        # 自动更新数据的存储目录
DATA_HAND_DIR = 'data/hand'        # 手动维护数据的存储目录
```

### 3. 可选配置项

```python
# 调试配置
DEBUG_LOG_ENABLED = False          # 是否启用调试日志

# 性能配置
CHUNK_SIZE = 1000                  # 数据处理的批次大小
MAX_WORKERS = 4                    # 最大并行工作进程数

# 可视化配置
DEFAULT_DPI = 100                  # 默认图表分辨率
DEFAULT_FIGSIZE = (12, 8)         # 默认图表尺寸
```

## 工具函数

### 1. 通用工具 (`utils.py`)

```python
from common.utils import (
    check_if_update_should_be_skipped,
    format_date_string,
    safe_divide,
    moving_average
)

# 检查是否需要更新数据
should_skip = check_if_update_should_be_skipped(
    file_path='data/auto/stock_data.csv',
    date_column_name='交易日期'
)

# 格式化日期字符串
date_str = format_date_string('20220101', '%Y%m%d', '%Y-%m-%d')

# 安全除法（避免除零错误）
result = safe_divide(10, 0, default=0)

# 计算移动平均
ma = moving_average(data, window=20)
```

### 2. Tushare工具 (`utils_ts.py`)

```python
from common.utils_ts import (
    initialize_tushare,
    convert_to_ts_code,
    get_pro_bar
)

# 初始化Tushare
pro = initialize_tushare()

# 转换股票代码格式
ts_code = convert_to_ts_code('600036')  # 返回 '600036.SH'

# 获取行情数据
df = get_pro_bar(ts_code='600036.SH', start_date='20220101')
```

## 开发指南

### 1. 添加新的配置项

1. 首先在 `config.template.py` 中添加新配置：
```python
# 新功能的配置项
NEW_FEATURE_ENABLED = True
NEW_FEATURE_PARAM = 'default_value'
```

2. 添加配置注释：
```python
"""
配置项说明：
- NEW_FEATURE_ENABLED: 是否启用新功能
- NEW_FEATURE_PARAM: 新功能的参数值
"""
```

### 2. 添加新的工具函数

1. 在适当的工具文件中添加函数：
```python
def new_utility_function(param1, param2=None):
    """
    新工具函数的文档字符串
    
    Args:
        param1: 参数1的说明
        param2: 参数2的说明
    
    Returns:
        返回值的说明
    
    Raises:
        ValueError: 错误条件说明
    """
    # 函数实现
    pass
```

2. 添加单元测试：
```python
def test_new_utility_function():
    """测试新工具函数"""
    result = new_utility_function('test')
    assert result == expected_value
```

## 最佳实践

### 1. 配置管理
- 使用环境变量覆盖敏感配置
- 为所有配置项提供默认值
- 在启动时验证必需的配置

### 2. 工具函数
- 保持函数功能单一
- 提供详细的文档字符串
- 实现适当的错误处理
- 编写单元测试

### 3. 代码质量
- 遵循PEP 8规范
- 使用类型注解
- 添加适当的注释
- 定期重构优化

## 注意事项

1. **安全性**
   - 不要在代码中硬编码敏感信息
   - 使用环境变量或配置文件
   - 注意日志中的敏感信息

2. **兼容性**
   - 考虑不同Python版本
   - 处理不同操作系统差异
   - 注意依赖包的版本兼容

3. **性能**
   - 优化频繁调用的函数
   - 使用适当的缓存机制
   - 注意内存使用 