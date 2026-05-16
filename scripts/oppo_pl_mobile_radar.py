import os
import re
import json
import html
import hashlib
import requests
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup

FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

RSS_SOURCES = [
    "https://www.gsmarena.com/rss-news-reviews.php3",
    "https://www.androidauthority.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.phonearena.com/feed",
    "https://9to5google.com/feed/",
    "https://www.tabletowo.pl/feed/",
    "https://www.telepolis.pl/rss",
    "https://www.benchmark.pl/rss/aktualnosci.xml",
    "https://spidersweb.pl/feed",
]

KEYWORDS = [
    "oppo", "oneplus", "samsung", "xiaomi", "motorola", "realme", "honor", "vivo", "apple",
    "smartphone", "phone", "android", "ai phone", "foldable", "camera phone",
    "poland", "polska", "media expert", "media markt", "rtv euro agd", "orange", "play", "t-mobile", "plus",
    "premiera", "cena", "promocja", "operator", "telefon","Poland smartphone market","Polska smartfony","Media Expert smartfon OPPO","Media Markt Polska OPPO","RTV Euro AGD OPPO","Play OPPO smartfon","Orange Polska OPPO"
]

COMPETITOR_KEYWORDS = [
    "samsung", "xiaomi", "motorola", "realme", "honor", "vivo", "apple", "nothing", "google pixel"
]

HASHTAGS = [
    "#smartphone",
    "#tech",
    "#phonereview",
    "#unboxing",
    "#phonephotography",
]

def clean_text(text: str) -> str:
    text = BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def score_item(title: str, summary: str) -> int:
    content = f"{title} {summary}".lower()
    score = 0
    for kw in KEYWORDS:
        if kw.lower() in content:
            score += 2
    for kw in COMPETITOR_KEYWORDS:
        if kw.lower() in content:
            score += 1
    if any(x in content for x in ["launch", "released", "premiera", "price", "cena", "review", "camera", "ai", "promotion", "promocja", "sale"]):
        score += 3
    return score

def fetch_items():
    results = []
    seen = set()

    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            source = feed.feed.get("title", url)
            for entry in feed.entries[:25]:
                title = clean_text(entry.get("title", ""))
                summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
                link = entry.get("link", "")
                uid = hashlib.md5((title + link).encode("utf-8")).hexdigest()

                if uid in seen:
                    continue
                seen.add(uid)

                score = score_item(title, summary)
                if score <= 0:
                    continue

                results.append({
                    "title": title,
                    "summary": summary[:500],
                    "link": link,
                    "source": source,
                    "published": entry.get("published", "") or entry.get("updated", ""),
                    "score": score
                })

        except Exception as e:
            print(f"Failed source: {url} | {e}")

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:40]

