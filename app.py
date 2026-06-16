"""
Flask web app for Honda car price prediction.
"""
import os
import json
import joblib
import numpy as np
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, 'model')

# Load model, encoders, features, stats, options on startup
print("Loading model and artifacts...")

model = joblib.load(os.path.join(MODEL_DIR, 'honda_price_model.pkl'))
encoders = joblib.load(os.path.join(MODEL_DIR, 'encoders.pkl'))
features = joblib.load(os.path.join(MODEL_DIR, 'features.pkl'))

with open(os.path.join(MODEL_DIR, 'model_stats.json'), 'r', encoding='utf-8') as f:
    model_stats = json.load(f)

with open(os.path.join(MODEL_DIR, 'options.json'), 'r', encoding='utf-8') as f:
    options_data = json.load(f)

print(f"Model loaded. R² = {model_stats['r2']:.4f}")


def encode_feature(col, value, encoders):
    """Encode a categorical feature, returning -1 for unknown labels."""
    if col not in encoders:
        return 0
    le = encoders[col]
    try:
        return int(le.transform([str(value)])[0])
    except ValueError:
        # Unseen label - return 0 (use first class as fallback)
        return 0


@app.route('/')
def index():
    return render_template('index_predict.html')


@app.route('/api/options', methods=['GET'])
def get_options():
    """Return unique values for each categorical field."""
    car_model = request.args.get('model', None)

    response = {
        'model': options_data.get('model', []),
        'year': options_data.get('year', []),
        'trim': options_data.get('trim', []),
        'engine': options_data.get('engine', []),
        'transmission': options_data.get('transmission', []),
        'fuel_type': options_data.get('fuel_type', []),
        'region_specs': options_data.get('region_specs', []),
        'category': options_data.get('category', []),
    }

    # If a specific model is requested, filter trims and engines
    if car_model and car_model in options_data.get('model_options', {}):
        model_specific = options_data['model_options'][car_model]
        response['trim'] = model_specific.get('trim', response['trim'])
        response['engine'] = model_specific.get('engine', response['engine'])
        response['year'] = model_specific.get('year', response['year'])
        response['category'] = model_specific.get('category', response['category'])

    return jsonify(response)


@app.route('/api/predict', methods=['POST'])
def predict():
    """Accept prediction request and return predicted price."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400

    required_fields = ['model', 'year', 'trim', 'mileage_km', 'engine', 'transmission', 'fuel_type', 'region_specs']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400

    try:
        # Build feature vector in the same order as training
        categorical_features = ['model', 'trim', 'category', 'engine', 'transmission', 'fuel_type', 'region_specs']
        numeric_features = ['year', 'mileage_km']
        all_features_order = categorical_features + numeric_features

        # Get category from model_options if not provided
        category = data.get('category', '')
        if not category and data['model'] in options_data.get('model_options', {}):
            cats = options_data['model_options'][data['model']].get('category', [])
            category = cats[0] if cats else ''

        feature_values = []
        for feat in all_features_order:
            if feat in categorical_features:
                if feat == 'category':
                    val = encode_feature(feat, category, encoders)
                else:
                    val = encode_feature(feat, data.get(feat, ''), encoders)
            else:
                val = float(data.get(feat, 0))
            feature_values.append(val)

        X = np.array([feature_values])
        predicted_price_aed = float(model.predict(X)[0])

        # Clamp to reasonable range
        predicted_price_aed = max(10000, predicted_price_aed)

        # SAR conversion (approx 1 AED = 1.02 SAR)
        predicted_price_sar = predicted_price_aed * 1.02

        # Price range ±15%
        price_range_min = predicted_price_aed * 0.85
        price_range_max = predicted_price_aed * 1.15

        # Confidence from model R²
        confidence = model_stats['r2_percent']

        return jsonify({
            'price_aed': round(predicted_price_aed),
            'price_sar': round(predicted_price_sar),
            'price_range_min': round(price_range_min),
            'price_range_max': round(price_range_max),
            'confidence': round(confidence, 1)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Return model performance statistics."""
    return jsonify(model_stats)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
