# web/app.py
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def hello():
    return "<h1>In-Class Snap API</h1><p>✅ Flask is running!</p>"

@app.route('/api/status')
def status():
    return jsonify({
        "status": "ok",
        "module": "inclass-snap-web",
        "version": "0.1.0"
    })

if __name__ == '__main__':
    # 开发模式：允许外部访问（如手机、局域网）
    app.run(host='0.0.0.0', port=5000, debug=True)
