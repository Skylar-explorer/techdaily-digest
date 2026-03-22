#!/usr/bin/env python3
"""
RSS Feed Fetcher - Fetches articles from subscribed RSS feeds
"""
import feedparser
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from typing import List, Optional
import hashlib
import json
import os
import time
import requests
from bs4 import BeautifulSoup


@dataclass
class Article:
    """Represents a fetched article"""
    id: str
    title: str
    link: str
    author: str
    published: datetime
    summary: str
    content: str
    source_name: str
    source_url: str
    fetched_at: datetime


class RSSFetcher:
    def __init__(self, opml_path: str, db_path: str):
        self.opml_path = opml_path
        self.db_path = db_path
        self.feeds = self._load_feeds()
        self._ensure_db()

    def _load_feeds(self) -> List[dict]:
        """Load RSS feeds from OPML file"""
        tree = ET.parse(self.opml_path)
        root = tree.getroot()

        feeds = []
        for outline in root.findall('.//outline[@type="rss"]'):
            feeds.append({
                'title': outline.get('title', ''),
                'text': outline.get('text', ''),
                'xml_url': outline.get('xmlUrl', ''),
                'html_url': outline.get('htmlUrl', '')
            })

        print(f"Loaded {len(feeds)} RSS feeds")
        return feeds

    def _ensure_db(self):
        """Ensure database directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _generate_id(self, link: str) -> str:
        """Generate unique ID for article"""
        return hashlib.md5(link.encode()).hexdigest()

    def _parse_date(self, entry) -> Optional[datetime]:
        """Parse publication date from feed entry.

        feedparser normalises all timestamps to UTC struct_time.
        We reconstruct them as UTC-aware datetimes so comparisons
        against datetime.now(timezone.utc) are always correct.
        Returns None when no date is available (entry will be skipped).
        """
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        else:
            return None  # No date → skip, don't fake datetime.now()

    def _fetch_full_content(self, url: str) -> str:
        """Fetch full article content from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; TechDailyBot/1.0)'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                script.decompose()

            # Try to find main content
            main_content = None

            # Common content selectors
            selectors = [
                'article', 'main', '.post-content', '.entry-content',
                '.article-content', '#content', '.content', '[role="main"]'
            ]

            for selector in selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            if not main_content:
                main_content = soup.body

            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
                # Clean up excessive whitespace
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                return '\n'.join(lines)

            return ""

        except Exception as e:
            print(f"Error fetching content from {url}: {e}")
            return ""

    def fetch_feed(self, feed_info: dict, since: Optional[datetime] = None) -> List[Article]:
        """Fetch articles from a single feed"""
        articles = []

        try:
            print(f"Fetching: {feed_info['title']}...", end=' ')
            feed = feedparser.parse(feed_info['xml_url'])

            if feed.bozo:
                print(f"WARNING: {feed.bozo_exception}")

            for entry in feed.entries:
                published = self._parse_date(entry)

                # Skip entries with no parseable date (avoids treating
                # undated archive posts as "just published")
                if published is None:
                    continue

                # Skip if article is too old
                if since and published < since:
                    continue

                # Get summary/content
                summary = entry.get('summary', '')
                if hasattr(entry, 'content'):
                    content = entry.content[0].value
                else:
                    content = summary

                # Generate ID
                article_id = self._generate_id(entry.link)

                article = Article(
                    id=article_id,
                    title=entry.get('title', 'Untitled'),
                    link=entry.link,
                    author=entry.get('author', feed_info['title']),
                    published=published,
                    summary=summary,
                    content=content,
                    source_name=feed_info['title'],
                    source_url=feed_info['html_url'],
                    fetched_at=datetime.now()
                )

                articles.append(article)

            print(f"Found {len(articles)} articles")

        except Exception as e:
            print(f"ERROR: {e}")

        return articles

    def fetch_all(self, since_hours: int = 24) -> List[Article]:
        """Fetch articles from all feeds"""
        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        all_articles = []

        print(f"\nFetching articles since {since}...")
        print("=" * 60)

        for feed in self.feeds:
            articles = self.fetch_feed(feed, since)
            all_articles.extend(articles)
            time.sleep(0.5)  # Be nice to servers

        print("=" * 60)
        print(f"Total articles fetched: {len(all_articles)}")

        return all_articles

    def save_articles(self, articles: List[Article]):
        """Save articles to JSON database"""
        db = []

        # Load existing database
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r', encoding='utf-8') as f:
                db = json.load(f)

        existing_ids = {a['id'] for a in db}
        new_count = 0

        # Add new articles
        for article in articles:
            if article.id not in existing_ids:
                db.append(asdict(article))
                existing_ids.add(article.id)
                new_count += 1

        # Save updated database
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, default=str)

        print(f"Saved {new_count} new articles to database")
        return new_count


def main():
    """Test the RSS fetcher"""
    fetcher = RSSFetcher(
        opml_path='/Users/kangshuning/subscribe_rss.txt',
        db_path='/Users/kangshuning/techdaily-digest/database/articles.json'
    )

    # Fetch articles from last 24 hours
    articles = fetcher.fetch_all(since_hours=24)

    # Save to database
    if articles:
        fetcher.save_articles(articles)

        # Print sample
        print("\n" + "=" * 60)
        print("SAMPLE ARTICLES:")
        print("=" * 60)
        for article in articles[:3]:
            print(f"\nTitle: {article.title}")
            print(f"Source: {article.source_name}")
            print(f"Published: {article.published}")
            print(f"Link: {article.link}")
            print(f"Content length: {len(article.content)} chars")
            print("-" * 60)


if __name__ == '__main__':
    main()
