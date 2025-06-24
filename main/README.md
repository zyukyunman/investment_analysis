# 主流程模块

本目录存放的是将各个子模块（updater, visualizer）串联起来，形成完整分析流程的入口脚本。

## 现有流程

- `main_spread_analysis.py`: **完整的股债性价比分析流程**。这是一个一键式的执行脚本，它会自动协调完成以下所有步骤：
    1.  调用 `updater` 模块更新所需的股票和国债数据。
    2.  调用 `calculator` 模块计算股债性价比。
    3.  调用 `visualizer` 模块生成最终的分析图表。

脚本支持通过命令行参数指定股票代码，详细使用方法请直接查阅其文件顶部的注释。

## 开发框架与规范

`main` 目录下的脚本是项目功能的直接体现者，开发时请遵循以下框架和规范：

1.  **作为"协调者"而非"实现者"**:
    `main` 脚本的核心职责是**调用**和**协调**其他模块的功能，而不是在自身内部实现复杂的数据处理或计算逻辑。
    - **目标**: 保持主流程代码的简洁和清晰，使其易于理解整个分析任务的步骤。
    - **实践**: 几乎所有的核心逻辑都应该在 `updater`、`visualizer/calculator` 或 `common` 中实现。`main` 脚本应该像一个总指挥，依次发出指令（函数调用），而不是亲自下场干活。

2.  **模块化调用**:
    - 所有的功能调用都应该是模块化的。例如，通过 `from updater import updater_stock` 来引入功能，而不是使用 `os.system('python updater/updater_stock.py')` 这样的外部命令。

3.  **统一的配置入口**:
    - 主流程脚本是用户与整个系统交互的入口。所有可配置的参数（如股票代码、是否强制刷新等）都应通过 `common/config.py` 进行管理，并通过 `main` 脚本的命令行参数暴露给用户。

4.  **清晰的流程日志**:
    - 在每个主要步骤（如"开始更新数据"、"开始计算"、"开始绘图"）执行前后，都应有清晰的 `print()` 日志输出，让用户能够实时了解任务执行到了哪一步。

遵循以上规范，可以确保我们的主流程脚本始终是整个项目的清晰、稳定的入口。

## 目录说明

- `main_spread_analysis.py`: 股债利差分析主程序，包含完整的分析流程

所有脚本都支持独立运行，使用方法见各文件的注释说明。

## 可用的分析流程

### 1. 股债利差分析 (`main_spread_analysis.py`)

完整的股债利差分析流程，包括：
1. 更新股票数据
2. 更新国债数据
3. 计算股债利差
4. 生成分析图表

```bash
# 分析指定股票
python main_spread_analysis.py --code 600036

# 使用自定义参数
python main_spread_analysis.py --code 600036 --window 20 --force
```

#### 参数说明
- `--code`: 股票代码（必需）
- `--window`: 移动平均窗口（可选，默认20）
- `--force`: 强制更新所有数据（可选）
- `--style`: 图表样式（可选，默认classic）
- `--dpi`: 图表分辨率（可选，默认100）

## 开发新的分析流程

### 1. 基本结构

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
main_new_analysis.py
新分析流程的主程序入口
"""

import argparse
import logging
from datetime import datetime

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='新的分析流程')
    parser.add_argument('--param1', required=True, help='参数1的说明')
    parser.add_argument('--param2', default='default', help='参数2的说明')
    return parser.parse_args()

def main():
    """主函数"""
    # 设置日志
    logger = setup_logging()
    
    # 解析参数
    args = parse_args()
    
    try:
        # 1. 数据更新
        logger.info('开始更新数据...')
        # TODO: 调用updater模块
        
        # 2. 数据分析
        logger.info('开始数据分析...')
        # TODO: 调用calculator模块
        
        # 3. 结果可视化
        logger.info('开始生成图表...')
        # TODO: 调用visualizer模块
        
        logger.info('分析流程完成')
        
    except Exception as e:
        logger.error(f'发生错误: {str(e)}')
        raise

if __name__ == '__main__':
    main()
```

### 2. 错误处理

```python
class AnalysisError(Exception):
    """分析流程错误基类"""
    pass

class DataUpdateError(AnalysisError):
    """数据更新错误"""
    pass

class CalculationError(AnalysisError):
    """计算错误"""
    pass

class VisualizationError(AnalysisError):
    """可视化错误"""
    pass

def safe_update_data():
    """安全的数据更新"""
    try:
        # 更新数据
        pass
    except Exception as e:
        raise DataUpdateError(f"数据更新失败: {str(e)}")
```

### 3. 配置管理

```python
from common.config import Config

def load_config():
    """加载配置"""
    config = Config()
    
    # 验证配置
    required_fields = ['param1', 'param2']
    for field in required_fields:
        if not hasattr(config, field):
            raise ValueError(f"缺少必需的配置项: {field}")
    
    return config
```

## 最佳实践

### 1. 代码组织
- 主程序文件应保持简洁
- 复杂逻辑应封装在相应模块中
- 使用清晰的日志记录流程

### 2. 错误处理
- 捕获并记录所有可能的错误
- 提供清晰的错误信息
- 实现优雅的退出机制

### 3. 性能优化
- 避免重复计算
- 使用适当的缓存机制
- 支持断点续传

### 4. 用户体验
- 提供进度反馈
- 支持配置的灵活性
- 添加适当的帮助信息

## 注意事项

1. **依赖管理**
   - 确保所需模块已安装
   - 检查模块版本兼容性
   - 维护requirements.txt

2. **资源管理**
   - 及时释放内存
   - 清理临时文件
   - 关闭打开的文件

3. **配置检查**
   - 验证必需的配置项
   - 检查配置值的有效性
   - 提供合理的默认值

4. **测试建议**
   - 编写集成测试
   - 测试不同参数组合
   - 验证错误处理机制 