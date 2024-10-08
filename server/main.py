from flask import Flask, jsonify, request
import pandas as pd
from flask_cors import CORS
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib
import os
from datetime import datetime


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# Load dataset
launch_data = pd.read_csv('dataset/launches.csv', encoding='latin1')
capsule_data = pd.read_csv('dataset/SPACEX/capsules.csv', encoding='latin1')
cores_data = pd.read_csv('dataset/SPACEX/cores.csv', encoding='latin1')
spacex_launch_data = pd.read_csv('dataset/SPACEX/launches.csv', encoding='latin1')
launchpad_data = pd.read_csv('dataset/SPACEX/launchpads.csv', encoding='latin1')
payloads_data = pd.read_csv('dataset/SPACEX/payloads.csv', encoding='latin1')
rockets_data = pd.read_csv('dataset/SPACEX/rockets.csv', encoding='latin1')
ship_data = pd.read_csv('dataset/SPACEX/ships.csv', encoding='latin1')


# ISRO Rocket Data

def preprocess_isro_data(data):
    label_encoders = {}
    for column in ['Launch Vehicle', 'Orbit Type', 'Application']:
        le = LabelEncoder()
        data[column] = le.fit_transform(data[column].astype(str))
        label_encoders[column] = le
    X = data[['Launch Vehicle', 'Orbit Type', 'Application']]
    y = data['Remarks'].apply(lambda x: 1 if 'successful' in x.lower() else 0)
    return X, y, label_encoders

def calculate_mission_lifetime(launch_date_str):
    try:
        launch_date = datetime.strptime(launch_date_str, '%d-%b-%y')
        current_date = datetime.now()
        lifetime_in_years = (current_date - launch_date).days / 365
        return round(lifetime_in_years, 2)
    except Exception as e:
        print(f"Error calculating lifetime: {e}")
        return None
    
def train_isro_launch_model():
    X, y, _ = preprocess_isro_data(launch_data)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    # Save the model
    joblib.dump(model, 'models/isro_launch_model.pkl')


train_isro_launch_model()

@app.route('/isro-launch-prediction', methods=['POST'])
def predict_isro_launch():
    launches = launch_data.to_dict(orient='records')
    predictions = []
    model = joblib.load('models/isro_launch_model.pkl')

    for launch in launches:
        launch_vehicle = launch.get('Launch Vehicle')
        orbit_type = launch.get('Orbit Type')
        application = launch.get('Application')
        launch_date = launch.get('Launch Date')

        # Predict mission success
        X_input = pd.DataFrame([[launch_vehicle, orbit_type, application]], columns=['Launch Vehicle', 'Orbit Type', 'Application'])
        X_preprocessed, _, _ = preprocess_isro_data(X_input)
        predicted_success = model.predict(X_preprocessed)[0]
        predicted_success_str = 'Launch successful' if predicted_success == 1 else 'Launch unsuccessful'

        # Calculate mission lifetime
        mission_lifetime = calculate_mission_lifetime(launch_date)

        predictions.append({
            'Launch Vehicle': launch.get('Launch Vehicle'),
            'Launch Date': launch.get('Launch Date'),
            'Orbit Type': launch.get('Orbit Type'),
            'Application': launch.get('Application'),
            'Predicted Success': predicted_success_str,
            'Mission Lifetime (years)': mission_lifetime
        })

    return jsonify(predictions), 200


@app.route('/isro-launch-details', methods=['GET'])
def get_isro_launch_details():
    orbit_types = launch_data['Orbit Type'].unique().tolist()
    launch_vehicles = launch_data['Launch Vehicle'].unique().tolist()
    applications = launch_data['Application'].unique().tolist()

    details = {
        'orbit_types': orbit_types,
        'launch_vehicles': launch_vehicles,
        'applications': applications
    }

    return jsonify(details), 200





# SpaceX Data
def preprocess_data(data, target_column):
    label_encoders = {}
    for column in data.select_dtypes(include=['object']).columns:
        le = LabelEncoder()
        data[column] = le.fit_transform(data[column].astype(str))
        label_encoders[column] = le
    X = data.drop(target_column, axis=1)
    y = data[target_column]
    return X, y, label_encoders

# Train model for capsule status prediction
def train_capsule_model():
    X, y, _ = preprocess_data(capsule_data, 'status')
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    joblib.dump(model, 'models/capsule_model.pkl')

# Train model for core status prediction
def train_core_model():
    X, y, _ = preprocess_data(cores_data, 'status')
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    joblib.dump(model, 'models/core_model.pkl')

