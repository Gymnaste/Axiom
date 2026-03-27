import asyncio
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
        try:
            from playwright.async_api import async_playwright
            try:
                import playwright_stealth
                # On essaie de trouver la fonction la plus appropriée
                if hasattr(playwright_stealth, "stealth_async"):
                    stealth_func = playwright_stealth.stealth_async
                elif hasattr(playwright_stealth, "stealth"):
                    stealth_func = playwright_stealth.stealth
                else:
                    logger.warning("Aucune fonction stealth trouvée dans le module.")
                    stealth_func = None
            except ImportError:
                logger.warning("playwright-stealth n'est pas installé.")
                stealth_func = None
        except ImportError:
            logger.error("Playwright n'est pas installé. Scraping Twitter désactivé.")
            return []

        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
            except Exception as e:
                logger.error(f"Impossible de lancer le navigateur (Chromium manquant ?) : {e}")
                return []
            context = await browser.new_context(
                user_agent=random.choice(self.user_agents),
                viewport={'width': 1280, 'height': 800}
            )
            page = await context.new_page()
            
            # Application du mode stealth (async ou sync selon la version)
            if stealth_func:
                try:
                    if asyncio.iscoroutinefunction(stealth_func):
                        await stealth_func(page)
                    else:
                        stealth_func(page)
                except Exception as e:
                    logger.warning(f"Erreur lors de l'application du mode stealth : {e}")

            url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{target_user}"
            logger.info(f"Scraping tweets pour @{target_user} via {url}")

            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
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
                await context.close()
                await browser.close()
        
        return results

    async def scrape_hashtag(self, hashtag: str, limit: int = 5):
        """Note: Le scraping de hashtag est plus complexe sans auth. 
        Pour la V1, on se focalise sur les profils sources d'autorité."""
        return []
