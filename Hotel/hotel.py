import eventlet
eventlet.monkey_patch()
import time
import datetime
from threading import Thread, Lock
import os
import re
from queue import Queue, Empty
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
import json
import subprocess
from bs4 import BeautifulSoup

# 配置区
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

IP_DIR = "Hotel/ip"
# 创建IP目录
if not os.path.exists(IP_DIR):
    os.makedirs(IP_DIR)

# 频道分类定义
CHANNEL_CATEGORIES = {
    "央视频道": [
        "CCTV-1 综合", "CCTV-2 财经", "CCTV-3 综艺", "CCTV-4 中文国际", "CCTV-4 欧洲", "CCTV-4 美洲", "CCTV-5 体育", "CCTV-5+ 体育赛事", "CCTV-6 电影", "CCTV-7 国防军事",
        "CCTV-8 电视剧", "CCTV-9 纪录", "CCTV-10 科教", "CCTV-11 戏曲", "CCTV-12 社会与法", "CCTV-13 新闻", "CCTV-14 少儿", "CCTV-15 音乐", "CCTV-16 奥林匹克", "CCTV-17 农业农村", 
        "CCTV-4K 超高清", "CCTV-8K 超高清", "CCTV-兵器科技", "CCTV-风云音乐", "CCTV-风云足球", "CCTV-风云剧场", "CCTV-怀旧剧场", "CCTV-第一剧场", "CCTV-女性时尚", "CCTV-世界地理", 
        "CCTV-央视台球", "CCTV-高尔夫网球", "CCTV-央视文化精品", "CCTV-卫生健康", "CCTV-电视指南", "中央新影-老故事", "中央新影-中学生", "中央新影-发现之旅", 
        "CETV1", "CETV2", "CETV3", "CETV4", "CETV早期教育", "CGTN纪录", "CGTN俄语", "CGTN英语", "中国天气", "中国交通",
    ],
    "卫视频道": [
        "北京卫视", "东方卫视", "广东卫视", "深圳卫视", "浙江卫视", "江苏卫视", "湖南卫视", "山东卫视", "四川卫视", "河南卫视", "广西卫视", "湖北卫视", 
        "河北卫视", "安徽卫视", "重庆卫视", "天津卫视", "东南卫视", "贵州卫视", "云南卫视", "海南卫视", "江西卫视", "山西卫视", "陕西卫视", "甘肃卫视", 
        "新疆卫视", "西藏卫视", "内蒙古卫视", "宁夏卫视", "青海卫视", "黑龙江卫视", "吉林卫视", "辽宁卫视", "兵团卫视", "三沙卫视", "厦门卫视", "海峡卫视", 
        "农林卫视", "康巴卫视", "延边卫视", "大湾区卫视", "安多卫视", "新视觉",
    ],
    "4K专区": [
        "北京卫视4K", "东方卫视4K", "广东卫视4K", "深圳卫视4K", "浙江卫视4K", "江苏卫视4K", "湖南卫视4K", "山东卫视4K", "四川卫视4K", "欢笑剧场4K", "爱上4K", "淘4K", "4K超清",
    ],
    "体育频道": [
        "CCTV-5 体育", "CCTV-5+ 体育赛事", "CCTV-16 奥林匹克", "CCTV-风云足球", "CCTV-央视台球", "CCTV-高尔夫网球", "广东体育", "劲爆体育", "五星体育", "睛彩青少", "睛彩竞技", "睛彩篮球", 
        "睛彩广场舞", "魅力足球", "纬来体育", "澳门体育", "快乐垂钓", "四海钓鱼", "先锋乒羽", "天元围棋", "汽摩", "车迷频道", "游戏风云", "北京体育",
    ],
    "数字影视": [
        "CHC动作电影", "CHC家庭影院", "CHC影迷电影", "重温经典", "淘电影", "淘精彩", "淘剧场", "淘娱乐", "4K电影", "IPTV戏曲", "IPTV综艺", "IPTV体育", "IPTV电影", "IPTV国防军事", 
        "IPTV电视剧", "IPTV科教", "IPTV社会与法", "IPTV音乐", "华数热播剧场", "华数谍战剧场", "IPTV经典电影", "IPTV喜剧影院", "华数动作影院", "华数家庭影院", "IPTV武侠剧场", 
        "华数精选", "华数星影", "华数光影", "IPTV精品剧场", "IPTV-精彩影视", "书画频道", "环球奇观", "求索纪录", "EETV生态环境", "乐游", "生活时尚", "都市剧场", "金鹰纪实", "龙祥时代", 
        "法治天地", "东方影视",  
    ],
    "少儿频道": [
         "淘BABY", "淘萌宠", "华数少儿动画", "卡酷少儿", "广东少儿", "嘉佳卡通", "江西少儿", "金色学堂", "动漫秀场", "哈哈炫动", "优漫卡通", "金鹰卡通", "优优宝贝",  
    ],
    "港澳台频道": [
        "CHANNEL[V]", "凤凰卫视中文台", "凤凰卫视香港台", "凤凰卫视资讯台", "凤凰卫视电影台", "澳门莲花", "澳视澳门", "TVB星河", "TVB翡翠台", "TVB明珠台", 
    ],
    "贵州频道": [
        "贵州卫视", "贵州-2", "贵州-3", "贵州-4", "贵州-5", "贵州-6","贵州-7", "贵州-移动电视", "六盘水综合",
    ], 
}

# 特殊符号映射,在匹配时将特殊符号替换为空
SPECIAL_SYMBOLS = ["HD", "LT", "XF", "_", ".", "·", "高清", "标清", "超清", "H265", "4K", "FHD", "HDTV"]

# ==================== ★ 新增：分辨率/质量评分配置 ====================
FFPROBE_TIMEOUT = 8          # ffprobe 探测超时（秒）
SPEED_FULL_MARK_KB = 2000    # 达到该速度（KB/s）即速度满分
SPEED_WEIGHT = 0.3           # 速度权重
QUALITY_WEIGHT = 0.7         # 质量权重（提高质量权重，优先高清）
MIN_QUALITY_TO_KEEP = 0      # 综合分低于此值的直接丢弃（0 表示不丢弃）
# ========================================================


# 移除特殊符号的函数
def remove_special_symbols(text):
    """移除频道名称中的特殊符号"""
    for symbol in SPECIAL_SYMBOLS:
        text = text.replace(symbol, "")
    
    # 移除多余的空格
    text = re.sub(r'\s+', '', text)
    return text.strip()

