import pandas as pd
import os
import glob
from datetime import datetime

def province_convert(province):
    provdict = {
        '北京市': 'BJ', '上海市': 'SH', '天津市': 'TJ', '重庆市': 'CQ',
        '河北省': 'HE', '山西省': 'SX', '内蒙古自治区': 'NM', '辽宁省': 'LN',
        '吉林省': 'JL', '黑龙江省': 'HL', '江苏省': 'JS', '浙江省': 'ZJ',
        '安徽省': 'AH', '福建省': 'FJ', '江西省': 'JX', '山东省': 'SD',
        '河南省': 'HA', '湖北省': 'HB', '湖南省': 'HN', '广东省': 'GD',
        '广西壮族自治区': 'GX', '海南省': 'HI', '四川省': 'SC', '贵州省': 'GZ',
        '云南省': 'YN', '西藏自治区': 'XZ', '陕西省': 'SN', '甘肃省': 'GS',
        '青海省': 'QH', '宁夏回族自治区': 'NX', '新疆维吾尔族自治区': 'XJ',
        '台湾省': 'TW', '香港特别行政区': 'HK', '澳门特别行政区': 'MO'
    }
    return provdict.get(str(province).strip(), 'CN')

def process_file(file_path):
    try:
        # 1. 读取 Excel
        df = pd.read_excel(file_path)
        df.columns = [str(c).strip() for c in df.columns]

        # 2. 定位地点列 (IUCN受胁级别的前一列)
        try:
            iucn_pos = list(df.columns).index('IUCN受胁级别')
            loc_col_name = df.columns[iucn_pos - 1]
        except ValueError:
            return "跳过：找不到 'IUCN受胁级别' 列"

        ebird_data = []
        for index, row in df.iterrows():
            # --- 鸟种俗名处理 (纯简体) ---
            common_name = str(row.get('中文名', '')).strip()
            
            # 特殊单字鸟名硬映射，确保能通过 eBird 校验
            special_map = {
                "鹗": "鹗 (鱼鹰)",
                "隼": "隼形目未知"
            }
            
            if common_name in special_map:
                common_name = special_map[common_name]
            
            # 长度检查：eBird 要求俗名至少 2 个字符
            if len(common_name) < 2:
                common_name += " "

            # 使用字段名：拉丁名
            sci_name = str(row.get('拉丁名', '')).strip()
            
            # 数量处理
            count_val = row.get('鸟种数量', 1)
            count = int(count_val) if pd.notnull(count_val) and count_val > 0 else 1
            obs_note = "heard" if (pd.notnull(count_val) and count_val == 0) else ""
            
            # 时间与时长 (eBird 限制 0-1440 min)
            start_dt = pd.to_datetime(row['观测开始时间'])
            end_dt = pd.to_datetime(row['观测结束时间'])
            duration = int((end_dt - start_dt).total_seconds() / 60)
            
            duration_remark = ""
            if duration > 1440 or duration < 0:
                duration_remark = f" [Time Error: {duration}min]"
                duration = 1440 # 熔断处理
            elif duration < 1:
                duration = 1
            
            # 默认提取报告编号写入备注
            report_id = str(row.get('报告编号', 'Unknown'))
            remarks = f"Originally uploaded to birdreport.cn, record id = {report_id}.{duration_remark}"

            # eBird 19 列标准格式
            items = [''] * 19
            items[0] = common_name                       # 0: 俗名
            items[2] = sci_name                         # 2: 拉丁名
            items[3] = count                            # 3: 数量
            items[4] = obs_note                         # 4: 备注
            items[5] = str(row.get(loc_col_name, '')).strip() # 5: 地点
            items[8] = start_dt.strftime('%m/%d/%Y')    # 8: 日期
            items[9] = start_dt.strftime('%H:%M')       # 9: 时间
            items[10] = province_convert(row['省'])      # 10: 省份
            items[11] = 'CN'                             # 11: 国家
            items[12] = 'stationary'                     # 12: 协议
            items[13] = '1'                              # 13: 人数
            items[14] = duration                         # 14: 时长
            items[15] = 'Y'                              # 15: 记录完整
            items[18] = remarks                          # 18: 记录备注
            
            ebird_data.append(items)
            
        # 导出 CSV
        outfile = os.path.splitext(file_path)[0] + '_ebird.csv'
        pd.DataFrame(ebird_data).to_csv(outfile, index=False, header=False, encoding='utf-8-sig')
        return f"成功：转换 {len(ebird_data)} 条记录 (简体版)"

    except Exception as e:
        return f"失败：{e}"

def batch_convert():
    # 默认当前脚本所在路径
    current_dir = os.getcwd()
    print(f"=== 自动转换工具 (目录: {current_dir}) ===")
    
    # 扫描目录下所有 Excel 文件
    files = glob.glob(os.path.join(current_dir, "*.xlsx")) + glob.glob(os.path.join(current_dir, "*.xls"))
    
    # 排除 Excel 临时文件
    files = [f for f in files if "~$" not in f]

    if not files:
        print("未发现 Excel 文件，请确保脚本与文件在同一文件夹。")
        return

    print(f"发现 {len(files)} 个文件，开始自动处理...\n")
    
    for f in files:
        filename = os.path.basename(f)
        result = process_file(f)
        print(f"[{filename}] -> {result}")

    print("\n任务完成！CSV 已生成在同级目录。")

if __name__ == '__main__':
    batch_convert()