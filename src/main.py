import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from src.models.database import db
from src.routes.sources import sources_bp
from src.routes.data import data_bp
from src.routes.tags import tags_bp
from src.routes.lineage import lineage_bp
from src.config import config

def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))
    
    # Register blueprints
    app.register_blueprint(sources_bp, url_prefix='/api/sources')
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(tags_bp, url_prefix='/api/tags')
    app.register_blueprint(lineage_bp, url_prefix='/api/lineage')
    
    # Health check endpoint for AWS
    @app.route('/api/health')
    def health_check():
        """Health check endpoint for load balancer"""
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            return jsonify({
                'status': 'healthy',
                'service': 'geopolitical-data-platform',
                'version': '1.0.0'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 503
    
    # Root endpoint
    @app.route('/api/')
    def api_root():
        return jsonify({
            'message': 'Geo-Political Data Platform API',
            'version': '1.0.0',
            'status': 'running'
        })
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
                return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return "index.html not found", 404
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    # Get port from environment variable (for AWS deployment)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=port,
        debug=app.config.get('DEBUG', False)
    )

