import sqlite3
conn = sqlite3.connect('../data/sqlite/metadata.db')
cursor = conn.cursor()
cursor.execute("SELECT id, filename, status FROM images")
for row in cursor.fetchall():
    print(row)
