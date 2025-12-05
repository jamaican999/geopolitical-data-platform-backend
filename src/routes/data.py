from flask import Blueprint, request, jsonify
from src.models.database import db, DataEntry, CountryProfile, Source
from datetime import datetime
import hashlib
import uuid
import json

data_bp = Blueprint('data', __name__)

@data_bp.route('/entries', methods=['GET'])
def get_data_entries():
    """Get data entries with optional filtering"""
    try:
        # Get query parameters
        source_id = request.args.get('source_id')
        content_type = request.args.get('content_type')
        processed = request.args.get('processed', type=bool)
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Build query
        query = DataEntry.query
        
        if source_id:
            query = query.filter(DataEntry.source_id == source_id)
        if content_type:
            query = query.filter(DataEntry.content_type == content_type)
        if processed is not None:
            query = query.filter(DataEntry.processed == processed)
        
        # Apply pagination
        entries = query.offset(offset).limit(limit).all()
        total = query.count()
        
        return jsonify({
            'entries': [entry.to_dict() for entry in entries],
            'total': total,
            'limit': limit,
            'offset': offset
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@data_bp.route('/entries', methods=['POST'])
def create_data_entry():
    """Create a new data entry"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['source_id', 'title', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify source exists
        source = Source.query.get(data['source_id'])
        if not source:
            return jsonify({'error': 'Source not found'}), 404
        
        # Generate hash of raw content
        content_hash = hashlib.sha256(data['content'].encode()).hexdigest()
        
        # Create new data entry
        entry = DataEntry(
            id=str(uuid.uuid4()),
            source_id=data['source_id'],
            title=data['title'],
            content=data['content'],
            content_type=data.get('content_type', 'article'),
            url=data.get('url'),
            published_date=datetime.fromisoformat(data['published_date']) if data.get('published_date') else None,
            raw_data_hash=content_hash
        )
        
        db.session.add(entry)
        db.session.commit()
        
        return jsonify(entry.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@data_bp.route('/entries/<entry_id>', methods=['GET'])
def get_data_entry(entry_id):
    """Get a specific data entry"""
    try:
        entry = DataEntry.query.get_or_404(entry_id)
        return jsonify(entry.to_dict())
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@data_bp.route('/entries/<entry_id>/process', methods=['POST'])
def mark_entry_processed(entry_id):
    """Mark a data entry as processed"""
    try:
        entry = DataEntry.query.get_or_404(entry_id)
        entry.processed = True
        db.session.commit()
        return jsonify(entry.to_dict())
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@data_bp.route('/countries', methods=['GET'])
def get_countries():
    """Get country profiles with optional filtering"""
    try:
        region = request.args.get('region')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = CountryProfile.query
        
        if region:
            query = query.filter(CountryProfile.region == region)
        
        countries = query.offset(offset).limit(limit).all()
        total = query.count()
        
        return jsonify({
            'countries': [country.to_dict() for country in countries],
            'total': total,
            'limit': limit,
            'offset': offset
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@data_bp.route('/countries', methods=['POST'])
def create_country_profile():
    """Create or update a country profile"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['id', 'name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if country already exists
        country = CountryProfile.query.get(data['id'])
        if country:
            # Update existing country
            for field in ['name', 'official_name', 'region', 'subregion', 'capital',
                         'population', 'area', 'gdp', 'currency', 'government_type',
                         'head_of_state', 'head_of_government', 'data_source_id']:
                if field in data:
                    setattr(country, field, data[field])
            
            if 'languages' in data:
                country.languages = json.dumps(data['languages'])
            if 'independence_date' in data:
                country.independence_date = datetime.fromisoformat(data['independence_date']).date()
            
            country.last_updated = datetime.utcnow()
        else:
            # Create new country
            country = CountryProfile(
                id=data['id'],
                name=data['name'],
                official_name=data.get('official_name'),
                region=data.get('region'),
                subregion=data.get('subregion'),
                capital=data.get('capital'),
                population=data.get('population'),
                area=data.get('area'),
                gdp=data.get('gdp'),
                currency=data.get('currency'),
                languages=json.dumps(data.get('languages', [])),
                government_type=data.get('government_type'),
                head_of_state=data.get('head_of_state'),
                head_of_government=data.get('head_of_government'),
                independence_date=datetime.fromisoformat(data['independence_date']).date() if data.get('independence_date') else None,
                data_source_id=data.get('data_source_id')
            )
            db.session.add(country)
        
        db.session.commit()
        return jsonify(country.to_dict()), 201 if not country else 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@data_bp.route('/countries/<country_id>', methods=['GET'])
def get_country_profile(country_id):
    """Get a specific country profile"""
    try:
        country = CountryProfile.query.get_or_404(country_id)
        return jsonify(country.to_dict())
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@data_bp.route('/search', methods=['GET'])
def search_data():
    """Search across data entries and country profiles"""
    try:
        query_text = request.args.get('q', '')
        content_type = request.args.get('type')  # 'entries' or 'countries'
        limit = request.args.get('limit', 20, type=int)
        
        results = []
        
        if not content_type or content_type == 'entries':
            # Search data entries
            entries = DataEntry.query.filter(
                db.or_(
                    DataEntry.title.contains(query_text),
                    DataEntry.content.contains(query_text)
                )
            ).limit(limit).all()
            
            results.extend([{
                'type': 'entry',
                'data': entry.to_dict()
            } for entry in entries])
        
        if not content_type or content_type == 'countries':
            # Search country profiles
            countries = CountryProfile.query.filter(
                db.or_(
                    CountryProfile.name.contains(query_text),
                    CountryProfile.official_name.contains(query_text),
                    CountryProfile.capital.contains(query_text)
                )
            ).limit(limit).all()
            
            results.extend([{
                'type': 'country',
                'data': country.to_dict()
            } for country in countries])
        
        return jsonify({
            'results': results[:limit],
            'query': query_text,
            'total_results': len(results)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