# 改进的频道名称映射,使用精确匹配
CHANNEL_MAPPING = {
    "CCTV-1 综合": ["CCTV1", "CCTV-1", "CCTV1综合", "CCTV1高清", "CCTV1HD", "cctv1","中央1台","sCCTV1-综合","CCTV01","CCTV1-综合","CCTV1-综合高清"],
    "CCTV-2 财经": ["CCTV2", "CCTV-2", "CCTV2财经", "CCTV2高清", "CCTV2HD", "cctv2","中央2台","aCCTV2","sCCTV2-财经","CCTV02","CCTV2-财经高清","CCTV2-财经"],
    "CCTV-3 综艺": ["CCTV3", "CCTV-3", "CCTV3综艺", "CCTV3高清", "CCTV3HD", "cctv3","中央3台","acctv3","sCCTV3-综艺","CCTV03","CCTV3-综艺","CCTV3-综艺高清"],
    "CCTV-4 中文国际": ["CCTV4", "CCTV-4", "CCTV4中文国际", "CCTV4高清", "CCTV4HD", "cctv4","中央4台","aCCTV4","sCCTV4-国际","CCTV04","CCTV4-国际","CCTV4-国际高清"],
    "CCTV-5 体育": ["CCTV5", "CCTV-5", "CCTV5体育", "CCTV5高清", "CCTV5HD", "cctv5","中央5台","sCCTV5-体育","CCTV05","CCTV5-体育","CCTV5-体育高清"],
    "CCTV-5+ 体育赛事": ["CCTV5+", "CCTV-5+", "CCTV5+体育赛事", "CCTV5+高清", "CCTV5+HD", "cctv5+", "CCTV5plus","CCTV5+体育赛事高清", "CCTV-5+高清"],
    "CCTV-6 电影": ["CCTV6", "CCTV-6", "CCTV6电影", "CCTV6高清", "CCTV6HD", "cctv6","中央6台","sCCTV6-电影","CCTV06","CCTV6-电影","CCTV6-电影高清"],
    "CCTV-7 国防军事": ["CCTV7", "CCTV-7", "CCTV7军事", "CCTV7高清", "CCTV7HD", "cctv7","中央7台","CCTV07","CCTV7-军农高清"],
    "CCTV-8 电视剧": ["CCTV8", "CCTV-8", "CCTV8电视剧", "CCTV8高清", "CCTV8HD", "cctv8","中央8台","sCCTV8-电视剧","CCTV08","CCTV8-电视剧高清"],
    "CCTV-9 纪录": ["CCTV9", "CCTV-9", "CCTV9纪录", "CCTV9高清", "CCTV9HD", "cctv9","中央9台","sCCTV9-纪录","CCTV09","CCTV9-纪录高清"],
    "CCTV-10 科教": ["CCTV10", "CCTV-10", "CCTV10科教", "CCTV10高清", "CCTV10HD", "cctv10","中央10台","sCCTV10-科教","CCTV10-科教高清"],
    "CCTV-11 戏曲": ["CCTV11", "CCTV-11", "CCTV11戏曲", "CCTV11高清", "CCTV11HD", "cctv11", "中央11台","sCCTV11-戏曲","CCTV11-戏曲","CCTV11-戏曲高清"],
    "CCTV-12 社会与法": ["CCTV12", "CCTV-12", "CCTV12社会与法", "CCTV12高清", "CCTV12HD", "cctv12","中央12台","sCCTV12-社会与法","CCTV12-社会与法","CCTV12-社会与法高清"],
    "CCTV-13 新闻": ["CCTV13", "CCTV-13", "CCTV13新闻", "CCTV13高清", "CCTV13HD", "cctv13","中央13台","sCCTV13-新闻","CCTV-新闻","CCTV13-新闻","CCTV13-新闻","CCTV13-新闻高清"],
    "CCTV-14 少儿": ["CCTV14", "CCTV-14", "CCTV14少儿", "CCTV14高清", "CCTV14HD", "cctv14","中央14台","sCCTV14-少儿","CCTV-少儿高清","CCTV-少儿","CCTV14-少儿高清"],
    "CCTV-15 音乐": ["CCTV15", "CCTV-15", "CCTV15音乐", "CCTV15高清", "CCTV15HD", "cctv15","中央15台","sCCTV15-音乐","CCTV-音乐","CCTV15-音乐"],
    "CCTV-16 奥林匹克": ["CCTV16", "CCTV-16", "CCTV16奥林匹克", "CCTV16高清", "CCTV16HD", "cctv16","中央16台", "CCTV-16奥林匹克FHD"],
    "CCTV-17 农业农村": ["CCTV17", "CCTV-17", "CCTV17农业农村", "CCTV17高清", "CCTV17HD", "cctv17","中央17台"],
    
    "CCTV-4 欧洲": ["CCTV4欧洲", "CCTV-4欧洲", "CCTV4欧洲高清", "CCTV4欧洲HD"],
    "CCTV-4 美洲": ["CCTV4美洲", "CCTV-4美洲", "CCTV4美洲高清", "CCTV4美洲HD"],
    
    "CCTV-兵器科技": ["兵器科技", "CCTV兵器科技", "CCTV兵器科技高清", "兵器科技频道","兵器科技HD"],
    "CCTV-风云音乐": ["风云音乐", "CCTV风云音乐", "CCTV-风云音乐HD", "风云音乐高清"],
    "CCTV-第一剧场": ["第一剧场", "CCTV第一剧场", "CCTV-第一剧场高清", "第一剧场HD"],
    "CCTV-风云足球": ["风云足球", "CCTV风云足球", "CCTV-风云足球高清", "风云足球HD", "风云足球高清"],
    "CCTV-风云剧场": ["风云剧场", "CCTV风云剧场", "CCTV-风云剧场高清", "风云剧场HD", "风云剧场高清"],
    "CCTV-怀旧剧场": ["怀旧剧场", "CCTV怀旧剧场", "CCTV-怀旧剧场高清", "怀旧剧场HD"],
    "CCTV-卫生健康": ["卫生健康", "CCTV卫生健康", "CCTV-卫生健康"],
    "CCTV-电视指南": ["电视指南", "CCTV电视指南", "CCTV-电视指南"],
    "CCTV-女性时尚": ["女性时尚", "CCTV女性时尚", "CCTV-女性时尚"],
    "CCTV-世界地理": ["地理世界", "CCTV世界地理", "CCTV-世界地理", "世界地理高清"],
    "CCTV-央视台球": ["央视台球", "CCTV央视台球", "CCTV-央视台球", "央视台球HD"],
    "CCTV-高尔夫网球": ["高尔夫网球", "央视高网", "CCTV高尔夫网球", "CCTV-高尔夫网球", "高尔夫","高尔夫·网球HD"],
    "CCTV-央视文化精品": ["文化精品", "CCTV央视文化精品", "CCTV-央视文化精品", "央视精品"],
    "中央新影-发现之旅": ["CCTV发现之旅", "发现之旅高清", "发现之旅HD"],
    "中央新影-老故事": ["CCTV老故事", "老故事高清", "老故事HD"],
    "中央新影-中学生": ["中学生", "中学生HD", "中学生高清"],
    "CETV1": ["中国教育1台", "中国教育一台", "中国教育一套高清", "教育一套" ,"CETV-1高清","中国教育","CETV 1HD","CETV-1HD","中国教育-1","中国教育1","CETV-1"],
    "CETV2": ["中国教育2台", "中国教育二台", "中国教育二套高清","CETV2 标清","CETV-2"],
    "CETV3": ["中国教育3台", "中国教育三台", "中国教育三套高清","CETV3 标清","CETV-3"],
    "CETV4": ["中国教育4台", "中国教育四台", "中国教育四套高清","CETV4 标清","CETV-4","中国教育-4"],
    "CETV早期教育": ["早期教育"],
    "CGTN纪录": ["CGTN纪录高清"],
    "CGTN英语": ["CGTN英语高清"],
    "CGTN俄语": ["CGTN俄语高清"],
    "中国交通": ["中国交通", "中国交通频道"],
    "中国天气": ["中国气象", "中国天气频道", "中央气象"],

    "北京卫视": ["北京卫视HD", "北京卫视高清", "BTV北京卫视", "BTV北京", "北京高清", "北京卫视-高清"],
    "东方卫视": ["上海卫视", "东方卫视", "SBN", "上海卫视高清", "东方卫视HD", "东方卫视高清", "上海东方卫视", "东方高清", "东方卫视-高清"],
    "广东卫视": ["广东卫视HD", "广东卫视高清", "广东高清", "广东卫视-高清"],
    "深圳卫视": ["深圳卫视高清", "深圳卫视HD", "深圳高清", "深圳卫视-高清"],
    "浙江卫视": ["浙江卫视高清", "浙江卫视HD", "浙江高清", "浙江卫视-高清"],
    "江苏卫视": ["江苏卫视HD", "江苏卫视高清", "江苏高清", "江苏卫视-高清"],
    "湖南卫视": ["湖南卫视HD", "湖南电视", "湖南卫视高清", "湖南高清", "湖南卫视-高清"],
    "山东卫视": ["山东高清", "山东卫视高清", "山东卫视HD", "山东高清", "山东卫视-高清"],
    "四川卫视": ["四川卫视HD", "四川卫视高清", "四川高清", "四川卫视-高清"],
    "河南卫视": ["河南卫视HD", "河南卫视高清", "河南高清", "河南卫视-高清"],
    "广西卫视": ["广西卫视HD", "广西卫视高清", "广西高清", "广西卫视-高清"],
    "湖北卫视": ["湖北卫视HD", "湖北卫视高清", "湖北高清", "湖北卫视-高清"],
    "河北卫视": ["河北卫视HD", "河北卫视高清", "河北高清", "河北卫视-高清"],
    "安徽卫视": ["安徽卫视高清", "安徽卫视HD", "安徽高清", "安徽卫视-高清"],
    "重庆卫视": ["重庆卫视HD", "重庆卫视高清", "重庆高清", "重庆卫视-高清"],
    "天津卫视": ["天津卫视", "天津卫视高清", "天津卫视HD", "天津高清", "天津卫视-高清"],
    "东南卫视": ["福建东南", "福建卫视", "东南卫视高清", "东南卫视HD", "福建东南卫视", "东南卫视-高清"],
    "贵州卫视": ["贵州卫视HD", "贵州卫视高清", "贵州-1", "贵州卫视-高清"],
    "云南卫视": ["云南卫视HD", "云南卫视高清", "云南卫视-高清"],
    "海南卫视": ["旅游卫视", "海南卫视HD", "海南卫视高清", "旅游卫视HD", "海南卫视-高清", "旅游卫视-高清"],
    "江西卫视": ["江西卫视HD", "江西卫视高清", "江西卫视-高清"],
    "山西卫视": ["山西卫视高清", "山西高清HD", "山西卫视-高清"],
    "陕西卫视": ["陕西卫视高清", "陕西卫视HD", "陕西卫视-高清"],
    "甘肃卫视": ["甘肃卫视HD", "甘肃卫视高清", "甘肃卫视-高清"],
    "新疆卫视": ["新疆卫视", "新疆卫视高清", "新疆卫视-高清"],
    "西藏卫视": ["XZTV2", "西藏卫视高清", "西藏卫视HD", "西藏卫视-高清"],
    "内蒙古卫视": ["内蒙古卫视高清", "内蒙古", "内蒙古卫视HD", "内蒙古卫视-高清"],
    "宁夏卫视": ["宁夏卫视高清", "宁夏卫视HD", "宁夏卫视-高清"],
    "青海卫视": ["青海卫视高清", "青海卫视HD", "青海卫视-高清"],
    "黑龙江卫视": ["黑龙江卫视高清", "黑龙江卫视HD", "黑龙江卫视-高清"],
    "吉林卫视": ["吉林卫视HD", "吉林卫视高清", "吉林卫视-高清"],
    "辽宁卫视": ["辽宁卫视HD", "辽宁卫视高清", "辽宁卫视-高清"],
    "海峡卫视": ["海峡卫视高清", "海峡卫视HD"],
    "农林卫视": ["陕西农林卫视", "农林卫视"],
    "三沙卫视": ["三沙卫视高清", "三沙卫视HD"],
    "厦门卫视": ["厦门卫视HD", "厦门卫视高清"],
    "康巴卫视": ["四川康巴卫视", "SCTV康巴卫视"],
    "大湾区卫视": ["南方卫视高清", "南方卫视", "广东南方卫视", "大湾区卫视HD", "大湾区卫视高清"],
    "兵团卫视": ["兵团卫视HD", "兵团卫视高清"],
    "新视觉": ["新视觉HD"],

    "北京卫视4K": ["北京卫视4K超高清", "北京卫视4K 超高清", "北京卫视4K FHD", "北京卫视4K FDR"],
    "东方卫视4K": ["东方卫视4K超高清", "东方卫视4K 超高清", "东方卫视4K FHD", "东方卫视4K FDR"],
    "广东卫视4K": ["广东卫视4K超高清", "广东卫视4K 超高清", "广东卫视4K FHD", "广东卫视4K FDR"],
    "深圳卫视4K": ["深圳卫视4K超高清", "深圳卫视4K 超高清", "深圳卫视4K FHD", "深圳卫视4K FDR"],
    "浙江卫视4K": ["浙江卫视4K超高清", "浙江卫视4K 超高清", "浙江卫视4K FHD", "浙江卫视4K FDR"],
    "江苏卫视4K": ["江苏卫视4K超高清", "江苏卫视4K 超高清", "江苏卫视4K FHD", "江苏卫视4K FDR"],
    "湖南卫视4K": ["湖南卫视4K超高清", "湖南卫视4K 超高清", "湖南卫视4K FHD", "湖南卫视4K FDR"],
    "山东卫视4K": ["山东卫视4K超高清", "山东卫视4K 超高清", "山东卫视4K FHD", "山东卫视4K FDR"],
    "四川卫视4K": ["四川卫视4K超高清", "四川卫视4K 超高清", "四川卫视4K FHD", "四川卫视4K FDR"],
    "欢笑剧场4K": ["上海欢笑剧场", "欢笑剧场"],
    "淘4K": ["淘4K", "IPTV淘4K"],
    "4K超清": ["北京IPTV4K超清", "IPTV4K超清"],

    "广东体育": ["广东体育++", "广东体育高清", "广东体育HD", "广东体育频道高清", "广东体育频道"],
    "劲爆体育": ["劲爆体育高清", "劲爆体育HD"],
    "五星体育": ["五星体育高清", "五星体育HD", "上海五星体育HD", "上海五星体育高清", "五星体育频道高清", "五星体育频道"],
    "睛彩青少": ["睛彩青少HD", "睛彩羽毛球"],
    "睛彩竞技": ["睛彩竞技高清", "睛彩竞技HD"],
    "睛彩篮球": ["睛彩篮球高清", "睛彩篮球HD"],
    "睛彩广场舞": ["睛彩广场舞高清", "睛彩广场舞HD"],
    "魅力足球": ["魅力足球HD", "上海魅力足球"],
    "纬来体育": ["纬来体育高清", "纬来体育HD"],
    "澳门体育": ["澳门体育高清", "澳门体育HD"],
    "快乐垂钓": ["快乐垂钓HD", "快乐垂钓高清"],
    "四海钓鱼": ["四海钓鱼高清", "四海钓鱼HD"],
    "先锋乒羽": ["先锋乒羽HD", "先锋乒羽高清"],
    "天元围棋": ["天元围棋HD", "天元围棋高清"],
    "汽摩": ["汽摩HD", "汽摩频道", "重庆汽摩"],
    "车迷频道": ["车迷"],
    "游戏风云": ["SiTV游戏风云", "上海游戏风云", "游戏风云高清", "游戏风云HD"],
    "网络棋牌": ["网络棋牌", "IPTV网络棋牌"],
    "北京体育": ["BTV体育"],

    "CHC动作电影": ["动作电影","CHC 动作电影",],
    "CHC家庭影院": ["家庭影院","CHC 家庭影院",],
    "CHC影迷电影": ["高清电影","CHC 高清电影","高清影院"],
    "重温经典": ["重温经典高清"],
    "淘电影": ["淘电影", "IPTV淘电影"],
    "淘精彩": ["淘精彩", "IPTV淘精彩"],
    "淘剧场": ["淘剧场", "IPTV淘剧场"],
    "淘娱乐": ["淘娱乐", "IPTV淘娱乐"],
    "IPTV戏曲": ["相声小品",],
    "IPTV综艺": ["IPTV相声","IPTV3+","iptv3+",],
    "IPTV体育": ["iptv5+"],
    "IPTV电影": ["iptv6+",],
    "IPTV国防军事": ["军事"],
    "IPTV电视剧": ["iptv8+"],
    "IPTV科教": ["野外"],
    "IPTV社会与法": ["IPTV法制","法制","法治"],
    "IPTV音乐": ["音乐现场",],
    "华数热播剧场": ["IPTV-热播剧场","热播剧场"],
    "华数谍战剧场": ["IPTV-谍战剧场","谍战剧场"],
    
    "IPTV经典电影": ["经典电影", "IPTV-经典电影"],
    "IPTV喜剧影院": ["喜剧影院", "IPTV-喜剧影院"],
    "华数动作影院": ["动作影院", "IPTV-动作影院"],
    "华数家庭影院": ["家庭影院"],
    "IPTV抗战剧场": ["测试频道15","抗战剧场","IPTV-抗战剧场"],
    "IPTV武侠剧场": ["武侠剧场"],
    "华数精选": ["精选"],
    "华数星影": ["星影"],
    "华数光影": ["光影"],
    "精品剧场": ["精品剧场", "IPTV精品剧场"],
    "精彩影视": ["精彩影视", "IPTV-精彩影视"],
    "书画频道": ["书法频道", "书法书画","书法"],
    "环球奇观": ["环球奇观", "环球旅游", "安广网络"],
    "求索纪录": ["求索纪录", "求索记录"],
    "EETV生态环境": ["生态环境"],
    "乐游": ["乐游", "乐游频道", "乐游纪实","全纪实"],
    "生活时尚": ["生活时尚", "SiTV生活时尚", "上海生活时尚","生活时尚HD"],
    "都市剧场": ["都市剧场高清", "SiTV都市剧场", "上海都市剧场", "都市时尚","都市剧场HD"],
    "金鹰纪实": ["金鹰纪实HD", "金鹰纪视高清", "金鹰记实", "金鹰纪实高清"],
    "龙祥时代": ["龙祥时代", "XF有线电影"],
    "法治天地": ["法治天地高清", "法制天地"],

    "淘BABY": ["淘BABY", "IPTV淘BABY", "淘baby"],
    "淘萌宠": ["淘萌宠", "IPTV淘萌宠"],
    "华数少儿动画": ["IPTV-少儿动画","少儿动画","早教"],
    "卡酷少儿": ["卡酷", "北京卡酷少儿", "卡酷动画", "卡酷动漫", "北京卡酷", "北京少儿", "卡通卫视", "北京卡通", "BTV-卡酷", "卡酷少儿HD", "BTV+KAKU少儿"], 
    "广东少儿": ["南方五", "广东少儿高清"],
    "嘉佳卡通": ["嘉佳卡通", "广东嘉佳卡通", "佳佳卡通", "嘉佳卡通高清"],    
    "江西少儿": ["JXTV-6", "江西少儿高清"],
    "金色学堂": ["金色学堂", "SiTV金色学堂", "上海金色学堂"],
    "动漫秀场": ["动漫秀场", "SiTV动漫秀场", "上海动漫秀场", "动漫剧场", "新动漫"],
    "哈哈炫动": ["哈哈炫动", "炫动卡通"],
    "优漫卡通": ["优漫卡通", "优漫漫画"],
    "金鹰卡通": ["金鹰卡通", "湖南金鹰卡通", "金鹰卡通HD"],
   
    "CHANNEL[V]": ["Channel[V]", "CHANNEL[V]"],
    "凤凰卫视中文台": ["凤凰卫视中文", "凤凰中文", "凤凰卫视", "凤凰中文台", "凤凰中文高清"],
    "凤凰卫视香港台": ["凤凰卫视香港", "凤凰香港"],
    "凤凰卫视资讯台": ["凤凰卫视资讯", "凤凰资讯", "凤凰咨询", "凤凰资讯高清"],
    "凤凰卫视电影台": ["凤凰卫视电影", "凤凰电影", "鳳凰衛視電影台"],
    "澳门莲花": ["澳门莲花HD"],
    "TVB星河": ["星河台"],
    "TVB翡翠台": ["翡翠台","香港翡翠"],
    "TVB明珠台": ["明珠台","香港明珠"],
 
    "贵州-2": ["GTV-2", "公共频道", "贵州公共", "贵州公共频道"],
    "贵州-3": ["GTV-3", "影视文艺频道", "贵州影视文艺", "贵州影视文艺频道"],
    "贵州-4": ["GTV-4", "大众生活频道", "贵州大众生活", "贵州大众生活频道"],
    "贵州-5": ["GTV-5", "法制频道", "贵州法制", "贵州法制频道"],
    "贵州-6": ["GTV-6", "科教健康频道", "贵州科教健康", "贵州科教健康频道"],
    "贵州-7": ["GTV-7", "经济频道", "贵州经济", "贵州经济频道"],
    "贵州-移动电视": ["GTV-移动电视"],
    "六盘水": ["六盘水综合"],
}

