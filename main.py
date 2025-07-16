"""
Cloud Run ↔︎ Vertex AI 端點 Proxy
--------------------------------
  • 讀環境變數：PROJECT_ID / LOCATION / ENDPOINT_ID
  • /       → liveness probe
  • /predict → 轉發前端 JSON 到 Vertex AI，回傳原樣 JSON
"""

import os, json
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import aiplatform
from google.protobuf.json_format import MessageToJson

# ---------- 基本設定 ----------
app = Flask(__name__)
CORS(app)                                   # 允許所有來源呼叫

# Cloud Run 內建變數；手動部署可另外 export GCP_PROJECT / GCP_REGION
PROJECT_ID  = (
    os.getenv("GOOGLE_CLOUD_PROJECT") or
    os.getenv("GCLOUD_PROJECT")       or
    os.getenv("GCP_PROJECT")
)
LOCATION    = os.getenv("GCP_REGION", "asia-east1")
ENDPOINT_ID = os.getenv("VERTEX_ENDPOINT_ID")   # 必填，沒設會丟 TypeError

# ---------- 健康檢查 ----------
@app.get("/")
def health_check():
    return "OK", 200

# ---------- 主要 API ----------
@app.post("/predict")
def handle_prediction():
    try:
        body = request.get_json(force=True, silent=False)
        if not body or "instances" not in body:
            return jsonify(error="request JSON 必須包含 'instances'"), 400

        api_endpoint     = f"{LOCATION}-aiplatform.googleapis.com"
        client           = aiplatform.gapic.PredictionServiceClient(
            client_options={"api_endpoint": api_endpoint}
        )
        endpoint_path    = client.endpoint_path(
            project=PROJECT_ID, location=LOCATION, endpoint=ENDPOINT_ID
        )

        resp = client.predict(endpoint=endpoint_path,
                              instances=body["instances"])

        return jsonify(json.loads(MessageToJson(resp._pb)))

    except Exception as exc:                         # noqa: BLE001
        app.logger.exception("Vertex AI proxy error: %s", exc)
        return jsonify(error=str(exc)), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0",
            port=int(os.getenv("PORT", "8080")),
            debug=True)
