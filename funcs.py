import random
import sqlite3
def shuffled(arr):
    random.shuffle(arr)
    return arr

def db_request_fetchone(database, request, arguments):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(request, arguments)
    response = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return response

def db_request_fetchall(database, request, arguments):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(request, arguments)
    response = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()
    return response