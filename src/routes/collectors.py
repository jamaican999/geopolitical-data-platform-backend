"""
Data Collectors API Routes

This module provides API endpoints for managing and running data collectors.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

collectors_bp = Blueprint('collectors', __name__)

@collectors_bp.route('/', methods=['GET'])
def list_collectors():
    """List all available data collectors"""
    collectors = [
        {
            'name': 'cia_factbook',
            'display_name': 'CIA Factbook',
            'description': 'Collects country profile data from CIA Factbook',
            'status': 'active',
            'last_run': None
        }
    ]
    
    return jsonify({
        'collectors': collectors,
        'total': len(collectors)
    })

@collectors_bp.route('/<collector_name>/run', methods=['POST'])
def run_collector(collector_name):
    """Run a specific data collector"""
    try:
        logger.info(f"Starting collector: {collector_name}")
        
        if collector_name == 'cia_factbook':
            # Import here to avoid circular dependencies
            from ..collectors.cia_factbook import collect_cia_factbook_data
            result = collect_cia_factbook_data()
        else:
            return jsonify({
                'error': f'Unknown collector: {collector_name}'
            }), 400
        
        logger.info(f"Collector {collector_name} completed: {result}")
        
        return jsonify({
            'collector': collector_name,
            'status': 'completed',
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error running collector {collector_name}: {e}")
        return jsonify({
            'error': f'Failed to run collector: {str(e)}',
            'collector': collector_name,
            'status': 'failed',
            'timestamp': datetime.now().isoformat()
        }), 500

@collectors_bp.route('/stats', methods=['GET'])
def get_collectors_stats():
    """Get statistics about all collectors"""
    stats = {
        'total_collectors': 1,
        'active_collectors': 1,
        'total_runs_today': 0,
        'successful_runs_today': 0,
        'failed_runs_today': 0,
        'last_successful_run': None
    }
    
    return jsonify(stats)
