import sqlite3
import json
import os

def check_db(db_path):
    if not os.path.exists(db_path):
        print(f"File {db_path} not found.")
        return
    
    print(f"Checking {db_path}...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = c.fetchall()
        print(f"Tables: {tables}")
        
        for table in tables:
            t_name = table[0]
            print(f"\nLast 3 entries from {t_name}:")
            try:
                c.execute(f"SELECT * FROM {t_name} ORDER BY rowid DESC LIMIT 3")
                rows = c.fetchall()
                for row in rows:
                    print(row)
            except Exception as e:
                print(f"Error reading {t_name}: {e}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db("archemidas.db")
    check_db("backend/archemidas.db")
