import ee
import flask
from flask_cors import CORS
import logging
import dotenv
import os

# ---------- ONLY ADDITION (dotenv load) ----------
dotenv.load_dotenv()   # loads .env from current working directory
# -----------------------------------------------

app = flask.Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})


from google import genai
from google.genai import types

# ---------- ONLY ADDITION (read env vars) ----------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PROJECT_ID = os.getenv("PROJECT_ID")

print("GEMINI_API_KEY loaded:", bool(GEMINI_API_KEY))
print("PROJECT_ID loaded:", PROJECT_ID)
# -------------------------------------------------

# Initialize client
client = genai.Client(api_key=GEMINI_API_KEY)

@app.route('/get_gemini_report')
def get_gemini_report():
    lat = flask.request.args.get('lat')
    lng = flask.request.args.get('lng')
    
    system_instr = (
        "You are a Senior Environmental Scientist and Enforcement Officer. "
        "Your task is to analyze environmental threats in the Aravalli Range."
    )
    
    user_prompt = f"""
    COORDINATES: Latitude {lat}, Longitude {lng}
    
    TASKS:
    1. Identify specific factors causing soil erosion at this location based on its Aravalli geography.
    2. Judge and report the meteorological (weather) vulnerabilities for this coordinate.
    3. Recommend the best strategic options to stop mining and stabilize the terrain.
    
    FORMAT: Use bullet points for the weather and action plan.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        config=types.GenerateContentConfig(
            system_instruction=system_instr,
            temperature=0.3
        ),
        contents=user_prompt
    )
    
    return {"report": response.text}

# Replace with your actual Project ID from Google Cloud Console
# ---------- ONLY FIX (use env value instead of self-reference) ----------
PROJECT_ID = PROJECT_ID
# ---------------------------------------------------------------------

try:
    ee.Initialize(project=PROJECT_ID)
    print("Google Earth Engine Initialized Successfully")
except Exception as e:
    print(f"EE Initialization Failed: {e}")

@app.route('/get_mining_map')
def get_mining_map():
    try:
        year = int(flask.request.args.get('year', 2024))
        region = ee.Geometry.Rectangle([76.5, 27.5, 77.5, 28.5])
        
        img = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
                .filterBounds(region) \
                .filterDate(f'{year}-01-01', f'{year}-12-31') \
                .median()

        bsi = img.expression(
            '((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))', {
                'B11': img.select('B11'), 'B4': img.select('B4'),
                'B8': img.select('B8'), 'B2': img.select('B2')
            })

        map_id = bsi.getMapId({'min': 0, 'max': 0.3, 'palette': ['green', 'yellow', 'orange', 'red']})
        return {"tile_url": map_id['tile_fetcher'].url_format}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/get_ai_prediction')
def get_ai_prediction():
    try:
        region = ee.Geometry.Rectangle([76.5, 27.5, 77.5, 28.5])
        
        now = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate('2024-01-01', '2024-12-31').median()
        past = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate('2022-01-01', '2022-12-31').median()

        def get_bsi(img):
            return img.expression(
                '((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))',
                {'B11': img.select('B11'), 'B4': img.select('B4'),
                 'B8': img.select('B8'), 'B2': img.select('B2')}
            )

        diff = get_bsi(now).subtract(get_bsi(past)).gt(0.05)
        
        vectors = diff.selfMask().reduceToVectors(
            geometry=region,
            scale=200,
            geometryType='centroid',
            maxPixels=1e8
        ).limit(5)
        
        features = vectors.getInfo()['features']
        coords_list = []

        for f in features:
            c = f['geometry']['coordinates']
            coords_list.append({"lat": c[1], "lng": c[0], "status": "CRITICAL EXCAVATION"})

        if not coords_list:
            coords_list = [
                {"lat": 28.1245, "lng": 76.9856, "status": "PREDICTIVE RISK: ZONE A"},
                {"lat": 27.9567, "lng": 77.1023, "status": "PREDICTIVE RISK: ZONE B"}
            ]

        map_id = diff.updateMask(diff).getMapId({'palette': ['#ff00ff']})
        
        return {
            "tile_url": map_id['tile_fetcher'].url_format,
            "critical_points": coords_list
        }

    except Exception as e:
        logging.error(f"AI Prediction Error: {e}")
        return {
            "tile_url": "",
            "critical_points": [{"lat": 28.0, "lng": 77.0, "status": "DEMO MODE: RECHECK API"}]
        }, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
