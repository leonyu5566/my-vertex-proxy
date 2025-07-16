# --- Dockerfile ---
# 這是一個設定檔，告訴 Cloud Build 如何打包我們的應用程式。

# 1. 使用官方的 Python 3.9 slim 版本作為基礎
# slim 版本比較小，可以讓我們的容器更輕便
FROM python:3.9-slim

# 2. 設定環境變數，防止 Python 將 .pyc 檔案寫入容器中
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. 在容器內建立一個工作目錄
WORKDIR /app

# 4. 複製 requirements.txt 檔案到工作目錄
COPY requirements.txt .

# 5. 安裝所有必要的 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 6. 將我們應用程式的其他所有檔案 (也就是 main.py) 複製到工作目錄
COPY . .

# 7. 設定 Gunicorn (一個更適合正式環境的網頁伺服器) 來運行我們的 Flask 應用程式
# 它會在 8080 連接埠上監聽請求
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]