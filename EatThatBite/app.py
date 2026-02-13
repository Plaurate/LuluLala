from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)


#mājaslapas forma
@app.route("/")
def home():
    return render_template("index.html")   

#Datu saglabāšana
@app.route("/submit", methods=["POST"])
def submit():
    if request.method == "POST":
        name = request.form["name"]   #iegūst ievadīto vārdu no formas
        if name: #pārbauda vai nav tukšs
            conn = sqlite3.connect("./database.db")
            conn.execute("INSERT INTO users (name) VALUES (?)", (name,))
            conn.commit()
            conn.close()

        return redirect("/")  # pēc datu saglabāšanas atgriežas uz sākuma lapu
    

@app.route("/vardi")
def show_names():
    conn = sqlite3.connect("./database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users")
    names = cursor.fetchall()
    conn.close()
    return render_template("vardi.html", names=names)

@app.route("/dzest/<int:id>")
def delete_name(id):
    conn = sqlite3.connect("./database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/vardi") # pēc dzēšanas atgriežas sarakstā

@app.route("/rediget/<int:id>", methods = ["GET", "POST"])
def edit_name(id):
    conn = sqlite3.connect("./database.db")
    cursor = conn.cursor()
    if request.method == "POST":
        new_name = request.form["name"]
        cursor.execute("UPDATE users SET name=? WHERE id=?", (new_name, id))
        conn.commit()
        conn.close()
        return redirect("/vardi") # pēc dzēšanas atgriežas sarakstā

    #GET metode - parāda esošo vārdu
    elif request.method == "GET":
        cursor.execute("SELECT name FROM users WHERE id=?", (id, ))
        name = cursor.fetchone()
        conn.commit()
        conn.close()
        if name:
            return render_template("rediget.html", id=id, name=name[0])
        else:
            return "Ieraksts nav atrasts", 404

if __name__ == "__main__":
    app.run(debug=True)