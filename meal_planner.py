from flask import Flask
import sqlite3
import pdfplumber

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/database_build")
def build_database():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE recipes (id,name,page_nu,ingredients,rating)")
    con.commit()
    con.close()
    return "database built"