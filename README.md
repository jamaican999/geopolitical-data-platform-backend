# Internet Trawler Data Platform - Backend

This is the backend component of the Internet Trawler Data Platform, built with Flask and SQLAlchemy.

## Features

- **Data Source Management**: Register and manage various data sources with metadata
- **Data Collection**: Automated collectors for CIA Factbook and other sources
- **Tagging System**: Comprehensive tagging for geographic, temporal, topical, and entity classification
- **Data Lineage**: Complete audit trail and provenance tracking
- **RESTful API**: Full CRUD operations for all data types
- **Quality Metrics**: Data quality scoring and validation

## API Endpoints

### Sources (`/api/sources`)
- `GET /` - List all sources with filtering
- `POST /` - Create new source
- `GET /<id>` - Get specific source
- `PUT /<id>` - Update source
- `DELETE /<id>` - Delete source
- `GET /types` - Get available source types
- `GET /stats` - Get source statistics

### Data (`/api/data`)
- `GET /entries` - List data entries with pagination
- `POST /entries` - Create new data entry
- `GET /entries/<id>` - Get specific entry
- `POST /entries/<id>/process` - Mark entry as processed
- `GET /countries` - List country profiles
- `POST /countries` - Create/update country profile
- `GET /countries/<id>` - Get specific country
- `GET /search` - Search across all data

### Tags (`/api/tags`)
- `GET /` - List tags with filtering
- `POST /` - Create new tag
- `POST /bulk` - Create multiple tags
- `GET /<id>` - Get specific tag
- `PUT /<id>` - Update tag
- `DELETE /<id>` - Delete tag
- `GET /types` - Get tag schema
- `GET /search` - Search tags
- `GET /stats` - Get tag statistics

### Lineage (`/api/lineage`)
- `GET /` - List lineage records
- `POST /` - Create lineage record
- `GET /<id>` - Get specific record
- `POST /<id>/validate` - Validate lineage
- `GET /trace/<data_entry_id>` - Trace complete lineage
- `GET /quality-report` - Get quality report
- `GET /stats` - Get lineage statistics

## Data Models

### Source
Represents a data source with metadata including reliability score, bias rating, and verification status.

### DataEntry
Individual pieces of collected data with content, metadata, and processing status.

### Tag
Classification tags for data entries supporting multiple tag types and categories.

### DataLineage
Audit trail for data provenance and quality metrics.

### CountryProfile
Structured country information extracted from various sources.

## Data Collection

The platform includes automated collectors starting with the CIA Factbook:

### CIA Factbook Collector
- Fetches country profiles from factbook.json GitHub repository
- Processes and stores structured country data
- Creates comprehensive lineage records
- Supports incremental updates

## Installation

1. Navigate to the project directory:
```bash
cd geopolitical-data-platform
```

2. Activate the virtual environment:
```bash
source venv/bin/activate
```

3. Install additional dependencies:
```bash
pip install flask-cors requests
pip freeze > requirements.txt
```

4. Run the application:
```bash
python src/main.py
```

The API will be available at `http://localhost:5000`

## Database

The application uses SQLite by default for development. The database file is located at `src/database/app.db` and is automatically created when the application starts.

## CORS

Cross-Origin Resource Sharing (CORS) is enabled for all routes to support frontend integration.

## Development

- All models are defined in `src/models/database.py`
- API routes are organized in separate blueprint files in `src/routes/`
- Data collectors are in `src/collectors/`
- The main application entry point is `src/main.py`

