import httpx
import asyncio
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os

load_dotenv()

async def find_siren():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "cadastre"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )
    
    # Get 100 large parcels in Soissons
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT code_dep, code_com, section, numero, idu, contenance 
            FROM parcelles 
            WHERE code_com = '02722' AND contenance > 2000 
            LIMIT 50;
            """
        )
        parcels = cur.fetchall()
        
    conn.close()
    print(f"Testing {len(parcels)} large parcels in Soissons...")
    
    async with httpx.AsyncClient(timeout=10) as client:
        for p in parcels:
            url = f"https://apicarto.ign.fr/api/cadastre/proprietaire?code_dep={p['code_dep']}&code_com={p['code_com']}&section={p['section']}&numero={p['numero']}"
            resp = await client.get(url)
            
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                if features:
                    props = features[0].get("properties", {})
                    if props.get("siren"):
                        print(f"FOUND! IDU: {p['idu']} (Area: {p['contenance']} m²)")
                        print(f"URL: {url}")
                        print(f"SIREN: {props['siren']} - {props.get('denominataire')}")
                        return
                    
            elif resp.status_code != 404 and resp.status_code != 400:
                 print(f"Error {resp.status_code} for {url}: {resp.text[:100]}")
                 
    print("None found in this batch.")

if __name__ == "__main__":
    asyncio.run(find_siren())