RESULTS_PER_CHANNEL = 30


# ==================== ★ 新增：ffprobe 真实分辨率探测 ====================
def probe_real_resolution(url, timeout=FFPROBE_TIMEOUT):
    """
    用 ffprobe 探测 HLS 流的真实分辨率。
    返回 (width, height, quality_score)
    - 探测失败返回 (None, None, 0)
    """
    if not url:
        return None, None, 0

    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            "-analyzeduration", "2M",
            "-probesize", "2M",
            "-timeout", "5000000",   # 5 秒
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return None, None, 0

        output = result.stdout.strip()
        if not output:
            return None, None, 0

        # ffprobe csv 输出格式：width,height （可能有多个 stream，取第一个）
        for line in output.split('\n'):
            line = line.strip()
            if ',' in line:
                parts = line.split(',')
                try:
                    w = int(parts[0])
                    h = int(parts[1])
                except (ValueError, IndexError):
                    continue

                # 按分辨率计算质量分
                pixels = w * h
                if pixels >= 3840 * 2160:
                    q = 100
                elif pixels >= 1920 * 1080:
                    q = 90
                elif pixels >= 1280 * 720:
                    q = 55   # ★ 720p 大幅降分
                elif pixels >= 720 * 576:
                    q = 30
                else:
                    q = 15
                return w, h, q

        return None, None, 0
    except subprocess.TimeoutExpired:
        return None, None, 0
    except Exception:
        return None, None, 0


