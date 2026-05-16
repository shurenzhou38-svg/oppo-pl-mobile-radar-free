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
    "premiera", "cena", "promocja", "operator", "telefon"
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
你是OPPO波兰市场/零售团队的每日手机行业情报助手。请基于RSS抓取结果输出中文日报。
以下所有输出内容用中文用总结，每一点总结控制在60字，不搬原文
日报结构：
1. 波兰科技行业/手机相关动态：筛选10条，按“标题-来源-核心事实-对OPPO启示”输出。
2. 友商新品：只写确有新品/上市/核心配置/价格的信息；没有就写“今日未发现高确定性新品发布”。同时给出与OPPO同档内位产品的可能对比点，禁止编造。
3. 社交媒体手机相关TOP5话题/标签：可基于新闻和行业趋势判断，但必须标注“趋势判断/待验证”。
4. 欧洲优质手机短视频案例：免费版无法稳定抓TT/INS真实链接，请输出一个“今日可复刻案例方向”和具体拍摄脚本。
5. 今日建议动作：KA、零售、社媒内容各1条。
6. 收集波兰主流线上手机销售平台对OPPO新品热销品的评论并做总结，每天3条
7. 收集社媒用户对OPPO新品热销品的评论并做总计，每天3条
原则：宁可保守，不要编造；不确定信息标注“待验证”。

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