# Train model for launch application prediction
def train_launch_model():
    X, y, _ = preprocess_data(launch_data, 'Application')
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    joblib.dump(model, 'models/launch_model.pkl')

# Ensure the models directory exists
if not os.path.exists('models'):
    os.makedirs('models')

# Call training functions if models don't exist
if not os.path.exists('models/capsule_model.pkl'):
    train_capsule_model()
if not os.path.exists('models/core_model.pkl'):
    train_core_model()
if not os.path.exists('models/launch_model.pkl'):
    train_launch_model()

# Prediction helper functions
def predict_capsule_status(model, status):
    return 'Reusable' if status == 'active' else 'Retired'

def predict_core_status(model, status):
    return 'Operational' if status == 'active' else 'Decommissioned'

def predict_launch_application(model, application):
    return 'Commercial' if 'Commercial' in application else 'Government'

def predict_payload_type(payload_type):
    return 'Satellite' if payload_type == 'Satellite' else 'Other'

def predict_rocket_status(active):
    return 'In Service' if active else 'Not in Service'

def predict_ship_status(active):
    return 'Operational' if active else 'Inactive'


@app.route('/predict-capsules', methods=['POST'])
def predict_capsules():
    capsules = capsule_data.to_dict(orient='records')
    predictions = []
    model = joblib.load('models/capsule_model.pkl')
    for capsule in capsules:
        status = capsule.get('status')
        predicted_status = predict_capsule_status(model, status)
        predictions.append({
            'Capsule ID': capsule.get('capsule_id'),
            'Predicted Status': predicted_status
        })
    return jsonify(predictions), 200

@app.route('/predict-cores', methods=['POST'])
def predict_cores():
    cores = cores_data.to_dict(orient='records')
    predictions = []
    model = joblib.load('models/core_model.pkl')
    for core in cores:
        status = core.get('status')
        predicted_status = predict_core_status(model, status)
        predictions.append({
            'Core ID': core.get('core_id'),
            'Predicted Status': predicted_status
        })
    return jsonify(predictions), 200

@app.route('/predict-launches', methods=['POST'])
def predict_launches():
    launches = launch_data.to_dict(orient='records')
    predictions = []
    model = joblib.load('models/launch_model.pkl')
    for launch in launches:
        application = launch.get('Application')
        if not isinstance(application, str):
            return jsonify({"error": "Application field must be a string."}), 400
        predicted_application = predict_launch_application(model, application)
        predictions.append({
            'Launch Vehicle': launch.get('Launch Vehicle'),
            'Predicted Application': predicted_application
        })
    return jsonify(predictions), 200

@app.route('/predict-payloads', methods=['POST'])
def predict_payloads():
    payloads = payloads_data.to_dict(orient='records')
    predictions = []
    for payload in payloads:
        payload_type = payload.get('type')
        predicted_type = predict_payload_type(payload_type)
        predictions.append({
            'Payload ID': payload.get('payload_id'),
            'Predicted Type': predicted_type
        })
    return jsonify(predictions), 200

@app.route('/predict-rockets', methods=['POST'])
def predict_rockets():
    rockets = rockets_data.to_dict(orient='records')
    predictions = []
    for rocket in rockets:
        active = rocket.get('active')
        predicted_status = predict_rocket_status(active)
        predictions.append({
            'Rocket ID': rocket.get('rocket_id'),
            'Predicted Status': predicted_status
        })
    return jsonify(predictions), 200

@app.route('/predict-ships', methods=['POST'])
def predict_ships():
    ships = ship_data.to_dict(orient='records')
    predictions = []
    for ship in ships:
        active = ship.get('active')
        predicted_status = predict_ship_status(active)
        predictions.append({
            'Ship ID': ship.get('ship_id'),
            'Predicted Status': predicted_status
        })
    return jsonify(predictions), 200

@app.route('/dataset-titles', methods=['GET'])
def get_dataset_titles():
    titles = {
        'launch_data': launch_data.columns.tolist(),
        'capsule_data': capsule_data.columns.tolist(),
        'cores_data': cores_data.columns.tolist(),
        'spacex_launch_data': spacex_launch_data.columns.tolist(),
        'launchpad_data': launchpad_data.columns.tolist(),
        'payloads_data': payloads_data.columns.tolist(),
        'rockets_data': rockets_data.columns.tolist(),
        'ship_data': ship_data.columns.tolist(),
    }
    return jsonify(titles), 200

if __name__ == '__main__':
    app.run(debug=True)
