import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from api import app
from config import API_PORT, API_HOST

if __name__ == '__main__':
    print(f"Starting GMB Scraper API on port {API_PORT}...")
    app.run(host=API_HOST, port=API_PORT)
