from flask import Blueprint, request, jsonify
from src.models.database import db, Tag, DataEntry
from datetime import datetime
import uuid

tags_bp = Blueprint('tags', __name__)

@tags_bp.route('/', methods=['GET'])
def get_tags():
    """Get tags with optional filtering"""
    try:
        data_entry_id = request.args.get('data_entry_id')
        tag_type = request.args.get('tag_type')
        tag_category = request.args.get('tag_category')
        is_manual = request.args.get('is_manual', type=bool)
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = Tag.query
        
        if data_entry_id:
            query = query.filter(Tag.data_entry_id == data_entry_id)
        if tag_type:
            query = query.filter(Tag.tag_type == tag_type)
        if tag_category:
            query = query.filter(Tag.tag_category == tag_category)
        if is_manual is not None:
            query = query.filter(Tag.is_manual == is_manual)
        
        tags = query.offset(offset).limit(limit).all()
        total = query.count()
        
        return jsonify({
            'tags': [tag.to_dict() for tag in tags],
            'total': total,
            'limit': limit,
            'offset': offset
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tags_bp.route('/', methods=['POST'])
def create_tag():
    """Create a new tag"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['data_entry_id', 'tag_type', 'tag_value']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify data entry exists
        entry = DataEntry.query.get(data['data_entry_id'])
        if not entry:
            return jsonify({'error': 'Data entry not found'}), 404
        
        # Create new tag
        tag = Tag(
            data_entry_id=data['data_entry_id'],
            tag_type=data['tag_type'],
            tag_category=data.get('tag_category'),
            tag_value=data['tag_value'],
            confidence_score=data.get('confidence_score', 1.0),
            is_manual=data.get('is_manual', False),
            created_by=data.get('created_by', 'system')
        )
        
        db.session.add(tag)
        db.session.commit()
        
        return jsonify(tag.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tags_bp.route('/bulk', methods=['POST'])
def create_bulk_tags():
    """Create multiple tags at once"""
    try:
        data = request.get_json()
        tags_data = data.get('tags', [])
        
        if not tags_data:
            return jsonify({'error': 'No tags provided'}), 400
        
        created_tags = []
        
        for tag_data in tags_data:
            # Validate required fields
            required_fields = ['data_entry_id', 'tag_type', 'tag_value']
            for field in required_fields:
                if field not in tag_data:
                    return jsonify({'error': f'Missing required field: {field} in tag'}), 400
            
            # Create tag
            tag = Tag(
                data_entry_id=tag_data['data_entry_id'],
                tag_type=tag_data['tag_type'],
                tag_category=tag_data.get('tag_category'),
                tag_value=tag_data['tag_value'],
                confidence_score=tag_data.get('confidence_score', 1.0),
                is_manual=tag_data.get('is_manual', False),
                created_by=tag_data.get('created_by', 'system')
            )
            
            db.session.add(tag)
            created_tags.append(tag)
        
        db.session.commit()
        
        return jsonify({
            'created_tags': [tag.to_dict() for tag in created_tags],
            'count': len(created_tags)
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tags_bp.route('/<int:tag_id>', methods=['GET'])
def get_tag(tag_id):
    """Get a specific tag"""
    try:
        tag = Tag.query.get_or_404(tag_id)
        return jsonify(tag.to_dict())
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tags_bp.route('/<int:tag_id>', methods=['PUT'])
def update_tag(tag_id):
    """Update a tag"""
    try:
        tag = Tag.query.get_or_404(tag_id)
        data = request.get_json()
        
        # Update fields
        for field in ['tag_type', 'tag_category', 'tag_value', 'confidence_score', 'is_manual']:
            if field in data:
                setattr(tag, field, data[field])
        
        db.session.commit()
        return jsonify(tag.to_dict())
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tags_bp.route('/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    """Delete a tag"""
    try:
        tag = Tag.query.get_or_404(tag_id)
        db.session.delete(tag)
        db.session.commit()
        return jsonify({'message': 'Tag deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@tags_bp.route('/types', methods=['GET'])
def get_tag_types():
    """Get available tag types and categories"""
    tag_schema = {
        'geographic': ['countries', 'regions', 'cities'],
        'temporal': ['date', 'year', 'decade', 'era'],
        'topic': ['economy', 'politics', 'security', 'trade', 'environment', 'social'],
        'event': ['election', 'conflict', 'treaty', 'scandal', 'crisis', 'summit'],
        'entity': ['people', 'organizations', 'companies', 'government_agencies']
    }
    return jsonify(tag_schema)

@tags_bp.route('/search', methods=['GET'])
def search_tags():
    """Search tags by value"""
    try:
        query_text = request.args.get('q', '')
        tag_type = request.args.get('tag_type')
        limit = request.args.get('limit', 50, type=int)
        
        query = Tag.query.filter(Tag.tag_value.contains(query_text))
        
        if tag_type:
            query = query.filter(Tag.tag_type == tag_type)
        
        tags = query.limit(limit).all()
        
        return jsonify({
            'tags': [tag.to_dict() for tag in tags],
            'query': query_text,
            'total_results': len(tags)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@tags_bp.route('/stats', methods=['GET'])
def get_tag_stats():
    """Get statistics about tags"""
    try:
        total_tags = Tag.query.count()
        manual_tags = Tag.query.filter(Tag.is_manual == True).count()
        
        # Count by tag type
        type_counts = db.session.query(
            Tag.tag_type,
            db.func.count(Tag.id)
        ).group_by(Tag.tag_type).all()
        
        # Most common tag values
        popular_tags = db.session.query(
            Tag.tag_value,
            db.func.count(Tag.id).label('count')
        ).group_by(Tag.tag_value).order_by(db.func.count(Tag.id).desc()).limit(20).all()
        
        stats = {
            'total_tags': total_tags,
            'manual_tags': manual_tags,
            'automatic_tags': total_tags - manual_tags,
            'tags_by_type': {tag_type: count for tag_type, count in type_counts},
            'popular_tags': [{'value': value, 'count': count} for value, count in popular_tags]
        }
        
        return jsonify(stats)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

