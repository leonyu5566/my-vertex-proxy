# main.py
import os, json
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import aiplatform
from google.protobuf.json_format import MessageToJson

app = Flask(__name__)
CORS(app)

# --- 1. 基本環境變數 ---
PROJECT_ID   = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
LOCATION     = os.getenv("GCP_REGION", "asia-east1")
ENDPOINT_ID  = os.getenv("VERTEX_ENDPOINT_ID")

if not PROJECT_ID or not ENDPOINT_ID:
    raise RuntimeError(
        f"Missing env vars: PROJECT_ID={PROJECT_ID}, ENDPOINT_ID={ENDPOINT_ID}"
    )

# --- 2. Scikit‑learn 模型需要固定順序的 list ---
FEATURE_ORDER = [
    "t_1", "t_2",
    "Us_Dollar_Index", "US10YY", "US2YY",
    "Unemployment_Rate", "CPI", "PMI_Index",
    "VIX_Index", "EFFR", "gold", "Nfarm"
]

def prepare_instances(raw_instances):
    """
    將前端送來的 instances 轉成 Vertex Scikit‑learn 容器可接受的
    List[List[float]] 形式；同時驗證欄位與型別。
    """
    prepared = []
    for idx, inst in enumerate(raw_instances, start=1):
        # dict → list
        if isinstance(inst, dict):
            try:
                row = [float(inst[f]) for f in FEATURE_ORDER]
            except KeyError as ke:
                raise ValueError(f"Instance {idx} 缺少必要欄位: {ke}") from ke
            prepared.append(row)
        # list → 確保都是 float
        elif isinstance(inst, (list, tuple)):
            row = [float(x) for x in inst]
            prepared.append(row)
        else:
            raise ValueError(f"Instance {idx} 必須是 dict 或 list，收到 {type(inst)}")
    return prepared

# --- 3. 健康檢查 ---
@app.get("/")
def health():
    return "OK", 200

# --- 4. 預測端點 ---
@app.post("/predict")
def predict():
    try:
        body = request.get_json(force=True)
        if not body or "instances" not in body:
            return jsonify(error="request JSON needs 'instances'"), 400

        # 4‑1. 轉換資料格式 ----------------------------
        try:
            instances = prepare_instances(body["instances"])
        except ValueError as ve:
            return jsonify(error=str(ve)), 400

        app.logger.info("Prepared instances => %s", instances)

        # 4‑2. 呼叫 Vertex Endpoint --------------------
        client = aiplatform.gapic.PredictionServiceClient(
            client_options={"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
        )
        endpoint_path = client.endpoint_path(
            project=PROJECT_ID, location=LOCATION, endpoint=ENDPOINT_ID
        )
        resp = client.predict(endpoint=endpoint_path, instances=instances)

        # 4‑3. 回傳結果 (pb → JSON) --------------------
        return jsonify(json.loads(MessageToJson(resp._pb)))

    except Exception as e:
        app.logger.exception("proxy error")
        return jsonify(error=str(e)), 500

# --- 5. 本地測試方便 ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=True)


