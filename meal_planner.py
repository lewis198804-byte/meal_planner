from flask import Flask, render_template, request
import sqlite3
import pdfplumber

app = Flask(__name__)

def database_con(query):
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    return cur.execute(query)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/database_build")
def build_database():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE recipes (" \
    "id INTEGER PRIMARY KEY AUTOINCREMENT," \
    "name TEXT," \
    "ingredients TEXT,"\
    "location TEXT," \
    "page_nu INTEGER," \
    "rating INTEGER)")
    cur.execute("CREATE TABLE ingredients (" \
    "id INTEGER PRIMARY KEY AUTOINCREMENT," \
    "name TEXT," \
    "recipe_id INTEGER)")
    con.commit()
    con.close()
    return "database built"

@app.route("/add_recipe")
def add_recipe():
    return render_template("add_recipe.html")


@app.route("/recipe_save", methods=["POST"])
def recipe_save():
    formData = request.form
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("INSERT INTO recipes (name,location,page_nu,rating) VALUES (?,?,?,?)" ,(formData['recipe_name'], formData['where'], formData['page_number'],formData['rating']))
    recipe_id = cur.lastrowid
    print(recipe_id)
    ingredients_strings = formData['ingredients'].split(",")
    ingredients_list = []
    
    for item in ingredients_strings:
        
        if len(item.strip()) > 0:
            this_ingredient = (item.strip(), recipe_id)
            ingredients_list.append(this_ingredient)
    
    print(ingredients_list)
       
    cur.executemany("INSERT INTO ingredients (name,recipe_id) VALUES (?,?)" , ingredients_list)

    con.commit()
    con.close()
    return render_template("recipe_save.html",recipeName = formData['recipe_name'])



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=5002)