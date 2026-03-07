import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from datetime import datetime
from app.core.logger import setup_logger
import random

logger = setup_logger("twitter_provider")

class TwitterProvider:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]

    async def scrape_tweets(self, target_user: str, limit: int = 5):
        """Scrape les derniers tweets d'un utilisateur sans API."""
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=random.choice(self.user_agents),
                viewport={'width': 1280, 'height': 800}
            )
            page = await context.new_page()
            await stealth_async(page)

            url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{target_user}"
            logger.info(f"Scraping tweets pour @{target_user} via {url}")

            try:
                await page.goto(url, wait_until="networkidle")
                # Twitter Syndication renvoie du JSON ou du HTML simplifié
                # On cherche les éléments de tweet
                tweets = await page.query_selector_all('li.timeline-Tweet')
                
                for tweet in tweets[:limit]:
                    text_el = await tweet.query_selector('.timeline-Tweet-text')
                    date_el = await tweet.query_selector('time')
                    
                    if text_el:
                        content = await text_el.inner_text()
                        timestamp_str = await date_el.get_attribute('datetime') if date_el else None
                        
                        results.append({
                            "content": content,
                            "url": f"https://twitter.com/{target_user}",
                            "source": f"Twitter (@{target_user})",
                            "published_at": timestamp_str
                        })
            except Exception as e:
                logger.error(f"Erreur scraping Twitter pour {target_user}: {e}")
            finally:
                await browser.close()
        
        return results

    async def scrape_hashtag(self, hashtag: str, limit: int = 5):
        """Note: Le scraping de hashtag est plus complexe sans auth. 
        Pour la V1, on se focalise sur les profils sources d'autorité."""
        return []
