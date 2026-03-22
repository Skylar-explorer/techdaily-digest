#!/usr/bin/env python3
"""
Daily Digest Generator - Fetches RSS articles and generates HTML digest
"""
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

# Import our modules
from rss_fetcher import RSSFetcher, Article
from summarizer import ArticleSummarizer


class DigestGenerator:
    """Generates daily HTML digest from RSS articles"""

    def __init__(self, opml_path: str, db_path: str, output_path: str):
        self.opml_path = opml_path
        self.db_path = db_path
        self.output_path = output_path
        self.fetcher = RSSFetcher(opml_path, db_path)
        self.summarizer = ArticleSummarizer()

    def generate_summary(self, article: Article) -> Dict:
        """Generate summary for an article"""
        # Use content or summary for AI processing
        text_content = article.content if article.content else article.summary

        result = self.summarizer.summarize(
            title=article.title,
            content=text_content,
            source=article.source_name
        )

        # Add article metadata
        result['id'] = article.id
        result['link'] = article.link
        result['published'] = article.published.isoformat()
        result['author'] = article.author

        return result

    def estimate_reading_time(self, content: str) -> int:
        """Estimate reading time in minutes"""
        words = len(content.split())
        return max(1, round(words / 200))

    def format_date(self, date_str: str) -> str:
        """Format date for display"""
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%Y年%m月%d日")

    def format_short_date(self, date_str: str) -> str:
        """Format short date for meta"""
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%m/%d")

    def render_article(self, summary: Dict, index: int) -> str:
        """Render a single article with 5 sections"""
        from urllib.parse import urlparse

        def clean(text):
            return text.replace('...', '').replace('…', '').strip() if text else ''

        # Derive display source from the actual article link domain
        try:
            parsed = urlparse(summary.get('link', ''))
            display_source = parsed.netloc.replace('www.', '') or summary.get('source', '')
        except Exception:
            display_source = summary.get('source', '')

        one_liner = clean(summary.get('one_liner', ''))
        detailed_analysis = clean(summary.get('detailed_analysis', summary.get('summary', '')))
        key_insight = clean(summary.get('key_insight', ''))
        why_it_matters = clean(summary.get('why_it_matters', ''))

        # Key points
        kp_html = ''
        for i, point in enumerate(summary.get('key_points', [])[:3], 1):
            p = clean(point)
            if p.startswith('要点') and '：' in p:
                p = p.split('：', 1)[-1].strip()
            kp_html += f'''<li>
              <span class="kp-n">{i:02d}</span>
              <span class="kp-body">{p}</span>
            </li>'''

        # Tags
        tags_html = ''.join(f'<span class="tag">{t}</span>' for t in summary.get('tags', [])[:3])

        level = summary.get('level', '中级')
        level_cls = 'lv-b' if '初' in level else ('lv-a' if '高' in level else 'lv-m')

        pub_date = summary.get('published', '')[:10]
        try:
            from datetime import datetime as _dt
            pub_date = _dt.fromisoformat(pub_date).strftime('%-m月%-d日')
        except Exception:
            pass

        # Index formatted as roman-ish leading zero
        idx_str = f'{index:02d}'

        return f'''
<article class="story">
  <div class="story-index">{idx_str}</div>

  <div class="story-inner">

    <header class="story-head">
      <div class="story-meta">
        <span class="meta-source">{display_source}</span>
        <span class="meta-dot">·</span>
        <span class="meta-date">{pub_date}</span>
        <span class="meta-dot">·</span>
        <span class="meta-level {level_cls}">{level}</span>
      </div>
      <h2 class="story-title">
        <a href="{summary['link']}" target="_blank" rel="noopener">{summary['headline']}</a>
      </h2>
    </header>

    <div class="lede-wrap">
      <p class="lede">{one_liner}</p>
    </div>

    <div class="story-grid">

      <section class="sec-points">
        <h3 class="sec-label">关键要点</h3>
        <ol class="kp-list">{kp_html}</ol>
      </section>

      <section class="sec-analysis">
        <h3 class="sec-label">深度解读</h3>
        <p class="prose">{detailed_analysis}</p>
      </section>

    </div>

    <div class="insight-band">
      <div class="insight-inner">
        <span class="insight-eyebrow">关键洞察</span>
        <p class="insight-text">{key_insight}</p>
      </div>
    </div>

    <div class="matters-wrap">
      <h3 class="sec-label matters-label">为什么现在值得关注</h3>
      <p class="prose matters-prose">{why_it_matters}</p>
    </div>

    <footer class="story-foot">
      <div class="foot-tags">{tags_html}</div>
      <a class="foot-link" href="{summary['link']}" target="_blank" rel="noopener">阅读原文 ↗</a>
    </footer>

  </div>
</article>
'''

    def render_html(self, summaries: List[Dict], date_str: str) -> str:
        """Render complete HTML page"""

        articles_html = ""
        for i, summary in enumerate(summaries, 1):
            articles_html += self.render_article(summary, i)

        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>TechDaily — 每日技术精选</title>
