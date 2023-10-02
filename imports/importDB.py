import csv
import psycopg2.pool
import psycopg2.extras
import os

# Create a connection pool
pool = psycopg2.pool.SimpleConnectionPool(0, 80, os.environ['DATABASE_URL'])

# Get a connection from the pool
conn = pool.getconn()

# Create a cursor using the connection
cur = conn.cursor()

# Read the CSV file and determine column names
csv_file_path = 'akselerasi-All-IDs_v3.csv'
with open(csv_file_path, 'r') as f:
    reader = csv.reader(f)
    columns = next(reader)
    sanitized_columns = [col.replace(" ", "_") for col in columns]

    # Create the table if it doesn't exist
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS ppl_classes (
        index SERIAL PRIMARY KEY,
        {', '.join([f'{col} TEXT' for col in sanitized_columns])}
    )
    """
    cur.execute(create_table_query)
    conn.commit()

    # Prepare for batch insert
    batch_size = 100
    batch_values = []

    for row in reader:
        values = [str(value) for value in row]
        batch_values.append(values)

        if len(batch_values) >= batch_size:
            # Modify this query to include ON CONFLICT clause if you have a unique constraint
            psycopg2.extras.execute_values(cur, f"""
            INSERT INTO ppl_classes ({', '.join(sanitized_columns)})
            VALUES %s
            ON CONFLICT (student_id) DO NOTHING
            """, batch_values)
            print(f"{len(batch_values)} rows inserted.")
            batch_values = []

    # Insert any remaining rows
    if batch_values:
        # Modify this query to include ON CONFLICT clause if you have a unique constraint
        psycopg2.extras.execute_values(cur, f"""
        INSERT INTO ppl_classes ({', '.join(sanitized_columns)})
        VALUES %s
        ON CONFLICT (student_id) DO NOTHING
        """, batch_values)
        print(f"{len(batch_values)} rows inserted.")

# Commit changes
conn.commit()

# Display success message
print("Data successfully imported into ppl_classes.")

# Fetch and display the first 5 entries
cur.execute("SELECT * FROM ppl_classes LIMIT 5;")
rows = cur.fetchall()
print("First 5 entries:")
for row in rows:
    print(row)

# Close the cursor and return the connection to the pool
cur.close()
pool.putconn(conn)

# Close the pool when done
pool.closeall()
