from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import sqlite3
import requests
import base64
import json
from dotenv import load_dotenv
import os
import uuid

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
app = Flask(__name__)

def database_con(query):
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    return cur.execute(query)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from PIL import Image
import os

from PIL import Image, ImageOps
import os

def save_recipe_image(uploaded_file, output_path, max_size=800):
    """Process with correct orientation."""
    img = Image.open(uploaded_file)
    
    # Fix orientation FIRST
    img = ImageOps.exif_transpose(img)
    
    # Convert if needed (after rotation)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    # Resize & save
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    img.save(output_path, 'JPEG', quality=85, optimize=True, subsampling=0)




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
    cur.execute("CREATE TABLE meal_plans (" \
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

@app.route("/save_ai_recipe", methods=['POST'])
def save_ai_recipe():
    name = request.form['recipe_name']
    location = request.form['recipe_location']
    page = request.form['page_number']
    instructions = request.form['instructions']
    ingredients = request.form['ingredients']
    difficulty = request.form['difficulty']
    con = sqlite3.connect("database.db")
    cur = con.cursor()

    error_text = ""
    if name == "" or ingredients == "" or location == "":
        error_text = "Error: missing required field!" 

    photo = request.files.get('recipe_photo')
    if photo and photo.filename:  # Real file check
        safe_name = secure_filename(photo.filename)  
        # 2. Add unique ID BEFORE
        unique_id = str(uuid.uuid4()).replace('-', '')[:8]
        filename = f"{unique_id}_{safe_name}"  # "a1b2c3d4_recipe.jpg"
        image_filename = filename


        
        save_recipe_image(photo,f"static/recipe_images/{filename}")

    else:
        image_filename = None  # Or default image
    
    if error_text != "":
         return jsonify({"ok": False, "error": error_text})

    
    cur.execute("INSERT INTO recipes (name,location,page_nu,instructions,difficulty,photo_path) VALUES (?,?,?,?,?,?)" ,(name, location, page,instructions,difficulty,image_filename))
    
    recipe_id = cur.lastrowid
    ingredients_strings = ingredients.split(",")
    ingredients_list = []
    
    for item in ingredients_strings:
        
        if len(item.strip()) > 0:
            this_ingredient = (item.strip(), recipe_id)
            ingredients_list.append(this_ingredient)
    
    print(ingredients_list)
       
    cur.executemany("INSERT INTO ingredients (name,recipe_id) VALUES (?,?)" , ingredients_list)

    con.commit()
    con.close()
    return jsonify({"ok": True, "success": "Recipe added succesfully!"})

@app.route("/get_recipes", methods=['POST'])
def get_recipes():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM recipes ORDER BY id")
    response = cur.fetchall()
    con.close()
    return response

@app.route("/search_recipes")
def search_recipes():
    search_term = request.args.get('q', '').strip()
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM recipes WHERE name LIKE ? OR tags LIKE ?", (f'%{search_term}%',)*2)
    response = cur.fetchall()
    con.close()
    return response

@app.route("/get_recipe_overview/<recipe_id>", methods=['GET']) 
def get_recipe_overview(recipe_id):
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    cur.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    row = cur.fetchone()
    
    con.close()
    
    if row:
        return jsonify(dict(row)) 
    else:
        return jsonify({"error": "Recipe not found"}), 404

@app.route("/save_recipe_day_change/", methods=['POST'])
def save_recipe_day_change():
    day = request.form['dayToChange']
    newRecipe = request.form['newRecipe']
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("UPDATE meal_plans SET "+day+" = ? WHERE current_plan = 1", (newRecipe,))
    con.commit()
    con.close()

    return {"success" : "ok"}

@app.route("/get_menu", methods=['POST'])
def get_menu():
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    # Get the current plan
    days = ['monday_recipe_id', 'tuesday_recipe_id', 'wednesday_recipe_id',
            'thursday_recipe_id', 'friday_recipe_id', 'saturday_recipe_id', 'sunday_recipe_id']
    
    cur.execute("SELECT " + ", ".join(days) + " FROM meal_plans WHERE current_plan = 1")
    plan = cur.fetchone()
    
    if not plan:
        con.close()
        return jsonify({"ok": False, "error": "no plan found"})
    
    # Simple loop like your original, but builds ordered array
    menu = []
    for day in days:
        recipe_id = plan[day]
        if recipe_id:
            cur.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
            recipe = cur.fetchone()
            if recipe:
                menu.append({day: dict(recipe)})
    
    con.close()
   
    return jsonify({"ok": True, "menu": menu})


@app.route("/gen_new_meal_plan", methods=['POST'])
def gen_new_plan():
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    if request.form["planType"] == "auto":
        cur.execute("SELECT * FROM recipes ORDER BY RANDOM() LIMIT 7")
        rows = cur.fetchall()
        
        # Convert Row → dicts for JSON
        recipes = [dict(row) for row in rows]
        
        con.close()
        return jsonify(recipes)
    #else take the params provided and apply them to each days recipe selection

    con.close()
    return "something"


@app.route("/save_new_plan", methods=['POST'])
def save_new_plan():
    print(request.form['monday_recipe_id'])
    days = ['monday_recipe_id', 'tuesday_recipe_id', 'wednesday_recipe_id',
            'thursday_recipe_id', 'friday_recipe_id', 'saturday_recipe_id', 'sunday_recipe_id']
    columns = ','.join(days)
    recipe_ids = []
    for day in request.form:
        recipe_ids.append(request.form[day])
    recipes_to_enter = ','.join(recipe_ids)    
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("UPDATE meal_plans SET current_plan = 0 WHERE current_plan = 1")
    cur.execute("INSERT INTO meal_plans ("+columns+", current_plan) VALUES ("+recipes_to_enter+", 1)")
    con.commit()
    con.close()

    return {"success" : "ok"}

@app.route("/del_recipe/<recipe_id>", methods=['POST'])
def delete_recipe(recipe_id):
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    cur.execute("DELETE FROM ingredients WHERE recipe_id = ?",(recipe_id,))
    con.commit()
    con.close()
    return "deleted"

@app.route("/view_recipe/<recipe_id>", methods=['GET'])
def view_recipe(recipe_id):
    print(recipe_id)
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
    recipe_response = cur.fetchone()
    cur.execute("SELECT * FROM ingredients WHERE recipe_id = ?", (recipe_id,))
    ingredients_response = cur.fetchall()
    con.close()
    return render_template("view_recipe.html", recipe_details = recipe_response,recipe_ingredients = ingredients_response)



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
                    When describing the recipe instructions use a full stop to seperate the different steps. DO NOT use any commas. String will be split using the full stop as a serperator. 
                    Any temperatures should be in celcius as i live in the UK. 
                    Generate common sense tags for the recipe using context like included ingredients, vegetarian or meat, batch cook or single meal etc.
                    Output will be read by python program:
                    {
                      "recipe_name": "",
                      "ingredients": ["item qty unit"],
                      "instructions": ["step 1", "step 2"],
                      "servings": "",
                      "prep_time": "",
                      "difficulty": "easy/medium/hard",
                      "tags" : ["#related_tag #related_tag"],
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