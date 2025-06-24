# 分析与可视化模块

本目录包含所有数据分析和可视化相关的脚本。它的核心思想是 **计算与呈现分离**：一部分脚本专门负责数据处理和计算，另一部分脚本则负责将计算结果以图表的形式呈现出来。

## 现有脚本

- `calculator_spread.py`: **股债性价比计算器**。读取股票和国债数据，计算股债性价比及其历史百分位（温度计），并将结果保存为 CSV 文件。
- `visualizer_spread.py`: **股债性价比可视化器**。读取由 `calculator_spread.py` 生成的结果文件，并创建包含股价、温度计、性价比等核心指标的合并分析图。

所有脚本都设计为可以独立运行。详细的参数和使用说明，请直接查阅对应脚本文件顶部的注释。

## 开发框架与规范

为了保持项目代码的一致性和可维护性，开发新的分析或可视化脚本时，请遵循以下框架和规范：

1.  **计算与呈现分离 (SoC)**:
    - **分析器 (`calculator_*.py`)**: 负责数据的读取、清洗、计算和分析。其唯一的输出应该是结构化的数据文件（如 CSV），存放在 `visualizer/results/` 目录下。分析器不应包含任何绘图代码。
    - **可视化器 (`visualizer_*.py`)**: 负责读取分析器生成的中间数据文件，并将其可视化。可视化器不应包含复杂的数据计算逻辑。

2.  **优先使用公共模块**:
    在编写任何新功能之前，请首先检查 `common/` 目录。该目录提供了项目通用的配置 (`config.py`) 和工具函数 (`utils.py`)。
    - **目标**: 避免重复造轮子，实现代码复用。
    - **实践**: 如果需要配置字体、获取文件路径、或使用其他通用功能，请首先在 `common/` 模块中寻找。如果找不到，请考虑将新功能添加到 `common/` 中，使其可以被项目其他部分复用。

3.  **独立可执行**:
    每个脚本都应该是一个独立的可执行单元，可以被直接运行。

4.  **统一的输入输出**:
    - **输入**: 脚本应从 `data/` 目录或 `visualizer/results/` 目录（对于可视化器）读取数据。
    - **输出**: 计算结果（数据）和可视化结果（图片）都应保存在 `visualizer/results/` 目录下。
    - **路径管理**: 所有文件路径都应通过 `common/config.py` 统一管理，禁止在脚本中硬编码。

遵循以上规范，可以帮助我们构建一个逻辑清晰、易于扩展的分析与可视化流程。

## 目录说明

- `calculator_spread.py`: 股债利差计算器
- `visualizer_spread.py`: 股债利差可视化工具
- `results/`: 存放分析结果和图表
  - `spread/`: 股债利差分析结果
  - `custom/`: 自定义分析结果

所有脚本都支持独立运行，使用方法见各文件的注释说明。

## 功能模块

### 1. 股债利差分析器 (`calculator_spread.py`)

计算股票的股债利差（风险溢价）：

```bash
# 计算指定股票的股债利差
python calculator_spread.py --code 600036

# 使用自定义参数计算
python calculator_spread.py --code 600036 --window 20 --method "mean"
```

#### 参数说明
- `--code`: 股票代码
- `--window`: 移动平均窗口大小（默认20）
- `--method`: 计算方法（mean/median，默认mean）

### 2. 股债利差可视化器 (`visualizer_spread.py`)

生成股债利差的可视化图表：

```bash
# 生成标准图表
python visualizer_spread.py --code 600036

# 自定义图表样式
python visualizer_spread.py --code 600036 --style "dark" --dpi 300
```

#### 参数说明
- `--code`: 股票代码
- `--style`: 图表样式（默认classic）
- `--dpi`: 图像分辨率（默认100）

## 输出目录结构

```
visualizer/
├── results/                    # 分析结果输出目录
│   ├── spread/                # 股债利差分析结果
│   │   ├── csv/              # 数据文件
│   │   └── plots/            # 图表文件
│   └── custom/               # 自定义分析结果
└── templates/                 # 图表模板
```

## 可视化风格指南

### 1. 颜色方案

```python
# 标准颜色方案
COLORS = {
    'up': '#D3323C',       # 上涨红
    'down': '#2B8A6F',     # 下跌绿
    'primary': '#2878B5',  # 主要蓝
    'secondary': '#916FA1' # 次要紫
}
```

### 2. 图表规范

- 字体：微软雅黑（中文）、Arial（英文）
- 主标题：16号，粗体
- 副标题：14号，常规
- 轴标签：12号，常规
- 图例：10号，常规
- DPI：
  - 屏显：100
  - 打印：300

### 3. 布局模板

```python
def create_figure(figsize=(12, 8)):
    """创建标准图表布局"""
    fig = plt.figure(figsize=figsize)
    
    # 主图
    ax1 = plt.subplot2grid((4, 1), (0, 0), rowspan=3)
    # 副图
    ax2 = plt.subplot2grid((4, 1), (3, 0), rowspan=1)
    
    return fig, (ax1, ax2)
```

## 开发指南

### 1. 创建新的分析器

```python
class NewAnalyzer:
    def __init__(self):
        self.data = None
        self.results = {}
    
    def load_data(self, file_path):
        """加载数据"""
        self.data = pd.read_csv(file_path)
    
    def analyze(self):
        """执行分析"""
        pass
    
    def save_results(self, output_path):
        """保存结果"""
        pass
```

### 2. 创建新的可视化器

```python
class NewVisualizer:
    def __init__(self, style='classic'):
        plt.style.use(style)
        self.fig = None
        self.axes = None
    
    def create_plot(self):
        """创建图表"""
        pass
    
    def add_elements(self):
        """添加图表元素"""
        pass
    
    def save_plot(self, output_path):
        """保存图表"""
        pass
```

### 3. 添加命令行支持

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    
    analyzer = NewAnalyzer()
    analyzer.load_data(args.input)
    analyzer.analyze()
    analyzer.save_results(args.output)

if __name__ == '__main__':
    main()
```

## 注意事项

1. **性能优化**
   - 使用向量化操作
   - 避免循环处理大数据
   - 合理使用多进程

2. **内存管理**
   - 及时释放大型数据集
   - 使用生成器处理大文件
   - 避免不必要的数据复制

3. **代码质量**
   - 编写单元测试
   - 添加详细注释
   - 遵循PEP 8规范

4. **可视化最佳实践**
   - 保持图表简洁清晰
   - 使用恰当的图表类型
   - 添加必要的图例和标签
   - 考虑色盲友好的配色方案 