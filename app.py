# Species Database - Complete Backend with Folium Export
# Save this as: app.py

from flask import Flask, render_template, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
import pandas as pd
import json
import os
from datetime import datetime
import uuid
from io import BytesIO
import logging
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import folium
from folium.plugins import HeatMap
import zipfile
from pathlib import Path
import glob

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'species-database-secret-key-2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)
os.makedirs('static/exports', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# In-memory storage
datasets_storage = {}
observations_storage = {}

def get_session_id():
    """Get or create session ID"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def allowed_file(filename):
    """Check if file type is allowed"""
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'kml', 'kmz'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_kml_boundary(file_path, original_filename):
    """Parse KML file to extract boundary coordinates"""
    try:
        if original_filename.lower().endswith('.kmz'):
            import zipfile
            with zipfile.ZipFile(file_path, 'r') as kmz:
                kml_files = [f for f in kmz.namelist() if f.lower().endswith('.kml')]
                if not kml_files:
                    raise ValueError("No KML file found in KMZ archive")
                kml_content = kmz.read(kml_files[0])
                root = ET.fromstring(kml_content)
        else:
            tree = ET.parse(file_path)
            root = tree.getroot()
        
        coordinates_elements = (root.findall('.//{http://www.opengis.net/kml/2.2}coordinates') or 
                               root.findall('.//coordinates'))
        
        if not coordinates_elements:
            raise ValueError("No coordinates found in KML file")
        
        all_coords = []
        for coord_elem in coordinates_elements:
            coords_text = coord_elem.text.strip()
            coord_pairs = coords_text.replace('\n', ' ').replace('\t', ' ').split()
            for pair in coord_pairs:
                if ',' in pair:
                    parts = pair.split(',')
                    if len(parts) >= 2:
                        try:
                            lng, lat = float(parts[0]), float(parts[1])
                            if -180 <= lng <= 180 and -90 <= lat <= 90:
                                all_coords.append([lat, lng])
                        except ValueError:
                            continue
        
        if not all_coords:
            raise ValueError("No valid coordinates found in KML boundary file")
        
        lats = [coord[0] for coord in all_coords]
        lngs = [coord[1] for coord in all_coords]
        
        bounds = {
            'north': max(lats),
            'south': min(lats),
            'east': max(lngs),
            'west': min(lngs),
            'coordinates': all_coords[:100]
        }
        
        return bounds
        
    except Exception as e:
        logger.error(f"Error parsing KML boundary: {str(e)}")
        raise Exception(f"Error parsing KML boundary: {str(e)}")

def process_uploaded_file(file_path, original_filename):
    """Process uploaded Excel/CSV/KML file and return cleaned data"""
    try:
        file_type = original_filename.lower().split('.')[-1]
        
        if file_type in ['kml', 'kmz']:
            return parse_kml_boundary(file_path, original_filename), []
        
        if original_filename.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        logger.info(f"Read {len(df)} rows from {original_filename}")
        
        df.columns = df.columns.str.lower().str.strip()
        
        column_mappings = {
            'species': ['species', 'species_name', 'scientific_name', 'name', 'taxon', 'bird_name'],
            'latitude': ['latitude', 'lat', 'y', 'decimal_latitude', 'y_coord'],
            'longitude': ['longitude', 'long', 'lng', 'lon', 'x', 'decimal_longitude', 'x_coord'],
            'count': ['count', 'abundance', 'number', 'individuals', 'quantity', 'total', 'no_of_birds'],
            'date': ['date', 'observation_date', 'survey_date', 'recorded_date', 'date_observed'],
            'location': ['location', 'place', 'site', 'area', 'locality']
        }
        
        mapped_columns = {}
        for standard_name, possible_names in column_mappings.items():
            for col in df.columns:
                if any(name in col for name in possible_names):
                    mapped_columns[standard_name] = col
                    break
        
        required_columns = ['species', 'latitude', 'longitude']
        missing_columns = [col for col in required_columns if col not in mapped_columns]
        
        if missing_columns:
            available_cols = ', '.join(df.columns)
            raise ValueError(f"Missing required columns: {missing_columns}. Available columns: {available_cols}")
        
        cleaned_data = []
        errors = []
        
        for idx, row in df.iterrows():
            try:
                species = str(row[mapped_columns['species']]).strip()
                lat = float(row[mapped_columns['latitude']])
                lng = float(row[mapped_columns['longitude']])
                count = int(row[mapped_columns.get('count', 'count')]) if 'count' in mapped_columns and pd.notna(row[mapped_columns['count']]) else 1
                date = str(row[mapped_columns['date']]) if 'date' in mapped_columns and pd.notna(row[mapped_columns['date']]) else None
                location = str(row[mapped_columns['location']]) if 'location' in mapped_columns and pd.notna(row[mapped_columns['location']]) else None
                
                if not species or species.lower() in ['nan', 'none', '']:
                    errors.append(f"Row {idx + 2}: Missing species name")
                    continue
                    
                if not (-90 <= lat <= 90):
                    errors.append(f"Row {idx + 2}: Invalid latitude {lat}")
                    continue
                    
                if not (-180 <= lng <= 180):
                    errors.append(f"Row {idx + 2}: Invalid longitude {lng}")
                    continue
                
                if count < 0:
                    errors.append(f"Row {idx + 2}: Invalid count {count}")
                    continue
                
                cleaned_data.append({
                    'id': str(uuid.uuid4()),
                    'species': species,
                    'latitude': lat,
                    'longitude': lng,
                    'count': count,
                    'date': date if date and date.lower() not in ['nan', 'none', ''] else None,
                    'location': location if location and location.lower() not in ['nan', 'none', ''] else None,
                    'created_at': datetime.now().isoformat()
                })
                
            except Exception as e:
                errors.append(f"Row {idx + 2}: {str(e)}")
        
        return cleaned_data, errors
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise Exception(f"Error processing file: {str(e)}")

# Routes
@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        unique_filename = timestamp + filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        file_type = filename.lower().split('.')[-1]
        
        try:
            result_data, errors = process_uploaded_file(file_path, filename)
        except Exception as e:
            os.remove(file_path)
            return jsonify({'success': False, 'message': str(e)}), 400
        
        session_id = get_session_id()
        
        if file_type in ['kml', 'kmz']:
            if not result_data:
                os.remove(file_path)
                return jsonify({'success': False, 'message': 'No valid boundary data found'}), 400
            
            boundary_id = str(uuid.uuid4())
            
            if session_id not in datasets_storage:
                datasets_storage[session_id] = {}
            
            datasets_storage[session_id][boundary_id] = {
                'id': boundary_id,
                'name': filename + ' (Study Area)',
                'file_type': file_type,
                'upload_date': datetime.now().isoformat(),
                'total_records': len(result_data.get('coordinates', [])),
                'unique_species': 0,
                'unique_locations': len(result_data.get('coordinates', [])),
                'bounds': result_data,
                'is_boundary': True
            }
            
            os.remove(file_path)
            
            return jsonify({
                'success': True,
                'message': f'Boundary loaded from {filename}',
                'dataset_id': boundary_id,
                'is_boundary': True,
                'bounds': result_data
            })
        
        if not result_data:
            os.remove(file_path)
            return jsonify({'success': False, 'message': 'No valid species data found'}), 400
        
        dataset_id = str(uuid.uuid4())
        
        total_records = len(result_data)
        unique_species = len(set(d['species'] for d in result_data))
        unique_locations = len(set(f"{d['latitude']},{d['longitude']}" for d in result_data))
        
        lats = [d['latitude'] for d in result_data]
        lngs = [d['longitude'] for d in result_data]
        bounds = {
            'north': max(lats),
            'south': min(lats),
            'east': max(lngs),
            'west': min(lngs)
        } if lats else None
        
        if session_id not in datasets_storage:
            datasets_storage[session_id] = {}
        
        datasets_storage[session_id][dataset_id] = {
            'id': dataset_id,
            'name': filename,
            'file_type': file_type,
            'upload_date': datetime.now().isoformat(),
            'total_records': total_records,
            'unique_species': unique_species,
            'unique_locations': unique_locations,
            'bounds': bounds,
            'is_boundary': False
        }
        
        if session_id not in observations_storage:
            observations_storage[session_id] = {}
        
        observations_storage[session_id][dataset_id] = result_data
        
        os.remove(file_path)
        
        response_data = {
            'success': True,
            'message': f'Successfully processed {len(result_data)} records',
            'dataset_id': dataset_id,
            'is_boundary': False,
            'stats': {
                'total_records': total_records,
                'unique_species': unique_species,
                'unique_locations': unique_locations,
                'bounds': bounds
            }
        }
        
        if errors:
            response_data['warnings'] = f"{len(errors)} rows had issues and were skipped"
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/datasets')
def get_datasets():
    """Get all datasets for current session"""
    try:
        session_id = get_session_id()
        user_datasets = datasets_storage.get(session_id, {})
        
        datasets_list = [dataset for dataset in user_datasets.values() 
                        if not dataset.get('is_boundary', False)]
        
        return jsonify({'success': True, 'datasets': datasets_list})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/boundaries')
def get_boundaries():
    """Get all boundary datasets for current session"""
    try:
        session_id = get_session_id()
        user_datasets = datasets_storage.get(session_id, {})
        
        boundaries = [dataset for dataset in user_datasets.values() 
                     if dataset.get('is_boundary', False)]
        
        return jsonify({'success': True, 'boundaries': boundaries})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/dataset/<dataset_id>/data')
def get_dataset_data(dataset_id):
    """Get observations for a specific dataset"""
    try:
        session_id = get_session_id()
        
        if (session_id not in datasets_storage or 
            dataset_id not in datasets_storage[session_id]):
            return jsonify({'success': False, 'message': 'Dataset not found'}), 404
        
        dataset_info = datasets_storage[session_id][dataset_id]
        observations = observations_storage[session_id].get(dataset_id, [])
        
        return jsonify({
            'success': True,
            'dataset': dataset_info,
            'data': observations
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/dataset/<dataset_id>/export')
def export_dataset(dataset_id):
    """Export dataset as CSV"""
    try:
        session_id = get_session_id()
        
        if (session_id not in datasets_storage or 
            dataset_id not in datasets_storage[session_id]):
            return jsonify({'success': False, 'message': 'Dataset not found'}), 404
        
        dataset_info = datasets_storage[session_id][dataset_id]
        observations = observations_storage[session_id].get(dataset_id, [])
        
        df = pd.DataFrame([{
            'Species': obs['species'],
            'Latitude': obs['latitude'],
            'Longitude': obs['longitude'],
            'Count': obs['count'],
            'Date': obs['date'] or '',
            'Location': obs.get('location', ''),
            'Created_At': obs['created_at']
        } for obs in observations])
        
        output = BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        
        filename = f"species_export_{dataset_info['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/dataset/<dataset_id>/export/enhanced', methods=['GET'])
def export_enhanced_data(dataset_id):
    """Export enhanced dataset with Folium-generated interactive HTML files"""
    try:
        session_id = get_session_id()
        
        if (session_id not in datasets_storage or 
            dataset_id not in datasets_storage[session_id]):
            return jsonify({'success': False, 'message': 'Dataset not found'}), 404
        
        dataset_info = datasets_storage[session_id][dataset_id]
        observations = observations_storage[session_id].get(dataset_id, [])
        boundaries = [b for b in datasets_storage[session_id].values() if b.get('is_boundary', False)]
        
        if not observations:
            return jsonify({'success': False, 'message': 'No data to export'}), 400
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dataset_name = dataset_info['name'].replace(' ', '_').replace('.', '_')
        
        # Create export directory
        export_dir = Path('static/exports')
        export_dir.mkdir(exist_ok=True)
        
        files_created = {}
        
        try:
            # 1. Interactive Heatmap using Folium
            lats = [obs['latitude'] for obs in observations]
            lngs = [obs['longitude'] for obs in observations]
            center_lat, center_lng = sum(lats) / len(lats), sum(lngs) / len(lngs)
            
            # Create heatmap
            m = folium.Map(location=[center_lat, center_lng], zoom_start=10, tiles='OpenStreetMap')
            
            # Add title
            title_html = f'''
            <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); 
                        background: white; padding: 15px; border-radius: 10px; 
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1); z-index: 1000; text-align: center;">
                <h2 style="color: #2E8B57; margin: 0;">Species Heatmap</h2>
                <p style="margin: 5px 0 0 0; color: #666;">{dataset_info["name"]}</p>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(title_html))
            
            # Add heatmap data
            heat_data = [[obs['latitude'], obs['longitude'], obs['count']] for obs in observations]
            HeatMap(heat_data, radius=25, blur=15, gradient={0.0: 'blue', 0.5: 'green', 1.0: 'red'}).add_to(m)
            
            # Add boundaries if available
            for boundary in boundaries:
                if boundary.get('bounds') and boundary['bounds'].get('coordinates'):
                    coords = boundary['bounds']['coordinates']
                    folium.Polygon(locations=coords, color='red', weight=2, opacity=0.8, fillOpacity=0.1).add_to(m)
            
            # Add statistics
            total_obs = sum(obs['count'] for obs in observations)
            unique_species = len(set(obs['species'] for obs in observations))
            
            stats_html = f'''
            <div style="position: fixed; top: 100px; right: 20px; width: 200px; 
                        background: white; padding: 15px; border-radius: 10px; 
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1); z-index: 1000;">
                <h4 style="color: #2E8B57; margin: 0 0 10px 0;">Statistics</h4>
                <p><strong>Total:</strong> {total_obs:,}</p>
                <p><strong>Species:</strong> {unique_species}</p>
                <p style="font-size: 11px; color: #666; margin-top: 10px;">
                    Generated: {datetime.now().strftime('%Y-%m-%d')}
                </p>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(stats_html))
            
            # Save heatmap
            heatmap_path = export_dir / f'interactive_heatmap_{dataset_name}_{timestamp}.html'
            m.save(str(heatmap_path))
            files_created['interactive_heatmap'] = f'/static/exports/{heatmap_path.name}'
            
            # 2. Dashboard
            m2 = folium.Map(location=[center_lat, center_lng], zoom_start=9)
            
            # Dashboard title
            dashboard_title = f'''
            <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); 
                        background: white; padding: 20px; border-radius: 10px; 
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1); z-index: 1000; text-align: center;">
                <h1 style="color: #2E8B57; margin: 0;">Species Dashboard</h1>
                <p style="margin: 5px 0 0 0; color: #666;">{dataset_info["name"]}</p>
            </div>
            '''
            m2.get_root().html.add_child(folium.Element(dashboard_title))
            
            # Add heatmap to dashboard
            HeatMap(heat_data, radius=30, blur=20).add_to(m2)
            
            # Add sample markers (limit for performance)
            colors = ['red', 'blue', 'green', 'purple', 'orange']
            for i, obs in enumerate(observations[:50]):  # Limit to 50 markers
                color = colors[hash(obs['species']) % len(colors)]
                folium.CircleMarker(
                    location=[obs['latitude'], obs['longitude']],
                    radius=max(5, min(obs['count'], 15)),
                    popup=f"<b>{obs['species']}</b><br>Count: {obs['count']}",
                    color=color,
                    fillOpacity=0.7
                ).add_to(m2)
            
            # Save dashboard
            dashboard_path = export_dir / f'statistical_dashboard_{dataset_name}_{timestamp}.html'
            m2.save(str(dashboard_path))
            files_created['dashboard'] = f'/static/exports/{dashboard_path.name}'
            
            # 3. Species-specific maps
            species_counts = {}
            for obs in observations:
                species_counts[obs['species']] = species_counts.get(obs['species'], 0) + obs['count']
            
            top_species = sorted(species_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            species_heatmaps = {}
            
            for species, count in top_species:
                species_obs = [obs for obs in observations if obs['species'] == species]
                if len(species_obs) >= 3:
                    # Create species map
                    species_lats = [obs['latitude'] for obs in species_obs]
                    species_lngs = [obs['longitude'] for obs in species_obs]
                    species_center_lat = sum(species_lats) / len(species_lats)
                    species_center_lng = sum(species_lngs) / len(species_lngs)
                    
                    m3 = folium.Map(location=[species_center_lat, species_center_lng], zoom_start=11)
                    
                    # Add title
                    species_title = f'''
                    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); 
                                background: white; padding: 15px; border-radius: 10px; 
                                box-shadow: 0 4px 8px rgba(0,0,0,0.1); z-index: 1000; text-align: center;">
                        <h2 style="color: #2E8B57; margin: 0;">{species}</h2>
                        <p style="margin: 5px 0 0 0; color: #666;">Distribution Map</p>
                    </div>
                    '''
                    m3.get_root().html.add_child(folium.Element(species_title))
                    
                    # Add heatmap for this species
                    species_heat_data = [[obs['latitude'], obs['longitude'], obs['count']] for obs in species_obs]
                    HeatMap(species_heat_data, radius=20, blur=10).add_to(m3)
                    
                    # Save species map
                    safe_species_name = species.replace(' ', '_').replace('/', '_')[:20]
                    species_path = export_dir / f'species_heatmap_{safe_species_name}_{dataset_name}_{timestamp}.html'
                    m3.save(str(species_path))
                    species_heatmaps[species] = f'/static/exports/{species_path.name}'
            
            files_created['species_heatmaps'] = species_heatmaps
            
            # Calculate final statistics
            total_observations = sum(obs['count'] for obs in observations)
            unique_species = len(set(obs['species'] for obs in observations))
            unique_locations = len(set(f"{obs['latitude']},{obs['longitude']}" for obs in observations))
            
            return jsonify({
                'success': True,
                'files': files_created,
                'stats': {
                    'total_observations': total_observations,
                    'unique_species': unique_species,
                    'unique_locations': unique_locations,
                    'average_density': round(total_observations / unique_locations, 1) if unique_locations > 0 else 0
                },
                'species_count': len(species_heatmaps),
                'dataset_name': dataset_info['name']
            })
            
        except Exception as create_error:
            logger.error(f"Error creating export files: {str(create_error)}")
            return jsonify({'success': False, 'message': f'Error creating files: {str(create_error)}'}), 500
            
    except Exception as e:
        logger.error(f"Enhanced export error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/dataset/<dataset_id>/delete', methods=['DELETE'])
def delete_dataset(dataset_id):
    """Delete a dataset"""
    try:
        session_id = get_session_id()
        
        if (session_id in datasets_storage and 
            dataset_id in datasets_storage[session_id]):
            del datasets_storage[session_id][dataset_id]
        
        if (session_id in observations_storage and 
            dataset_id in observations_storage[session_id]):
            del observations_storage[session_id][dataset_id]
        
        return jsonify({'success': True, 'message': 'Dataset deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    print("Species Database - Backend with Folium Export")
    print("Starting server at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)