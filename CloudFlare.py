import requests
from bs4 import BeautifulSoup
import re
import os
import time # 导入time模块用于添加延迟
import json # 导入json模块用于解析API响应

# --- 配置信息 ---
IP_OUTPUT_FILE = 'CloudFlare.txt'  # 输出文件名更改，以反映内容和语言
IP_PATTERN = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'  # 标准IPv4正则表达式
REQUEST_TIMEOUT = 10  # 网页请求超时时间 (秒)
API_REQUEST_TIMEOUT = 5 # IP查询API请求超时时间 (秒)
API_DELAY_SECONDS = 1.5 # 每次API调用后的延迟时间 (秒)，避免触发速率限制 (ip-api.com ~45 reqs/min)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 目标站点配置列表
SITES_CONFIG = [
    {'url': 'https://monitor.gacjie.cn/page/cloudflare/ipv4.html', 'element_tag': 'tr'},
    {'url': 'https://ip.164746.xyz', 'element_tag': 'tr'}
]

# --- IP地理位置查询函数 ---
def get_country_for_ip(ip_address):
    """
    使用 ip-api.com 查询IP地址的国家信息。
    """
    # 在URL中添加 lang=zh-CN 参数
    api_url = f"http://ip-api.com/json/{ip_address}?fields=status,message,country&lang=zh-CN"
    try:
        response = requests.get(api_url, timeout=API_REQUEST_TIMEOUT)
        response.raise_for_status() # 检查HTTP错误
        data = response.json()

        if data.get('status') == 'success' and data.get('country'):
            return data['country'] # API将直接返回中文国家名
        elif data.get('status') == 'fail':
            print(f"  API查询失败 for {ip_address}: {data.get('message', 'Unknown API error')}")
            return "查询失败" # 返回中文提示
        else:
            # 确保即使没有 'country' 字段，也有一个默认的中文返回值
            print(f"  API查询成功但未返回国家信息 for {ip_address}: {data}")
            return "未知国家" # 返回中文提示
            
    except requests.exceptions.Timeout:
        print(f"  API查询超时 for {ip_address}")
        return "查询超时" # 返回中文提示
    except requests.exceptions.RequestException as e:
        print(f"  API请求错误 for {ip_address}: {e}")
        return "查询错误" # 返回中文提示
    except json.JSONDecodeError:
        print(f"  API响应解析错误 for {ip_address}")
        return "响应解析错误" # 返回中文提示
    except Exception as e:
        print(f"  查询国家时发生未知错误 for {ip_address}: {e}")
        return "未知错误" # 返回中文提示

# --- 主脚本 ---
collected_ips = set()

if os.path.exists(IP_OUTPUT_FILE):
    os.remove(IP_OUTPUT_FILE)
    print(f"已删除已存在的文件: {IP_OUTPUT_FILE}")

print("开始收集IP地址...")
for site_info in SITES_CONFIG:
    url = site_info['url']
    element_tag = site_info['element_tag']
    print(f"\n正在从以下地址获取IP: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        elements = soup.find_all(element_tag)
        
        if not elements:
            print(f"  在 {url} 上未找到标签为 '{element_tag}' 的元素。")
            continue

        found_on_this_page = 0
        for element in elements:
            element_text = element.get_text(separator=' ', strip=True)
            ip_matches = re.findall(IP_PATTERN, element_text)
            for ip in ip_matches:
                if ip not in collected_ips:
                    found_on_this_page += 1
                collected_ips.add(ip)
        print(f"  在此页面上新发现 {found_on_this_page} 个唯一IP地址。")

    except requests.exceptions.Timeout:
        print(f"  错误: 连接 {url} 超时。")
    except requests.exceptions.RequestException as e:
        print(f"  错误: 无法从 {url} 获取内容。原因: {e}")
    except Exception as e:
        print(f"  处理 {url} 时发生未知错误: {e}")

if collected_ips:
    print(f"\n共收集到 {len(collected_ips)} 个唯一的IP地址。开始查询国家信息")
    
    output_lines = []
    sorted_ips = sorted(list(collected_ips))

    for i, ip in enumerate(sorted_ips):
        print(f"  正在查询 ({i+1}/{len(sorted_ips)}): {ip} ...")
        country = get_country_for_ip(ip)
        output_lines.append(f"{ip}#{country}")
        
        if i < len(sorted_ips) - 1:
            time.sleep(API_DELAY_SECONDS) 

    with open(IP_OUTPUT_FILE, 'w', encoding='utf-8') as file: # 确保使用utf-8编码写入文件
        for line in output_lines:
            file.write(line + '\n')
    print(f"\nIP地址及其国家信息已保存到 {IP_OUTPUT_FILE} 文件中。")
else:
    print("\n未能收集到任何IP地址。")