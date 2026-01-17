from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import os

app = Flask(__name__)

app.secret_key = 'secret-key'

DB_PATH = 'weather.db'


# -------------------------
# DB初期化
# -------------------------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY,
                api_key TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT,
                temperature REAL,
                description TEXT,
                fetched_at TEXT
            )
        """)

        conn.commit()


# -------------------------
# APIキー取得
# -------------------------
def get_api_key():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute("SELECT api_key FROM settings WHERE id=1")

        row = c.fetchone()

        return row[0] if row else None


# -------------------------
# ルート - トップ
# -------------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    weather_data = None

    if request.method == 'POST':
        city = request.form['city']

        api_key = get_api_key()

        if not api_key:
            flash('APIキーが設定されていません', 'danger')

            return redirect(url_for('settings'))

        url = 'https://api.openweathermap.org/data/2.5/weather'

        params = {
            'q': city,
            'appid': api_key,
            'units': 'metric',
            'lang': 'ja'
        }

        res = requests.get(url, params=params)

        if res.status_code != 200:
            flash('天気情報の取得に失敗しました', 'danger')

            return redirect(url_for('index'))

        data = res.json()

        weather_data = {
            'city': city,
            'temp': data['main']['temp'],
            'desc': data['weather'][0]['description']
        }

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()

            c.execute("""
                INSERT INTO weather (city, temperature, description, fetched_at)
                VALUES (?, ?, ?, ?)
            """, (
                city,
                weather_data['temp'],
                weather_data['desc'],
                datetime.now(ZoneInfo('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
            ))

            conn.commit()

    return render_template('index.html', weather=weather_data)


# -------------------------
# 履歴表示
# -------------------------
@app.route('/history')
def history():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        c.execute("SELECT city, temperature, description, fetched_at FROM weather ORDER BY id DESC")

        rows = c.fetchall()

    return render_template('history.html', rows=rows)


# -------------------------
# 設定画面
# -------------------------
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        api_key = request.form['api_key']

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()

            c.execute("DELETE FROM settings")
            c.execute("INSERT INTO settings (id, api_key) VALUES (1, ?)", (api_key,))

            conn.commit()

        flash('APIキーを保存しました', 'success')

        return redirect(url_for('settings'))

    return render_template('settings.html', api_key=get_api_key())


# -------------------------
# DBリセット
# -------------------------
@app.route('/reset')
def reset_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    init_db()

    flash('データベースをリセットしました', 'success')

    return redirect(url_for('index'))


# -------------------------
# 起動
# -------------------------
if __name__ == '__main__':
    init_db()

    app.run(host='0.0.0.0', port=5000, debug=True)