import os
import httpx
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Cadastre API – Département 02")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB connection ──────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "cadastre"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok"}


# ── Parcelles – bbox query ─────────────────────────────────────────────────────

@app.get("/parcelles")
def get_parcelles(
    bbox: str = Query(..., description="xmin,ymin,xmax,ymax in WGS84"),
    limit: int = Query(500, le=2000),
):
    """
    Return parcelles as GeoJSON FeatureCollection for the given bounding box.
    bbox format: lon_min,lat_min,lon_max,lat_max
    """
    try:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=400, detail="bbox must be xmin,ymin,xmax,ymax")

    xmin, ymin, xmax, ymax = parts

    sql = """
        SELECT
            gid,
            idu,
            numero,
            feuille,
            section,
            code_dep,
            code_com,
            com_abs,
            contenance,
            ST_AsGeoJSON(geom)::json AS geometry
        FROM parcelles
        WHERE geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
        LIMIT %s
    """

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (xmin, ymin, xmax, ymax, limit))
            rows = cur.fetchall()
    finally:
        conn.close()

    features = []
    for row in rows:
        geom = row.pop("geometry")
        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": dict(row),
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "count": len(features),
    }


# ── Single parcel ────────────────────────────────────────────────────────────

@app.get("/parcelles/{idu}")
def get_parcelle(idu: str):
    """Return a single parcelle by its IDU (unique parcel identifier)."""
    sql = """
        SELECT
            gid, idu, numero, feuille, section,
            code_dep, code_com, com_abs, contenance,
            ST_AsGeoJSON(geom)::json AS geometry
        FROM parcelles
        WHERE idu = %s
    """
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (idu,))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Parcelle not found")

    geom = row.pop("geometry")
    return {
        "type": "Feature",
        "geometry": geom,
        "properties": dict(row),
    }


# ── SIREN lookup via Koumoul MAJIC API ──────────────────────────────────────────

@app.get("/parcelles/{idu}/siren")
async def get_siren(idu: str):
    """
    Look up the owner SIREN for a parcelle using the Koumoul MAJIC API.
    Only works for legal-entity (personne morale) owners.
    """
    # Koumoul MAJIC API - Parcelles des personnes morales
    url = f"https://koumoul.com/data-fair/api/v1/datasets/parcelles-des-personnes-morales/lines?q={idu}"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)

    if resp.status_code != 200:
        return {"siren": None, "message": f"Koumoul API error: {resp.status_code}"}

    data = resp.json()
    results = data.get("results", [])
    if not results:
        return {"siren": None, "message": "No owner data found (may be private individual)"}

    # Extract SIREN from the first result
    owner = results[0]
    siren = owner.get("numero_siren")
    
    return {
        "siren": siren,
        "denominataire": owner.get("denomination"),
        "proprietaire": owner,
    }


# ──INSEE Sirene API ────────────────────────────────────────────────────

@app.get("/siren/{siren}")
async def get_company(siren: str):
    """Fetch company info from INSEE Sirene API (requires API key in .env)."""
    api_key = os.getenv("INSEE_API_KEY", "")

    # Use the public Sirene open data endpoint (no key needed for basic lookup)
    url = f"https://api.insee.fr/entreprises/sirene/V3.11/siren/{siren}"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="SIREN not found")
    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="INSEE API key required – set INSEE_API_KEY in .env")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"INSEE API error: {resp.status_code}")

    data = resp.json()
    unite = data.get("uniteLegale", {})
    return {
        "siren": siren,
        "denomination": unite.get("denominationUniteLegale"),
        "categorie_juridique": unite.get("categorieJuridiqueUniteLegale"),
        "activite_principale": unite.get("activitePrincipaleUniteLegale"),
        "etat": unite.get("etatAdministratifUniteLegale"),
    }