<link href="https://fonts.googleapis.com" rel="preconnect"/>
<link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,800;1,400;1,700&family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;0,8..60,500;1,8..60,400&family=IBM+Plex+Mono:wght@300;400;500&display=swap" rel="stylesheet"/>
<style>
        :root {{
            --paper:        #f5efdf;
            --paper-warm:   #ede6d0;
            --paper-deep:   #d9d0ba;
            --paper-line:   #c6bca6;

            --ink-0:   #0f0f0e;
            --ink-1:   #1a1916;
            --ink-2:   #2e2d2a;
            --ink-3:   #5c5b57;
            --ink-4:   #8a8880;

            --forest:       #1b5e38;
            --forest-mid:   #2d7a52;
            --forest-light: #3d9966;
            --forest-pale:  #e4efe9;

            --amber:        #92400e;
            --amber-mid:    #b45309;
            --amber-warm:   #d97706;
            --amber-mist:   #fdf6e3;

            --slate:        #1c2b3a;
            --slate-mid:    #243649;
            --slate-text:   #dde4ee;

            --font-display: 'Playfair Display', Georgia, serif;
            --font-body:    'Source Serif 4', Georgia, serif;
            --font-mono:    'IBM Plex Mono', 'Courier New', monospace;
        }}

        /* Reset */
        *, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}
        a {{ color: inherit; text-decoration: none; }}

        html {{
            font-size: 17px;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            text-rendering: optimizeLegibility;
        }}

        body {{
            font-family: var(--font-body);
            background-color: var(--paper);
            color: var(--ink-1);
            line-height: 1.8;
            min-height: 100vh;
        }}

        /* Page */
        .page {{
            max-width: 860px;
            margin: 0 auto;
            padding: 0 2.5rem;
        }}

        /* ══ Masthead ══ */
        .masthead {{
            padding: 4rem 0 0;
        }}
        .masthead-rule {{
            display: flex;
            flex-direction: column;
            gap: 3px;
            margin-bottom: 1.75rem;
        }}
        .masthead-rule span:first-child {{
            display: block; height: 4px; background: var(--ink-0);
        }}
        .masthead-rule span:last-child {{
            display: block; height: 1px; background: var(--ink-0);
        }}
        .masthead-logo {{
            font-family: var(--font-display);
            font-size: clamp(4rem, 10vw, 7.5rem);
            font-weight: 800;
            letter-spacing: -0.04em;
            line-height: 0.88;
            color: var(--ink-0);
            margin-bottom: 1.5rem;
        }}
        .masthead-logo em {{
            font-style: italic;
            color: var(--forest);
            font-weight: 700;
        }}
        .masthead-sub {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.9rem 0;
            border-top: 1px solid var(--paper-line);
            font-family: var(--font-mono);
            font-size: 0.6rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: var(--ink-4);
        }}
        .masthead-sub-date {{
            color: var(--forest);
            font-weight: 500;
        }}

        /* Edition bar */
        .edition-bar {{
            display: flex;
            align-items: center;
            gap: 1.25rem;
            padding: 2.75rem 0 2.25rem;
        }}
        .edition-bar-label {{
            font-family: var(--font-mono);
            font-size: 0.56rem;
            letter-spacing: 0.26em;
            text-transform: uppercase;
            color: var(--ink-4);
            white-space: nowrap;
            flex-shrink: 0;
        }}
        .edition-bar-line {{
            flex: 1; height: 1px;
            background: var(--paper-line);
        }}

        /* ══ Story ══ */
        .story {{
            display: grid;
            grid-template-columns: 3.5rem 1fr;
            gap: 0 2rem;
            padding: 3.5rem 0 4rem;
            border-bottom: 1px solid var(--paper-line);
        }}
        .story:last-child {{ border-bottom: none; }}

        .story-index {{
            font-family: var(--font-mono);
            font-size: 0.58rem;
            letter-spacing: 0.1em;
            color: var(--paper-deep);
            padding-top: 0.6rem;
            text-align: right;
            user-select: none;
        }}

        .story-inner {{ min-width: 0; }}

        /* Story head */
        .story-head {{ margin-bottom: 1.5rem; }}

        .story-meta {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.8rem;
            font-family: var(--font-mono);
            font-size: 0.6rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--ink-4);
            flex-wrap: wrap;
        }}
        .meta-source {{ color: var(--forest); font-weight: 500; }}
        .meta-dot {{ color: var(--paper-deep); }}
        .meta-level {{
            padding: 0.15em 0.55em;
            border: 1px solid currentColor;
            font-size: 0.52rem;
        }}
        .lv-b {{ color: var(--ink-4); }}
        .lv-m {{ color: var(--forest-mid); }}
        .lv-a {{ color: var(--amber-mid); }}

        .story-title {{
            font-family: var(--font-display);
            font-size: clamp(2rem, 4.5vw, 3rem);
            font-weight: 800;
            line-height: 1.06;
            letter-spacing: -0.03em;
            color: var(--ink-0);
            display: block;
            transition: color 0.15s;
        }}
        .story-title:hover, .story-title a:hover {{ color: var(--forest); }}
        .story-title a {{ color: inherit; text-decoration: none; }}

        /* Lede */
        .lede-wrap {{
            margin-bottom: 2.5rem;
            padding: 1.4rem 0 1.4rem 1.75rem;
            border-left: 4px solid var(--forest);
        }}
        .lede {{
            font-family: var(--font-display);
            font-size: clamp(1.25rem, 2.5vw, 1.6rem);
            font-style: italic;
            font-weight: 400;
            line-height: 1.45;
            color: var(--ink-2);
        }}

        /* Story grid */
        .story-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0 3rem;
        }}

        /* Section label */
        .sec-label {{
            font-family: var(--font-mono);
            font-size: 0.56rem;
            font-weight: 500;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: var(--ink-4);
            margin-bottom: 1.1rem;
            display: flex;
            align-items: center;
            gap: 0.7rem;
        }}
        .sec-label::after {{
            content: '';
            flex: 1; height: 1px;
            background: var(--paper-line);
        }}

        /* Key points */
        .kp-list {{ list-style: none; }}
        .kp-list li {{
            display: grid;
            grid-template-columns: 1.5rem 1fr;
            gap: 0.5rem;
            padding: 0.8rem 0;
            border-bottom: 1px solid var(--paper-line);
            align-items: baseline;
        }}
        .kp-list li:first-child {{ border-top: 1px solid var(--paper-line); }}
        .kp-n {{
            font-family: var(--font-mono);
            font-size: 0.6rem;
            font-weight: 500;
            color: var(--forest-mid);
            line-height: 1.8;
        }}
        .kp-body {{
            font-size: 0.87rem;
            line-height: 1.7;
            color: var(--ink-2);
        }}

        /* Analysis */
        .prose {{
            font-size: 0.95rem;
            line-height: 1.85;
            color: var(--ink-2);
        }}

        /* ══ 关键洞察 — 报纸拉引式，纯排版，无背景色 ══
           设计语言：用粗细双规线 + 超大 Playfair italic + 墨绿色
           做到突出显眼，但与纸面浑然一体，完全不割裂 */
        .insight-band {{
            /* 无背景色——留在纸面上 */
            margin: 3rem 0 0;
            padding: 2.25rem 0 2rem;
            /* 顶部双规线：3px 粗线 + 3px 间距 + 1px 细线 */
            border-top: 3px solid var(--ink-0);
            position: relative;
        }}
        /* 顶部细线（双规线效果，用伪元素实现第二条） */
        .insight-band::before {{
            content: '';
            position: absolute;
            top: 6px;   /* 3px border + 3px gap */
            left: 0; right: 0;
            height: 1px;
            background: var(--ink-0);
        }}
        /* 底部单细线 */
        .insight-band::after {{
            content: '';
            position: absolute;
            bottom: 0; left: 0; right: 0;
            height: 1px;
            background: var(--paper-line);
        }}
        .insight-inner {{
            padding-top: 1.5rem;
        }}
        .insight-eyebrow {{
            display: block;
            font-family: var(--font-mono);
            font-size: 0.54rem;
            letter-spacing: 0.26em;
            text-transform: uppercase;
            color: var(--forest);
            margin-bottom: 1rem;
        }}
        /* 核心文字——尺寸即态度 */
        .insight-text {{
            font-family: var(--font-display);
            font-size: clamp(1.55rem, 2.8vw, 2rem);
            font-style: italic;
            line-height: 1.4;
            letter-spacing: -0.015em;
            /* 墨绿色：authority + 与纸面协调 */
            color: var(--forest);
            font-weight: 400;
        }}

        /* ══ 为什么值得关注 — 纯排版，不用彩色方框 ══ */
        .matters-wrap {{
            margin-top: 2.75rem;
            padding-top: 1.5rem;
            border-top: 2px solid var(--amber-warm);
        }}
        .matters-label {{
            color: var(--amber-mid);
        }}
        .matters-label::after {{
            background: rgba(180,83,9,0.15);
        }}
        .matters-prose {{
            color: var(--ink-2);
            font-size: 0.93rem;
            line-height: 1.85;
        }}

        /* Story foot */
        .story-foot {{
            margin-top: 2rem;
            padding-top: 1.1rem;
            border-top: 1px solid var(--paper-line);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.75rem;
            flex-wrap: wrap;
        }}
        .foot-tags {{ display: flex; gap: 0.35rem; flex-wrap: wrap; }}
        .tag {{
            font-family: var(--font-mono);
            font-size: 0.53rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--ink-3);
            padding: 0.28em 0.75em;
            border: 1px solid var(--paper-deep);
            background: var(--paper-warm);
            white-space: nowrap;
            transition: border-color 0.15s, color 0.15s;
        }}
        .tag:hover {{ border-color: var(--forest-mid); color: var(--forest); }}
        .foot-link {{
            font-family: var(--font-mono);
            font-size: 0.62rem;
            font-weight: 500;
            letter-spacing: 0.06em;
            color: var(--forest);
            border-bottom: 1px solid var(--forest-mid);
            padding-bottom: 1px;
            white-space: nowrap;
            transition: color 0.12s, border-color 0.12s;
        }}
        .foot-link:hover {{ color: var(--forest-light); border-color: var(--forest-light); }}

        /* Page footer */
        .page-footer {{
            border-top: 1px solid var(--paper-line);
            padding: 2.25rem 0 4rem;
            margin-top: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.75rem;
            font-family: var(--font-mono);
            font-size: 0.58rem;
            letter-spacing: 0.1em;
            color: var(--ink-4);
        }}
        .footer-brand {{ color: var(--ink-3); }}

        /* Empty state */
        .empty-state {{
            text-align: center;
            padding: 8rem 2rem;
        }}
        .empty-state h2 {{
            font-family: var(--font-display);
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--ink-3);
            margin-bottom: 1rem;
        }}
        .empty-state p {{ color: var(--ink-4); }}

        /* ══ 入场动画 ══ */

        /* Masthead & edition-bar：页面加载时淡入上升 */
        .masthead {{
            opacity: 0;
            animation: anim-fade-up 0.65s cubic-bezier(0.22, 1, 0.36, 1) 0.1s forwards;
        }}
        .edition-bar {{
            opacity: 0;
            animation: anim-fade-up 0.55s cubic-bezier(0.22, 1, 0.36, 1) 0.3s forwards;
        }}
        @keyframes anim-fade-up {{
            from {{ opacity: 0; transform: translateY(18px); }}
            to   {{ opacity: 1; transform: none; }}
        }}

        /* Story：初始隐藏，滚动进入视口时 is-visible 触发 */
        .story {{
            opacity: 0;
            transform: translateY(24px);
            transition:
                opacity 0.6s cubic-bezier(0.22, 1, 0.36, 1),
                transform 0.6s cubic-bezier(0.22, 1, 0.36, 1);
        }}
        .story.is-visible {{
            opacity: 1;
            transform: none;
        }}

        /* Story index 数字：比主体稍晚出现 */
        .story-index {{
            transition:
                opacity 0.5s ease 0.15s,
                color 0.18s;
        }}
        .story:not(.is-visible) .story-index {{ opacity: 0; }}

        /* insight-band 内容：滚动进入时向上滑入 */
        .insight-inner {{
            opacity: 0;
            transform: translateY(10px);
            transition:
                opacity 0.5s ease 0.18s,
                transform 0.5s ease 0.18s;
        }}
        .insight-band.is-visible .insight-inner {{
            opacity: 1;
            transform: none;
        }}
        /* 双规线的第二条细线：从左向右划入 */
        .insight-band::before {{
            transform: scaleX(0);
            transform-origin: left center;
            transition: transform 0.7s cubic-bezier(0.22, 1, 0.36, 1) 0.1s;
        }}
        .insight-band.is-visible::before {{
            transform: scaleX(1);
        }}

        /* ══ Hover 交互 ══ */

        /* Lede 左侧绿条：悬停时加深 + 微加粗 */
        .lede-wrap {{
            transition:
                border-left-color 0.2s ease,
                border-left-width 0.2s ease,
                padding-left 0.2s ease;
        }}
        .story:hover .lede-wrap {{
            border-left-color: var(--forest-mid);
            border-left-width: 5px;
            padding-left: 1.6rem;
        }}

        /* 关键要点每行：悬停时左侧轻微缩进 + 底纹 */
        .kp-list li {{
            transition:
                background-color 0.15s ease,
                padding-left 0.18s ease;
        }}
        .kp-list li:hover {{
            background-color: rgba(27, 94, 56, 0.04);
            padding-left: 0.3rem;
        }}

        /* 关键洞察文字：悬停时颜色略微加深 */
        .insight-text {{
            transition: color 0.2s ease;
        }}
        .insight-band:hover .insight-text {{
            color: var(--forest-mid);
        }}

        /* 阅读原文链接：下划线从左向右擦入 */
        .foot-link {{
            position: relative;
            border-bottom: none !important;
            padding-bottom: 2px;
        }}
        .foot-link::after {{
            content: '';
            position: absolute;
            bottom: 0; left: 0;
            width: 0;
            height: 1px;
            background: currentColor;
            transition: width 0.22s ease;
        }}
        .foot-link:hover::after {{
            width: 100%;
        }}

        /* Responsive */
        @media (max-width: 680px) {{
            html {{ font-size: 16px; }}
            .page {{ padding: 0 1.25rem; }}
            .masthead {{ padding: 2.5rem 0 0; }}
            .story {{
                grid-template-columns: 1fr;
                padding: 2.5rem 0 3rem;
            }}
            .story-index {{ display: none; }}
            .story-grid {{ grid-template-columns: 1fr; gap: 2rem; }}
            .insight-band {{
                padding: 2.75rem 0;
            }}
            .insight-band::before {{ margin-left: 1.25rem; }}
            .insight-band::after {{ margin-left: 1.25rem; }}
            .insight-inner {{
                padding: 0 1.25rem 0 1.25rem;
            }}
            .insight-inner::before {{ font-size: 10rem; top: -2rem; left: 0; }}
            .insight-text {{ font-size: clamp(1.4rem, 6vw, 1.8rem); }}
            .lede-wrap {{ padding-left: 1.25rem; }}
            .matters-wrap {{ margin-top: 2rem; }}
        }}

        /* 无障碍：尊重用户的减少动画偏好 */
        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
                transition-duration: 0.01ms !important;
                animation-duration: 0.01ms !important;
                animation-delay: 0ms !important;
            }}
            /* 确保内容在无动画时仍然可见 */
            .story,
            .insight-inner,
            .masthead,
            .edition-bar {{
                opacity: 1;
                transform: none;
                animation: none;
            }}
            .insight-band::before {{
                transform: scaleX(1);
            }}
        }}

        /* ══ 历史推送 ══ */
        .history-edition-bar {{
            margin-top: 3.5rem;
            padding-top: 2rem;
            border-top: 2px solid var(--paper-line);
        }}

        .load-more-wrap {{
            padding: 3rem 0 2.5rem;
            text-align: center;
            display: none;
        }}
        .load-more-btn {{
            font-family: var(--font-mono);
            font-size: 0.65rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: var(--forest);
            background: transparent;
            border: 1px solid var(--forest-mid);
            padding: 0.85em 2.75em;
            cursor: pointer;
            transition: background 0.18s, color 0.18s, border-color 0.18s;
        }}
        .load-more-btn:hover:not(:disabled) {{
            background: var(--forest);
            color: var(--paper);
        }}
        .load-more-btn:disabled {{
            color: var(--ink-4);
            border-color: var(--paper-deep);
            cursor: default;
        }}
    </style>
