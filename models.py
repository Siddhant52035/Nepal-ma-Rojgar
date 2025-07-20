import sqlite3
from sqlite3 import Error
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

def create_connection():
    """Create a database connection to SQLite database"""
    conn = None
    try:
        conn = sqlite3.connect('job_portal.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Error as e:
        print(e)
    return conn

def initialize_database():
    """Initialize the database with tables"""
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
            
            # Create applications table with CV and status
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    cover_letter TEXT,
                    cv_filename TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'reviewed', 'accepted', 'rejected')),
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
        print("Error! Cannot create database connection.")

class User:
    def __init__(self, id, username, email, password, user_type, created_at=None):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.user_type = user_type
        self.created_at = created_at
    
    @staticmethod
    def create(username, email, password, user_type):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                hashed_password = generate_password_hash(password)
                cursor.execute(
                    "INSERT INTO users (username, email, password, user_type) VALUES (?, ?, ?, ?)",
                    (username, email, hashed_password, user_type)
                )
                conn.commit()
                return cursor.lastrowid
            except Exception as e:
                print(f"Error creating user: {e}")
                return None
            finally:
                conn.close()
        return None
    
    @staticmethod
    def get_by_username(username):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                user_data = cursor.fetchone()
                if user_data:
                    return User(**user_data)
                return None
            except Exception as e:
                print(f"Error fetching user: {e}")
                return None
            finally:
                conn.close()
        return None
    
    @staticmethod
    def get_by_id(user_id):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                user_data = cursor.fetchone()
                if user_data:
                    return User(**user_data)
                return None
            except Exception as e:
                print(f"Error fetching user: {e}")
                return None
            finally:
                conn.close()
        return None
    
    def verify_password(self, password):
        return check_password_hash(self.password, password)

class Job:
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.title = kwargs.get('title')
        self.description = kwargs.get('description')
        self.company = kwargs.get('company')
        self.location = kwargs.get('location')
        self.salary = kwargs.get('salary')
        self.posted_by = kwargs.get('posted_by')
        self.created_at = kwargs.get('created_at')
        self.application_count = kwargs.get('application_count', 0)
    
    @staticmethod
    def create(title, description, company, location, salary, posted_by):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO jobs (title, description, company, location, salary, posted_by) VALUES (?, ?, ?, ?, ?, ?)",
                    (title, description, company, location, salary, posted_by)
                )
                conn.commit()
                return cursor.lastrowid
            except Exception as e:
                print(f"Error creating job: {e}")
                return None
            finally:
                conn.close()
        return None
    
    @staticmethod
    def get_all():
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
                return [Job(**row) for row in cursor.fetchall()]
            except Exception as e:
                print(f"Error fetching jobs: {e}")
                return []
            finally:
                conn.close()
        return []
    
    @staticmethod
    def get_by_id(job_id):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
                job_data = cursor.fetchone()
                if job_data:
                    return Job(**job_data)
                return None
            except Exception as e:
                print(f"Error fetching job: {e}")
                return None
            finally:
                conn.close()
        return None
    
    @staticmethod
    def get_by_employer(employer_id):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT j.*, COUNT(a.id) as application_count
                    FROM jobs j
                    LEFT JOIN applications a ON j.id = a.job_id
                    WHERE j.posted_by = ?
                    GROUP BY j.id
                    ORDER BY j.created_at DESC
                """, (employer_id,))
                return [Job(**row) for row in cursor.fetchall()]
            except Exception as e:
                print(f"Error fetching employer jobs: {e}")
                return []
            finally:
                conn.close()
        return []

class Application:
    @staticmethod
    def create(job_id, user_id, cover_letter, cv_filename=None):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO applications (job_id, user_id, cover_letter, cv_filename) VALUES (?, ?, ?, ?)",
                    (job_id, user_id, cover_letter, cv_filename)
                )
                conn.commit()
                return cursor.lastrowid
            except Exception as e:
                print(f"Error creating application: {e}")
                return None
            finally:
                conn.close()
        return None
    
    @staticmethod
    def get_by_job(job_id):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT a.*, u.username 
                    FROM applications a 
                    JOIN users u ON a.user_id = u.id 
                    WHERE a.job_id = ?
                """, (job_id,))
                return cursor.fetchall()
            except Exception as e:
                print(f"Error fetching applications: {e}")
                return []
            finally:
                conn.close()
        return []
    
    @staticmethod
    def get_by_user(user_id):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        a.*, 
                        j.title, 
                        j.company,
                        j.id as job_id
                    FROM applications a 
                    JOIN jobs j ON a.job_id = j.id 
                    WHERE a.user_id = ?
                    ORDER BY a.applied_at DESC
                """, (user_id,))
                return [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                print(f"Error fetching user applications: {e}")
                return []
            finally:
                conn.close()
        return []
    
    @staticmethod
    def get_by_id(app_id):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT a.*, u.username, j.title as job_title, j.company
                    FROM applications a
                    JOIN users u ON a.user_id = u.id
                    JOIN jobs j ON a.job_id = j.id
                    WHERE a.id = ?
                """, (app_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
            except Exception as e:
                print(f"Error getting application: {e}")
                return None
            finally:
                conn.close()
        return None
    
    @staticmethod
    def update_status(app_id, status):
        conn = create_connection()
        if conn is not None:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE applications SET status = ? WHERE id = ?",
                    (status, app_id)
                )
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"Error updating application status: {e}")
                return False
            finally:
                conn.close()
        return False