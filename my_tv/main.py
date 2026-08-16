from threading import Thread
import os
import time
import datetime
from datetime import timezone, timedelta
import glob
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import urllib3
import re
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== 配置区 ====================
# 只处理包含以下运营商关键词的城市
ALLOWED_OPERATORS = ["联通", "移动"]

# 城市特定的测试流地址（仅用于验证IP有效性）
CITY_STREAMS = {
    "北京联通": ["rtp/239.3.1.139:8001"],
    "海南联通": ["rtp/239.254.96.82:7640"],
    "河北联通": ["rtp/239.253.93.245:6423"],
    "天津联通": ["udp/225.1.2.166:5002"],
    "上海联通": ["rtp/233.18.204.58:5140"],
    "浙江联通": ["rtp/233.50.201.118:5140"],
    "重庆联通": ["udp/225.0.4.74:7980"],
}

# 设置工作目录
WORKING_DIR = os.getcwd()
MY_TV_DIR = os.path.join(WORKING_DIR, "my_tv")
OUTPUT_DIR = os.path.join(MY_TV_DIR, "output")


def get_city_config(city_name):
    """根据城市名获取配置"""
    if city_name in CITY_STREAMS:
        return {
            "test_streams": CITY_STREAMS[city_name]
        }
    return None


def get_headers():
    """获取固定的请求头"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Range': 'bytes=0-',
    }


def clean_ip_line(ip_line):
    """清理IP行，移除后面的速度值和多余空格"""
    if not ip_line:
        return ""
    if '#' in ip_line:
        ip_line = ip_line.split('#')[0]
    ip_line = ip_line.strip()
    if 'KB/s' in ip_line:
        kb_s_index = ip_line.find('KB/s')
        if kb_s_index > 0:
            i = kb_s_index - 1
            while i >= 0 and (ip_line[i].isdigit() or ip_line[i] in ' .'):
                i -= 1
            ip_line = ip_line[:i+1].strip()
    if ' ' in ip_line:
        parts = ip_line.split()
        if parts:
            ip_line = parts[0].strip()
    return ip_line


def read_channel_template():
    """读取频道模板文件（从本地 my_tv/template/demo.txt）"""
    template_file = os.path.join(MY_TV_DIR, "template", "demo.txt")
    if not os.path.exists(template_file):
        print(f"✗ 频道模板文件不存在: {template_file}")
        return {}
    
    print(f"读取频道模板文件: {template_file}")
    channel_template = {}
    current_category = None
    current_channels = []
    
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if ",#genre#" in line:
                    if current_category and current_channels:
                        channel_template[current_category] = current_channels.copy()
                    current_category = line.replace(",#genre#", "").strip()
                    current_channels = []
                elif "|" in line:
                    parts = [part.strip() for part in line.split("|") if part.strip()]
                    if len(parts) >= 1:
                        main_channel = parts[0]
                        aliases = parts[1:] if len(parts) > 1 else []
                        current_channels.append((main_channel, aliases))
        if current_category and current_channels:
            channel_template[current_category] = current_channels.copy()
        total_categories = len(channel_template)
        total_channels = sum(len(channels) for channels in channel_template.values())
        print(f"✓ 共读取到 {total_categories} 个分类，总计 {total_channels} 个频道")
        return channel_template
    except Exception as e:
        print(f"✗ 读取频道模板文件错误: {e}")
        return {}


def clean_channel_name(channel_name):
    """清理频道名称，移除特殊符号和空格，统一格式"""
    if not channel_name:
        return ""
    cleaned_name = channel_name.strip()
    cleaned_name = re.sub(r'[【】\[\]()（）\-—－\s]', '', cleaned_name)
    cleaned_name = re.sub(r'CCTV-(\d+)', r'CCTV\1', cleaned_name, flags=re.IGNORECASE)
    return cleaned_name.lower()


def is_channel_match(actual_channel, template_channel):
    """检查实际频道是否匹配模板频道（支持别名）"""
    if not actual_channel or not template_channel:
        return False
    cleaned_actual = clean_channel_name(actual_channel)
    cleaned_template = clean_channel_name(template_channel)
    if not cleaned_actual or not cleaned_template:
        return False
    if cleaned_actual == cleaned_template:
        return True
    if cleaned_template.startswith("cctv"):
        actual_match = re.search(r'cctv(\d+)', cleaned_actual)
        template_match = re.search(r'cctv(\d+)', cleaned_template)
        if actual_match and template_match:
            return actual_match.group(1) == template_match.group(1)
        elif actual_match or template_match:
            return False
        else:
            return cleaned_actual == cleaned_template
    return cleaned_template in cleaned_actual


def get_channel_category(channel_name, channel_template):
    """根据频道名称获取对应的分类"""
    if not channel_name:
        return "其它频道"
    for category, channels in channel_template.items():
        for main_channel, aliases in channels:
            if is_channel_match(channel_name, main_channel):
                return category
            for alias in aliases:
                if is_channel_match(channel_name, alias):
                    return category
    return "其它频道"


def get_main_channel_name(channel_name, channel_template):
    """根据频道名称获取对应的主频道名"""
    if not channel_name:
        return channel_name
    for category, channels in channel_template.items():
        for main_channel, aliases in channels:
            if is_channel_match(channel_name, main_channel):
                return main_channel
            for alias in aliases:
                if is_channel_match(channel_name, alias):
                    return main_channel
    return channel_name


def test_stream_speed(stream_url, timeout=8):
    """测试流媒体速度，返回速度(KB/s)和是否成功"""
    try:
        headers = get_headers()
        start_time = time.time()
        response = requests.get(stream_url, headers=headers, timeout=timeout,
                              verify=False, allow_redirects=True, stream=True)
        if response.status_code not in [200, 206]:
            return 0, False
        downloaded = 0
        chunk_size = 100 * 1024
        max_download = 1000 * 1024
        for chunk in response.iter_content(chunk_size=chunk_size):
            downloaded += len(chunk)
            if downloaded >= max_download:
                break
        end_time = time.time()
        duration = end_time - start_time
        if duration > 0:
            speed_kbs = downloaded / duration / 1024
            return speed_kbs, True
        else:
            return 0, False
    except Exception as e:
        return 0, False


def test_ip_single(ip_port, test_stream, timeout=8):
    """测试单个IP，返回速度"""
    stream_url = f"http://{ip_port}/{test_stream}"
    try:
        time.sleep(random.uniform(0.1, 0.3))
        speed, success = test_stream_speed(stream_url, timeout)
        if success and speed > 0:
            print(f"✓ {ip_port} 可用 - 速度: {speed:.2f} KB/s")
            return ip_port, speed
        else:
            print(f"× {ip_port} 不可用或速度过慢")
            return None, 0
    except Exception as e:
        print(f"× {ip_port} 测试出错: {str(e)[:50]}")
        return None, 0


# ==================== 新增函数：删除失效IP ====================
def delete_invalid_ips(city_name, invalid_ips):
    """
    从 ip.txt 和 对应的 template.txt 中删除失效IP
    """
    # 1. 从 ip.txt 中删除失效IP
    ip_file = os.path.join(MY_TV_DIR, "ip", f"{city_name}_ip.txt")
    if os.path.exists(ip_file):
        try:
            with open(ip_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 过滤掉失效IP行
            new_lines = []
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith('#'):
                    new_lines.append(line)
                    continue
                cleaned_ip = clean_ip_line(line_stripped)
                if cleaned_ip and ':' in cleaned_ip:
                    ip_port = cleaned_ip.split(' ')[0] if ' ' in cleaned_ip else cleaned_ip
                    if ip_port not in invalid_ips:
                        new_lines.append(line)
                    else:
                        print(f"  从 {os.path.basename(ip_file)} 中删除: {ip_port}")

            # 写回文件
            with open(ip_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"✓ 已更新 {os.path.basename(ip_file)}")

        except Exception as e:
            print(f"✗ 更新IP文件失败: {e}")

    # 2. 从对应的 template.txt 中删除包含失效IP的频道行
    template_file = os.path.join(MY_TV_DIR, "template", f"{city_name}.txt")
    if os.path.exists(template_file):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            new_lines = []
            deleted_count = 0
            for line in lines:
                line_stripped = line.strip()
                # 保留分类行和空行
                if not line_stripped or ",#genre#" in line_stripped:
                    new_lines.append(line)
                    continue

                # 检查频道行是否包含失效IP
                should_keep = True
                if ',' in line_stripped:
                    parts = line_stripped.split(',', 1)
                    if len(parts) == 2:
                        url_part = parts[1].strip()
                        # 检查URL中是否包含失效IP
                        for invalid_ip in invalid_ips:
                            if invalid_ip in url_part:
                                should_keep = False
                                deleted_count += 1
                                print(f"  从 {os.path.basename(template_file)} 中删除包含 {invalid_ip} 的频道: {parts[0]}")
                                break

                if should_keep:
                    new_lines.append(line)

            # 写回文件
            with open(template_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"✓ 已更新 {os.path.basename(template_file)}，删除了 {deleted_count} 个频道")

        except Exception as e:
            print(f"✗ 更新模板文件失败: {e}")

    # 3. 如果 ip.txt 为空，删除它
    if os.path.exists(ip_file):
        try:
            with open(ip_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if not content:
                os.remove(ip_file)
                print(f"✓ {os.path.basename(ip_file)} 为空，已删除")
        except:
            pass
# ==================== 新增结束 ====================


# ==================== 修改后的验证函数 ====================
def validate_city_ips(city_name, city_config):
    """
    验证城市IP
    - 从本地 my_tv/ip/{城市名}_ip.txt 读取所有IP
    - 测速验证，记录有效IP
    - 自动从 ip.txt 和 对应的 template.txt 中删除失效IP
    """
    local_ip_file = os.path.join(MY_TV_DIR, "ip", f"{city_name}_ip.txt")
    if not os.path.exists(local_ip_file):
        print(f"本地IP文件不存在: {local_ip_file}")
        return []

    print(f"读取本地IP文件: {local_ip_file}")
    ip_configs = []
    with open(local_ip_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line and not line.startswith('#'):
                cleaned_ip = clean_ip_line(line)
                if cleaned_ip and ':' in cleaned_ip:
                    ip_configs.append(cleaned_ip)

    if not ip_configs:
        print(f"{city_name} 本地IP文件为空")
        return []

    print(f"从本地读取到 {len(ip_configs)} 个IP")

    test_stream = city_config.get("test_streams", [None])[0]
    if not test_stream:
        print(f"✗ {city_name} 没有测试流，无法验证IP")
        return [(ip, 0) for ip in ip_configs]

    print(f"开始测速验证IP...")
    valid_ips = []
    invalid_ips = []  # 记录失效IP

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for ip_port in ip_configs:
            future = executor.submit(test_ip_single, ip_port, test_stream)
            futures[future] = ip_port

        for future in as_completed(futures):
            ip_port = futures[future]
            result_ip, speed = future.result()
            if result_ip and speed > 0:
                valid_ips.append((result_ip, speed))
                print(f"✓ {result_ip} 有效 - 速度: {speed:.2f} KB/s")
            else:
                invalid_ips.append(ip_port)
                print(f"✗ {ip_port} 失效，将被删除")

    # ========== 新增：删除失效IP ==========
    if invalid_ips:
        print(f"\n发现 {len(invalid_ips)} 个失效IP，正在删除...")
        delete_invalid_ips(city_name, invalid_ips)
    else:
        print(f"\n✓ 所有IP均有效")

    # 按速度排序
    valid_ips.sort(key=lambda x: x[1], reverse=True)

    if not valid_ips:
        print(f"⚠️ {city_name} 所有IP均失效，已清空相关文件")
        return []

    return valid_ips
# ==================== 修改结束 ====================


def read_template_file(city_name):
    """读取城市对应的频道模板文件（从本地 my_tv/template/{城市名}.txt）"""
    template_file = os.path.join(MY_TV_DIR, "template", f"{city_name}.txt")
    if not os.path.exists(template_file):
        print(f"✗ 频道模板文件不存在: {template_file}")
        return None
    
    print(f"读取频道模板: {template_file}")
    channels = []
    seen_channels = set()
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or ",#genre#" in line:
                    continue
                if "," in line:
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        channel_name = parts[0].strip()
                        channel_url = parts[1].strip()
                        if channel_name not in seen_channels:
                            seen_channels.add(channel_name)
                            channels.append((channel_name, channel_url))
        print(f"✓ 共读取到 {len(channels)} 个频道")
        return channels
    except Exception as e:
        print(f"✗ 读取模板文件错误: {e}")
        return None


def read_logo_file():
    """读取本地台标文件 my_tv/template/logo.txt"""
    logo_dict = {}
    local_logo_file = os.path.join(MY_TV_DIR, "template", "logo.txt")
    if os.path.exists(local_logo_file):
        try:
            with open(local_logo_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ',' in line:
                        parts = line.split(',', 1)
                        if len(parts) == 2:
                            channel_name = parts[0].strip()
                            logo_url = parts[1].strip()
                            logo_dict[channel_name] = logo_url
            print(f"✓ 读取到 {len(logo_dict)} 个台标")
        except Exception as e:
            print(f"✗ 读取台标文件错误: {e}")
    else:
        print(f"✗ 台标文件不存在: {local_logo_file}")
    return logo_dict


def categorize_channels(channels, channel_template):
    """将频道按照 demo.txt 的分类进行分类"""
    categorized = {}
    for channel_name, channel_url in channels:
        category = get_channel_category(channel_name, channel_template)
        if category not in categorized:
            categorized[category] = []
        categorized[category].append((channel_name, channel_url))
    return categorized


def generate_files_for_city(city_name, top_ips, logo_dict, channels, channel_template):
    """为城市生成 TXT 和 M3U 文件"""
    print(f"\n开始为 {city_name} 生成文件...")
    if not channels:
        print(f"✗ {city_name} 没有频道")
        return
    if not top_ips:
        print(f"✗ {city_name} 没有可用的IP")
        return
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    available_ips = [ip for ip, _ in top_ips]
    print(f"将使用 {len(available_ips)} 个IP: {available_ips}")
    
    categorized_channels = categorize_channels(channels, channel_template)
    txt_file = os.path.join(OUTPUT_DIR, f"{city_name}.txt")
    m3u_file = os.path.join(OUTPUT_DIR, f"{city_name}.m3u")
    
    try:
        with open(txt_file, 'w', encoding='utf-8') as txt_f:
            for category, channel_list in categorized_channels.items():
                txt_f.write(f"{category},#genre#\n")
                for channel_name, channel_url in channel_list:
                    for ip_port in available_ips:
                        new_url = channel_url.replace("ipipip", ip_port)
                        txt_f.write(f"{channel_name},{new_url}${city_name}\n")
        print(f"✓ TXT文件生成: {txt_file}")
        
        with open(m3u_file, 'w', encoding='utf-8') as m3u_f:
            m3u_f.write("#EXTM3U\n")
            for category, channel_list in categorized_channels.items():
                for channel_name, channel_url in channel_list:
                    for ip_port in available_ips:
                        new_url = channel_url.replace("ipipip", ip_port)
                        logo_url = logo_dict.get(channel_name, "")
                        if logo_url:
                            m3u_f.write(f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" tvg-logo="{logo_url}" group-title="{category}",{channel_name}\n')
                        else:
                            m3u_f.write(f'#EXTINF:-1 tvg-id="{channel_name}" tvg-name="{channel_name}" group-title="{category}",{channel_name}\n')
                        m3u_f.write(f"{new_url}\n")
        print(f"✓ M3U文件生成: {m3u_file}")
    except Exception as e:
        print(f"✗ 生成文件错误: {e}")


def get_ip_speed(ip_port, city_name):
    """从IP文件中获取IP的速度"""
    ip_file = os.path.join(MY_TV_DIR, "ip", f"{city_name}_ip.txt")
    if not os.path.exists(ip_file):
        return 0
    try:
        with open(ip_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if ip_port in line and "KB/s" in line:
                    parts = line.split()
                    for part in parts[1:]:
                        if 'KB/s' in part:
                            speed_str = part.replace('KB/s', '')
                            try:
                                return float(speed_str)
                            except ValueError:
                                pass
    except:
        pass
    return 0


def merge_all_files(channel_template, max_sources_per_channel=10):
    """合并所有城市的文件，按频道模板排序，每个频道最多保留 max_sources_per_channel 个源"""
    print(f"\n开始合并所有文件...")
    output_files = []
    if os.path.exists(OUTPUT_DIR):
        for file in os.listdir(OUTPUT_DIR):
            file_path = os.path.join(OUTPUT_DIR, file)
            if os.path.isfile(file_path) and file.endswith(('.txt', '.m3u')):
                output_files.append(file_path)
    
    txt_files = [f for f in output_files if f.endswith('.txt')]
    if not txt_files:
        print("✗ 没有找到TXT文件可合并")
        return
    
    logo_dict = read_logo_file()
    try:
        now = datetime.datetime.now(timezone.utc) + timedelta(hours=8)
    except:
        now = datetime.datetime.utcnow() + timedelta(hours=8)
    current_time = now.strftime("%Y/%m/%d %H:%M")
    
    all_channels_with_sources = {}
    for txt_file in txt_files:
        city_name = os.path.basename(txt_file).replace('.txt', '')
        print(f"处理: {txt_file} (城市: {city_name})")
        with open(txt_file, 'r', encoding='utf-8') as f:
            current_category = ""
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if ",#genre#" in line:
                    current_category = line.replace(",#genre#", "").strip()
                elif line and "," in line and current_category:
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        channel_name = parts[0].strip()
                        channel_part = parts[1].strip()
                        if "$" in channel_part:
                            channel_url, city = channel_part.rsplit("$", 1)
                        else:
                            channel_url = channel_part
                            city = city_name
                        url_parts = channel_url.split('/')
                        if len(url_parts) >= 3:
                            ip_port = url_parts[2]
                            speed = get_ip_speed(ip_port, city)
                            main_channel_name = get_main_channel_name(channel_name, channel_template)
                            if main_channel_name not in all_channels_with_sources:
                                all_channels_with_sources[main_channel_name] = []
                            all_channels_with_sources[main_channel_name].append((speed, channel_name, channel_url, city, ip_port))
    
    print(f"总共收集到 {len(all_channels_with_sources)} 个不同的频道")
    
    organized_channels = {}
    for category in channel_template.keys():
        organized_channels[category] = {}
    organized_channels["其它频道"] = {}
    
    for main_channel_name, sources in all_channels_with_sources.items():
        sources.sort(key=lambda x: x[0], reverse=True)
        limited_sources = sources[:max_sources_per_channel]
        category = get_channel_category(main_channel_name, channel_template)
        if category not in organized_channels:
            organized_channels[category] = {}
        if main_channel_name not in organized_channels[category]:
            organized_channels[category][main_channel_name] = []
        for speed, original_channel_name, url, city, ip_port in limited_sources:
            organized_channels[category][main_channel_name].append((original_channel_name, url, city))
    
    merged_txt_file = os.path.join(MY_TV_DIR, "zubo_all.txt")
    with open(merged_txt_file, "w", encoding="utf-8") as f:
        f.write(f"{current_time}更新,#genre#\n")
        f.write(f"浙江卫视,http://ali-m-l.cztv.com/channels/lantian/channel001/1080p.m3u8\n")
        for category in channel_template.keys():
            if category in organized_channels and organized_channels[category]:
                f.write(f"{category},#genre#\n")
                for main_channel, aliases in channel_template[category]:
                    if main_channel in organized_channels[category]:
                        for original_channel_name, url, city in organized_channels[category][main_channel]:
                            f.write(f"{main_channel},{url}${city}\n")
        if organized_channels.get("其它频道") and organized_channels["其它频道"]:
            f.write(f"其它频道,#genre#\n")
            other_channels = sorted(organized_channels["其它频道"].keys())
            for main_channel in other_channels:
                for original_channel_name, url, city in organized_channels["其它频道"][main_channel]:
                    f.write(f"{main_channel},{url}${city}\n")
    
    print(f"✓ 合并TXT文件: {merged_txt_file}")
    
    merged_m3u_file = os.path.join(MY_TV_DIR, "zubo_all.m3u")
    with open(merged_m3u_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        zjws_logo = logo_dict.get("浙江卫视", "")
        if zjws_logo:
            f.write(f'#EXTINF:-1 tvg-id="" tvg-name="浙江卫视" tvg-logo="{zjws_logo}" group-title="示例频道",浙江卫视\n')
        else:
            f.write(f'#EXTINF:-1 tvg-id="" tvg-name="浙江卫视" group-title="示例频道",浙江卫视\n')
        f.write(f"http://ali-m-l.cztv.com/channels/lantian/channel001/1080p.m3u8\n")
        
        for category in channel_template.keys():
            if category in organized_channels and organized_channels[category]:
                for main_channel, aliases in channel_template[category]:
                    if main_channel in organized_channels[category]:
                        for original_channel_name, url, city in organized_channels[category][main_channel]:
                            logo_url = logo_dict.get(original_channel_name, "")
                            display_name = f"{main_channel}"
                            if logo_url:
                                f.write(f'#EXTINF:-1 tvg-id="{main_channel}" tvg-name="{main_channel}" tvg-logo="{logo_url}" group-title="{category}",{display_name}\n')
                            else:
                                f.write(f'#EXTINF:-1 tvg-id="{main_channel}" tvg-name="{main_channel}" group-title="{category}",{display_name}\n')
                            f.write(f"{url}\n")
        
        if organized_channels.get("其它频道") and organized_channels["其它频道"]:
            other_channels = sorted(organized_channels["其它频道"].keys())
            for main_channel in other_channels:
                for original_channel_name, url, city in organized_channels["其它频道"][main_channel]:
                    logo_url = logo_dict.get(original_channel_name, "")
                    display_name = f"{main_channel}"
                    if logo_url:
                        f.write(f'#EXTINF:-1 tvg-id="" tvg-name="{main_channel}" tvg-logo="{logo_url}" group-title="其它频道",{display_name}\n')
                    else:
                        f.write(f'#EXTINF:-1 tvg-id="" tvg-name="{main_channel}" group-title="其它频道",{display_name}\n')
                    f.write(f"{url}\n")
    
    print(f"✓ 合并M3U文件: {merged_m3u_file}")
    
    simple_txt_file = os.path.join(MY_TV_DIR, "zubo_simple.txt")
    with open(simple_txt_file, "w", encoding="utf-8") as f:
        f.write(f"{current_time}更新,#genre#\n")
        for category in channel_template.keys():
            if category in organized_channels and organized_channels[category]:
                f.write(f"{category},#genre#\n")
                written_channels = set()
                for main_channel, aliases in channel_template[category]:
                    if main_channel in organized_channels[category] and organized_channels[category][main_channel]:
                        for original_channel_name, url, city in organized_channels[category][main_channel]:
                            if main_channel not in written_channels:
                                f.write(f"{main_channel},{url}\n")
                                written_channels.add(main_channel)
                                break
        if organized_channels.get("其它频道") and organized_channels["其它频道"]:
            f.write(f"其它频道,#genre#\n")
            written_channels = set()
            other_channels = sorted(organized_channels["其它频道"].keys())
            for main_channel in other_channels:
                if main_channel not in written_channels and organized_channels["其它频道"][main_channel]:
                    for original_channel_name, url, city in organized_channels["其它频道"][main_channel]:
                        f.write(f"{main_channel},{url}\n")
                        written_channels.add(main_channel)
                        break
    
    print(f"✓ 生成简化版TXT: {simple_txt_file}")


def main():
    print("="*60)
    print("组播源处理系统 (本地模式)")
    print(f"工作目录: {WORKING_DIR}")
    print(f"数据目录: {MY_TV_DIR}")
    print(f"仅处理运营商: {ALLOWED_OPERATORS}")
    print("="*60)
    
    # 清理旧的输出目录
    if os.path.exists(OUTPUT_DIR):
        for file in os.listdir(OUTPUT_DIR):
            try:
                os.remove(os.path.join(OUTPUT_DIR, file))
            except:
                pass
    
    # 创建必要的目录
    os.makedirs(os.path.join(MY_TV_DIR, "ip"), exist_ok=True)
    os.makedirs(os.path.join(MY_TV_DIR, "template"), exist_ok=True)
    os.makedirs(os.path.join(MY_TV_DIR, "output"), exist_ok=True)
    
    # 读取频道模板（demo.txt）
    print(f"\n步骤1: 读取频道模板...")
    channel_template = read_channel_template()
    if not channel_template:
        print("✗ 无法读取频道模板，程序退出")
        return
    
    # 处理每个城市
    processed_cities = []
    
    for city_name in CITY_STREAMS:
        # 运营商过滤
        if not any(op in city_name for op in ALLOWED_OPERATORS):
            print(f"跳过 {city_name}（非允许运营商）")
            continue
        
        print(f"\n{'='*60}")
        print(f"处理城市: {city_name}")
        print(f"{'='*60}")
        
        city_config = get_city_config(city_name)
        if not city_config:
            print(f"✗ 无法获取城市配置: {city_name}")
            continue
        
        # 步骤1: 读取本地IP列表并验证
        print(f"步骤1: 验证本地IP...")
        top_ips = validate_city_ips(city_name, city_config)
        if not top_ips:
            print(f"✗ {city_name} 没有可用IP，跳过")
            continue
        
        print(f"✓ {city_name} 共有 {len(top_ips)} 个可用IP")
        for i, (ip, speed) in enumerate(top_ips, 1):
            print(f"  第{i}名: {ip} - 速度: {speed:.2f} KB/s")
        
        # 步骤2: 读取本地频道模板
        print(f"步骤2: 读取本地频道模板...")
        channels = read_template_file(city_name)
        if not channels:
            print(f"✗ {city_name} 没有频道，跳过")
            continue
        
        # 步骤3: 读取台标文件
        print(f"步骤3: 读取台标文件...")
        logo_dict = read_logo_file()
        
        # 步骤4: 生成文件
        print(f"步骤4: 生成输出文件...")
        generate_files_for_city(city_name, top_ips, logo_dict, channels, channel_template)
        processed_cities.append(city_name)
        time.sleep(2)
    
    print(f"\n{'='*60}")
    print(f"城市处理完成:")
    print(f"  成功处理: {processed_cities}")
    print(f"{'='*60}")
    
    if processed_cities:
        print(f"\n开始合并所有文件...")
        merge_all_files(channel_template, max_sources_per_channel=10)
    else:
        print(f"\n✗ 没有成功处理任何城市")
    
    print(f"\n{'='*60}")
    print("所有处理完成！")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"合并文件: {os.path.join(MY_TV_DIR, 'zubo_all.txt')}")
    print(f"合并文件: {os.path.join(MY_TV_DIR, 'zubo_all.m3u')}")
    print(f"简化文件: {os.path.join(MY_TV_DIR, 'zubo_simple.txt')}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
