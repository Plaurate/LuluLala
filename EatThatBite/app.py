# app.py  (updated)
from flask import Flask, render_template, request, redirect, session
import sqlite3
import requests
import math

app = Flask(__name__)
app.secret_key = "lululalaland"


# Palīgfunkcijas

def valstis():
    # iegūst sarakstu ar visām šobrīd pieejamām valstīm
    url = "https://www.themealdb.com/api/json/v1/1/list.php?a=list"
    resp = requests.get(url)
    if resp.status_code != 200:
        raise Exception("API died, sorry yall")
    data = resp.json()
    
    countries = []
    for item in data["meals"]:
        countries.append(item["strArea"])
    
    return countries

# vienkārši pievieno linka beigās valsti kuru izvēlās ar dropdown
def switcharoo(x):
    return f"https://www.themealdb.com/api/json/v1/1/filter.php?a={x}"


def get_meals_by_country(country):
    # Iegūst api no izvēlētās valsts
    url = switcharoo(country)
    resp = requests.get(url)
    if resp.status_code != 200:
        return []
    data = resp.json()
    if data["meals"]:
        return data["meals"] 
    else:
        return []


def insert_meals_into_db(meals, country):
    # Ievieto ēdienu info no api tabulā. api tiek atjaunināts, informācija tiek papildināta un ja kāds ēdiens tiek izdzēsts no api, tas paliek datubāzē.
    conn = sqlite3.connect("./database.db")
    cur = conn.cursor()

    for meal in meals:
        name = meal["strMeal"]
        image = meal["strMealThumb"]
        meal_id = meal["idMeal"]

        cur.execute("SELECT id FROM foods WHERE meal_id=?", (meal_id,))
        exists = cur.fetchone()
        if not exists:
            cur.execute(
                "INSERT INTO foods (name, country, image, meal_id) VALUES (?, ?, ?, ?)",
                (name, country, image, meal_id)
            )

    conn.commit()
    conn.close()


# Izveido savienojumu, to atgriež (lai nebūtu visur copy paste ar šo daļu)
def _connect():
    conn = sqlite3.connect("./database.db")
    conn.row_factory = sqlite3.Row
    return conn


def get_personal_favorites(user_id):
    # Atgriež informāciju par mīļāko/iem ēdieniem
    conn = _connect()
    cur = conn.cursor()

    # Iegūst visus ratings ko lietotājs ir ieguvis
    cur.execute("""
        SELECT foods.id as food_id, foods.name, foods.image, CAST(ratings.rating AS INTEGER) as rating, foods.country
        FROM ratings
        JOIN foods ON ratings.food_id = foods.id
        WHERE ratings.user_id = ?
    """, (user_id,))
    rows = cur.fetchall()

    # Ja nav vērtējumu, atgriezt neko
    if not rows:
        conn.close()
        return [], None

    # atrod maksimālo rating
    ratings = [r['rating'] for r in rows]
    max_rating = max(ratings)

    # saraksts ar mīļākajiem ēdieniem, ar domu, ka tādi varētu būt vairāki
    favorite_foods = []
    for r in rows:
        if r['rating'] == max_rating:
            favorite_foods.append({
                "id": r["food_id"],
                "name": r["name"],
                "image": r["image"],
                "rating": r["rating"]
            })

    # Mīļākā valsts pēc augstākā vidējā rating
    cur.execute("""
        SELECT foods.country as country, AVG(CAST(ratings.rating AS FLOAT)) as avg_rating
        FROM ratings
        JOIN foods ON ratings.food_id = foods.id
        WHERE ratings.user_id = ?
        GROUP BY foods.country
    """, (user_id,))
    country_rows = cur.fetchall()

    favorite_country = []

    if country_rows:
        # augstākais vidējais
        avg_list = []
        for cr in country_rows:
            avg_list.append(cr['avg_rating'])

        best_avg = max(avg_list)
        # if there are multiple countries tied we will pick them all
        for cr in country_rows:
            if cr['avg_rating'] == best_avg:
                top_countries = [{"country": cr['country'], "avg": cr['avg_rating']}]
        # Atgriež sarakstu ar top valstīm
        favorite_country = top_countries

    conn.close()
    return favorite_foods, favorite_country

