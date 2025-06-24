# 投资分析套件 (Investment Analysis Suite)

本项目是一个灵活、可扩展的投资分析工具集，旨在利用模块化的设计，为不同的投资分析策略提供支持。

## 项目规则与约定

### 1. 模块化设计
- 每个功能模块都是独立的，可以单独运行和测试
- 模块之间通过标准化的数据格式和接口进行交互
- 每个目录都有自己的 README.md，详细说明该模块的功能和使用方法

### 2. 数据流转规则
- 原始数据统一存放在 `data/` 目录
- 分析结果统一存放在 `visualizer/results/` 目录

### 3. 配置管理
- 所有配置项集中在 `common/config.py`
- 敏感配置（如API Token）通过环境变量或配置文件注入
- 每个模块可以有自己的配置文件，但需要在主配置中注册

### 4. 代码规范
- 所有Python脚本都支持独立运行
- 所有脚本都必须提供命令行参数支持
- 代码必须包含适当的注释和文档字符串

### 5. 错误处理
- 所有可能的错误都需要被捕获并适当处理
- 关键错误需要记录到日志
- 用户友好的错误提示

## 快速开始

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **配置环境**
- 复制 `common/config.template.py` 到 `common/config.py`
- 设置必要的配置项（参见 `common/README.md`）

3. **查看模块说明**
- [数据更新模块说明](updater/README.md)
- [数据存储规范](data/README.md)
- [可视化模块说明](visualizer/README.md)
- [主程序使用指南](main/README.md)
- [通用工具说明](common/README.md)

## 项目结构

```
investment_analysis/
├── main/               # 主程序入口
├── updater/            # 数据更新模块
├── data/               # 数据存储目录
├── visualizer/         # 分析和可视化模块
├── common/             # 通用工具和配置
└── requirements.txt    # 项目依赖
```

## 贡献指南

1. **开发新功能**
- 在相应目录创建新的Python模块
- 更新该目录的 README.md
- 添加必要的单元测试
- 更新 requirements.txt（如果添加了新依赖）

2. **提交变更**
- 确保代码符合项目规范
- 更新相关文档
- 提交前进行本地测试

## 许可证

MIT License