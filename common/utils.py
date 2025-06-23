import pandas as pd
import os
from datetime import datetime, timedelta
import sys
import platform
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入项目配置
from common import config

def find_existing_data_file(filename):
    """
    按优先级查找已存在的数据文件。
    优先级1: data/auto/ 目录 (脚本自动生成的数据)
    优先级2: data/hand/ 目录 (手动维护的数据)
    
    :param filename: 文件名（不含路径）
    :return: 文件的完整路径，如果都不存在则返回None
    """
    # 优先级1: data/auto/ 目录
    auto_path = os.path.join(config.DATA_AUTO_UPDATE_DIR, filename)
    if os.path.exists(auto_path):
        print(f"在自动更新目录中找到数据文件: {auto_path}")
        return auto_path
        
    # 优先级2: data/hand/ 目录
    hand_path = os.path.join(config.DATA_HAND_UPDATE_DIR, filename)
    if os.path.exists(hand_path):
        print(f"在手动更新目录中找到数据文件: {hand_path}")
        return hand_path
        
    print(f"未找到数据文件: {filename}")
    return None

def check_if_update_should_be_skipped(file_path, date_column_name, force_refresh_flag, weekend_no_update=True):
    """
    通用函数，用于检查本地数据是否已是最新，从而决定是否跳过网络更新。

    :param file_path: 要检查的CSV文件的完整路径。
    :param date_column_name: 文件中日期列的名称。
    :param force_refresh_flag: 是否强制刷新的布尔开关。
    :param weekend_no_update: 是否考虑周末不更新数据的情况。
    :return: 如果应跳过更新，则返回 True；否则返回 False。
    """
    if not file_path:
        # 如果文件路径为空或None，说明文件不存在，必须从网络获取，不能跳过
        return False
        
    if force_refresh_flag:
        print("配置中已设置强制刷新，将执行网络更新。")
        return False

    if not os.path.exists(file_path):
        # 文件不存在，必须从网络获取，不能跳过
        return False

    try:
        # 高效读取，只加载指定的日期列
        df_existing = pd.read_csv(file_path, usecols=[date_column_name])
        if df_existing.empty:
            # 文件存在但为空，需要更新
            return False

        latest_date = pd.to_datetime(df_existing[date_column_name]).max()
        current_date = datetime.now().date()
        
        # 计算最新数据日期与当前日期之间的天数差
        days_diff = (current_date - latest_date.date()).days
        
        # 考虑周末不更新的情况
        if weekend_no_update:
            # 获取当前是星期几（0=周一，6=周日）
            current_weekday = current_date.weekday()
            
            # 如果今天是周六（5）或周日（6），且最新数据是周五或之前不超过2天
            if current_weekday >= 5:  # 周六或周日
                # 找到上一个周五的日期
                last_friday = current_date - timedelta(days=(current_weekday - 4))
                
                # 如果最新数据日期是上一个周五或之后的日期，视为最新
                if latest_date.date() >= last_friday:
                    print(f"数据文件 {os.path.basename(file_path)} 已是最新 (本地数据日期: {latest_date.strftime('%Y-%m-%d')})，今天是周末，数据源通常不更新，无需联网更新。")
                    return True
            
            # 如果今天是周一（0），且最新数据是上周五，视为最新
            elif current_weekday == 0:  # 周一
                last_friday = current_date - timedelta(days=3)
                if latest_date.date() >= last_friday:
                    print(f"数据文件 {os.path.basename(file_path)} 已是最新 (本地数据日期: {latest_date.strftime('%Y-%m-%d')})，上周末数据源通常不更新，无需联网更新。")
                    return True
        
        # 如果不是特殊情况（周末），则使用常规的判断逻辑
        if days_diff <= 1:
            print(f"数据文件 {os.path.basename(file_path)} 已是最新 (本地数据日期: {latest_date.strftime('%Y-%m-%d')})，无需联网更新。")
            return True
        else:
            # 数据不是最新的，需要更新
            return False

    except FileNotFoundError:
        # 文件不存在的另一种情况
        return False
    except (KeyError, ValueError) as e:
        print(f"检查本地数据时出错 (文件: {os.path.basename(file_path)}, 错误: {e})。将继续执行网络更新。")
        # 发生错误，最好还是更新一下以修复文件
        return False
    
    # 默认情况下，需要更新
    return False

def set_chinese_font():
    """
    自动设置支持中文的字体，以确保图表在不同操作系统上都能正确显示中文。
    """
    os_type = platform.system()
    
    if os_type == 'Darwin':  # macOS
        font_names = ['Hei', 'Hiragino Sans GB', 'STHeiti', 'Heiti SC', 'Songti SC', 'Arial Unicode MS']
    elif os_type == 'Windows':
        font_names = ['SimHei', 'Microsoft YaHei', 'DengXian']
    else:  # Linux
        font_names = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'DejaVu Sans', 'Droid Sans Fallback']
        
    for font_name in font_names:
        # 使用font_manager查找字体，如果找到则设置并返回
        if font_manager.findfont(font_name, fallback_to_default=False):
            plt.rcParams['font.sans-serif'] = [font_name]
            plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号
            print(f"Matplotlib 字体已设置为 '{font_name}' 以支持中文。")
            return

    # 如果上述字体都未找到，给出警告和建议
    print("警告：在您的系统上未找到推荐的中文字体。")
    print("图表中的中文可能无法正常显示。")
    print("建议您根据操作系统安装以下字体之一：")
    if os_type == 'Darwin':
        print(" - macOS: 'PingFang SC' (默认), 'STHeiti', 'Heiti SC'")
    elif os_type == 'Windows':
        print(" - Windows: 'SimHei' (黑体), 'Microsoft YaHei' (微软雅黑)")
    else:
        print(" - Linux: 'WenQuanYi Micro Hei' 或 'WenQuanYi Zen Hei' (可通过包管理器安装)")
