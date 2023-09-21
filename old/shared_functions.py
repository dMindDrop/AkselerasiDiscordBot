import psycopg2

# Function to get authenticated class
def get_authenticated_class(conn, staff_id):
    cur = conn.cursor()
    query = "SELECT class_id FROM ppl_classes WHERE teacher_id = %s OR principal_id = %s;"
    cur.execute(query, (staff_id, staff_id))
    result = cur.fetchone()
    cur.close()
    return result[0] if result else None


