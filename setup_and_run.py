# Species Database - Clean Setup and Run Script (No HTML Generation)
# Save this as: setup_and_run.py

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_banner():
    """Print welcome banner"""
    print("=" * 70)
    print("🐦 SPECIES DATABASE - Clean Architecture Setup 🐦")
    print("=" * 70)
    print("🌟 Features:")
    print("   • CSV & Excel species data support")
    print("   • KML/KMZ boundary file support") 
    print("   • Interactive maps with heatmaps")
    print("   • Species-specific visualizations")
    print("   • Auto-fit to study areas")
    print("   • Clean export functionality")
    print("   • Beautiful bird-themed design")
    print("=" * 70)

def check_python_version():
    """Check Python version compatibility"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required. Current version:", sys.version)
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def install_requirements():
    """Install required packages"""
    requirements = [
        "flask>=2.3.0",
        "pandas>=1.5.0", 
        "openpyxl>=3.1.0",
        "werkzeug>=2.3.0",
        "lxml>=4.9.0",
        "matplotlib>=3.5.0",
        "folium>=0.12.0",
        "numpy>=1.21.0"
    ]
    
    print("\n📦 Installing Python packages...")
    failed_packages = []
    
    for req in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", req], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"   ✅ {req}")
        except subprocess.CalledProcessError:
            print(f"   ❌ Failed to install {req}")
            failed_packages.append(req)
    
    if failed_packages:
        print(f"\n⚠️  Some packages failed to install: {', '.join(failed_packages)}")
        print("You may need to install them manually:")
        for pkg in failed_packages:
            print(f"   pip install {pkg}")
        return False
    
    return True

def create_directory_structure():
    """Create necessary directories"""
    directories = [
        "templates",
        "static", 
        "uploads"
    ]
    
    print("\n📁 Creating directory structure...")
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   ✅ {directory}/")

def create_requirements_txt():
    """Create requirements.txt file"""
    requirements_content = """# Species Database Requirements - Clean Architecture
# Core Flask framework
flask>=2.3.0
werkzeug>=2.3.0

# Data processing
pandas>=1.5.0
openpyxl>=3.1.0
numpy>=1.21.0

# XML/KML processing
lxml>=4.9.0

# Visualization for export
matplotlib>=3.5.0
folium>=0.12.0

# Optional: For enhanced Excel support
xlrd>=2.0.0

# Optional: For better error handling
python-dotenv>=1.0.0
"""
    
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write(requirements_content)
    print("✅ Created requirements.txt")

def check_html_template():
    """Check if HTML template exists"""
    template_path = "templates/index.html"
    
    if os.path.exists(template_path):
        print("✅ templates/index.html found")
        return True
    else:
        print("⚠️  templates/index.html not found")
        print("   👉 Make sure to place your HTML frontend file at templates/index.html")
        return False

def check_existing_files():
    """Check if required files exist"""
    files_status = []
    
    if os.path.exists("app.py"):
        print("✅ app.py found")
        files_status.append(True)
    else:
        print("❌ app.py not found!")
        print("   👉 Make sure your Flask backend is saved as app.py")
        files_status.append(False)
    
    html_exists = check_html_template()
    files_status.append(html_exists)
    
    return all(files_status)

def create_sample_data():
    """Create sample data files for testing"""
    print("\n📄 Creating sample data files...")
    
    # Create sample CSV
    sample_csv_content = """species,latitude,longitude,count,date,location
