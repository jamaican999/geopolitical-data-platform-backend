from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Source(db.Model):
    __tablename__ = 'sources'
    
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # government, media, international_org, academic, commercial
    url = db.Column(db.String(500))
    reliability_score = db.Column(db.Float, default=5.0)  # 1-10 scale
    bias_rating = db.Column(db.String(20))  # left, center-left, center, center-right, right, unknown
    update_frequency = db.Column(db.String(20))  # real-time, daily, weekly, monthly, irregular
    language = db.Column(db.String(10), default='en')
    country_focus = db.Column(db.Text)  # JSON array of country codes
    topic_coverage = db.Column(db.Text)  # JSON array of topics
    api_available = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    verification_status = db.Column(db.String(20), default='pending')  # verified, pending, flagged
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'url': self.url,
            'reliability_score': self.reliability_score,
            'bias_rating': self.bias_rating,
            'update_frequency': self.update_frequency,
            'language': self.language,
            'country_focus': json.loads(self.country_focus) if self.country_focus else [],
            'topic_coverage': json.loads(self.topic_coverage) if self.topic_coverage else [],
            'api_available': self.api_available,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'verification_status': self.verification_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class DataEntry(db.Model):
    __tablename__ = 'data_entries'
    
    id = db.Column(db.String(50), primary_key=True)
    source_id = db.Column(db.String(50), db.ForeignKey('sources.id'), nullable=False)
    title = db.Column(db.String(500))
    content = db.Column(db.Text)
    content_type = db.Column(db.String(50))  # article, profile, report, statistic
    url = db.Column(db.String(500))
    published_date = db.Column(db.DateTime)
    collected_date = db.Column(db.DateTime, default=datetime.utcnow)
    raw_data_hash = db.Column(db.String(64))
    processed = db.Column(db.Boolean, default=False)
    
    # Relationships
    source = db.relationship('Source', backref='data_entries')
    
    def to_dict(self):
        return {
            'id': self.id,
            'source_id': self.source_id,
            'title': self.title,
            'content': self.content,
            'content_type': self.content_type,
            'url': self.url,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'collected_date': self.collected_date.isoformat() if self.collected_date else None,
            'raw_data_hash': self.raw_data_hash,
            'processed': self.processed
        }

class Tag(db.Model):
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    data_entry_id = db.Column(db.String(50), db.ForeignKey('data_entries.id'), nullable=False)
    tag_type = db.Column(db.String(50), nullable=False)  # geographic, temporal, topic, event, entity
    tag_category = db.Column(db.String(50))  # countries, regions, people, organizations, etc.
    tag_value = db.Column(db.String(200), nullable=False)
    confidence_score = db.Column(db.Float, default=1.0)
    is_manual = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(50))  # user_id or 'system'
    
    # Relationships
    data_entry = db.relationship('DataEntry', backref='tags')
    
    def to_dict(self):
        return {
            'id': self.id,
            'data_entry_id': self.data_entry_id,
            'tag_type': self.tag_type,
            'tag_category': self.tag_category,
            'tag_value': self.tag_value,
            'confidence_score': self.confidence_score,
            'is_manual': self.is_manual,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }

class DataLineage(db.Model):
    __tablename__ = 'data_lineage'
    
    id = db.Column(db.String(50), primary_key=True)
    data_entry_id = db.Column(db.String(50), db.ForeignKey('data_entries.id'), nullable=False)
    source_chain = db.Column(db.Text)  # JSON array of source chain
    quality_metrics = db.Column(db.Text)  # JSON object with quality scores
    validation_status = db.Column(db.String(20), default='pending')  # validated, pending, failed
    last_verified = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    data_entry = db.relationship('DataEntry', backref='lineage')
    
    def to_dict(self):
        return {
            'id': self.id,
            'data_entry_id': self.data_entry_id,
            'source_chain': json.loads(self.source_chain) if self.source_chain else [],
            'quality_metrics': json.loads(self.quality_metrics) if self.quality_metrics else {},
            'validation_status': self.validation_status,
            'last_verified': self.last_verified.isoformat() if self.last_verified else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class CountryProfile(db.Model):
    __tablename__ = 'country_profiles'
    
    id = db.Column(db.String(10), primary_key=True)  # country code
    name = db.Column(db.String(100), nullable=False)
    official_name = db.Column(db.String(200))
    region = db.Column(db.String(50))
    subregion = db.Column(db.String(50))
    capital = db.Column(db.String(100))
    population = db.Column(db.BigInteger)
    area = db.Column(db.Float)  # in sq km
    gdp = db.Column(db.Float)  # in USD
    currency = db.Column(db.String(10))
    languages = db.Column(db.Text)  # JSON array
    government_type = db.Column(db.String(100))
    head_of_state = db.Column(db.String(100))
    head_of_government = db.Column(db.String(100))
    independence_date = db.Column(db.Date)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    data_source_id = db.Column(db.String(50), db.ForeignKey('sources.id'))
    
    # Relationships
    data_source = db.relationship('Source')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'official_name': self.official_name,
            'region': self.region,
            'subregion': self.subregion,
            'capital': self.capital,
            'population': self.population,
            'area': self.area,
            'gdp': self.gdp,
            'currency': self.currency,
            'languages': json.loads(self.languages) if self.languages else [],
            'government_type': self.government_type,
            'head_of_state': self.head_of_state,
            'head_of_government': self.head_of_government,
            'independence_date': self.independence_date.isoformat() if self.independence_date else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'data_source_id': self.data_source_id
        }

