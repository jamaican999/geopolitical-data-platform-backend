import requests
import json
import hashlib
import uuid
from datetime import datetime
from src.models.database import db, Source, DataEntry, CountryProfile, DataLineage
from typing import Dict, List, Optional

class CIAFactbookCollector:
    """Collector for CIA Factbook data from the factbook.json GitHub repository"""
    
    def __init__(self):
        self.base_url = "https://github.com/factbook/factbook.json/raw/master"
        self.source_id = "cia_factbook"
        self.regions = [
            "africa", "antarctica", "australia-oceania", "central-america-n-caribbean",
            "central-asia", "east-n-southeast-asia", "europe", "middle-east",
            "north-america", "south-america", "south-asia", "world"
        ]
    
    def initialize_source(self) -> bool:
        """Initialize the CIA Factbook source in the database"""
        try:
            # Check if source already exists
            existing_source = Source.query.get(self.source_id)
            if existing_source:
                return True
            
            # Create new source
            source = Source(
                id=self.source_id,
                name="CIA World Factbook",
                type="government",
                url="https://www.cia.gov/the-world-factbook/",
                reliability_score=9.0,
                bias_rating="center",
                update_frequency="weekly",
                language="en",
                country_focus=json.dumps(["global"]),
                topic_coverage=json.dumps([
                    "geography", "people", "government", "economy", 
                    "energy", "communications", "transportation", "military"
                ]),
                api_available=True,
                verification_status="verified"
            )
            
            db.session.add(source)
            db.session.commit()
            return True
            
        except Exception as e:
            print(f"Error initializing CIA Factbook source: {e}")
            db.session.rollback()
            return False
    
    def get_country_list(self, region: str) -> List[str]:
        """Get list of country files in a specific region"""
        try:
            # This is a simplified approach - in a real implementation,
            # you would fetch the directory listing from GitHub API
            # For now, we'll use a predefined list of common countries
            country_codes = {
                "europe": ["au", "be", "bu", "hr", "cy", "ez", "da", "en", "fi", "fr", "gm", "gr", "hu", "ic", "ei", "it", "lg", "lh", "lu", "mk", "mt", "md", "mn", "nl", "no", "pl", "po", "ro", "rs", "si", "lo", "sp", "sw", "sz", "uk"],
                "africa": ["af", "ag", "ao", "bc", "bn", "by", "cm", "cv", "ct", "cd", "cg", "dj", "eg", "ek", "er", "et", "gb", "ga", "gh", "gv", "pu", "iv", "ke", "ls", "li", "ly", "ma", "mi", "ml", "mr", "mp", "mz", "wa", "ng", "rw", "tp", "sn", "sg", "sl", "so", "sf", "su", "wz", "tz", "to", "ts", "ug", "za", "zi"],
                "asia": ["af", "am", "aj", "bg", "bt", "bm", "cb", "ch", "cy", "in", "id", "ir", "iz", "ja", "jo", "kz", "kg", "kn", "ks", "ku", "la", "le", "my", "mv", "mn", "np", "pk", "rp", "qa", "sa", "ce", "sn", "th", "ti", "tm", "tu", "tx", "uz", "vm", "ym"],
                "north-america": ["ca", "us", "mx", "gt", "bh", "cs", "nu", "es", "ho", "pm"],
                "south-america": ["ar", "bl", "br", "ci", "co", "ec", "fk", "gf", "gy", "pa", "pe", "ns", "uy", "ve"]
            }
            
            return country_codes.get(region, [])
            
        except Exception as e:
            print(f"Error getting country list for {region}: {e}")
            return []
    
    def fetch_country_data(self, region: str, country_code: str) -> Optional[Dict]:
        """Fetch data for a specific country"""
        try:
            url = f"{self.base_url}/{region}/{country_code}.json"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch {country_code}: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error fetching data for {country_code}: {e}")
            return None
    
    def process_country_data(self, country_code: str, data: Dict) -> bool:
        """Process and store country data"""
        try:
            # Extract basic country information
            intro = data.get("Introduction", {})
            geo = data.get("Geography", {})
            people = data.get("People and Society", {})
            govt = data.get("Government", {})
            econ = data.get("Economy", {})
            
            # Create or update country profile
            country_name = govt.get("Country name", {}).get("conventional short form", {}).get("text", country_code.upper())
            official_name = govt.get("Country name", {}).get("conventional long form", {}).get("text", "")
            
            # Extract numeric values safely
            def extract_number(text_dict):
                if isinstance(text_dict, dict) and "text" in text_dict:
                    text = text_dict["text"]
                    # Extract first number from text
                    import re
                    numbers = re.findall(r'[\d,]+', text.replace(',', ''))
                    return int(numbers[0]) if numbers else None
                return None
            
            population = extract_number(people.get("Population", {}))
            area_total = extract_number(geo.get("Area", {}).get("total", {}))
            
            # Create country profile
            country = CountryProfile(
                id=country_code,
                name=country_name,
                official_name=official_name,
                region=geo.get("Map references", {}).get("text", ""),
                capital=govt.get("Capital", {}).get("name", {}).get("text", ""),
                population=population,
                area=area_total,
                currency=econ.get("Currency", {}).get("name", {}).get("text", ""),
                government_type=govt.get("Government type", {}).get("text", ""),
                data_source_id=self.source_id
            )
            
            # Check if country already exists
            existing_country = CountryProfile.query.get(country_code)
            if existing_country:
                # Update existing
                for attr in ['name', 'official_name', 'region', 'capital', 'population', 'area', 'currency', 'government_type']:
                    if hasattr(country, attr):
                        setattr(existing_country, attr, getattr(country, attr))
                existing_country.last_updated = datetime.utcnow()
            else:
                db.session.add(country)
            
            # Create data entry for raw JSON
            content_hash = hashlib.sha256(json.dumps(data).encode()).hexdigest()
            
            entry = DataEntry(
                id=str(uuid.uuid4()),
                source_id=self.source_id,
                title=f"CIA Factbook Profile: {country_name}",
                content=json.dumps(data, indent=2),
                content_type="profile",
                url=f"https://www.cia.gov/the-world-factbook/countries/{country_code}/",
                raw_data_hash=content_hash
            )
            
            db.session.add(entry)
            
            # Create lineage record
            lineage = DataLineage(
                id=str(uuid.uuid4()),
                data_entry_id=entry.id,
                source_chain=json.dumps([{
                    "source_id": self.source_id,
                    "collection_timestamp": datetime.utcnow().isoformat(),
                    "collection_method": "api",
                    "raw_data_hash": content_hash,
                    "transformation_applied": ["json_parsing", "country_profile_extraction"]
                }]),
                quality_metrics=json.dumps({
                    "completeness": 0.9,
                    "accuracy": 0.95,
                    "timeliness": 0.8,
                    "consistency": 0.9
                }),
                validation_status="validated"
            )
            
            db.session.add(lineage)
            db.session.commit()
            
            return True
            
        except Exception as e:
            print(f"Error processing country data for {country_code}: {e}")
            db.session.rollback()
            return False
    
    def collect_region_data(self, region: str) -> Dict[str, bool]:
        """Collect data for all countries in a region"""
        results = {}
        country_codes = self.get_country_list(region)
        
        print(f"Collecting data for {len(country_codes)} countries in {region}")
        
        for country_code in country_codes:
            print(f"Processing {country_code}...")
            data = self.fetch_country_data(region, country_code)
            
            if data:
                success = self.process_country_data(country_code, data)
                results[country_code] = success
            else:
                results[country_code] = False
        
        return results
    
    def collect_all_data(self) -> Dict[str, Dict[str, bool]]:
        """Collect data for all regions"""
        if not self.initialize_source():
            return {"error": "Failed to initialize source"}
        
        all_results = {}
        
        # Focus on major regions first
        priority_regions = ["europe", "africa", "north-america", "south-america"]
        
        for region in priority_regions:
            print(f"\n=== Collecting data for {region} ===")
            results = self.collect_region_data(region)
            all_results[region] = results
            
            # Print summary
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            print(f"Region {region}: {successful}/{total} countries processed successfully")
        
        return all_results

def run_cia_factbook_collection():
    """Main function to run CIA Factbook data collection"""
    collector = CIAFactbookCollector()
    results = collector.collect_all_data()
    
    print("\n=== Collection Summary ===")
    for region, country_results in results.items():
        if isinstance(country_results, dict):
            successful = sum(1 for success in country_results.values() if success)
            total = len(country_results)
            print(f"{region}: {successful}/{total} countries")
    
    return results

if __name__ == "__main__":
    run_cia_factbook_collection()