# Tieši tas pats bet pasaulei
def get_worldwide_favorites():

    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT foods.id as food_id, foods.name, foods.image, AVG(CAST(ratings.rating AS FLOAT)) as avg_rating
        FROM ratings
        JOIN foods ON ratings.food_id = foods.id
        GROUP BY foods.id
    """)
    food_avgs = cur.fetchall()

    if not food_avgs:
        conn.close()
        return [], []

    max_avg = max([f['avg_rating'] for f in food_avgs])

    favorite_foods = []
    for f in food_avgs:
        if f['avg_rating'] == max_avg:
            favorite_foods.append({
                "id": f["food_id"],
                "name": f["name"],
                "image": f["image"],
                "avg": f["avg_rating"]
            })

    cur.execute("""
        SELECT foods.country as country, AVG(CAST(ratings.rating AS FLOAT)) as avg_rating
        FROM ratings
        JOIN foods ON ratings.food_id = foods.id
        GROUP BY foods.country
    """)
    country_avgs = cur.fetchall()

    favorite_countries = []
    if country_avgs:
        max_country_avg = max([c['avg_rating'] for c in country_avgs])
        for c in country_avgs:
            if c['avg_rating'] == max_country_avg:
                favorite_countries.append({
                    "country": c["country"],
                    "avg": c["avg_rating"]
                })

    conn.close()
    return favorite_foods, favorite_countries


# Routes

# home sweet home
@app.route("/")
def home():
    return render_template("index.html")



# logošanās sistēma
@app.route("/submit", methods=["GET", "POST"])
def submit():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]


        # paķer tikai e-pastu, jo balstās uz e-pasta eksistēšanu
        if email and password:
            conn = sqlite3.connect("./database.db")
            cur = conn.cursor()
            cur.execute("SELECT id, password FROM users WHERE email=?", (email,))
            data = cur.fetchone()

            # ja nav e-pasta, tad izveido jaunu lietotaju
            if not data:
                cur.execute(
                    "INSERT INTO users (email, password) VALUES (?, ?)",
                    (email, password)
                )
                conn.commit()
                cur.execute("SELECT id FROM users WHERE email=?", (email,))
                user_id = cur.fetchone()[0]
                session["user_id"] = user_id

            # ja neatbilst parole eksistejosam epastam, izmet paziņojumu
            elif data[1] != password:
                conn.close()
                return render_template("index.html", error="Password is incorrect")
            # sūta tālāk
            else:
                session["user_id"] = data[0]

            conn.close()
            return redirect("/rateit")


# vērtēšana
@app.route("/rateit", methods=["GET", "POST"])
def rateit():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/")

    countries = valstis()  # dropdown


    #ievieto izvēlēto valsti datubāzē, plus parāda uz ekrāna tieši izvēlētās valsts ēdienus
    if request.method == "POST" and "country" in request.form:
        country = request.form.get("country")
        meals = get_meals_by_country(country)
        insert_meals_into_db(meals, country)
        # session ir katram lietotājam savs, tas pielāgojas tam kas ielogoies
        session["country"] = country
        return redirect("/rateit")

 
    # rating brīnumi (ievieto rating tabulā)
    if request.method == "POST" and "rating" in request.form:
        rating = int(request.form.get("rating"))
        food_id = int(request.form.get("food_id"))

        conn = sqlite3.connect("./database.db")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ratings (user_id, food_id, rating) VALUES (?, ?, ?)",
            (user_id, food_id, rating)
        )
        conn.commit()
        conn.close()
        return redirect("/rateit")

    # parāda nākamo ēdienu

    # šis gabals parāda vai lietotāja sesijā ir saglabāta valsts, un ja nav tad vienkārši atgriež sākuma stāvoklī.
    country = session.get("country")
    if not country:
        return render_template("rateit.html", countries=countries, meal=None, finished=False)

    # paņem ēdienu kurš vel nav novērtēts, limit 1 nosaka ka paņemts tikai viens
    conn = sqlite3.connect("./database.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, image
        FROM foods
        WHERE country=?
        AND id NOT IN (
            SELECT food_id FROM ratings WHERE user_id=?
        )
        LIMIT 1
    """, (country, user_id))
    meal = cur.fetchone()
    conn.close()

    if meal:
        # Ja vēl ir ēdiens kuru vajak rated, tad viņš parādās un turpinās viss
        return render_template(
            "rateit.html",
            countries=countries,
            meal=meal,
            food_id=meal[0],
            name_food=meal[1],
            food_image=meal[2],
            finished=False
        )
    else:
        # ēdiena nav, process ir beidzies
        return render_template(
            "rateit.html",
            countries=countries,
            meal=None,
            finished=True
        )


