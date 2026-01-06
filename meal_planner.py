from flask import Flask, render_template, request, jsonify
import sqlite3
import requests
import base64
import json
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
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
    "location TEXT," \
    "page_nu INTEGER," \
    "instructions JSON," \
    "photo_path TEXT,"\
    "difficulty TEXT)")
    cur.execute("CREATE TABLE ingredients (" \
    "id INTEGER PRIMARY KEY AUTOINCREMENT," \
    "name TEXT," \
    "recipe_id INTEGER)")
    cur.execute("CREATE TABLE meal_plan (" \
    "id INTEGER PRIMARY KEY AUTOINCREMENT," \
    "monday_recipe_id INTEGER," \
    "tuesday_recipe_id INTEGER," \
    "wednesday_recipe_id INTEGER," \
    "thursday_recipe_id INTEGER," \
    "friday_recipe_id INTEGER," \
    "saturday_recipe_id INTEGER," \
    "current_plan BOOL," \
    "sunday_recipe_id INTEGER)")
    con.commit()
    con.close()
    return "database built"

@app.route("/add_recipe")
def add_recipe():
    return render_template("add_recipe.html")

@app.route("/recipes")
def recipes():
    return render_template("recipes.html")

@app.route("/ai_recipe_add")
def ai_recipe_add():
    return render_template("ai_recipe_add.html")


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

@app.route("/save_ai_recipe", methods=['POST'])
def save_ai_recipe():
    rec_data = request.get_json()
    con = sqlite3.connect("database.db")
    cur = con.cursor()

    error_text = ""
    if rec_data["recipe_name"] == "" or rec_data['ingredients'] == "" or rec_data['location'] == "":
        error_text = "Error: missing required field!" 

    if error_text != "":
         return jsonify({"ok": False, "error": error_text})

    
    cur.execute("INSERT INTO recipes (name,location,page_nu,instructions,difficulty,photo_path) VALUES (?,?,?,?,?,?)" ,(rec_data['recipe_name'], rec_data['location'], rec_data['page_number'],rec_data['instructions'],rec_data['difficulty'],rec_data['recipe_photo']))
    
    recipe_id = cur.lastrowid
    ingredients_strings = rec_data['ingredients'].split(",")
    ingredients_list = []
    
    for item in ingredients_strings:
        
        if len(item.strip()) > 0:
            this_ingredient = (item.strip(), recipe_id)
            ingredients_list.append(this_ingredient)
    
    print(ingredients_list)
       
    cur.executemany("INSERT INTO ingredients (name,recipe_id) VALUES (?,?)" , ingredients_list)

    con.commit()
    con.close()
    return jsonify({"ok": True})

@app.route("/get_recipes", methods=['POST'])
def get_recipes():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM recipes ORDER BY id")
    response = cur.fetchall()
    con.close()
    return response


@app.route("/del_recipe/<recipe_id>", methods=['POST'])
def delete_recipe(recipe_id):
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("DELETE FROM recipes WHERE id = ?", (recipe_id))
    cur.execute("DELETE FROM ingredients WHERE recipe_id = ?",(recipe_id))
    con.commit()
    con.close()
    return "deleted"


@app.route('/analyze-recipe', methods=['POST'])
def analyze_recipe():
    if 'image' not in request.files:
        return jsonify({'error': 'Missing image file'}), 400
    
    # Read + encode uploaded image
    img_data = request.files['image'].read()
    img_b64 = base64.b64encode(img_data).decode()
    
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': 'gpt-4o-mini',
        'messages': [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': '''
                    Analyze this recipe photo. Extract as RAW JSON only with no formatting. 
                    When describing the ingredients do not use commas within a single ingredient description as the ingredients will be split using comma as a seperator. 
                    Any temperatures should be in celcius as i live in the UK. 
                    Output will be read by python program:
                    {
                      "recipe_name": "",
                      "ingredients": ["item qty unit"],
                      "instructions": ["step 1", "step 2"],
                      "servings": "",
                      "prep_time": "",
                      "difficulty": "easy/medium/hard",
                      "page_number": ""
                 
                    }
                    Output ONLY valid JSON. 
                '''},
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}}
            ]
        }],
        'max_tokens': 800,
        'temperature': 0.1
    }
    
    response = requests.post('https://api.openai.com/v1/chat/completions', 
                           headers=headers, json=payload)
    
    if response.status_code != 200:
        return jsonify({'error': response.json()}), 500
    
    result = response.json()['choices'][0]['message']['content']
    return jsonify({'recipe': result})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=5002)