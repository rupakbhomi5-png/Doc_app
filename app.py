from flask import Flask, render_template, request, jsonify, redirect
from functools import wraps
import os
from dotenv import load_dotenv
from extract import extract_invoice_data
import logging
from datetime import datetime
import hashlib
import json

load_dotenv()

app = Flask(__name__)
@app.before_request
def redirect_to_https():
    if request.headers.get("X-Forwarded-Proto") == "http":
        return redirect(request.url.replace("http://", "https://", 1), code=308)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

logging.basicConfig(
    filename='invoice_extractor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

request_counts = {}
def rate_limit(max_requests=10, window=3600):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            client_id = request.remote_addr
            now = datetime.now().timestamp()

            if client_id not in request_counts:
                request_counts[client_id] = []

            request_counts[client_id] = [t for t in request_counts[client_id] if now - t < window]

            if len(request_counts[client_id]) >= max_requests:
                logging.warning(f"Rate limit exceeded: {client_id}")
                return jsonify({'error': 'Rate limit exceeded'}), 429

            request_counts[client_id].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

def require_api_key(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        valid_key = os.environ.get('API_KEY', 'demo-key-123')

        if not api_key or api_key != valid_key:
            logging.warning(f"Invalid API key attempt: {request.remote_addr}")
            return jsonify({'error': 'Invalid API key'}), 401

        return f(*args, **kwargs)
    return wrapped
    
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Invoice Extractor</title>
        <style>
            body { font-family: Arial; max-width: 600px; margin: 50px auto; }
            .container { border: 1px solid #ccc; padding: 20px; border-radius: 8px; }
            input, button { padding: 10px; margin: 10px 0; width: 100%; box-sizing: border-box; }
            button { background: #007bff; color: white; cursor: pointer; border: none; border-radius: 4px; }
            button:hover { background: #0056b3; }
            #result { margin-top: 20px; white-space: pre-wrap; background: #f5f5f5; padding: 10px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Invoice Extractor</h1>
            <p>Upload a PDF invoice or receipt to extract structured data.</p>
            <input type="file" id="pdfFile" accept=".pdf" />
            <button onclick="uploadFile()">Extract Data</button>
            <div id="result"></div>
        </div>
        <script>
            function uploadFile() {
                const file = document.getElementById('pdfFile').files[0];
                if (!file) {
                    alert('Please select a PDF file');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', file);
                
                document.getElementById('result').textContent = 'Processing...';
                
                fetch('/extract', {
                    method: 'POST',
                    headers: { 'X-API-Key': 'demo-key-123' },
                    body: formData
                })
                .then(res => res.json())
                .then(data => {
                    document.getElementById('result').textContent = JSON.stringify(data, null, 2);
                })
                .catch(err => {
                    document.getElementById('result').textContent = 'Error: ' + err;
                });
            }
        </script>
    </body>
    </html>
    '''

@app.route('/extract', methods=['POST'])
@rate_limit(max_requests=10, window=3600)
@require_api_key
def extract():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Only PDF files allowed'}), 400

    if file.content_length and file.content_length > 5 * 1024 * 1024:
        return jsonify({'error': 'File too large'}), 413

    temp_path = f'temp_{hashlib.md5(file.filename.encode()).hexdigest()}.pdf'
    file.save(temp_path)

    try:
        logging.info(f"Extracting: {file.filename} from {request.remote_addr}")
        result = extract_invoice_data(temp_path)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Extraction failed: {type(e).__name__}")
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == '__main__':
    app.run(debug=False, port=5000)