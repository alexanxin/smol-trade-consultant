print("Importing feedparser...", flush=True)
import feedparser
print("Imported feedparser.", flush=True)

print("Importing NewsAgent...", flush=True)
from news_agent import NewsAgent
print("Imported NewsAgent.", flush=True)

print("Initializing NewsAgent...", flush=True)
agent = NewsAgent()
print("Initialized NewsAgent.", flush=True)
