# Google Maps Data Scraper Extension

A powerful browser extension and Python backend to scrape business data from Google Maps.

## Project Structure

```
google-maps-scraper/
├── backend/            # Python Flask API & Selenium Scraper
├── extension/          # Chrome Extension (Manifest V3)
└── requirements.txt    # Python dependencies
```

## Setup Instructions

### 1. Backend Setup

1.  **Install Python**: Ensure Python 3.8+ is installed.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the Backend**:
    ```bash
    cd backend
    python api.py
    ```
    The server will start at `http://localhost:5000`.

### 2. Extension Setup

1.  Open Chrome and navigate to `chrome://extensions/`.
2.  Enable **Developer mode** (top right).
3.  Click **Load unpacked**.
4.  Select the `extension` directory from this project.
5.  The "Google Maps Data Scraper" icon should appear in your toolbar.

## Usage

1.  Ensure the Python backend is running.
2.  Click the extension icon.
3.  Enter a **Search Query** (e.g., "Pizza") and **Location** (e.g., "Chicago, IL").
4.  Click **Start Scraping**.
5.  Wait for the process to complete. The backend will open a Chrome window; **do not close it**.
6.  Once finished, click **Download Excel** to save the data.

## Features

-   **Automated Scraping**: Scrolls and paginates through results.
-   **Data Extraction**: Name, Phone, Email (regex), Website, Address, Rating, Reviews, Category, Hours.
-   **Excel Export**: Auto-formatted .xlsx files with summary.
-   **Anti-Detection**: Random delays, user-agent rotation.

## Legal Disclaimer

**EDUCATIONAL PURPOSE ONLY.**
This tool is intended for educational purposes to demonstrate web scraping and browser automation techniques. 

-   **Terms of Service**: You must comply with Google Maps' Terms of Service.
-   **Respectful Usage**: Do not overwhelm servers. The tool implements delays for this reason.
-   **No Commercial Use**: Do not use this tool for commercial data harvesting without authorization.

## Troubleshooting

-   **Backend not connecting**: Ensure `api.py` is running and port 5000 is open.
-   **Chrome crash**: Ensure you have a stable internet connection and latest Chrome version.
-   **0 Results**: The scraper might be detected or the CSS selectors changed. Google frequently updates their DOM.
