from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from routes import auth_bp, game_bp, lb_bp

app = Flask(__name__)
app.config.from_object(Config)


CORS(app, resources={r'/api/*': {'origins': '*'}})

app.register_blueprint(auth_bp)
app.register_blueprint(game_bp)
app.register_blueprint(lb_bp)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get('/api/health')
def health():
    return jsonify({'status': 'ok', 'game': 'Latipov Game – Math Tug of War'})


# ── Global error handlers ─────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(_):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error', 'detail': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)