</head>
<body>
<div class="page">

  <header class="masthead">
    <div class="masthead-rule"><span></span><span></span></div>
    <h1 class="masthead-logo">Tech<em>Daily</em></h1>
    <div class="masthead-sub">
      <span>精选技术情报 · 每日更新</span>
      <span class="masthead-sub-date">{date_str}</span>
    </div>
  </header>

  <div class="edition-bar">
    <span class="edition-bar-label">今日精选</span>
    <span class="edition-bar-line"></span>
  </div>

  <main id="main-feed">
{articles_html}
  </main>

  <div class="load-more-wrap" id="load-more-wrap">
    <button class="load-more-btn" id="load-more-btn" onclick="loadMore()">
      查看更多历史推送
    </button>
  </div>

  <footer class="page-footer">
    <span class="footer-brand">TechDaily — 精选技术博客每日摘要</span>
    <span>{datetime.now().strftime("%Y")} · 每日自动生成</span>
  </footer>

</div>

<script>
(function() {{
  // ── 滚动入场 Observer（今日 + 历史动态插入均共用） ──────────────
  var io = new IntersectionObserver(function(entries) {{
    entries.forEach(function(e) {{
      if (e.isIntersecting) {{
        e.target.classList.add('is-visible');
        io.unobserve(e.target);
      }}
    }});
  }}, {{ threshold: 0.07, rootMargin: '0px 0px -32px 0px' }});

  document.querySelectorAll('.story').forEach(function(el, idx) {{
    el.style.transitionDelay = (idx * 0.08) + 's';
    io.observe(el);
  }});
  document.querySelectorAll('.insight-band').forEach(function(el) {{
    io.observe(el);
  }});

  // ── 平滑滚动锚点 ────────────────────────────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(function(a) {{
    a.addEventListener('click', function(e) {{
      var target = document.querySelector(a.getAttribute('href'));
      if (target) {{
        e.preventDefault();
        target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }}
    }});
  }});

  // ── 历史推送加载 ─────────────────────────────────────────────────
  var allDates = [];
  var currentIndex = 1;  // index 0 = 今日（已预渲染），从 1 开始加载

  // 工具函数
  function clean(s) {{
    return s ? s.replace(/\.\.\./g, '').replace(/…/g, '').trim() : '';
  }}
  function getSource(link, fallback) {{
    try {{ return new URL(link || '').hostname.replace(/^www\./, '') || fallback || ''; }}
    catch(e) {{ return fallback || ''; }}
  }}
  function fmtDate(pub) {{
    var p = (pub || '').slice(0, 10).split('-');
    return p.length === 3 ? (parseInt(p[1]) + '月' + parseInt(p[2]) + '日') : pub;
  }}
  function levelCls(lv) {{
    lv = lv || '中级';
    return lv.indexOf('初') !== -1 ? 'lv-b' : (lv.indexOf('高') !== -1 ? 'lv-a' : 'lv-m');
  }}

  function buildKeyPoints(pts) {{
    return (pts || []).slice(0, 3).map(function(pt, i) {{
      var p = clean(pt);
      if (p.indexOf('要点') === 0 && p.indexOf('：') !== -1)
        p = p.split('：').slice(1).join('：').trim();
      return '<li><span class="kp-n">' + String(i+1).padStart(2,'0') +
             '</span><span class="kp-body">' + p + '</span></li>';
    }}).join('');
  }}
  function buildTags(tags) {{
    return (tags || []).slice(0, 3).map(function(t) {{
      return '<span class="tag">' + t + '</span>';
    }}).join('');
  }}

  function buildArticle(s, idx) {{
    var lv = s.level || '中级';
    return '<article class="story">' +
      '<div class="story-index">' + String(idx).padStart(2,'0') + '</div>' +
      '<div class="story-inner">' +
        '<header class="story-head">' +
          '<div class="story-meta">' +
            '<span class="meta-source">' + getSource(s.link, s.source) + '</span>' +
            '<span class="meta-dot">·</span>' +
            '<span class="meta-date">' + fmtDate(s.published) + '</span>' +
            '<span class="meta-dot">·</span>' +
            '<span class="meta-level ' + levelCls(lv) + '">' + lv + '</span>' +
          '</div>' +
          '<h2 class="story-title"><a href="' + s.link + '" target="_blank" rel="noopener">' +
            (s.headline || '') + '</a></h2>' +
        '</header>' +
        '<div class="lede-wrap"><p class="lede">' + clean(s.one_liner || '') + '</p></div>' +
        '<div class="story-grid">' +
          '<section class="sec-points"><h3 class="sec-label">关键要点</h3>' +
            '<ol class="kp-list">' + buildKeyPoints(s.key_points) + '</ol></section>' +
          '<section class="sec-analysis"><h3 class="sec-label">深度解读</h3>' +
            '<p class="prose">' + clean(s.detailed_analysis || s.summary || '') + '</p></section>' +
        '</div>' +
        '<div class="insight-band"><div class="insight-inner">' +
          '<span class="insight-eyebrow">关键洞察</span>' +
          '<p class="insight-text">' + clean(s.key_insight || '') + '</p>' +
        '</div></div>' +
        '<div class="matters-wrap">' +
          '<h3 class="sec-label matters-label">为什么现在值得关注</h3>' +
          '<p class="prose matters-prose">' + clean(s.why_it_matters || '') + '</p>' +
        '</div>' +
        '<footer class="story-foot">' +
          '<div class="foot-tags">' + buildTags(s.tags) + '</div>' +
          '<a class="foot-link" href="' + s.link + '" target="_blank" rel="noopener">阅读原文 ↗</a>' +
        '</footer>' +
      '</div></article>';
  }}

  function buildDateHeader(dateStr) {{
    var p = dateStr.split('-');
    var label = p[0] + '年' + parseInt(p[1]) + '月' + parseInt(p[2]) + '日';
    return '<div class="edition-bar history-edition-bar">' +
      '<span class="edition-bar-label">' + label + ' · 历史推送</span>' +
      '<span class="edition-bar-line"></span></div>';
  }}

  // 初始化：拉取日期索引，决定是否显示按钮
  fetch('data/index.json')
    .then(function(r) {{ return r.ok ? r.json() : Promise.reject(); }})
    .then(function(dates) {{
      allDates = dates;
      if (allDates.length >= 1) {{
        var wrap = document.getElementById('load-more-wrap');
        var btn = document.getElementById('load-more-btn');
        wrap.style.display = '';
        if (currentIndex >= allDates.length) {{
          btn.textContent = '已显示全部历史';
          btn.disabled = true;
        }}
      }}
    }})
    .catch(function() {{ /* 无历史数据，静默忽略 */ }});

  window.loadMore = function() {{
    if (currentIndex >= allDates.length) return;
    var btn = document.getElementById('load-more-btn');
    btn.disabled = true;
    btn.textContent = '加载中 …';

    var date = allDates[currentIndex];
    currentIndex++;

    fetch('data/' + date + '.json')
      .then(function(r) {{ return r.ok ? r.json() : Promise.reject(); }})
      .then(function(data) {{
        var feed = document.getElementById('main-feed');

        // 日期分隔标题
        var hWrap = document.createElement('div');
        hWrap.innerHTML = buildDateHeader(date);
        feed.appendChild(hWrap.firstElementChild);

        // 文章列表
        var newStories = [];
        (data.articles || []).forEach(function(s, i) {{
          var wrap = document.createElement('div');
          wrap.innerHTML = buildArticle(s, i + 1);
          var article = wrap.firstElementChild;
          feed.appendChild(article);
          newStories.push(article);
          article.querySelectorAll('.insight-band').forEach(function(b) {{ io.observe(b); }});
        }});

        // 错开入场动画
        requestAnimationFrame(function() {{
          requestAnimationFrame(function() {{
            newStories.forEach(function(el, i) {{
              el.style.transitionDelay = (i * 0.06) + 's';
              io.observe(el);
            }});
          }});
        }});

        if (currentIndex < allDates.length) {{
          btn.disabled = false;
          btn.textContent = '查看更多历史推送';
        }} else {{
          btn.textContent = '已显示全部历史';
          btn.disabled = true;
        }}
      }})
      .catch(function() {{
        currentIndex--;
        btn.disabled = false;
        btn.textContent = '加载失败，点击重试';
      }});
  }};
}})();
</script>
</body>
</html>'''

    def get_data_dir(self) -> str:
        """Return (and create) the frontend/data/ directory"""
        data_dir = os.path.join(os.path.dirname(self.output_path), 'data')
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def save_daily_json(self, summaries: List[Dict], date_key: str, date_display: str):
        """Persist today's AI summaries as frontend/data/YYYY-MM-DD.json"""
        data_dir = self.get_data_dir()
        day_path = os.path.join(data_dir, f'{date_key}.json')
        payload = {
            'date': date_key,
            'date_display': date_display,
            'articles': summaries,
        }
        with open(day_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"Saved daily JSON: {day_path}")

    def update_index_json(self, date_key: str):
        """Maintain frontend/data/index.json — a sorted-desc list of available dates"""
        data_dir = self.get_data_dir()
        index_path = os.path.join(data_dir, 'index.json')

        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                dates = json.load(f)
        else:
            dates = []

        if date_key not in dates:
            dates.append(date_key)

        dates.sort(reverse=True)  # newest first

        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(dates, f, ensure_ascii=False, indent=2)
        print(f"Updated index.json: {len(dates)} date(s) on record")

    def generate(self, since_hours: int = 24, max_articles: Optional[int] = None) -> int:
        """
        Generate daily digest
        Returns number of articles processed
        """
        print("=" * 60)
        print("TechDaily Digest Generator")
        print("=" * 60)

        # Fetch articles
        print(f"\nFetching articles from last {since_hours} hours...")
        articles = self.fetcher.fetch_all(since_hours=since_hours)

        if not articles:
            print("No new articles found.")
            # Generate empty state HTML
            html = self.render_html([], datetime.now().strftime("%Y年%m月%d日"))
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"Generated empty digest at: {self.output_path}")
            return 0

        # Sort by publication date, newest first
        articles.sort(key=lambda a: a.published, reverse=True)

        # Optionally limit the number of articles
        if max_articles is not None:
            articles = articles[:max_articles]
        print(f"\nProcessing {len(articles)} articles...")

        # Generate summaries
        summaries = []
        for article in articles:
            print(f"  - {article.title[:60]}...")
            summary = self.generate_summary(article)
            summaries.append(summary)

        # Save to database
        self.fetcher.save_articles(articles)

        # Persist daily JSON for history feature
        date_key = datetime.now().strftime("%Y-%m-%d")
        date_str = datetime.now().strftime("%Y年%m月%d日")
        self.save_daily_json(summaries, date_key, date_str)
        self.update_index_json(date_key)

        # Generate HTML
        html = self.render_html(summaries, date_str)

        # Write output
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print("\n" + "=" * 60)
        print(f"Digest generated successfully!")
        print(f"Output: {self.output_path}")
        print(f"Articles: {len(summaries)}")
        print("=" * 60)

        return len(summaries)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate TechDaily digest')
    parser.add_argument('--hours', type=int, default=24, help='Fetch articles from last N hours')
    parser.add_argument('--max', type=int, default=None, help='Maximum articles to include (default: no limit)')
    parser.add_argument('--output', type=str, default=None, help='Output HTML path')

    args = parser.parse_args()

    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    opml_path = os.path.join(base_dir, 'config', 'feeds.opml')
    db_path = os.path.join(base_dir, 'database', 'articles.json')

    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(base_dir, 'frontend', 'index.html')

    # Generate
    generator = DigestGenerator(opml_path, db_path, output_path)
    count = generator.generate(since_hours=args.hours, max_articles=args.max)

    return 0 if count >= 0 else 1


if __name__ == '__main__':
    sys.exit(main())
