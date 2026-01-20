import ee
import flask
from flask_cors import CORS
import dotenv
import os
from google import genai
from google.genai import types

dotenv.load_dotenv()
app = flask.Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PROJECT_ID = os.getenv("PROJECT_ID")
client = genai.Client(api_key=GEMINI_API_KEY)

try:
    ee.Initialize(project=PROJECT_ID)
    print("Google Earth Engine Initialized Successfully")
except Exception as e:
    print(f"EE Initialization Failed: {e}")

def add_size_property(f):
    return f.set('size', f.get('count'))

# Helper Functions
def get_s2_composite(year, region):
    return ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .filterBounds(region) \
            .filterDate(f'{year}-01-01', f'{year}-12-31') \
            .median()

def get_clean_bsi(img):
    bsi = img.expression(
        '((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))',
        {'B11': img.select('B11'), 'B4': img.select('B4'),
         'B8': img.select('B8'), 'B2': img.select('B2')}
    )
    ndwi = img.normalizedDifference(['B3', 'B8'])
    return bsi.updateMask(ndwi.lt(0.2))

# --- ROUTES ---

@app.route('/get_gemini_report')
def get_gemini_report():
    try:
        lat, lng = flask.request.args.get('lat'), flask.request.args.get('lng')
        mode = flask.request.args.get('mode', 'mining')
        
        # Dynamic instruction based on mode
        if mode == 'forest':
            sys_msg = "You are a Forest Conservation Officer."
            user_msg = f"Report on forest loss and canopy reduction at Lat: {lat}, Lng: {lng}."
        elif mode == 'landslide':
            sys_msg = "You are a Disaster Management Specialist."
            user_msg = f"Analyze landslide risk due to slope instability and vegetation loss at Lat: {lat}, Lng: {lng}."
        else:
            sys_msg = "You are a Senior Mining Inspector."
            user_msg = f"Report on illegal mining excavation at Lat: {lat}, Lng: {lng}."

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite", 
            config=types.GenerateContentConfig(system_instruction=sys_msg, temperature=0.3),
            contents=user_msg
        )
        return {"report": response.text}
    except Exception as e:
        return {"report": f"AI Error: {str(e)}"}, 500

@app.route('/get_mining_map')
def get_mining_map():
    try:
        year = int(flask.request.args.get('year', 2024))
        bounds_raw = flask.request.args.get('bounds')
        region = ee.Geometry.Rectangle([float(x) for x in bounds_raw.split(',')]) if bounds_raw else ee.Geometry.Rectangle([76.5, 27.5, 77.5, 28.5])
        
        img = get_s2_composite(year, region)
        bsi = get_clean_bsi(img)
        mining_mask = bsi.gt(0.18) 
        map_id = bsi.updateMask(mining_mask).getMapId({'min': 0.18, 'max': 0.3, 'palette': ["#ffff00", '#ff8800', '#ff0000']})
        return {"tile_url": map_id['tile_fetcher'].url_format}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/get_forest_change')
def get_forest_change():
    try:
        year_now = int(flask.request.args.get('year', 2024))
        year_ref = int(flask.request.args.get('refYear', 2016)) # FIXED: Now uses slider
        bounds_raw = flask.request.args.get('bounds')
        region = ee.Geometry.Rectangle([float(x) for x in bounds_raw.split(',')]) if bounds_raw else ee.Geometry.Rectangle([76.5, 27.5, 77.5, 28.5])
        
        img_past = get_s2_composite(year_ref, region)
        img_now = get_s2_composite(year_now, region)
        diff = img_now.normalizedDifference(['B8', 'B4']).subtract(img_past.normalizedDifference(['B8', 'B4']))
        
        loss, gain = diff.lt(-0.15).selfMask(), diff.gt(0.15).selfMask()
        change_layer = ee.ImageCollection([loss.visualize(palette=['#ff0000']), gain.visualize(palette=['#00ff00'])]).mosaic()
        return {"tile_url": change_layer.getMapId()['tile_fetcher'].url_format}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/get_landslide_risk')
def get_landslide_risk():
    try:
        year_now = int(flask.request.args.get('year', 2024))
        year_ref = int(flask.request.args.get('refYear', 2016))
        bounds_raw = flask.request.args.get('bounds')
        region = ee.Geometry.Rectangle([float(x) for x in bounds_raw.split(',')]) if bounds_raw else ee.Geometry.Rectangle([76.5, 27.5, 77.5, 28.5])

        slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003"))
        ndvi_diff = get_s2_composite(year_now, region).normalizedDifference(['B8', 'B4']).subtract(get_s2_composite(year_ref, region).normalizedDifference(['B8', 'B4']))

        risk_score = slope.gt(15).add(ndvi_diff.lt(-0.1).multiply(2)) 
        map_id = risk_score.updateMask(slope.gt(15)).getMapId({'min': 1, 'max': 3, 'palette': ['#ffff00', '#ffaa00', '#ff0000']})
        return {"tile_url": map_id['tile_fetcher'].url_format}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/get_ai_prediction')
def get_ai_prediction():
    try:
        year_now = int(flask.request.args.get('year', 2024))
        year_ref = int(flask.request.args.get('refYear', 2016))
        bounds_raw = flask.request.args.get('bounds')
        region = ee.Geometry.Rectangle([float(x) for x in bounds_raw.split(',')]) if bounds_raw else ee.Geometry.Rectangle([76.5, 27.5, 77.5, 28.5])

        # Analysis
        diff = get_clean_bsi(get_s2_composite(year_now, region)).subtract(get_clean_bsi(get_s2_composite(year_ref, region))).gt(0.1)
        vectors = diff.selfMask().reduceToVectors(geometry=region, scale=500, geometryType='centroid', maxPixels=1e8, bestEffort=True)

        # FIXED: Using named function instead of lambda
        final_points = vectors.map(add_size_property).sort('size', False).limit(5)
        
        features = final_points.getInfo().get('features', [])
        coords_list = [{"lat": f['geometry']['coordinates'][1], "lng": f['geometry']['coordinates'][0], "status": f"MAJOR RISK (Size: {f['properties']['size']})"} for f in features]

        if not coords_list:
            c = region.centroid().getInfo()['coordinates']
            coords_list = [{"lat": c[1], "lng": c[0], "status": "SCAN COMPLETE: NO ANOMALIES"}]

        # FIXED: Added format: 'png' for better transparency in Leaflet
        map_id = diff.updateMask(diff).getMapId({'palette': ['#ff00ff'], 'format': 'png'})
        return {"tile_url": map_id['tile_fetcher'].url_format, "critical_points": coords_list}
    except Exception as e:
        print(f"Prediction Error: {e}")
        return {"tile_url": "", "critical_points": []}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)