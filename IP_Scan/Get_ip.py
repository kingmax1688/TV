import os
import re
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

IP_DIR = "IP_Scan/ip"
if not os.path.exists(IP_DIR):
    os.makedirs(IP_DIR)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def fetch_ips_from_html(url):
    """从 HTML 中提取所有 IP:端口"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"❌ 请求失败: {resp.status_code}")
            return []
        html = resp.text
        # 匹配 IP:端口（可能包含在链接、表格等中）
        pattern = r'(\d+\.\d+\.\d+\.\d+):(\d+)'
        matches = re.findall(pattern, html)
        # 去重
        ips = list(set([f"{ip}:{port}" for ip, port in matches if int(port) >= 1 and int(port) <= 65535]))
        print(f"✅ 从 HTML 提取到 {len(ips)} 个 IP:端口")
        return ips
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return []

def get_isp_and_region(ip):
    """通过 ip-api.com 获取运营商和省份"""
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                isp_raw = data.get("isp", "")
                region = data.get("regionName", "未知")
                # 判断运营商
                if "联通" in isp_raw or "Unicom" in isp_raw:
                    isp = "联通"
                elif "移动" in isp_raw or "Mobile" in isp_raw:
                    isp = "移动"
                else:
                    isp = "未知"
                return region, isp
    except:
        pass
    return None, None

def save_ips_by_region(ips):
    """按省份和运营商分类保存（仅保留联通和移动）"""
    # 先查询所有 IP 的运营商和省份（多线程）
    ip_info = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(get_isp_and_region, ip.split(":")[0]): ip for ip in ips}
        for future in as_completed(futures):
            ip_port = futures[future]
            region, isp = future.result()
            if region and isp and isp in ("联通", "移动"):
                ip_info[ip_port] = (region, isp)

    # 按省份+运营商分组
    groups = {}
    for ip_port, (region, isp) in ip_info.items():
        filename = f"{region}{isp}.txt"
        groups.setdefault(filename, set()).add(ip_port)

    # 写入文件
    for filename, ip_set in groups.items():
        filepath = os.path.join(IP_DIR, filename)
        # 读取已有内容去重
        existing = set()
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                existing.update(line.strip() for line in f if line.strip())
        all_ips = existing.union(ip_set)
        with open(filepath, 'w', encoding='utf-8') as f:
            for ip in sorted(all_ips):
                f.write(ip + '\n')
        print(f"💾 保存 {filename}: {len(all_ips)} 个IP")

    print(f"✅ 总共保存到 {len(groups)} 个文件")

def main():
    print("🚀 从 tonkiang.us 获取酒店源 IP...")
    url = "https://tonkiang.us/iptvhotelx.php"
    ips = fetch_ips_from_html(url)
    if not ips:
        print("❌ 未获取到任何 IP，退出")
        return
    save_ips_by_region(ips)

if __name__ == "__main__":
    main()
