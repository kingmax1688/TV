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

def fetch_tonkiang_ips():
    """从 tonkiang.us 酒店源专页获取 IP:端口 列表"""
    url = "http://tonkiang.us/hoteliptv.php"
    ips = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"❌ 请求失败: {resp.status_code}")
            return ips
        # 提取 IP:端口 格式
        pattern = r'(\d+\.\d+\.\d+\.\d+):(\d+)'
        matches = re.findall(pattern, resp.text)
        for ip, port in matches:
            ips.append(f"{ip}:{port}")
        print(f"✅ 从 tonkiang.us 获取 {len(ips)} 个原始 IP")
    except Exception as e:
        print(f"❌ 爬取失败: {e}")
    return ips

def get_isp_batch(ip_list, batch_size=100):
    """
    使用 ip-api.com 批量查询 IP 所属运营商
    返回字典 {ip_port: "联通"/"移动"/"电信"/"未知"}
    """
    result = {}
    for i in range(0, len(ip_list), batch_size):
        batch = ip_list[i:i+batch_size]
        # 构建批量查询URL
        ips_str = ",".join([item.split(":")[0] for item in batch])
        url = f"http://ip-api.com/batch/{ips_str}?lang=zh-CN"
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if len(data) == len(batch):
                    for idx, item in enumerate(data):
                        ip_port = batch[idx]
                        if item.get("status") == "success":
                            isp_raw = item.get("isp", "")
                            # 判断运营商
                            if "联通" in isp_raw or "Unicom" in isp_raw:
                                isp = "联通"
                            elif "移动" in isp_raw or "Mobile" in isp_raw:
                                isp = "移动"
                            elif "电信" in isp_raw or "Telecom" in isp_raw:
                                isp = "电信"
                            else:
                                isp = "未知"
                            result[ip_port] = isp
                        else:
                            result[ip_port] = "未知"
                else:
                    print(f"⚠️ 批量查询返回数量不符: {len(data)} vs {len(batch)}")
            else:
                print(f"⚠️ 批量查询 HTTP 错误: {resp.status_code}")
        except Exception as e:
            print(f"❌ 批量查询异常: {e}")
        # 控制请求频率，避免被限制
        time.sleep(2)
    return result

def save_ips_by_province(ips):
    """按省份和运营商分类保存（只保留联通和移动）"""
    # 先获取所有 IP 的运营商信息
    isp_dict = get_isp_batch(ips)
    
    # 过滤出联通和移动的 IP
    filtered_ips = [ip for ip, isp in isp_dict.items() if isp in ("联通", "移动")]
    print(f"📊 过滤后剩余 {len(filtered_ips)} 个联通/移动 IP")
    
    # 对过滤后的 IP 获取省份信息并分类保存
    province_isp_dict = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_ip_info, ip): ip for ip in filtered_ips}
        for future in as_completed(futures):
            province, isp, ip_port = future.result()
            if province and isp and isp != "未知":
                fname = f"{province}{isp}.txt"
                province_isp_dict.setdefault(fname, set()).add(ip_port)
    
    for fname, ip_set in province_isp_dict.items():
        filepath = os.path.join(IP_DIR, fname)
        existing = set()
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                existing.update(line.strip() for line in f if line.strip())
        all_ips = existing.union(ip_set)
        with open(filepath, 'w', encoding='utf-8') as f:
            for ip in sorted(all_ips):
                f.write(ip + '\n')
        print(f"💾 保存 {fname}: {len(all_ips)} 个IP")
    print(f"✅ 总共保存到 {len(province_isp_dict)} 个分类文件")

def get_ip_info(ip_port):
    """获取单个 IP 的省份和运营商（已在批量阶段获得运营商，这里只获取省份）"""
    ip = ip_port.split(":")[0]
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                province = data.get("regionName", "未知")
                # 复用之前获取的运营商结果？这里我们重新获取一次，也可从之前结果传入
                # 但为了节省请求，我们可以从过滤结果中传入运营商，这里为了简化，再查一次
                # 更好的做法：在过滤阶段同时获取省份，但为了保持结构，这里再查一次省份
                return province, "联通" if "联通" in data.get("isp", "") else "移动", ip_port
    except:
        pass
    return None, None, ip_port

def main():
    print("🚀 从 tonkiang.us 获取酒店源 IP...")
    ips = fetch_tonkiang_ips()
    if not ips:
        print("❌ 未获取到任何 IP，退出")
        return
    save_ips_by_province(ips)

if __name__ == "__main__":
    main()
