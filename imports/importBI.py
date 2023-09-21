import os
import csv
import psycopg2

# Initialize database connection
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

# Create a cursor
cur = conn.cursor()

# Create the test_bi_questions table
cur.execute('''
CREATE TABLE IF NOT EXISTS test_bi_questions (
    index SERIAL PRIMARY KEY,
    sequence INTEGER,
    task TEXT,
    topic TEXT,
    A TEXT,
    B TEXT,
    C TEXT,
    D TEXT,
    correct TEXT
);
''')

# Commit the table creation
conn.commit()

# Read the CSV file and insert data
with open('modified_bi.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cur.execute("INSERT INTO test_bi_questions (sequence, task, topic, A, B, C, D, correct) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (row['sequence'], row['task'], row['topic'], row['A'], row['B'], row['C'], row['D'], row['right']))

# Commit the data insertion
conn.commit()

# Close the cursor and connection
cur.close()
conn.close()