def parse_m3u8_quality_fallback(content, url):
    """
    当 ffprobe 探测失败时的后备方案：从 m3u8 内容解析质量分。
    """
    max_res_score = 0
    max_bw_score = 0

    for line in content.split('\n'):
        line = line.strip()
        if not line.startswith('#EXT-X-STREAM-INF'):
            continue

        res_match = re.search(r'RESOLUTION=(\d+)x(\d+)', line, re.IGNORECASE)
        if res_match:
            w = int(res_match.group(1))
            h = int(res_match.group(2))
            pixels = w * h
            if pixels >= 3840 * 2160:
                max_res_score = max(max_res_score, 100)
            elif pixels >= 1920 * 1080:
                max_res_score = max(max_res_score, 90)
            elif pixels >= 1280 * 720:
                max_res_score = max(max_res_score, 55)
            elif pixels >= 720 * 576:
                max_res_score = max(max_res_score, 30)
            else:
                max_res_score = max(max_res_score, 15)

        bw_match = re.search(r'BANDWIDTH=(\d+)', line, re.IGNORECASE)
        if bw_match:
            bw = int(bw_match.group(1))
            if bw >= 8_000_000:
                max_bw_score = max(max_bw_score, 100)
            elif bw >= 4_000_000:
                max_bw_score = max(max_bw_score, 85)
            elif bw >= 2_000_000:
                max_bw_score = max(max_bw_score, 60)
            else:
                max_bw_score = max(max_bw_score, 30)

    if max_res_score > 0 and max_bw_score > 0:
        return (max_res_score + max_bw_score) / 2
    elif max_res_score > 0:
        return max_res_score
    elif max_bw_score > 0:
        return max_bw_score
    else:
        u = url.lower()
        if '4k' in u or 'uhd' in u:
            return 90
        elif 'fhd' in u or '1080' in u:
            return 80
        elif 'hd' in u or '720' in u:
            return 55
        else:
            return 40
