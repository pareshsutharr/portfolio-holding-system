import psycopg2

# PostgreSQL connection
conn = psycopg2.connect(
    host="localhost",
    database="portfolio_analyzer",
    user="rahildoshi",
    password="rahildoshi"
)

cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS stocks_master (
    isin VARCHAR(20) PRIMARY KEY,
    sector VARCHAR(255)
);
""")

conn.commit()

print("stocks_master table created successfully.")

cursor.close()
conn.close()