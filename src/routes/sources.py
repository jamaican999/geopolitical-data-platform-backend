from flask import Blueprint, request, jsonify
from src.models.database import db, Source
import json
from datetime import datetime

sources_bp = Blueprint('sources', __name__)

@sources_bp.route('/', methods=['GET'])
def get_sources():
    """Get all data sources with optional filtering"""
    try:
        # Get query parameters
        source_type = request.args.get('type')
        verification_status = request.args.get('verification_status')
        min_reliability = request.args.get('min_reliability', type=float)
        
        # Build query
        query = Source.query
        
        if source_type:
            query = query.filter(Source.type == source_type)
        if verification_status:
            query = query.filter(Source.verification_status == verification_status)
        if min_reliability:
            query = query.filter(Source.reliability_score >= min_reliability)
        
        sources = query.all()
        return jsonify([source.to_dict() for source in sources])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@sources_bp.route('/', methods=['POST'])
def create_source():
    """Create a new data source"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['id', 'name', 'type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if source already exists
        existing_source = Source.query.get(data['id'])
        if existing_source:
            return jsonify({'error': 'Source with this ID already exists'}), 409
        
        # Create new source
        source = Source(
            id=data['id'],
            name=data['name'],
            type=data['type'],
            url=data.get('url'),
            reliability_score=data.get('reliability_score', 5.0),
            bias_rating=data.get('bias_rating'),
            update_frequency=data.get('update_frequency'),
            language=data.get('language', 'en'),
            country_focus=json.dumps(data.get('country_focus', [])),
            topic_coverage=json.dumps(data.get('topic_coverage', [])),
            api_available=data.get('api_available', False),
            verification_status=data.get('verification_status', 'pending')
        )
        
        db.session.add(source)
        db.session.commit()
        
        return jsonify(source.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@sources_bp.route('/<source_id>', methods=['GET'])
def get_source(source_id):
    """Get a specific data source"""
    try:
        source = Source.query.get_or_404(source_id)
        return jsonify(source.to_dict())
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@sources_bp.route('/<source_id>', methods=['PUT'])
def update_source(source_id):
    """Update a data source"""
    try:
        source = Source.query.get_or_404(source_id)
        data = request.get_json()
        
        # Update fields
        for field in ['name', 'type', 'url', 'reliability_score', 'bias_rating', 
                     'update_frequency', 'language', 'api_available', 'verification_status']:
            if field in data:
                setattr(source, field, data[field])
        
        # Handle JSON fields
        if 'country_focus' in data:
            source.country_focus = json.dumps(data['country_focus'])
        if 'topic_coverage' in data:
            source.topic_coverage = json.dumps(data['topic_coverage'])
        
        source.last_updated = datetime.utcnow()
        
        db.session.commit()
        return jsonify(source.to_dict())
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@sources_bp.route('/<source_id>', methods=['DELETE'])
def delete_source(source_id):
    """Delete a data source"""
    try:
        source = Source.query.get_or_404(source_id)
        db.session.delete(source)
        db.session.commit()
        return jsonify({'message': 'Source deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@sources_bp.route('/types', methods=['GET'])
def get_source_types():
    """Get available source types"""
    types = ['government', 'media', 'international_org', 'academic', 'commercial']
    return jsonify(types)

@sources_bp.route('/stats', methods=['GET'])
def get_source_stats():
    """Get statistics about data sources"""
    try:
        total_sources = Source.query.count()
        verified_sources = Source.query.filter(Source.verification_status == 'verified').count()
        avg_reliability = db.session.query(db.func.avg(Source.reliability_score)).scalar()
        
        type_counts = db.session.query(
            Source.type, 
            db.func.count(Source.id)
        ).group_by(Source.type).all()
        
        stats = {
            'total_sources': total_sources,
            'verified_sources': verified_sources,
            'average_reliability': round(avg_reliability, 2) if avg_reliability else 0,
            'sources_by_type': {type_name: count for type_name, count in type_counts}
        }
        
        return jsonify(stats)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