def rule_based_report(items):
    today = datetime.now().strftime("%Y-%m-%d")
    top10 = items[:10]
    competitor = [
        item for item in items
        if any(k in (item["title"] + " " + item["summary"]).lower() for k in COMPETITOR_KEYWORDS)
    ][:5]

    lines = []
    lines.append(f"📱 OPPO PL Mobile Radar｜{today}")
    lines.append("")
    lines.append("一、波兰/欧洲科技与手机行业动态 TOP10")
    if top10:
        for i, item in enumerate(top10, 1):
            lines.append(f"{i}. {item['title']}")
            lines.append(f"   来源：{item['source']}")
            lines.append(f"   核心信息：{item['summary'][:180] or '暂无摘要'}")
            lines.append(f"   链接：{item['link']}")
    else:
        lines.append("今日未抓取到高相关度手机行业新闻，请检查 RSS 源或关键词。")

    lines.append("")
    lines.append("二、友商新品与同档位产品对比线索")
    if competitor:
        for i, item in enumerate(competitor, 1):
            lines.append(f"{i}. {item['title']}")
            lines.append("   OPPO视角：关注价格、影像、AI、快充、续航、渠道促销是否形成同档位竞争。")
            lines.append(f"   链接：{item['link']}")
    else:
        lines.append("今日未发现高确定性友商新品发布。建议人工补查 Samsung/Xiaomi/Motorola/Honor 波兰零售页面。")

    lines.append("")
    lines.append("三、社交媒体手机相关 TOP5 话题/标签")
    for i, tag in enumerate(HASHTAGS, 1):
        lines.append(f"{i}. {tag}｜内容角度：开箱、影像对比、AI功能、真实生活场景、Promoter第一视角。")

    lines.append("")
    lines.append("四、欧洲优质手机短视频案例方向")
    lines.append("今日案例方向：30秒“痛点开场 → 功能展示 → 结果对比”的竖屏短视频。")
    lines.append("可复刻脚本：前3秒提出痛点；中间20秒展示OPPO功能；最后5秒给结果和门店/官网引导。")
    lines.append("备注：免费版不稳定抓取 TikTok/Instagram 真实热门链接，后续可接 Apify 或人工补1条案例。")

    lines.append("")
    lines.append("五、今日建议动作")
    lines.append("KA：检查友商新品/价格是否已在 Media Expert、Media Markt、RTV EURO AGD 上线。")
    lines.append("零售：把今日高频卖点转化为门店话术抽查题。")
    lines.append("社媒：围绕 TOP 标签做一条 20-30 秒竖屏短视频脚本。")
    return "\n".join(lines)

