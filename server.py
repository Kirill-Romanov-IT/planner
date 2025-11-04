from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import json
from datetime import datetime
from pathlib import Path

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)  # разрешаем CORS-запросы (на случай если фронт открывается как file://)

# Папка для сохранения данных
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


# === Роут главной страницы ===
@app.route("/")
def index():
    return render_template("index.html")


# === Роут для приёма JSON ===
@app.route("/api/tasks", methods=["POST"])
def save_tasks():
    try:
        data = request.get_json(force=True)
        if not data or "tasks" not in data:
            return jsonify({"error": "Неверный формат данных"}), 400

        # Формируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = DATA_DIR / f"tasks_{timestamp}.json"

        # Сохраняем в файл
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved: {filename}")
        return jsonify({"status": "ok", "file": filename.name})
    except Exception as e:
        print("❌ Ошибка:", e)
        return jsonify({"error": str(e)}), 500


# === Опционально: доступ к сохранённым JSON ===
@app.route("/data/<path:filename>")
def get_saved_file(filename):
    return send_from_directory(DATA_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
