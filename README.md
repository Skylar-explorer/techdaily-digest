# TechDaily — 每日技术精选

一个自动化的技术日报生成器，每天抓取 RSS 订阅源，用 AI 生成文章摘要，输出为精美的单页 HTML。

## 核心问题

技术信息过载——每天有大量技术博客、论文、新闻发布，手动筛选耗时耗力。TechDaily 用 RSS 聚合 + AI 摘要 + 精心设计的排版，把碎片信息变成一份可读的日报。

## 功能

- **RSS 聚合**：从多个技术源（博客、论文、新闻）自动抓取最新文章
- **AI 摘要**：用 DeepSeek API 生成文章核心摘要、关键要点、深度解读
- **精美排版**：单页 HTML，杂志级排版（Playfair Display + Source Serif 4），支持扫读和深读两种模式
- **自动部署**：GitHub Actions 每日定时运行，自动生成并部署到 GitHub Pages

## 技术栈

Python（RSS 抓取 + AI 摘要生成）、DeepSeek API、GitHub Actions、GitHub Pages

## 访问

- **Live**: https://skylar-explorer.github.io/techdaily-digest/
- **源码**: https://github.com/Skylar-explorer/techdaily-digest
