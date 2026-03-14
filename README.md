# Cadastre Aisne (02) - Interactive View & SIREN Lookup

This project is a full-stack application designed to visualize cadastral parcelles for the Aisne department (02) and retrieve owner information (SIREN/INSEE) via external APIs.

## 🚀 Features
- **PostGIS Integration**: Handles ~1 million parcels with fast spatial queries.
- **Interactive Map**: Built with Leaflet.js, showing parcels dynamically based on zoom and viewport.
- **Smart Highlighting**: Visual feedback for selected parcels.
- **Owner Lookup**: Real-time integration with **Koumoul API (MAJIC)** for SIREN retrieval.
- **Company Insights**: Enrichment with **INSEE Sirene API** (OAuth2/Integration Key).

---

## 🛠️ Setup Instructions

### 0. Clone the Repository
```powershell
git clone https://github.com/Ayoub1O/AdaptAI-intern.git
cd AdaptAI-intern
```

### 1. Database Setup
Ensure you have **PostgreSQL** with the **PostGIS** extension installed.

1. Create the database:
   ```sql
   CREATE DATABASE cadastre;
   \c cadastre
   CREATE EXTENSION postgis;
   ```
2. Import the data (PCI SHP files):
   ```powershell
   shp2pgsql -I -s 2154:4326 data/raw/PARCELLE.SHP parcelles | psql -U postgres -d cadastre
   ```

### 2. Backend Installation (FastAPI)
1. Install dependencies:
   ```powershell
   cd api
   pip install -r requirements.txt
   ```
2. Configure `.env` in the root directory:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=cadastre
   DB_USER=your_user
   DB_PASSWORD=your_password
   INSEE_API_KEY=your_insee_key
   ```

### 3. Frontend Setup
The frontend is a static HTML/JS application. No installation is required, just serve the directory.

---

## 🏃 Execution

1. **Start the API (Backend)**:
   ```powershell
   uvicorn api.main:app --reload --port 8000
   ```

2. **Start the Web Server (Frontend)**:
   ```powershell
   python -m http.server 3000 --directory frontend
   ```
   OR 
   
   open frontend/index.html 

3. **Access the App**:
   Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📖 API Endpoints
- `GET /parcelles?bbox=xmin,ymin,xmax,ymax`: Fetch parcels in a specific area.
- `GET /parcelles/{idu}/siren`: Get owner SIREN for a parcel.
- `GET /siren/{siren}`: Get detailed INSEE company information.

---
*Created for the AdaptAI internship.*
