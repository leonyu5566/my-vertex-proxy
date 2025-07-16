# 匯入必要的套件
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import aiplatform
from google.protobuf.json_format import MessageToJson
import gunicorn

# --- 初始化 Flask 應用程式 ---
app = Flask(__name__)
# 設定 CORS，允許所有來源的請求
CORS(app)

# --- 從環境變數讀取設定 ---
PROJECT_ID  = (
    os.environ.get("GOOGLE_CLOUD_PROJECT")      # Cloud Run / Functions
    or os.environ.get("GCP_PROJECT")            # 手動設定時也能相容
)
LOCATION     = os.environ.get("GCP_REGION",    "asia-east1")
ENDPOINT_ID  = os.environ.get("VERTEX_ENDPOINT_ID")


# --- 定義 API 路由 (Route) ---
@app.route("/predict", methods=["POST"])
def handle_prediction():
    """
    這是一個通用的代理函式。
    它會將收到的請求原封不動地轉發給 Vertex AI，
    並將 Vertex AI 的回應原封不動地傳回。
    """
    try:
        # 1. 取得前端傳來的整個 JSON 請求主體
        request_json = request.get_json()
        if not request_json or 'instances' not in request_json:
            return jsonify({"error": "無效的請求，請求主體必須是 JSON 格式且包含 'instances' 欄位。"}), 400

        # 2. 從請求中提取 'instances' 的內容
        instances_list = request_json.get('instances')

        # 3. 初始化 Vertex AI 客戶端
        api_endpoint = f"{LOCATION}-aiplatform.googleapis.com"
        client_options = {"api_endpoint": api_endpoint}
        client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)

        # 4. 組合完整的 endpoint 路徑
        endpoint_path = client.endpoint_path(
            project=PROJECT_ID, location=LOCATION, endpoint=ENDPOINT_ID
        )

        # 5. 直接將從前端收到的 instances_list 傳給 predict 方法
        response = client.predict(
            endpoint=endpoint_path,
            instances=instances_list,
        )

        # 6. 將 Vertex AI 回傳的 protobuf 格式回應，轉換成標準的 JSON 格式
        #    這樣可以確保回傳給前端的格式與直接呼叫 Vertex AI 完全相同
        response_json_string = MessageToJson(response._pb)
        response_dict = json.loads(response_json_string)
        
        # 7. 將轉換後的 JSON 回應傳回給前端
        return jsonify(response_dict)

    except Exception as e:
        # 如果過程中發生任何錯誤，記錄下來並回傳錯誤訊息
        app.logger.error(f"代理請求時發生錯誤：{e}")
        return jsonify({"error": str(e)}), 500

# --- 啟動伺服器 ---
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
