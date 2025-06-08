# visualizer/visualizer_spread.py
# 负责将股债利差分析结果可视化。

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 将项目根目录添加到Python路径，以便跨目录调用模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import config

def _set_matplotlib_font():
    """
    设置Matplotlib字体以支持中文显示。
    """
    try:
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 'SimHei' 是黑体
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号'-'显示为方块的问题
        print("Matplotlib 字体已设置为 'SimHei' 以支持中文。")
    except Exception as e:
        print(f"设置中文字体失败，图表中的中文可能无法正常显示。错误: {e}")
        print("请确保您的系统中安装了 'SimHei' 字体，或在代码中更换为其他已安装的中文字体。")

def visualize_spread():
    """
    读取分析结果，生成两张独立的图表：
    1. All-in-One合并图: 包含股价、温度计、性价比 (三Y轴)
    2. 独立核心指标图: 只包含温度计、性价比 (双Y轴)
    """
    print("\n--- 开始执行结果可视化任务 ---")
    _set_matplotlib_font()
    
    try:
        df = pd.read_csv(config.SPREAD_ANALYSIS_CSV)
        df['date'] = pd.to_datetime(df['date'])
    except (FileNotFoundError, KeyError) as e:
        print(f"[错误] 加载或处理分析文件时出错: {e}。")
        return

    # --- 任务1: 生成All-in-One合并图 ---
    print("正在生成All-in-One合并图表...")
    fig1, ax1 = plt.subplots(figsize=(20, 12))
    fig1.suptitle(f'{config.STOCK_NAME}({config.STOCK_CODE}) 全指标合并分析图', fontsize=20, y=0.92)

    # --- 终极修复：手动控制所有Y轴的层级和透明度 ---

    # Y轴3 (右2): 性价比 (背景) - 先画，层级最低
    ax3 = ax1.twinx()
    ax3.spines['right'].set_position(('outward', 60))
    p3, = ax3.plot(df['date'], df['股债性价比'], color='lightgrey', label='股债性价比', zorder=1) # 层级1
    ax3.set_ylabel('股债性价比 (倍数)', fontsize=12, color='grey')
    ax3.tick_params(axis='y', colors='grey')
    ax3.patch.set_visible(False) # <--- 让此轴的背景透明

    # Y轴2 (右1): 股价 (配角) - 后画，层级中等
    ax2 = ax1.twinx()
    p2, = ax2.plot(df['date'], df['收盘价(前复权)(元)'], color='dodgerblue', label='股价(前复权)', zorder=5) # 层级5
    ax2.set_ylabel('股价 (元)', fontsize=12, color='dodgerblue')
    ax2.tick_params(axis='y', colors='dodgerblue')
    ax2.patch.set_visible(False) # <--- 让此轴的背景透明

    # Y轴1 (左): 温度计 (主角) - 最后画，拥有不透明背景和最高层级
    p1, = ax1.plot(df['date'], df['温度计'], color='red', label='温度计', zorder=10, lw=2) # 层级10
    ax1.set_ylabel('温度计 (0-100, 越低越好)', color='red', fontsize=12)
    ax1.set_ylim(0, 100)
    ax1.set_yticks(range(0, 101, 10))
    ax1.axhline(y=50, color='grey', linestyle=':', lw=1.5)
    ax1.tick_params(axis='y', colors='red')
    ax1.patch.set_visible(True) # <--- 确保主轴背景不透明

    # 统一图例和X轴
    ax1.set_xlabel('日期', fontsize=12)
    ax1.legend(handles=[p1, p2, p3], loc='upper left')
    ax1.grid(True, linestyle='--', alpha=0.6, zorder=1)
    
    # 保存图1
    output_path_with_price = config.SPREAD_PLOT_IMAGE_PATH
    os.makedirs(os.path.dirname(output_path_with_price), exist_ok=True)
    plt.savefig(output_path_with_price, dpi=300, bbox_inches='tight')
    plt.close(fig1)
    print(f"All-in-One合并图已保存至: {output_path_with_price}")

    # --- 任务2: 生成独立核心指标图 ---
    print("正在生成独立的核心指标图表...")
    fig2, ax_core = plt.subplots(figsize=(20, 10))
    fig2.suptitle(f'{config.STOCK_NAME}({config.STOCK_CODE}) 核心指标分析', fontsize=20, y=0.92)
    
    ax_core_twin = ax_core.twinx()
    p_core2, = ax_core_twin.plot(df['date'], df['股债性价比'], color='lightgrey', label='股债性价比', zorder=1)
    ax_core_twin.set_ylabel('股债性价比 (倍数)', color='grey', fontsize=12)
    ax_core_twin.tick_params(axis='y', colors='grey')
    ax_core_twin.patch.set_visible(False)

    p_core1, = ax_core.plot(df['date'], df['温度计'], color='red', label='温度计 (历史百分位)', zorder=10, lw=2)
    ax_core.set_ylabel('温度计 (0-100, 越低越好)', color='red', fontsize=12)
    ax_core.set_ylim(0, 100)
    ax_core.set_yticks(range(0, 101, 10))
    ax_core.axhline(y=50, color='grey', linestyle=':', lw=1.5)
    ax_core.tick_params(axis='y', colors='red')
    ax_core.patch.set_visible(True)
    
    ax_core.set_xlabel('日期', fontsize=12)
    ax_core.legend(handles=[p_core1, p_core2], loc='upper left')
    ax_core.grid(True, linestyle='--', alpha=0.6)

    # 保存图2
    output_path_standalone = config.SPREAD_PLOT_IMAGE_STANDALONE_PATH
    os.makedirs(os.path.dirname(output_path_standalone), exist_ok=True)
    plt.savefig(output_path_standalone, dpi=300, bbox_inches='tight')
    plt.close(fig2)
    print(f"独立核心指标图已保存至: {output_path_standalone}")

    print("-" * 30)
    print("所有可视化图表生成成功！")
    print("-" * 30)

if __name__ == '__main__':
    visualize_spread() 