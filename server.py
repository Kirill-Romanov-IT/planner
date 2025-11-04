from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import json
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import os

# === Инициализация ===
load_dotenv()
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Настройка OpenRouter клиента
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


# === Генерация плана с OpenRouter ===
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

        # Отправляем на OpenRouter
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": os.getenv("SITE_URL"),
                "X-Title": os.getenv("SITE_TITLE"),
            },
            model="google/gemma-3-27b-it:free",
            messages=[{"role": "user", "content": user_prompt}],
        )

        result = completion.choices[0].message.content

        # Сохраняем как Markdown
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = DATA_DIR / f"plan_{timestamp}.md"
        out_file.write_text(result, encoding="utf-8")

        print(f"✅ Plan generated: {out_file}")
        return jsonify({"status": "ok", "file": out_file.name})
    except Exception as e:
        print("❌ Ошибка при генерации:", e)
        return jsonify({"error": str(e)}), 500


# === Отдача файлов ===
@app.route("/data/<path:filename>")
def get_saved_file(filename):
    return send_from_directory(DATA_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
