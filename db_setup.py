import sqlite3


def create_database():
    conn = sqlite3.connect('exchange_rates.db')
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exchange_rates (
            date TEXT,
            currency_code TEXT,
            currency_name TEXT,
            rate REAL
        );
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_database()
