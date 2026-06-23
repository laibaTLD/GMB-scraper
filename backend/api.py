from io import BytesIO
import os
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from scraper import scraper_instance
from excel_handler import generate_excel_bytes
from config import API_PORT, API_HOST

app = Flask(__name__)
CORS(app)

STATIC_DIR = os.environ.get('STATIC_DIR')
SERVE_FRONTEND = STATIC_DIR and os.path.isdir(STATIC_DIR)


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "running", "message": "Lead Engine API is active"}), 200


if not SERVE_FRONTEND:
    @app.route('/', methods=['GET'])
    def root_health_check():
        return health_check()

@app.route('/reset-scraper', methods=['POST'])
def reset_scraper():
    scraper_instance.stop_scraping()
    scraper_instance.is_scraping = False
    scraper_instance.status_message = "Idle"
    scraper_instance.results = []
    scraper_instance.scraped_count = 0
    scraper_instance.target_count = 0
    return jsonify({"message": "Scraper reset successfully"}), 200

@app.route('/start-scraping', methods=['POST'])
def start_scraping():
    data = request.get_json(silent=True) or {}
    query = data.get('query')
    location = data.get('location')
    limit = data.get('limit', 50)
    scraping_mode = data.get('scraping_mode', 'detailed')
    if scraping_mode not in ('simple', 'detailed'):
        scraping_mode = 'detailed'
    
    if not query:
        return jsonify({"error": "Missing business query"}), 400
        
    try:
        limit = int(limit)
        if limit < 1: limit = 1
        if limit > 150: limit = 150
    except ValueError:
        limit = 50
        
    success, message = scraper_instance.start_scraping(query, location, limit, scraping_mode)
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
    if not scraper_instance.results:
        return jsonify({"error": "No data available to download"}), 404

    excel_bytes, filename = generate_excel_bytes(scraper_instance.results)
    if not excel_bytes:
        return jsonify({"error": "Failed to generate file"}), 500

    return send_file(
        BytesIO(excel_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


if SERVE_FRONTEND:
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        file_path = os.path.join(STATIC_DIR, path)
        if path and os.path.isfile(file_path):
            return send_from_directory(STATIC_DIR, path)
        return send_from_directory(STATIC_DIR, 'index.html')

if __name__ == '__main__':
    print(f"Starting Lead Engine API on port {API_PORT}...")
    app.run(host=API_HOST, port=API_PORT)
