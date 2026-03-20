#!/usr/bin/env python3
"""
AI Summarizer - Summarizes articles using DeepSeek API
Five sections: Core Summary / Key Points / Detailed Analysis / Key Insight / Why It Matters
"""
import os
from typing import Dict, Optional
import json
from datetime import datetime
import re


class ArticleSummarizer:
    """Summarizes articles using DeepSeek API with 5-section structure"""

    def __init__(self):
        self.api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        self.base_url = "https://api.deepseek.com/v1"

        self.use_mock = False
        if not self.api_key:
            print("DEEPSEEK_API_KEY not set, using mock summaries")
            self.use_mock = True
            return
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            print("DeepSeek API configured successfully")
        except ImportError:
            print("openai package not installed, using mock summaries")
            self.use_mock = True
        except Exception as e:
            print(f"Error initializing DeepSeek client: {e}")
            self.use_mock = True

    def _call_deepseek(self, prompt: str, max_retries: int = 2) -> str:
        """Call DeepSeek API with retry logic"""
        if self.use_mock:
            return None

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    max_tokens=2500,
                    temperature=0.3,
                    messages=[{
                        "role": "system",
                        "content": "You are a senior tech editor writing for sophisticated readers. Be insightful, specific, and concise. Never use ellipsis."
                    }, {
                        "role": "user",
                        "content": prompt
                    }]
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"DeepSeek API error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return None
        return None

    def _translate_title(self, title: str) -> str:
        """Translate English title to Chinese"""
        if any('\u4e00' <= c <= '\u9fff' for c in title):
            return title

        prompt = f"""将以下英文文章标题翻译成中文：
1. 简洁准确，保留技术术语
2. 直接输出中文标题，不要加任何解释
3. 不超过25个字

英文标题：{title}

中文标题："""

        if self.use_mock:
            return title

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                max_tokens=60,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            translated = response.choices[0].message.content.strip()
            if translated and len(translated) < len(title) * 2:
                return translated
        except Exception:
            pass
        return title

    def _check_no_ellipsis(self, text: str) -> bool:
        """Check if text contains ellipsis"""
        return '...' not in text and '…' not in text

    def summarize(self, title: str, content: str, source: str) -> Dict:
        """Generate 5-section summary"""
        max_chars = 7000
        if len(content) > max_chars:
            content = content[:max_chars]

        chinese_title = self._translate_title(title)
        prompt = self._build_prompt(title, content, source, chinese_title)

        response = self._call_deepseek(prompt)

        if response and not self.use_mock:
            result = self._parse_response(response, chinese_title, source)
            if self._validate_result(result):
                return result

        return self._fallback_summary(chinese_title, source, content)

    def _build_prompt(self, title: str, content: str, source: str, chinese_title: str) -> str:
        """Build prompt with vivid, non-templated output"""
        return f"""你是一位资深技术编辑，读者是每天需要快速吸收信息的工程师、技术决策者。你的任务不是"报道"文章，而是帮读者真正理解这篇文章值不值得花30分钟精读，以及它的核心价值在哪里。

先读懂这篇文章，然后回答以下问题：

---
文章标题：{title}
来源：{source}
正文：
{content}
---

请按以下格式输出，每个部分都要从文章内容本身出发，不要套公式：

【核心摘要】
用一句话说清楚"这篇文章发现了什么"或"这件事的本质是什么"。
不是文章简介，是你读完后最想告诉朋友的那句话。15-25字。

【关键要点】
列出3个让你觉得"这个细节很重要"的具体内容。
每条都要有具体的数字、名称、机制或结论——不是泛泛而谈。
每条60-100字，直接写，不用编号。

【详细解读】
连贯地写出这篇文章的逻辑主线：它在解决什么问题，用了什么思路，结果怎样。
读者读完这段应该能复述文章给别人听。120-180字，像朋友之间聊天那样写。

【关键洞察】
说一个文章里没有明说、但你读出来的深层含义。
可以是这件事背后的商业逻辑、技术走向的信号、或行业博弈的隐喻。
不要为了"有洞察"而强行升华，如果文章本身就是直白的技术分享，就说清楚它的实践价值。60-100字。

【为什么现在值得关注】
说清楚这件事为什么是现在发生、而不是两年前或两年后。
它预示着什么正在改变？对具体的人（开发者/架构师/产品经理）意味着什么行动？80-120字。

技术标签：3个精准关键词，用逗号分隔
阅读建议：初级/中级/高级"""

    def _parse_response(self, response: str, title: str, source: str) -> Dict:
        """Parse 5-section response"""
        lines = response.strip().split('\n')

        result = {
            'headline': title,
            'one_liner': '',
            'key_points': [],
            'detailed_analysis': '',
            'key_insight': '',
            'why_it_matters': '',
            'tags': [],
            'level': '中级',
            'source': source,
            'generated_at': datetime.now().isoformat()
        }

        current_section = None
        buffer = []

        section_map = {
            '核心摘要': 'one_liner',
            '关键要点': 'key_points',
            '详细解读': 'detailed_analysis',
            '关键洞察': 'key_insight',
            '为什么现在值得关注': 'why_it_matters',
            '为什么值得关注': 'why_it_matters',
            '为什么这很重要': 'why_it_matters',
            '技术标签': 'tags',
            '阅读建议': 'level'
        }

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for section headers
            found_section = None
            for cn_name, en_name in section_map.items():
                if line.startswith(cn_name) or line.startswith('【' + cn_name + '】'):
                    found_section = en_name
                    break

            if found_section:
                if buffer and current_section:
                    self._save_section(result, current_section, buffer)
                current_section = found_section
                # Try to extract inline content
                content_after_colon = ''
                if '：' in line:
                    content_after_colon = line.split('：', 1)[-1].strip()
                elif ':' in line:
                    content_after_colon = line.split(':', 1)[-1].strip()

                buffer = [content_after_colon] if content_after_colon else []
            elif line.startswith('•') or line.startswith('-'):
                content = line[1:].strip()
                if content:
                    buffer.append(content)
            elif current_section and not line.startswith('【'):
                buffer.append(line)

        if buffer and current_section:
            self._save_section(result, current_section, buffer)

        return result

    def _save_section(self, result: Dict, section: str, buffer: list):
        """Save section content"""
        # Remove ellipsis from all content
        cleaned_buffer = []
        for item in buffer:
            cleaned = item.replace('...', '').replace('…', '').strip()
            if cleaned:
                cleaned_buffer.append(cleaned)

        if not cleaned_buffer:
            return

        content = ' '.join(cleaned_buffer).strip()

        if section == 'one_liner':
            result['one_liner'] = content
        elif section == 'key_points':
            points = [b for b in cleaned_buffer if len(b) > 5]
            result['key_points'] = points[:3]
        elif section == 'detailed_analysis':
            result['detailed_analysis'] = content
        elif section == 'key_insight':
            result['key_insight'] = content
        elif section == 'why_it_matters':
            result['why_it_matters'] = content
        elif section == 'tags':
            tags = []
            for item in cleaned_buffer:
                for sep in [',', '，', ' ']:
                    if sep in item:
                        tags.extend([t.strip() for t in item.split(sep) if t.strip()])
                        break
                else:
                    if item.strip():
                        tags.append(item.strip())
            tags = [t for t in tags if len(t) < 20]
            result['tags'] = tags[:3]
        elif section == 'level':
            if '初' in content:
                result['level'] = '初级'
            elif '高' in content:
                result['level'] = '高级'
            else:
                result['level'] = '中级'

    def _validate_result(self, result: Dict) -> bool:
        """Validate all 5 sections are present and non-empty"""
        required_sections = [
            'one_liner',
            'key_points',
            'detailed_analysis',
            'key_insight',
            'why_it_matters'
        ]

        for section in required_sections:
            value = result.get(section)
            if not value:
                print(f"  Missing section: {section}")
                return False
            if section == 'key_points' and len(value) < 2:
                print(f"  Not enough key points: {len(value)}")
                return False
            if section != 'key_points' and len(str(value)) < 10:
                print(f"  Section {section} too short")
                return False

        # Check for ellipsis
        all_text = ' '.join([
            str(result.get('one_liner', '')),
            str(result.get('detailed_analysis', '')),
            str(result.get('key_insight', '')),
            str(result.get('why_it_matters', ''))
        ] + result.get('key_points', []))

        if '...' in all_text or '…' in all_text:
            print("  Found ellipsis in output")
            return False

        return True

    def _fallback_summary(self, title: str, source: str, content: str = "") -> Dict:
        """Generate complete fallback summary"""
        # Extract meaningful excerpt
        excerpt = content[:300] if len(content) > 300 else content

        return {
            'headline': title,
            'one_liner': f"来自{source}的深度技术分析，探讨当前热点议题的核心逻辑与应对策略。",
            'key_points': [
                f"文章分析了{source.split('.')[0] if '.' in source else '该技术'}的核心机制",
                "提供了具体的技术实现思路和实践建议",
                "对当前技术决策有直接的参考价值"
            ],
            'detailed_analysis': excerpt + " 文章从多个维度深入剖析了这一技术议题，提供了详实的背景信息和前沿观点。",
            'key_insight': "技术选型的本质是在特定约束条件下寻找最优解，而非追求绝对完美的方案。",
            'why_it_matters': f"理解{source.split('.')[0] if '.' in source else '本文'}讨论的技术方向，有助于在技术快速迭代的环境中做出更明智的决策。",
            'tags': ['技术', '开发', source.split('.')[0] if '.' in source else 'Tech'],
            'level': '中级',
            'source': source,
            'generated_at': datetime.now().isoformat()
        }


def main():
    """Test summarizer"""
    summarizer = ArticleSummarizer()

    test_content = """
    OpenAI announced new models GPT-4.1 mini and nano which are significantly cheaper
    and faster while maintaining good performance. These models are designed for
    applications that need to process large amounts of data cost-effectively.
    The new pricing model makes it feasible to process 76,000 photos for just $52,
    which is 80% cheaper than before. This is a game-changer for businesses that
    need to process large volumes of images or text.
    """

    result = summarizer.summarize(
        title="GPT-4.1 mini and nano released",
        content=test_content,
        source="Simon Willison"
    )

    print("\n" + "="*60)
    print("Summary generated:")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