def ai_report(items):
    if not OPENAI_API_KEY:
        return rule_based_report(items)

    prompt = f"""
你是 OPPO 波兰市场的手机行业情报分析助手。请每天围绕“波兰手机与科技行业、社交媒体趋势、OPPO产品口碑、线上平台评价、友商新品对比”生成一份结构化日报。
禁止直接输出英文，每一个单独信息都用中文翻译总结输出，每一条控制在60字以内，一定要保证读者读到你的总结就能知道发生了什么，而不是都去点击链接观看
日报标题格式：
📱 OPPO PL Mobile Radar | YYYY-MM-DD

输出语言：
中文为主，保留必要英文/波兰语原文关键词。内容要适合直接推送到飞书/Lark群，让团队成员快速看懂。

重要要求：
不要只输出新闻链接。每一条信息都必须包含“这件事是什么、为什么值得关注、对OPPO波兰可能有什么启发”。

请按照以下 5 个模块输出：

一、波兰/欧洲科技与手机行业动态 TOP10
要求：
1. 每天最多10条。
2. 优先级：波兰本地手机/科技新闻 > 欧洲手机行业新闻 > 全球重要手机行业新闻。
3. 每条必须包含：
- 标题
- 来源
- 用中文1-2句话简短总结：让人不用点链接也知道新闻讲什么
- 对OPPO波兰的启发/影响：一句话即可
- 原文链接
4. 不要收集与手机行业无关的泛科技新闻，除非对手机市场、AI终端、芯片、零售渠道、运营商、消费者电子有明显影响。

输出格式：
1. 标题
   来源：
   简短总结：
   对OPPO波兰的启发：
   链接：

二、波兰本地社交媒体手机相关 TOP5 话题 + 优质短视频案例
要求：
1. 每天收集波兰本地 TikTok / Instagram / YouTube Shorts / Facebook Reels 上与手机、拍照、AI手机、安卓、iPhone、折叠屏、手机价格、手机评测、手机摄影相关的热门话题或标签。
2. 每天最多5个话题。
3. 每个话题必须给出一个优质短视频案例。
4. 每个案例需要说明：
- 话题/标签
- 平台
- 案例标题或账号名称
- 为什么这个视频值得关注：例如拍摄手法、卖点表达、用户痛点、互动高、评论方向好
- 可借鉴点：OPPO波兰可以怎么模仿或优化
- 视频链接

输出格式：
1. 话题/标签：
   平台：
   优质案例：
   为什么值得关注：
   OPPO可借鉴点：
   链接：

三、社交媒体上关于OPPO产品的新增高热度评价，每天3条
要求：
1. 从 TikTok / Instagram / YouTube / Facebook / X / Reddit 等平台中收集。
2. 只收集最近24-48小时内新增，或者近期明显有互动热度的内容。
3. 每天最多3条。
4. 优先收集波兰语、英语或欧洲用户评论。
5. 每条必须包含：
- 平台
- 产品/型号
- 原评论或内容摘要
- 情绪判断：正面 / 中性 / 负面
- 热点原因：为什么值得关注
- 对OPPO波兰的建议
- 链接

输出格式：
1. 平台：
   产品/型号：
   用户评价摘要：
   情绪判断：
   热点原因：
   OPPO建议：
   链接：

四、波兰主流线上购机平台 OPPO 产品新增评价，每天5条
要求：
1. 监测波兰主流线上购机平台，包括但不限于：
- Media Expert
- Media Markt
- RTV Euro AGD
- x-kom
- Komputronik
- Allegro
- Orange
- Play
- T-Mobile
- Plus
- OPPO Poland official store
2. 每天最多5条新增评价。
3. 每条必须包含：
- 平台
- OPPO产品型号
- 星级/评分，如果有
- 用户评价简短翻译/总结
- 情绪判断：正面 / 中性 / 负面
- 反映的问题或机会点
- 链接
4. 如果当天没有明显新增评价，请输出“今日未监测到明确新增高价值评价”，不要编造。

输出格式：
1. 平台：
   产品型号：
   评分：
   评价摘要：
   情绪判断：
   问题/机会点：
   链接：

五、友商新品与OPPO同档位产品对比线索
要求：
1. 只收集过去7天内发布或确认即将上市的友商新品。
2. 每天最多2款。
3. 友商范围包括但不限于：
Samsung, Xiaomi, Redmi, realme, Honor, Motorola, vivo, OnePlus, Nothing, Apple, Google Pixel。
4. 不只是说“某产品发布”，必须选择一个OPPO同档位、同类型、可对标的产品做简单对比。
5. 输出一个简单表格，字段包括：
- 友商新品
- 友商核心卖点
- 预计价格/定位
- OPPO对标产品
- OPPO优势
- OPPO风险点
- 建议动作
6. 如果过去7天没有值得关注的新品，则输出“近7天暂无需要重点对比的友商新品”。

输出格式：
| 友商新品 | 核心卖点 | 价格/定位 | OPPO对标产品 | OPPO优势 | 风险点 | 建议动作 |
|---|---|---|---|---|---|---|

最后输出：
六、今日管理层关注重点
请用3条以内总结今天最值得OPPO波兰团队关注的事项。
格式：
1. ...
2. ...
3. ...

整体风格要求：
- 简洁、专业、可直接转发。
- 不要输出太长的大段文字。
- 不要只堆链接。
- 遇到不确定信息要标注“待确认”。
- 没有找到有效信息时要写“今日未监测到明确新增信息”，不要编造。

RSS ITEMS:
{json.dumps(items, ensure_ascii=False)[:50000]}
"""
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENAI_MODEL,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": "你是严谨的市场情报分析师，必须区分事实、判断和建议。"},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"OpenAI failed, using rule-based report. Error: {e}")
        return rule_based_report(items)

def send_feishu(text):
    if not FEISHU_WEBHOOK_URL:
        raise RuntimeError("Missing FEISHU_WEBHOOK_URL secret.")
    payload = {
        "msg_type": "text",
        "content": {
            "text": text[:15000]
        }
    }
    response = requests.post(FEISHU_WEBHOOK_URL, json=payload, timeout=30)
    print(response.status_code, response.text[:500])
    response.raise_for_status()

def main():
    items = fetch_items()
    report = ai_report(items)
    print(report[:3000])
    send_feishu(report)

if __name__ == "__main__":
    main()