# ==================== ★ 新增结束 ====================


# 读取台标文件
def read_logo_file():
    logo_dict = {}
    logo_file = "Hotel/logo.txt"
    if os.path.exists(logo_file):
        try:
            with open(logo_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ',' in line:
                        parts = line.split(',', 1)
                        channel_name = parts[0].strip()
                        logo_url = parts[1].strip()
                        logo_dict[channel_name] = logo_url
        except Exception as e:
            print(f"读取台标文件错误: {e}")
    return logo_dict

# 检测IP:端口可用性
def check_ip_availability(ip_port, timeout=2):
    """检测IP:端口是否可用"""
    try:
        test_urls = [
            f"http://{ip_port}/",
            f"http://{ip_port}/iptv/live/1000.json?key=txiptv",
            f"http://{ip_port}/ZHGXTV/Public/json/live_interface.txt"
        ]
        
        for url in test_urls:
            try:
                response = requests.get(url, timeout=timeout, headers=HEADERS)
                if response.status_code == 200:
                    return True
            except:
                continue
                
        return False
    except Exception as e:
        return False

# 批量检测IP可用性并更新文件
def check_and_update_ip_file(province_file):
    """检测IP可用性并更新文件"""
    print(f"\n开始检测 {province_file} 中的IP可用性...")
    
    available_ips = []
    all_ips = []
    
    try:
        with open(province_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    all_ips.append(line)
    except Exception as e:
        print(f"读取IP文件错误: {e}")
        return []
    
    total_ips = len(all_ips)
    print(f"需要检测 {total_ips} 个IP")
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {}
        for ip_port in all_ips:
            future = executor.submit(check_ip_availability, ip_port)
            futures[future] = ip_port
        
        completed = 0
        for future in as_completed(futures):
            ip_port = futures[future]
            try:
                is_available = future.result()
                completed += 1
                
                if is_available:
                    available_ips.append(ip_port)
                    print(f"✓ {ip_port} 可用 ({completed}/{total_ips})")
                else:
                    print(f"✗ {ip_port} 不可用 ({completed}/{total_ips})")
                    
                if completed % 10 == 0 or completed == total_ips:
                    print(f"进度: {completed}/{total_ips} ({completed/total_ips*100:.1f}%) - 可用: {len(available_ips)} 个")
                    
            except Exception as e:
                completed += 1
                print(f"✗ {ip_port} 检测失败 ({completed}/{total_ips})")
    
    with open(province_file, 'w', encoding='utf-8') as f:
        for ip_port in available_ips:
            f.write(f"{ip_port}\n")
    
    if available_ips:
        print(f"\n✓ 已更新 {province_file}")
        print(f"  原始IP数量: {total_ips}")
        print(f"  可用IP数量: {len(available_ips)}")
        print(f"  不可用IP已删除: {total_ips - len(available_ips)}")
    else:
        print(f"\n✓ 已更新 {province_file},没有可用的IP,文件已清空")
    
    return available_ips

# 读取文件并设置参数
def read_config(config_file):
    ip_configs = []
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                if '$' in line:
                    ip_port, region = line.split('$', 1)
                else:
                    ip_port = line
                    region = ""
                
                if ':' in ip_port:
                    ip_part, port = ip_port.split(':', 1)
                    
                    parts = ip_part.split('.')
                    if len(parts) == 4:
                        a, b, c, d = parts
                        ip = f"{a}.{b}.{c}.1"
                        ip_configs.append((ip, port))
                    else:
                        print(f"跳过无效IP格式: {ip_part}")
                
        return ip_configs
    except Exception as e:
        print(f"读取文件错误: {e}")
        return []
        
# 发送get请求检测url是否可访问
def check_ip_port(ip_port, url_end):
    try:
        url = f"http://{ip_port}{url_end}"
        resp = requests.get(url, timeout=3)
        resp.raise_for_status()
        if "tsfile" in resp.text or "hls" in resp.text or "m3u8" in resp.text:
            print(f"{url} 访问成功")
            return url
    except:
        return None

# 多线程检测url,获取有效ip_port
def scan_ip_port(ip, port, url_end):
    valid_urls = []
    a, b, c, d = map(int, ip.split('.'))
    ip_ports = [f"{a}.{b}.{c}.{x}:{port}" for x in range(1, 256)]
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = {executor.submit(check_ip_port, ip_port, url_end): ip_port for ip_port in ip_ports}
        for future in as_completed(futures):
            result = future.result()
            if result:
                valid_urls.append(result)
    return valid_urls    

# 发送GET请求获取JSON文件, 解析JSON文件, 获取频道信息
def extract_channels(url):
    hotel_channels = []
    try:
        urls = url.split('/', 3)
        url_x = f"{urls[0]}//{urls[2]}"
        
        if "iptv" in url:
            response = requests.get(url, timeout=3)
            json_data = response.json()
            for item in json_data.get('data', []):
                if isinstance(item, dict):
                    name = item.get('name')
                    urlx = item.get('url')
                    if urlx and ("tsfile" in urlx or "m3u8" in urlx):
                        if not urlx.startswith('/'):
                            urlx = '/' + urlx
                        urld = f"{url_x}{urlx}"
                        hotel_channels.append((name, urld))
        elif "ZHGXTV" in url:
            response = requests.get(url, timeout=2)
            json_data = response.content.decode('utf-8')
            data_lines = json_data.split('\n')
            for line in data_lines:
                if "," in line and ("hls" in line or "m3u8" in line):
                    name, channel_url = line.strip().split(',')
                    parts = channel_url.split('/', 3)
                    if len(parts) >= 4:
                        urld = f"{url_x}/{parts[3]}"
                        hotel_channels.append((name, urld))
        return hotel_channels
    except Exception as e:
        print(f"解析频道错误 {url}: {e}")
        return []


# ==================== ★ 修改：测速 + ffprobe 质量探测 ====================
def speed_test(channels):
    def show_progress():
        while checked[0] < len(channels):
            numberx = checked[0] / len(channels) * 100
            print(f"已测试{checked[0]}/{len(channels)},可用频道:{len(results)}个,进度:{numberx:.2f}%")
            time.sleep(5)
    
    def worker():
        while True:
            try:
                channel_name, channel_url = task_queue.get()
                
                best_speed = 0.0
                best_quality = 0.0
                best_resolution = "未知"
                attempts = 0
                max_attempts = 2
                
                while attempts < max_attempts:
                    attempts += 1
                    try:
                        # 获取 m3u8 文件内容
                        response = requests.get(channel_url, timeout=2)
                        if response.status_code != 200:
                            if attempts < max_attempts:
                                print(f"第{attempts}次测速 {channel_name}: HTTP {response.status_code},将重试")
                            continue
                        
                        m3u8_content = response.text
                        lines = m3u8_content.strip().split('\n')
                        
                        ts_lists = [line.split('/')[-1] for line in lines if line.startswith('#') == False]
                        if not ts_lists:
                            if attempts < max_attempts:
                                print(f"第{attempts}次测速 {channel_name}: 没有找到TS列表,将重试")
                            continue
                        
                        # 测速逻辑
                        channel_url_t = channel_url.rstrip(channel_url.split('/')[-1])
                        ts_url = channel_url_t + ts_lists[0]
                        
                        start_time = time.time()
                        try:
                            with eventlet.Timeout(5, False):
                                ts_response = requests.get(ts_url, timeout=6, stream=True)
                                if ts_response.status_code != 200:
                                    if attempts < max_attempts:
                                        print(f"第{attempts}次测速 {channel_name}: TS文件HTTP {ts_response.status_code},将重试")
                                    continue
                                
                                content_length = 0
                                chunk_size = 1024 * 1024
                                for chunk in ts_response.iter_content(chunk_size=chunk_size):
                                    if chunk:
                                        content_length += len(chunk)
                                        if content_length >= chunk_size:
                                            break
                                
                                resp_time = (time.time() - start_time) * 1
                                
                                if content_length > 0 and resp_time > 0:
                                    normalized_speed = content_length / resp_time / 1024 / 1024
                                    
                                    if normalized_speed > best_speed:
                                        best_speed = normalized_speed
                                    
                                    # ★ 测速成功后，用 ffprobe 探测真实分辨率
                                    if best_quality == 0:
                                        try:
                                            w, h, q = probe_real_resolution(channel_url)
                                            if q > 0:
                                                best_quality = q
                                                best_resolution = f"{w}x{h}"
                                                print(f"  🎬 {channel_name}: ffprobe 探测到 {w}x{h}，质量分 {q}")
                                            else:
                                                # ffprobe 失败，用后备方案
                                                fallback_q = parse_m3u8_quality_fallback(m3u8_content, channel_url)
                                                best_quality = fallback_q
                                                best_resolution = "fallback"
                                                print(f"  ⚠️ {channel_name}: ffprobe 探测失败，用 m3u8 后备质量分 {fallback_q:.0f}")
                                        except Exception as e:
                                            print(f"  ⚠️ {channel_name}: ffprobe 异常 {e}")
                                    
                                    if normalized_speed > 0.001 and attempts < max_attempts:
                                        break
                                    else:
                                        if attempts < max_attempts:
                                            print(f"第{attempts}次测速 {channel_name}: {normalized_speed:.3f} MB/s,将重试")
                                else:
                                    if attempts < max_attempts:
                                        print(f"第{attempts}次测速 {channel_name}: 获取内容失败,将重试")
                        except eventlet.Timeout:
                            if attempts < max_attempts:
                                print(f"第{attempts}次测速 {channel_name}: 请求超时,将重试")
                            continue
                        except Exception as e:
                            if attempts < max_attempts:
                                print(f"第{attempts}次测速 {channel_name} 失败: {str(e)},将重试")
                            continue
                            
                    except Exception as e:
                        if attempts < max_attempts:
                            print(f"第{attempts}次测速 {channel_name} 处理失败: {str(e)},将重试")
                        continue
                
                # ★ 综合评分：速度分 × SPEED_WEIGHT + 质量分 × QUALITY_WEIGHT
                if best_speed > 0.2:
                    speed_score = min(100.0, best_speed * 1024 / SPEED_FULL_MARK_KB * 100)
                    final_score = speed_score * SPEED_WEIGHT + best_quality * QUALITY_WEIGHT
                    
                    if final_score >= MIN_QUALITY_TO_KEEP:
                        result = (channel_name, channel_url, f"{final_score:.2f}")
                        print(f"✓ {channel_name}, {channel_url}: 速度{best_speed:.3f}MB/s 分辨率{best_resolution} 质量{best_quality:.0f} 综合{final_score:.1f}")
                        results.append(result)
                    else:
                        print(f"× {channel_name}, {channel_url}: 综合分 {final_score:.1f} 低于阈值 {MIN_QUALITY_TO_KEEP}，丢弃")
                else:
                    print(f"× {channel_name}, {channel_url}: 经过{attempts}次测速,最佳速度 {best_speed:.3f} MB/s,已过滤")
                
                checked[0] += 1
            except Exception as e:
                checked[0] += 1
                print(f"处理 {channel_name} 时发生错误: {e}")
            finally:
                task_queue.task_done()
    
    task_queue = Queue()
    results = []
    checked = [0]
    
    Thread(target=show_progress, daemon=True).start()
    
    for _ in range(min(10, len(channels))):
        Thread(target=worker, daemon=True).start()
    
    for channel in channels:
        task_queue.put(channel)
    
    task_queue.join()
    return results
# ==================== ★ 修改结束 ====================


# 精确频道名称匹配函数
def exact_channel_match(channel_name, pattern_name):
    clean_name = remove_special_symbols(channel_name.strip().lower())
    clean_pattern = remove_special_symbols(pattern_name.strip().lower())
    
    if clean_name == clean_pattern:
        return True
    
    cctv_match = re.match(r'^cctv[-_\s]?(\d+[a-z]?)$', clean_name)
    pattern_match = re.match(r'^cctv[-_\s]?(\d+[a-z]?)$', clean_pattern)
    
    if cctv_match and pattern_match:
        cctv_num1 = cctv_match.group(1)
        cctv_num2 = pattern_match.group(1)
        
        if cctv_num1 != cctv_num2:
            return False
        else:
            return clean_name == clean_pattern
    
    if "+" in clean_name and "+" in clean_pattern:
        if "cctv5+" in clean_name and "cctv5+" in clean_pattern:
            return True
    
    if clean_pattern in clean_name:
        if clean_pattern.endswith(('1', '2', '3', '4', '5', '6', '7', '8', '9', '0')):
            pattern_len = len(clean_pattern)
            if len(clean_name) > pattern_len:
                next_char = clean_name[pattern_len]
                if next_char.isdigit():
                    return False
        return True
    
    return False

# 统一频道名称 - 使用精确匹配
def unify_channel_name(channels_list):
    alias_list = []
    for std_name, aliases in CHANNEL_MAPPING.items():
        for alias in aliases:
            alias_list.append((alias, std_name))
    alias_list.sort(key=lambda x: len(x[0]), reverse=True)

    new_channels_list = []
    for name, channel_url, speed in channels_list:
        original_name = name
        unified_name = None

        for alias, std in alias_list:
            if name == alias:
                unified_name = std
                break

        if not unified_name:
            for alias, std in alias_list:
                if alias in name:
                    unified_name = std
                    break

        if not unified_name:
            unified_name = name

        new_channels_list.append(f"{unified_name},{channel_url},{speed}\n")
        if original_name != unified_name:
            print(f"频道名称统一: '{original_name}' -> '{unified_name}'")

    return new_channels_list

# 按照CHANNEL_CATEGORIES中指定的顺序排序
def sort_channels_by_specified_order(channels_list, category_channels):
    channel_order = {channel: index for index, channel in enumerate(category_channels)}
    
    def get_channel_sort_key(item):
        name, url, speed = item
        
        if name in channel_order:
            return (channel_order[name], -float(speed))
        else:
            return (float('inf'), name)
    
    return sorted(channels_list, key=get_channel_sort_key)

# 定义排序函数
def channel_key(channel_name):
    match = re.search(r'\d+', channel_name)
    return int(match.group()) if match else float('inf')

# 分类频道
def classify_channels_by_category(channels_data):
    categorized_channels = {}
    
    for category in CHANNEL_CATEGORIES.keys():
        categorized_channels[category] = []
    
    categorized_channels["其他频道"] = []
    
    for line in channels_data:
        try:
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
            name = parts[0]
            url = parts[1]
            speed = parts[2] if len(parts) > 2 else "0.000"
            assigned = False
            
            for category, channel_list in CHANNEL_CATEGORIES.items():
                if name in channel_list:
                    categorized_channels[category].append((name, url, speed))
                    assigned = True
                    break
            
            if not assigned:
                categorized_channels["其他频道"].append((name, url, speed))
        except Exception as e:
            print(f"分类频道时出错: {e}, 行: {line}")
            continue
    
    return categorized_channels

# 生成M3U文件
def generate_m3u_file(txt_file_path, m3u_file_path):
    print(f"开始生成M3U文件: {m3u_file_path}")
    
    logo_dict = read_logo_file()
    epg_url = "https://gh-proxy.com/https://raw.githubusercontent.com/adminouyang/231006/refs/heads/main/py/TV/EPG/epg.xml"
    
    channel_id_map = {}
    try:
        print("正在解析EPG数据以获取频道ID...")
        response = requests.get(epg_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'xml')
        
        for channel_tag in soup.find_all('channel'):
            channel_id = channel_tag.get('id')
            display_name_tag = channel_tag.find('display-name')
            if channel_id and display_name_tag:
                channel_name_in_epg = display_name_tag.text.strip()
                channel_id_map[channel_name_in_epg] = channel_id
        print(f"从EPG解析了 {len(channel_id_map)} 个频道的ID映射。")
    except Exception as e:
        print(f"警告：解析EPG链接失败,tvg-id将无法填入。错误: {e}")
    
    with open(m3u_file_path, 'w', encoding='utf-8') as m3u_file:
        m3u_file.write(f'#EXTM3U x-tvg-url="{epg_url}"\n')
        
        with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
            current_group = ""
            
            for line in txt_file:
                line = line.strip()
                if not line:
                    continue
                
                if line.endswith(',#genre#'):
                    current_group = line.replace(',#genre#', '')
                    continue
                
                if ',' in line and not line.startswith('#'):
                    try:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            channel_name = parts[0]
                            channel_url = parts[1]
                            
                            logo_url = logo_dict.get(channel_name, "")
                            tvg_id = channel_id_map.get(channel_name, "")
                            tvg_id_attr = f' tvg-id="{tvg_id}"' if tvg_id else ""
                            
                            m3u_file.write(f'#EXTINF:-1 {tvg_id_attr} tvg-name="{channel_name}" tvg-logo="{logo_url}" group-title="{current_group}",{channel_name}\n')
                            m3u_file.write(f'{channel_url}\n')
                    except Exception as e:
                        print(f"处理频道行错误: {line}, 错误: {e}")
    
    print(f"M3U文件已生成: {m3u_file_path}")

# 分组并排序频道
def group_and_sort_channels_by_category(categorized_channels):
    processed_categories = {}
    
    for category, channels in categorized_channels.items():
        if not channels:
            continue
            
        if category in CHANNEL_CATEGORIES:
            category_order = CHANNEL_CATEGORIES[category]
            
            channel_groups = {}
            for name, url, speed in channels:
                if name not in channel_groups:
                    channel_groups[name] = []
                channel_groups[name].append((name, url, speed))
            
            grouped_channels = []
            for channel_name in category_order:
                if channel_name in channel_groups:
                    url_list = channel_groups[channel_name]
                    url_list.sort(key=lambda x: -float(x[2]))
                    url_list = url_list[:RESULTS_PER_CHANNEL]
                    grouped_channels.extend(url_list)
                    del channel_groups[channel_name]
            
            for channel_name, url_list in channel_groups.items():
                url_list.sort(key=lambda x: -float(x[2]))
                url_list = url_list[:RESULTS_PER_CHANNEL]
                grouped_channels.extend(url_list)
            
            grouped_channels = sort_channels_by_specified_order(grouped_channels, category_order)
            processed_categories[category] = grouped_channels
        else:
            channels.sort(key=lambda x: -float(x[2]))
            channel_groups = {}
            
            for name, url, speed in channels:
                if name not in channel_groups:
                    channel_groups[name] = []
                channel_groups[name].append((name, url, speed))
            
            grouped_channels = []
            for channel_name, url_list in channel_groups.items():
                url_list.sort(key=lambda x: -float(x[2]))
                url_list = url_list[:RESULTS_PER_CHANNEL]
                grouped_channels.extend(url_list)
            
            grouped_channels.sort(key=lambda x: x[0])
            processed_categories[category] = grouped_channels
    
    return processed_categories

# 获取酒店源流程        
def hotel_iptv(config_file):
    available_ips = check_and_update_ip_file(config_file)
    
    if not available_ips:
        print(f"没有可用的IP,跳过 {config_file}")
        return
    
    ip_configs = read_config(config_file)
    valid_urls = []
    channels = []
    configs = []
    url_ends = ["/iptv/live/1000.json?key=txiptv", "/ZHGXTV/Public/json/live_interface.txt"]
    
    for url_end in url_ends:
        for ip, port in ip_configs:
            configs.append((ip, port, url_end))
    
    for ip, port, url_end in configs:
        valid_urls.extend(scan_ip_port(ip, port, url_end))
    
    print(f"扫描完成,获取有效url共：{len(valid_urls)}个")
    
    for valid_url in valid_urls:
        channels.extend(extract_channels(valid_url))
    
    print(f"共获取频道：{len(channels)}个\n开始测速")
    results = speed_test(channels)
    
    if not results:
        print(f"⚠️ 警告：IP检测通过但所有频道都不可用,将该IP视为不可用")
        print(f"🗑️ 从 {config_file} 中删除该IP")
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write("")
        
        print(f"✓ 已清空 {config_file}（没有可用的频道）")
        return
    else:
        print(f"✓ 找到 {len(results)} 个可用频道,IP保持有效")
    
    # results 里的第三字段已经是综合分，排序自动按综合分从高到低
    results.sort(key=lambda x: -float(x[2]))
    results.sort(key=lambda x: channel_key(x[0]))
    
    unified_channels = unify_channel_name(results)
    
    with open('1.txt', 'a', encoding='utf-8') as f:
        for line in unified_channels:
            f.write(line.split(',')[0] + ',' + line.split(',')[1] + '\n')
    
    print("测速完成")

# 主函数
def main():
    start_time = datetime.datetime.now()
    print(f"脚本开始运行时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    
    province_files = [f for f in os.listdir(IP_DIR) if f.endswith('.txt')]
    
    for province_file in province_files:
        province_name = province_file.replace('.txt', '')
        print(f"\n处理 {province_name} 的IP...")
        
        config_file = os.path.join(IP_DIR, province_file)
        hotel_iptv(config_file)
        try:
            if os.path.exists(config_file) and os.path.getsize(config_file) == 0:
                os.remove(config_file)
                print(f"  检测到空文件,已删除: {province_file}")
        except Exception as e:
            print(f"  处理文件 {province_file} 时发生错误: {e}")
    
    if not os.path.exists('1.txt'):
        print("没有找到频道数据文件")
        return
    
    with open('1.txt', 'r', encoding='utf-8') as f:
        raw_lines = f.readlines()
    
    channels_data = []
    for line in raw_lines:
        if ',' in line and line.strip():
            parts = line.strip().split(',')
            if len(parts) >= 2:
                name = parts[0]
                url = parts[1]
                speed = parts[2] if len(parts) > 2 else "0.000"
                channels_data.append(f"{name},{url},{speed}")
    
    categorized = classify_channels_by_category(channels_data)
    processed_categories = group_and_sort_channels_by_category(categorized)
    
    file_paths = []
    for category, channels in processed_categories.items():
        if channels:
            filename = f"{category.replace('频道', '')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"{category},#genre#\n")
                for name, url, speed in channels:
                    f.write(f"{name},{url}\n")
            
            file_paths.append(filename)
            print(f"已保存 {len(channels)} 个频道到 {filename}")
    
    file_contents = []
    
    for file_path in file_paths:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding="utf-8") as f:
                content = f.read()
                file_contents.append(content)
    
    beijing_time = datetime.datetime.now()
    current_time = beijing_time.strftime("%Y/%m/%d %H:%M")
    
    with open("1.txt", "w", encoding="utf-8") as f:
        f.write(f"{current_time}更新,#genre#\n")
        for content in file_contents:
            f.write(f"\n{content}")
    
    with open('1.txt', 'r', encoding="utf-8") as f:
        lines = f.readlines()
    
    unique_lines = [] 
    seen_lines = set() 
    for line in lines:
        if line not in seen_lines:
            unique_lines.append(line)
            seen_lines.add(line)
    
    output_dir = "Hotel"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    txt_output_path = 'Hotel/iptv.txt'
    with open(txt_output_path, 'w', encoding="utf-8") as f:
        f.writelines(unique_lines)
    
    m3u_output_path = 'Hotel/iptv.m3u'
    generate_m3u_file(txt_output_path, m3u_output_path)
    
    files_to_remove = ["1.txt"] + file_paths
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
    
    end_time = datetime.datetime.now()
    print(f"\n脚本结束运行时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    
    run_time = end_time - start_time
    hours, remainder = divmod(run_time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    print(f"总运行时间: {hours}小时{minutes}分{seconds}秒")
    print("任务运行完毕,所有频道合并到iptv.txt和iptv.m3u")

if __name__ == "__main__":
    main()
