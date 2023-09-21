# tests/student_manager.py
import os
import json
from .config import CLASSES_JSON_FILE_PATH, STUDENT_DATA_FOLDER_PATH

def get_students(class_name):
    with open(CLASSES_JSON_FILE_PATH, 'r') as file:
        classes_data = json.load(file)
        return classes_data[class_name]['students']

def get_student_data(student_file_path):
    with open(student_file_path, 'r') as file:
        return json.load(file)

def save_student_data(student_file_path, student_data):
    with open(student_file_path, 'w') as file:
        json.dump(student_data, file)

def create_student_file(student_file_path, student_data):
    os.makedirs(os.path.dirname(student_file_path), exist_ok=True)
    with open(student_file_path, 'w') as file:
        json.dump(student_data, file)
