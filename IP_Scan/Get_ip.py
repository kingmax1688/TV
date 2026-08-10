import os
import re
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

IP_DIR = "IP_Scan/ip"
if not os.path.exists(IP_DIR):
    os.makedirs(IP_DIR)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://tonkiang.us/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

def fetch_ips_from_html(url, retries=3):
    """带重试的 HTML 获取，返回 IP:端口 列表"""
    session = requests.Session()
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                html = resp.text
                # 如果 HTML 为空或太短，可能被反爬
                if len(html) < 1000:
                    print(f"⚠️ 第 {attempt+1} 次尝试：HTML 内容过短，可能被反爬")
                    time.sleep(2)
                    continue
                # 匹配 IP:端口
                pattern = r'(\d+\.\d+\.\d+\.\d+):(\d+)'
                matches = re.findall(pattern, html)
                ips = list(set([f"{ip}:{port}" for ip, port in matches if int(port) >= 1 and int(port) <= 65535]))
                print(f"✅ 从 HTML 提取到 {len(ips)} 个 IP:端口")
                return ips
            elif resp.status_code == 403:
                print(f"❌ 第 {attempt+1} 次尝试：403 禁止访问，可能需添加更多头部或使用代理")
                time.sleep(3)
            else:
                print(f"❌ 第 {attempt+1} 次尝试：状态码 {resp.status_code}")
                time.sleep(2)
        except Exception as e:
            print(f"❌ 第 {attempt+1} 次尝试请求失败: {e}")
            time.sleep(2)
    return []

def get_isp_and_region(ip):
    """通过 ip-api.com 获取运营商和省份（增加重试）"""
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
    if not ips:
        print("⚠️ 没有 IP 可保存")
        return
    # 多线程查询 IP 信息
    ip_info = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_isp_and_region, ip.split(":")[0]): ip for ip in ips}
        for future in as_completed(futures):
            ip_port = futures[future]
            region, isp = future.result()
            if region and isp and isp in ("联通", "移动"):
                ip_info[ip_port] = (region, isp)

    if not ip_info:
        print("⚠️ 没有找到联通或移动的 IP")
        return

    groups = {}
    for ip_port, (region, isp) in ip_info.items():
        filename = f"{region}{isp}.txt"
        groups.setdefault(filename, set()).add(ip_port)

    for filename, ip_set in groups.items():
        filepath = os.path.join(IP_DIR, filename)
        existing = set()
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                existing.update(line.strip() for line in f if line.strip())
        all_ips = existing.union(ip_set)
        with open(filepath, 'w', encoding='utf-8') as f:
            for ip in sorted(all_ips):
                f.write(ip + '\n')
        print(f"💾 保存 {filename}: {len(all_ips)} 个IP")

def main():
    print("🚀 从 tonkiang.us 获取酒店源 IP...")
    url = "https://tonkiang.us/iptvhotelx.php"
    ips = fetch_ips_from_html(url)
    if not ips:
        print("❌ 未获取到任何 IP，请检查网络或手动维护 IP 列表")
        print("💡 建议手动访问 https://tonkiang.us/iptvhotelx.php，搜索'联通'或'移动'，复制 IP 到 Hotel/ip/hotel_ip.txt")
        return
    save_ips_by_region(ips)

if __name__ == "__main__":
    main()
