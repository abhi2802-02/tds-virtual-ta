#!/usr/bin/env python3
"""
Discourse Scraping Script for TDS Course
=========================================

This script scrapes Discourse posts from the TDS course forum for a specified date range.
It's designed to work with the IIT Madras Online Degree program's Discourse instance.

Usage:
    python scrape_discourse.py --start-date 2025-01-01 --end-date 2025-04-14 --category tds-kb

Requirements:
    - requests
    - beautifulsoup4
    - python-dotenv

Author: TDS Virtual Teaching Assistant Project
License: MIT
"""

import requests
import json
import argparse
from datetime import datetime, timedelta
from urllib.parse import urljoin
import time
import logging
from typing import List, Dict, Any
import os
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DiscourseScraper:
    """Scraper for Discourse forum posts"""
    
    def __init__(self, base_url: str = "https://discourse.onlinedegree.iitm.ac.in"):
        """
        Initialize the scraper
        
        Args:
            base_url: Base URL of the Discourse instance
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def scrape_category(self, category_id: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Scrape posts from a specific category within a date range
        
        Args:
            category_id: Category identifier (e.g., 'tds-kb' or '34')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of post dictionaries
        """
        posts = []
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        try:
            # Get category URL - try both slug and ID
            if category_id.isdigit():
                category_url = f"{self.base_url}/c/{category_id}.json"
            else:
                category_url = f"{self.base_url}/c/{category_id}.json"
                
            logger.info(f"Fetching category data from: {category_url}")
            
            response = self.session.get(category_url)
            response.raise_for_status()
            
            category_data = response.json()
            
            if 'topic_list' not in category_data or 'topics' not in category_data['topic_list']:
                logger.warning("No topics found in category response")
                return posts
            
            topics = category_data['topic_list']['topics']
            logger.info(f"Found {len(topics)} topics in category")
            
            for topic in topics:
                try:
                    # Check if topic is within date range
                    created_at_str = topic.get('created_at', '')
                    if not created_at_str:
                        continue
                        
                    # Parse date (handle different formats)
                    try:
                        if 'T' in created_at_str:
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        else:
                            created_at = datetime.strptime(created_at_str, '%Y-%m-%d')
                    except ValueError as e:
                        logger.warning(f"Could not parse date {created_at_str}: {e}")
                        continue
                    
                    # Remove timezone info for comparison
                    created_at = created_at.replace(tzinfo=None)
                    
                    if not (start_dt <= created_at <= end_dt):
                        continue
                    
                    # Get topic details
                    topic_posts = self.scrape_topic(topic['id'])
                    posts.extend(topic_posts)
                    
                    # Be respectful - add small delay
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"Error processing topic {topic.get('id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(posts)} posts from date range {start_date} to {end_date}")
            return posts
            
        except Exception as e:
            logger.error(f"Error scraping category {category_id}: {e}")
            return posts
    
    def scrape_topic(self, topic_id: int) -> List[Dict[str, Any]]:
        """
        Scrape all posts from a specific topic
        
        Args:
            topic_id: Topic ID
            
        Returns:
            List of post dictionaries
        """
        posts = []
        
        try:
            topic_url = f"{self.base_url}/t/{topic_id}.json"
            response = self.session.get(topic_url)
            response.raise_for_status()
            
            topic_data = response.json()
            
            if 'post_stream' not in topic_data or 'posts' not in topic_data['post_stream']:
                return posts
            
            topic_title = topic_data.get('title', 'Unknown Topic')
            topic_slug = topic_data.get('slug', str(topic_id))
            
            for post in topic_data['post_stream']['posts']:
                post_content = self._clean_content(post.get('cooked', ''))
                
                if post_content and len(post_content.strip()) > 10:
                    posts.append({
                        'id': f"discourse_post_{post['id']}",
                        'type': 'discourse_post',
                        'title': topic_title,
                        'content': post_content,
                        'raw_content': post.get('raw', ''),
                        'url': f"{self.base_url}/t/{topic_slug}/{topic_id}/{post.get('post_number', 1)}",
                        'author': post.get('username', ''),
                        'created_at': post.get('created_at', ''),
                        'topic_id': topic_id,
                        'post_number': post.get('post_number', 1),
                        'scraped_at': datetime.utcnow().isoformat()
                    })
            
            return posts
            
        except Exception as e:
            logger.error(f"Error scraping topic {topic_id}: {e}")
            return posts
    
    def _clean_content(self, html_content: str) -> str:
        """Clean HTML content and extract text"""
        if not html_content:
            return ""
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.warning(f"Error cleaning content: {e}")
            return html_content
    
    def save_to_file(self, posts: List[Dict[str, Any]], output_file: str):
        """Save posts to JSON file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(posts)} posts to {output_file}")
        except Exception as e:
            logger.error(f"Error saving to file {output_file}: {e}")

def main():
    """Main function to run the scraper"""
    parser = argparse.ArgumentParser(description='Scrape Discourse posts from TDS course forum')
    parser.add_argument('--start-date', default='2025-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2025-04-14', help='End date (YYYY-MM-DD)')
    parser.add_argument('--category', default='tds-kb/34', help='Category slug or ID (e.g., tds-kb or 34)')
    parser.add_argument('--output', default='discourse_posts.json', help='Output JSON file')
    parser.add_argument('--base-url', default='https://discourse.onlinedegree.iitm.ac.in', help='Discourse base URL')
    
    args = parser.parse_args()
    
    # Validate dates
    try:
        datetime.strptime(args.start_date, '%Y-%m-%d')
        datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError:
        logger.error("Invalid date format. Use YYYY-MM-DD")
        return 1
    
    # Initialize scraper
    scraper = DiscourseScraper(args.base_url)
    
    # Handle category format (e.g., "tds-kb/34" or just "34")
    if '/' in args.category:
        category_parts = args.category.split('/')
        category_id = category_parts[-1]  # Use the last part (usually the ID)
    else:
        category_id = args.category
    
    logger.info(f"Starting scrape for category {category_id} from {args.start_date} to {args.end_date}")
    
    # Scrape posts
    posts = scraper.scrape_category(category_id, args.start_date, args.end_date)
    
    if posts:
        # Save to file
        scraper.save_to_file(posts, args.output)
        
        # Print summary
        print(f"\nScraping Summary:")
        print(f"Category: {args.category}")
        print(f"Date range: {args.start_date} to {args.end_date}")
        print(f"Total posts scraped: {len(posts)}")
        print(f"Output file: {args.output}")
        
        # Show sample post
        if posts:
            print(f"\nSample post:")
            sample = posts[0]
            print(f"Title: {sample.get('title', 'N/A')}")
            print(f"Author: {sample.get('author', 'N/A')}")
            print(f"URL: {sample.get('url', 'N/A')}")
            print(f"Content preview: {sample.get('content', '')[:200]}...")
    else:
        print("No posts found for the specified criteria.")
        
    return 0

if __name__ == "__main__":
    exit(main())