# jau novērtētie ēdieni
@app.route("/ratedfoods", methods=["GET", "POST"])
def show_names():

    # ja nav ielogojies, nevari skatities ratingus

    user_id = session.get("user_id")
    if not user_id:
        return redirect("/")
    countries = valstis()

    # ja izveleta valsts, tad vins to panem
    selected_country = None
    if request.method == "POST":
        selected_country = request.form.get("country")

    conn = sqlite3.connect("./database.db")
    cur = conn.cursor()

    # Paker edienus pec izveletas valsts
    if selected_country:
        cur.execute("""
            SELECT foods.id, foods.name, foods.country, foods.image, ratings.rating
            FROM foods
            INNER JOIN ratings ON foods.id = ratings.food_id
            WHERE ratings.user_id = ? AND foods.country = ?
        """, (user_id, selected_country))
    # ja valsts nav izveleta, paker visus edienus
    else:
        cur.execute("""
            SELECT foods.id, foods.name, foods.country, foods.image, ratings.rating
            FROM foods
            INNER JOIN ratings ON foods.id = ratings.food_id
            WHERE ratings.user_id = ?
        """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    return render_template("ratedfoods.html", rows=rows, countries=countries)


# redige savu rating
@app.route("/rediget/<int:food_id>", methods=["GET", "POST"])
def edit_food(food_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/")

    conn = sqlite3.connect("./database.db")
    cur = conn.cursor()

    # sanem info par ediena rating ko lietotajs grib rediget
    if request.method == "GET":
        cur.execute("""
            SELECT foods.name, foods.image, ratings.rating
            FROM foods
            INNER JOIN ratings ON foods.id = ratings.food_id
            WHERE foods.id = ? AND ratings.user_id = ?
        """, (food_id, user_id))
        data = cur.fetchone()
        conn.close()
        food_name, food_image, rating = data

        # visu atdod template
        return render_template(
            "re_rate.html",
            food_id=food_id,
            food_name=food_name,
            food_image=food_image,
            rating=int(rating)
        )

    # saglabaa rating
    elif request.method == "POST":
        new_rating = request.form.get("rating")
        if not new_rating:
            return redirect("/ratedfoods")

        new_rating = int(new_rating)
        conn = sqlite3.connect("./database.db")
        cur = conn.cursor()
        cur.execute("""
            UPDATE ratings
            SET rating = ?
            WHERE food_id = ? AND user_id = ?
        """, (new_rating, food_id, user_id))
        conn.commit()
        conn.close()

        return redirect("/ratedfoods")



# statistika

@app.route("/stats")
def stats():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/")

    # personīgā
    personal_foods, personal_countries = get_personal_favorites(user_id)

    # pasaules
    world_foods, world_countries = get_worldwide_favorites()

    # Noapaļoti vidējie lai tie neproblemātiski attēlotos ar zvaigznēm
    # Gadījumā ja kaut kad nākotnē vajadzēs decimālo versiju, saglabāta arī tā
    for f in world_foods:
        f['avg_rounded'] = int(round(f['avg']))
        f['avg_display'] = round(f['avg'], 2)
    for c in world_countries:
        c['avg_rounded'] = int(round(c['avg']))
        c['avg_display'] = round(c['avg'], 2)

    # Ja personālais eksistē, tad noapaļo datus
    if personal_countries:
        for c in personal_countries:
            c['avg_rounded'] = int(round(c['avg']))
            c['avg_display'] = round(c['avg'], 2)

    for f in personal_foods:
        # viņiem nav problēmu ar apaļošanu
        f['rating_display'] = int(f['rating'])

    return render_template(
        "stats.html",
        personal_foods=personal_foods,
        personal_countries=personal_countries,
        world_foods=world_foods,
        world_countries=world_countries
    )


if __name__ == "__main__":
    app.run(debug=True)