House Sparrow,28.6139,77.2090,5,2024-01-15,Delhi
Rock Pigeon,28.6129,77.2295,12,2024-01-15,Connaught Place
Indian Myna,28.6328,77.2197,8,2024-01-16,Karol Bagh
House Crow,28.6517,77.2219,15,2024-01-16,Civil Lines
Rose-ringed Parakeet,28.6280,77.2065,6,2024-01-17,Rajouri Garden
Red-vented Bulbul,28.6100,77.2300,4,2024-01-17,India Gate
Common Babbler,28.6200,77.2100,3,2024-01-18,Lodhi Gardens
White-cheeked Barbet,28.6050,77.2450,2,2024-01-18,Humayun Tomb
Oriental Magpie-Robin,28.6400,77.2000,7,2024-01-19,Red Fort
Spotted Dove,28.6300,77.2200,9,2024-01-19,Lotus Temple"""
    
    with open("sample_species_data.csv", "w", encoding="utf-8") as f:
        f.write(sample_csv_content)
    
    print("   ✅ sample_species_data.csv")
    
    # Create sample KML boundary
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Delhi Study Area</name>
    <Placemark>
      <name>Delhi Boundary</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.1000,28.7000,0
              77.3000,28.7000,0
              77.3000,28.5000,0
              77.1000,28.5000,0
              77.1000,28.7000,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""
    
    with open("sample_delhi_boundary.kml", "w", encoding="utf-8") as f:
        f.write(kml_content)
    
    print("   ✅ sample_delhi_boundary.kml")
    print("   👉 Use these files to test the upload functionality")

def run_application():
    """Run the Flask application"""
    print("\n🚀 Starting Species Database server...")
    print("=" * 50)
    print("🌐 Server will start at: http://localhost:5000")
    print("📦 Clean Export Features:")
    print("   • CSV Data Export")
    print("   • Interactive HTML Map Export") 
    print("   • JSON Chart Data Export")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        # Import and run the Flask app
        import app
        app.app.run(debug=True, host='0.0.0.0', port=5000)
    except ImportError:
        print("❌ Could not import app.py. Make sure it exists and is valid Python code.")
        return False
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False

def main():
    """Main setup and run function"""
    print_banner()
    
    # Check Python version
    check_python_version()
    
    # Check if required files exist
    files_exist = check_existing_files()
    
    if not files_exist:
        print("\n❌ Missing required files!")
        print("Please ensure you have:")
        print("   • app.py (Flask backend)")
        print("   • templates/index.html (Frontend)")
        print("\nRun this script again after adding the missing files.")
        return
    
    # Install requirements
    if not install_requirements():
        print("❌ Some packages failed to install.")
        print("Please install missing packages manually and try again.")
        return
    
    # Create directory structure
    create_directory_structure()
    
    # Create files
    create_requirements_txt()
    create_sample_data()
    
    print("\n✅ Setup completed successfully!")
    print("\n📋 Project structure:")
    print("   📁 Species Database/")
    print("   ├── 📄 app.py (Flask backend)")
    print("   ├── 📄 setup_and_run.py (this script)")
    print("   ├── 📄 requirements.txt")
    print("   ├── 📄 sample_species_data.csv (test data)")
    print("   ├── 📄 sample_delhi_boundary.kml (test boundary)")
    print("   ├── 📁 templates/")
    print("   │   └── 📄 index.html (frontend)")
    print("   ├── 📁 static/ (static files)")
    print("   └── 📁 uploads/ (temporary uploads)")
    
    print("\n🎯 Clean Architecture Benefits:")
    print("   • Backend handles data processing only")
    print("   • Frontend handles presentation only")
    print("   • No HTML generation in backend")
    print("   • Proper separation of concerns")
    print("   • Maintainable and scalable code")
    
    # Ask user if they want to run the application
    print("\n" + "=" * 50)
    response = input("🚀 Do you want to start the server now? (y/n): ").strip().lower()
    
    if response in ['y', 'yes']:
        run_application()
    else:
        print("\n💡 To start the server later, run:")
        print("   python setup_and_run.py")
        print("   or")
        print("   python app.py")
        
        print("\n📝 Testing steps:")
        print("   1. Start the server")
        print("   2. Upload sample_species_data.csv")
        print("   3. Upload sample_delhi_boundary.kml")
        print("   4. Test the clean export functionality")

if __name__ == "__main__":
    main()