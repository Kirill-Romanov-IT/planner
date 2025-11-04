from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import os
from dateutil import parser as dateparser
import requests

# === Инициализация ===
load_dotenv()
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# === Настройка OpenRouter клиента (рабочая схема) ===
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# === Роут главной страницы ===
@app.route("/")
def index():
    return render_template("index.html")


# === Сохранение задач ===
@app.route("/api/tasks", methods=["POST"])
def save_tasks():
    try:
        data = request.get_json(force=True)
        if not data or "tasks" not in data:
            return jsonify({"error": "Неверный формат данных"}), 400

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = DATA_DIR / f"tasks_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved: {filename}")
        return jsonify({"status": "ok", "file": filename.name})
    except Exception as e:
        print("❌ Ошибка:", e)
        return jsonify({"error": str(e)}), 500


# === Генерация плана с OpenRouter и выгрузка в Nextcloud ===
@app.route("/api/generate-plan", methods=["POST"])
def generate_plan():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Нет данных"}), 400

        # Формируем текст запроса к LLM
        user_prompt = f"""У меня есть JSON с задачами и диапазоном дат:\n\n{json.dumps(data, ensure_ascii=False, indent=2)}\n\n
Требуется:

1. Равномерно распределить задачи по указанным датам.
2. Для каждой задачи:
   - Добавить 4–6 реалистичных подзадач.
   - Указать оценку времени на выполнение (в часах).
   - Добавить краткий комментарий.
3. Сформировать три таблицы в формате Markdown:

**Таблица 1 — Распределение по дням**
| Дата | Основная задача | Подзадачи | Время, ч | Комментарий |

**Таблица 2 — Детализация подзадач**
| № | Подзадача | Описание | Время, ч |

**Таблица 3 — Сводная таблица графика**
| Этап | Время, ч | Время, дн (8 ч/день) | Дата выполнения |

4. Пример оформления возьми из стиля PDF «График работ с 31 окт по 7 ноября».
5. Не обобщай — заполни каждую таблицу полностью.
6. Ответ выведи только в виде Markdown-таблиц, без пояснений."""

        # === 1. Отправляем запрос в OpenRouter (не трогаем, т.к. работает!) ===
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": os.getenv("SITE_URL"),
                "X-Title": os.getenv("SITE_TITLE"),
            },
            model="google/gemma-3-27b-it:free",
            messages=[{"role": "user", "content": user_prompt}],
        )

        result = completion.choices[0].message.content

        # === Очистка Markdown от обёрток ===
        if result.strip().startswith("```"):
            result = result.strip().strip("`")
            result = result.replace("markdown", "", 1).strip()


        # === 2. Сохраняем результат локально ===
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_file = DATA_DIR / f"plan_{timestamp}.md"
        local_file.write_text(result, encoding="utf-8")
        print(f"✅ Plan saved locally: {local_file}")

        # === 3. Загружаем в Nextcloud через WebDAV ===
        nc_url = os.getenv("NEXTCLOUD_URL").rstrip('/')
        nc_user = os.getenv("NEXTCLOUD_USER")
        nc_pass = os.getenv("NEXTCLOUD_PASS")

        # Формируем имя папки (пример: 4ноя–5ноя)
        start_date = dateparser.parse(data["start"]).strftime("%-d%b").lower()
        end_date = dateparser.parse(data["end"]).strftime("%-d%b").lower()
        folder_name = f"{start_date}-{end_date}".replace('.', '')

        folder_path = f"{nc_url}/{folder_name}/"
        response = requests.request("MKCOL", folder_path, auth=(nc_user, nc_pass))
        if response.status_code in (201, 405):
            print(f"📁 Nextcloud folder ready: {folder_path}")
        else:
            print(f"⚠️ Ошибка создания папки: {response.status_code} {response.text}")

        # Загружаем Markdown-файл
        upload_url = f"{folder_path}{local_file.name}"
        with open(local_file, "rb") as f:
            upload = requests.put(upload_url, data=f, auth=(nc_user, nc_pass))
        if upload.status_code in (201, 204):
            print(f"☁️ Uploaded to Nextcloud: {upload_url}")
        else:
            print(f"⚠️ Ошибка загрузки: {upload.status_code} {upload.text}")

        public_url = upload_url.replace(
            "/remote.php/dav/files/",
            "/index.php/apps/files/?dir=/"
        )

        return jsonify({
            "status": "ok",
            "file": local_file.name,
            "nextcloud": public_url
        })

    except Exception as e:
        print("❌ Ошибка при генерации:", e)
        return jsonify({"error": str(e)}), 500


# === Отдача файлов ===
@app.route("/data/<path:filename>")
def get_saved_file(filename):
    return send_from_directory(DATA_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
