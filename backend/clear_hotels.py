import sqlite3
import os
DB_PATH = os.path.join(os.path.dirname(__file__), 'auth.db')
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute('DELETE FROM hotels')
conn.commit()
conn.close()
print('✓ Cleared hotels table')
