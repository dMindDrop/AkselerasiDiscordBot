import json
import psycopg2
import os

# Establish a connection to the PostgreSQL database
DATABASE_URL = os.environ['DATABASE_URL']  # Replace with your actual DATABASE_URL
conn = psycopg2.connect(DATABASE_URL)

# Create a cursor using the connection
cur = conn.cursor()

# Create the table if it doesn't exist
create_table_query = """
CREATE TABLE IF NOT EXISTS ppl_classes (
    index SERIAL PRIMARY KEY,
    Class_ID TEXT,
    Teacher_ID TEXT,
    Student_Name TEXT,
    Student_ID TEXT,
    Treatment_Group TEXT
);
"""
cur.execute(create_table_query)
conn.commit()

# Importing data from JSON
json_file_path = 'classes.json'  # Replace with your actual JSON file path
with open(json_file_path, 'r') as f:
    json_data = json.load(f)

    for class_id, class_data in json_data.items():
        teacher_id = class_data['teacher_ID']
        students = class_data['students']

        for student in students:
            student_name = student['student_name']
            student_id = student['student_id']

            # Prepare the SQL query and values
            insert_query = """
            INSERT INTO ppl_classes (Class_ID, Teacher_ID, Student_Name, Student_ID)
            VALUES (%s, %s, %s, %s);
            """
            values = (class_id, teacher_id, student_name, student_id)
            cur.execute(insert_query, values)

# Update Treatment_Group based on Teacher_ID
update_core_query = """
UPDATE ppl_classes
SET Treatment_Group = 'CORE'
WHERE Teacher_ID LIKE '22000%';
"""
cur.execute(update_core_query)
core_updated_count = cur.rowcount
print(f"{core_updated_count} rows updated with CORE in Treatment_Group.")

update_pilot_query = """
UPDATE ppl_classes
SET Treatment_Group = 'PILOT'
WHERE Teacher_ID LIKE '88%';
"""
cur.execute(update_pilot_query)
pilot_updated_count = cur.rowcount
print(f"{pilot_updated_count} rows updated with PILOT in Treatment_Group.")

# Commit changes
conn.commit()

# Fetch and display the first 10 entries
cur.execute("SELECT * FROM ppl_classes LIMIT 10;")
rows = cur.fetchall()
print("First 10 entries:")
for row in rows:
    print(row)

# Close the cursor and connection
cur.close()
conn.close()

# Display success message
print("Data successfully imported and updated in ppl_classes.")
