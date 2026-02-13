import sqlite3

def create_database():
    conn = sqlite3.connect("./database.db")
    conn.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY,
                 email TEXT,
                 password TEXT,
                 FOREIGN KEY (id) REFERENCES ratings (id)) """)
    
    conn.execute("""CREATE TABLE IF NOT EXISTS foods (id INTEGER PRIMARY KEY,
                 name TEXT,
                 country TEXT,
                 image TEXT,
                 meal_id TEXT,
                 FOREIGN KEY (id) REFERENCES ratings (id)) """)
    
    conn.execute("""CREATE TABLE IF NOT EXISTS ratings (id INTEGER PRIMARY KEY,
                 user_id INTEGER,
                 food_id INTEGER,
                 rating TEXT)""")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_database()