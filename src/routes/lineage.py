from flask import Blueprint, request, jsonify
from src.models.database import db, DataLineage, DataEntry
from datetime import datetime
import json
import uuid

lineage_bp = Blueprint('lineage', __name__)

@lineage_bp.route('/', methods=['GET'])
def get_lineage_records():
    """Get data lineage records with optional filtering"""
    try:
        data_entry_id = request.args.get('data_entry_id')
        validation_status = request.args.get('validation_status')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = DataLineage.query
        
        if data_entry_id:
            query = query.filter(DataLineage.data_entry_id == data_entry_id)
        if validation_status:
            query = query.filter(DataLineage.validation_status == validation_status)
        
        lineage_records = query.offset(offset).limit(limit).all()
        total = query.count()
        
        return jsonify({
            'lineage_records': [record.to_dict() for record in lineage_records],
            'total': total,
            'limit': limit,
            'offset': offset
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@lineage_bp.route('/', methods=['POST'])
def create_lineage_record():
    """Create a new data lineage record"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['data_entry_id', 'source_chain']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify data entry exists
        entry = DataEntry.query.get(data['data_entry_id'])
        if not entry:
            return jsonify({'error': 'Data entry not found'}), 404
        
        # Create new lineage record
        lineage = DataLineage(
            id=str(uuid.uuid4()),
            data_entry_id=data['data_entry_id'],
            source_chain=json.dumps(data['source_chain']),
            quality_metrics=json.dumps(data.get('quality_metrics', {})),
            validation_status=data.get('validation_status', 'pending')
        )
        
        db.session.add(lineage)
        db.session.commit()
        
        return jsonify(lineage.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@lineage_bp.route('/<lineage_id>', methods=['GET'])
def get_lineage_record(lineage_id):
    """Get a specific lineage record"""
    try:
        lineage = DataLineage.query.get_or_404(lineage_id)
        return jsonify(lineage.to_dict())
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@lineage_bp.route('/<lineage_id>/validate', methods=['POST'])
def validate_lineage(lineage_id):
    """Validate a lineage record"""
    try:
        lineage = DataLineage.query.get_or_404(lineage_id)
        data = request.get_json()
        
        validation_status = data.get('validation_status', 'validated')
        quality_metrics = data.get('quality_metrics', {})
        
        lineage.validation_status = validation_status
        lineage.last_verified = datetime.utcnow()
        
        if quality_metrics:
            existing_metrics = json.loads(lineage.quality_metrics) if lineage.quality_metrics else {}
            existing_metrics.update(quality_metrics)
            lineage.quality_metrics = json.dumps(existing_metrics)
        
        db.session.commit()
        return jsonify(lineage.to_dict())
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@lineage_bp.route('/trace/<data_entry_id>', methods=['GET'])
def trace_data_lineage(data_entry_id):
    """Trace the complete lineage of a data entry"""
    try:
        # Get the data entry
        entry = DataEntry.query.get_or_404(data_entry_id)
        
        # Get all lineage records for this entry
        lineage_records = DataLineage.query.filter(
            DataLineage.data_entry_id == data_entry_id
        ).all()
        
        # Build the complete trace
        trace = {
            'data_entry': entry.to_dict(),
            'lineage_records': [record.to_dict() for record in lineage_records],
            'source_info': entry.source.to_dict() if entry.source else None,
            'total_lineage_records': len(lineage_records)
        }
        
        return jsonify(trace)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@lineage_bp.route('/quality-report', methods=['GET'])
def get_quality_report():
    """Get a quality report across all lineage records"""
    try:
        # Get all lineage records with quality metrics
        lineage_records = DataLineage.query.filter(
            DataLineage.quality_metrics.isnot(None)
        ).all()
        
        if not lineage_records:
            return jsonify({
                'message': 'No quality metrics available',
                'total_records': 0
            })
        
        # Calculate aggregate quality metrics
        total_records = len(lineage_records)
        quality_sums = {
            'completeness': 0,
            'accuracy': 0,
            'timeliness': 0,
            'consistency': 0
        }
        quality_counts = {
            'completeness': 0,
            'accuracy': 0,
            'timeliness': 0,
            'consistency': 0
        }
        
        validation_counts = {
            'validated': 0,
            'pending': 0,
            'failed': 0
        }
        
        for record in lineage_records:
            # Count validation statuses
            validation_counts[record.validation_status] = validation_counts.get(record.validation_status, 0) + 1
            
            # Process quality metrics
            if record.quality_metrics:
                metrics = json.loads(record.quality_metrics)
                for metric in quality_sums.keys():
                    if metric in metrics and metrics[metric] is not None:
                        quality_sums[metric] += metrics[metric]
                        quality_counts[metric] += 1
        
        # Calculate averages
        quality_averages = {}
        for metric in quality_sums.keys():
            if quality_counts[metric] > 0:
                quality_averages[metric] = quality_sums[metric] / quality_counts[metric]
            else:
                quality_averages[metric] = None
        
        report = {
            'total_records': total_records,
            'validation_status_distribution': validation_counts,
            'average_quality_metrics': quality_averages,
            'quality_metric_coverage': {
                metric: f"{count}/{total_records}" for metric, count in quality_counts.items()
            }
        }
        
        return jsonify(report)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@lineage_bp.route('/stats', methods=['GET'])
def get_lineage_stats():
    """Get statistics about data lineage"""
    try:
        total_lineage = DataLineage.query.count()
        validated_lineage = DataLineage.query.filter(DataLineage.validation_status == 'validated').count()
        pending_lineage = DataLineage.query.filter(DataLineage.validation_status == 'pending').count()
        failed_lineage = DataLineage.query.filter(DataLineage.validation_status == 'failed').count()
        
        # Get entries with and without lineage
        total_entries = DataEntry.query.count()
        entries_with_lineage = db.session.query(DataLineage.data_entry_id).distinct().count()
        
        stats = {
            'total_lineage_records': total_lineage,
            'validated_records': validated_lineage,
            'pending_records': pending_lineage,
            'failed_records': failed_lineage,
            'total_data_entries': total_entries,
            'entries_with_lineage': entries_with_lineage,
            'entries_without_lineage': total_entries - entries_with_lineage,
            'lineage_coverage_percentage': round((entries_with_lineage / total_entries * 100), 2) if total_entries > 0 else 0
        }
        
        return jsonify(stats)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

