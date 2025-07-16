# main.py
import os, json
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import aiplatform
from google.protobuf.json_format import MessageToJson

app = Flask(__name__)
CORS(app)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
LOCATION = os.getenv("GCP_REGION", "asia‑east1")
ENDPOINT_ID = os.getenv("VERTEX_ENDPOINT_ID")

if not PROJECT_ID or not ENDPOINT_ID:
    raise RuntimeError(f"Missing env vars: PROJECT_ID={PROJECT_ID}, ENDPOINT_ID={ENDPOINT_ID}")

@app.get("/")
def health():
    return "OK", 200

@app.post("/predict")
def predict():
    try:
        body = request.get_json(force=True)
        if not body or "instances" not in body:
            return jsonify(error="request JSON needs 'instances'"), 400

        client = aiplatform.gapic.PredictionServiceClient(
            client_options={"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
        )
        endpoint_path = client.endpoint_path(
            project=PROJECT_ID, location=LOCATION, endpoint=ENDPOINT_ID
        )
        resp = client.predict(endpoint=endpoint_path, instances=body["instances"])
        return jsonify(json.loads(MessageToJson(resp._pb)))
    except Exception as e:
        app.logger.exception("proxy error")
        return jsonify(error=str(e)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=True)

