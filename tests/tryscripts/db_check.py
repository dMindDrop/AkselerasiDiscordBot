from replit import db

# Loop through the keys stored in the database to get access to the values of those keys
for key in db.keys():
    print(f"{key}: {db.get(key)}")