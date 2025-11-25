import feedparser
import urllib.parse
from datetime import datetime
import time

class NewsAgent:
    def __init__(self):
        self.base_url = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    def fetch_news(self, symbol: str, limit: int = 5) -> str:
        """
        Fetches news for a given token symbol using Google News RSS.
        Returns a formatted string summary of the news.
        """
        # Construct query: "Token Symbol" + "Crypto" to be more specific
        query = f"{symbol} crypto"
        encoded_query = urllib.parse.quote(query)
        url = self.base_url.format(query=encoded_query)

        try:
            feed = feedparser.parse(url)
            
            if not feed.entries:
                return f"No recent news found for {symbol}."

            summary_lines = [f"--- Recent News for {symbol} ---"]
            
            # Sort by published date (descending) just in case, though RSS usually is sorted
            sorted_entries = sorted(feed.entries, key=lambda x: x.published_parsed, reverse=True)
            
            for entry in sorted_entries[:limit]:
                title = entry.title
                # Published time
                published = entry.published
                # Source
                source = entry.source.title if hasattr(entry, 'source') else "Unknown Source"
                
                summary_lines.append(f"- [{published}] {source}: {title}")
                
            return "\n".join(summary_lines)

        except Exception as e:
            return f"Error fetching news for {symbol}: {str(e)}"

if __name__ == "__main__":
    # Simple test
    agent = NewsAgent()
    print(agent.fetch_news("SOL"))
