from flask import Flask, jsonify, request
import pandas as pd
import sqlite3
import requests
from configparser import ConfigParser

app = Flask(__name__)

config = ConfigParser()
config.read('config.ini')


def fetch_exchange_rates(start_date, end_date):
    date_range = pd.date_range(start_date, end_date)
    base_url = "https://www.cnb.cz/en/financial_markets/foreign_exchange_market/exchange_rate_fixing/daily.txt?date="

    for date in date_range:
        date_str = date.strftime("%Y-%m-%d")
        url = base_url + date.strftime("%d.%m.%Y")
        response = requests.get(url)
        response.encoding = 'utf-8'

        if response.status_code == 200:
            lines = response.text.split('\n')
            currency_data = [line.split('|') for line in lines[2:-1]]

            with sqlite3.connect('exchange_rates.db') as conn:
                for currency in currency_data:
                    conn.execute("INSERT INTO exchange_rates (date, currency_code, currency_name, rate) VALUES (?, ?, ?, ?)", (
                        date_str, currency[3], currency[1], currency[4]))
                conn.commit()
        else:
            print(
                f"Error fetching data for date {date_str}: {response.status_code}")


def save_today_rates():
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    fetch_exchange_rates(today, today)
    print(f"Exchange rates saved for {today}")



@app.route('/report', methods=['GET'])
def report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    selected_currencies = config.get(
        'currencies', 'selected_currencies').split(',')

    with sqlite3.connect('exchange_rates.db') as conn:
        cursor = conn.cursor()

        results = []
        for currency in selected_currencies:
            cursor.execute("""
                SELECT MIN(rate), MAX(rate), AVG(rate) FROM exchange_rates
                WHERE date >= ? AND date <= ? AND currency_code = ?""", (start_date, end_date, currency))

            min_rate, max_rate, avg_rate = cursor.fetchone()

            if min_rate is None or max_rate is None or avg_rate is None:
                results.append({
                    'currency': currency,
                    'error': 'No data available for the specified date range'
                })
            else:
                results.append({
                    'currency': currency,
                    'min_rate': float(min_rate),
                    'max_rate': float(max_rate),
                    'avg_rate': float(avg_rate)
                })

    return jsonify(results)

# http://127.0.0.1:5000/report?start_date=2023-04-01&end_date=2023-04-21



@app.route('/custom_query', methods=['GET'])
def custom_query():
    query = request.args.get('query')
    params = request.args.get('params', '')

    # Разделите параметры запроса на отдельные элементы
    params = params.split(',')

    with sqlite3.connect('exchange_rates.db') as conn:
        cursor = conn.cursor()

        try:
            # Выполните пользовательский запрос с использованием безопасных параметров
            cursor.execute(query, tuple(params))
            result = cursor.fetchall()

            # Верните результат в виде JSON
            return jsonify(result)

        except sqlite3.Error as e:
            return jsonify({'error': str(e)})

# http://127.0.0.1:5000/custom_query?query=SELECT%20*%20FROM%20exchange_rates%20WHERE%20currency_code%20=%20%3F%20AND%20date%20%3E%3D%20%3F%20AND%20date%20%3C%3D%20%3F&params=USD,2023-04-01,2023-04-21


@app.route('/fetch_data', methods=['GET'])
def fetch_data_api():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not start_date or not end_date:
        return jsonify({'error': 'Both start_date and end_date are required.'}), 400

    fetch_exchange_rates(start_date, end_date)
    return jsonify({'message': 'Data fetched and saved to the database.'})

# http://127.0.0.1:5000/fetch_data?start_date=2023-04-01&end_date=2023-04-21


@app.route('/save_today_rates', methods=['POST'])
def save_today_rates_api():
    save_today_rates()
    return jsonify({'message': 'Current exchange rates saved to the database.'})

		

if __name__ == "__main__":
    app.run()
