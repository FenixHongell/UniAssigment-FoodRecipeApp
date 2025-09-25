import sqlite3

def create_connection():
    db = sqlite3.connect("./database.db")
    return db

def close_connection(db):
    db.close()

def execute_cmd(cmd, params=[]):
    db = create_connection()
    result = db.execute(cmd, params)
    db.commit()
    close_connection(db)
    return result

def run_query(cmd, params=[], no_factory=False):
    db = create_connection()
    if no_factory:
        db.row_factory = None
    result = db.execute(cmd, params).fetchall()
    close_connection(db)
    return result
