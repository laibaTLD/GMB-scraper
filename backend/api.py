from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from scraper import scraper_instance
import os

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "running", "message": "GMB Scraper API is active"}), 200

@app.route('/reset-scraper', methods=['POST'])
def reset_scraper():
    scraper_instance.stop_scraping()
    scraper_instance.is_scraping = False
    scraper_instance.status_message = "Idle"
    scraper_instance.results = []
    scraper_instance.scraped_count = 0
    scraper_instance.target_count = 0
    scraper_instance.output_file = None
    return jsonify({"message": "Scraper reset successfully"}), 200

@app.route('/start-scraping', methods=['POST'])
def start_scraping():
    data = request.json
    query = data.get('query')
    location = data.get('location')
    limit = data.get('limit', 1000)
    
    if not query or not location:
        return jsonify({"error": "Missing query or location"}), 400
        
    try:
        limit = int(limit)
        if limit < 20: limit = 20
        if limit > 1000: limit = 1000
    except ValueError:
        limit = 1000
        
    success, message = scraper_instance.start_scraping(query, location, limit)
    if success:
        return jsonify({"message": message}), 200
    else:
        return jsonify({"error": message}), 409

@app.route('/stop-scraping', methods=['POST'])
def stop_scraping():
    scraper_instance.stop_scraping()
    return jsonify({"message": "Scraping stopped"}), 200

@app.route('/progress', methods=['GET'])
def get_progress():
    return jsonify(scraper_instance.get_progress())

@app.route('/results', methods=['GET'])
def get_results():
    limit = request.args.get('limit', default=50, type=int)
    # Return reversed list to show newest first
    results = scraper_instance.results[::-1][:limit]
    return jsonify(results)

@app.route('/download', methods=['GET'])
def download_file():
    filepath = scraper_instance.get_download_path()
    if filepath and os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return jsonify({"error": "File not ready"}), 404

if __name__ == '__main__':
    print("Starting GMB Scraper API on port 5001...")
    app.run(host='0.0.0.0', port=5001)
