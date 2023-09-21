import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database connection parameters
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Connect to the database
conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

# Create a cursor object
cur = conn.cursor()

# SQL query to insert data into admin_qrcode table
insert_query = """
INSERT INTO admin_qrcode (index, timestamp, title, description, image, link)
VALUES (%s, %s, %s, %s, %s, %s);
"""

# Metadata and file paths
index = 1
timestamp = "2022-01-01 12:34:56"
title = "Training"
description = "points for training and testing purposes"

# Get the current working directory
current_directory = os.getcwd()

# Construct the full path for the two files
image_full_path = os.path.join(current_directory, "qr", "QR_Training.png")
link_full_path = os.path.join(current_directory, "qr", "LINK_Training.txt")

# Read image and link content
with open(image_full_path, "rb") as img_file, open(link_full_path, "r") as link_file:
    image_data = img_file.read()
    link_data = link_file.read().strip()

# Execute the query
cur.execute(insert_query, (index, timestamp, title, description, image_data, link_data))

# Commit the changes
conn.commit()

# Close the cursor and connection
cur.close()
conn.close()
