# updater/updater_treasury.py
# 负责使用 akshare 下载或更新中美十年期国债利率数据。

import os
import sys
import pandas as pd
from datetime import datetime
import akshare as ak
import common.config as config
from common.utils import check_if_update_should_be_skipped, find_existing_data_file

def update_treasury_bond_data(weekend_no_update=True):
    """
    下载或更新中美十年期国债利率数据。
    采用"先检查，后下载"的高效策略。
    
    :param weekend_no_update: 是否考虑周末不更新数据的情况，默认为True
    """
    print("\n--- 开始更新中美十年期国债利率数据 ---")
    
    # --- 1. 使用通用函数查找文件并检查是否需要更新 ---
    base_filename = os.path.basename(config.TREASURY_BOND_CSV)
    existing_file_path = find_existing_data_file(base_filename)
    
    if check_if_update_should_be_skipped(
        file_path=existing_file_path,
        date_column_name='日期',      # <--- 修正：国债数据文件中的日期列名为'日期'
        force_refresh_flag=config.FORCE_FULL_DATA_REFRESH,
        weekend_no_update=weekend_no_update
    ):
        return # 如果通用函数决定跳过，则直接退出
    
    # --- 2. 如果程序能走到这里，说明需要联网更新 ---
    print("本地数据已过时或不存在，或已配置强制刷新，需要联网更新。")
        
    try:
        print("正在通过 akshare 获取在线数据...")
        ak_df = ak.bond_zh_us_rate()
        print("akshare 数据获取成功。")
    except Exception as e:
        print(f"通过 akshare 获取数据时发生错误: {e}")
        return

    # --- 3. 数据预处理 ---
    ak_df.rename(columns={
        '日期': 'date',
        '中国国债收益率10年': '十年',
        '美国国债收益率10年': 'us_ten_year_rate'
    }, inplace=True)
    ak_df['date'] = pd.to_datetime(ak_df['date'])
    
    # 将利率从字符串转为数值，并处理异常值
    ak_df['十年'] = pd.to_numeric(ak_df['十年'], errors='coerce')
    ak_df['us_ten_year_rate'] = pd.to_numeric(ak_df['us_ten_year_rate'], errors='coerce')

    # --- 4. 模式选择与数据更新 ---
    # 由于检查逻辑已前置，这里的逻辑可以简化
    # 我们总是执行合并去重，这是最安全、最健壮的策略
    
    existing_df = pd.DataFrame()
    if existing_file_path:
        try:
            existing_df = pd.read_csv(existing_file_path)
            # 兼容'日期'和'date'两种列名
            if '日期' in existing_df.columns:
                existing_df.rename(columns={'日期': 'date'}, inplace=True)
            existing_df['date'] = pd.to_datetime(existing_df['date'])
        except Exception as e:
            print(f"读取本地文件 {existing_file_path} 时出错: {e}，将只使用在线数据。")

    print("执行模式：全量合并去重。")
    combined_df = pd.concat([existing_df, ak_df], ignore_index=True)
    combined_df.drop_duplicates(subset=['date'], keep='last', inplace=True)
    combined_df.sort_values(by='date', inplace=True)
    
    # --- 5. 按起始日期过滤 ---
    start_date = datetime.strptime(config.DATA_START_DATE, "%Y-%m-%d")
    final_df = combined_df[combined_df['date'] >= start_date].copy()
    
    # 重命名日期列以符合项目规范
    final_df.rename(columns={'date': '日期'}, inplace=True)

    # --- 6. 保存到 data/auto/ 目录 ---
    output_path = config.TREASURY_BOND_CSV
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    final_df.to_csv(output_path, index=False, encoding='utf-8-sig', float_format='%.4f')
    
    print("-" * 30)
    print("中美十年期国债利率数据更新完成！")
    print(f"总共 {len(final_df)} 条记录。")
    print(f"数据已保存至: {output_path}")
    print("-" * 30)

if __name__ == '__main__':
    # 当此脚本被直接运行时，可以用于独立测试
    print("正在独立运行中美十年期国债利率更新脚本...")
    update_treasury_bond_data()
    print("独立运行结束。")