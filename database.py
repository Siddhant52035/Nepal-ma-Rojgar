import sqlite3
from sqlite3 import Error

def create_connection():
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect('job_portal.db')
        return conn
    except Error as e:
        print(e)
    
    return conn

def initialize_database():
    """Initialize the database with required tables"""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    user_type TEXT NOT NULL CHECK(user_type IN ('employer', 'job_seeker')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    salary TEXT,
                    posted_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (posted_by) REFERENCES users (id)
                )
            """)
            
            # Create applications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    cover_letter TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (job_id) REFERENCES jobs (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            conn.commit()
            print("Database initialized successfully")
        except Error as e:
            print(f"Error initializing database: {e}")
        finally:
            conn.close()
    else:
        print("Error! Cannot create the database connection.")