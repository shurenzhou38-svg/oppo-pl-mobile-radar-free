# OPPO PL Mobile Radar Free

这是一个免费版自动情报机器人：

GitHub Actions 定时运行 → Python 抓取手机行业 RSS → 可选 OpenAI 总结 → 推送到飞书群

## 文件结构必须保持这样

.github/workflows/oppo_pl_mobile_radar.yml
scripts/oppo_pl_mobile_radar.py
README.md

## 你需要做什么

1. 新建 GitHub 仓库，建议名字：
   oppo-pl-mobile-radar-free

2. 上传本文件夹里的三个内容：
   .github
   scripts
   README.md

3. 在飞书群添加自定义机器人，复制 Webhook。

4. 在 GitHub 仓库里添加 Secret：
   Settings → Secrets and variables → Actions → New repository secret

   Name:
   FEISHU_WEBHOOK_URL

   Secret:
   粘贴飞书 Webhook

5. 可选添加：
   OPENAI_API_KEY
   OPENAI_MODEL，例如 gpt-4o-mini

6. 测试运行：
   Actions → OPPO PL Mobile Radar Free → Run workflow

## 免费版说明

不填 OPENAI_API_KEY 也能运行，会使用规则版总结。
填了 OPENAI_API_KEY 后，日报质量更高。
免费版不稳定抓 TikTok/Instagram 真实热门链接，后续可再接 Apify 或其他社媒工具。
