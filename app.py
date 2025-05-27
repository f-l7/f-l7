
from flask import Flask, render_template, request, redirect, url_for, session
from flask_pymongo import PyMongo
from datetime import datetime, timedelta
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["MONGO_URI"] = "mongodb://localhost:27017/falcon_ids"
mongo = PyMongo(app)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123456"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/submit", methods=["GET", "POST"])
def submit():
    if request.method == "POST":
        discord = request.form.get("discord", "").strip()
        if not discord:
            return "الهوية مرفوضة: يجب وضع ايديك ديسكورد", 400

        existing = mongo.db.identities.find({"discord": discord, "status": "accepted"}).count()
        if existing >= 2:
            return "لا يمكنك تقديم أكثر من هويتين", 400

        data = {
            "name": request.form.get("name"),
            "age": request.form.get("age"),
            "dob": request.form.get("dob"),
            "nationality": request.form.get("nationality"),
            "gender": request.form.get("gender"),
            "discord": discord,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        mongo.db.identities.insert_one(data)
        return "تم إرسال هويتك لهيئة الأحوال المدنية للمراجعة (سنخبرك بالقبول)"
    return render_template("submit.html")

@app.route("/cards")
def cards():
    identities = list(mongo.db.identities.find({"status": "accepted"}))
    return render_template("cards.html", identities=identities)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        else:
            return "بيانات الدخول خاطئة", 403
    return render_template("login.html")

@app.route("/admin")
def admin_panel():
    if not session.get("admin"):
        return redirect("/login")
    return render_template("admin.html")

@app.route("/admin/pending")
def admin_pending():
    if not session.get("admin"):
        return redirect("/login")
    identities = list(mongo.db.identities.find({"status": "pending"}))
    return render_template("pending.html", identities=identities)

@app.route("/admin/accepted")
def admin_accepted():
    if not session.get("admin"):
        return redirect("/login")
    identities = list(mongo.db.identities.find({"status": "accepted"}))
    return render_template("accepted.html", identities=identities)

@app.route("/admin/rejected")
def admin_rejected():
    if not session.get("admin"):
        return redirect("/login")
    identities = list(mongo.db.identities.find({"status": "rejected"}))
    return render_template("rejected.html", identities=identities)

@app.route("/admin/accept/<id>")
def accept_identity(id):
    if not session.get("admin"):
        return redirect("/login")
    mongo.db.identities.update_one({"_id": ObjectId(id)}, {"$set": {"status": "accepted"}})
    return redirect("/admin/pending")

@app.route("/admin/reject/<id>")
def reject_identity(id):
    if not session.get("admin"):
        return redirect("/login")
    mongo.db.identities.update_one({"_id": ObjectId(id)}, {"$set": {"status": "rejected", "rejected_at": datetime.utcnow()}})
    return redirect("/admin/pending")

@app.route("/admin/remove/<id>")
def remove_identity(id):
    if not session.get("admin"):
        return redirect("/login")
    mongo.db.identities.update_one({"_id": ObjectId(id)}, {"$set": {"status": "rejected", "rejected_at": datetime.utcnow()}})
    return redirect("/admin/accepted")

@app.route("/admin/restore/<id>")
def restore_identity(id):
    if not session.get("admin"):
        return redirect("/login")
    mongo.db.identities.update_one({"_id": ObjectId(id)}, {"$set": {"status": "accepted"}})
    return redirect("/admin/rejected")

@app.before_request
def auto_delete_expired_rejected():
    mongo.db.identities.delete_many({
        "status": "rejected",
        "rejected_at": {"$lt": datetime.utcnow() - timedelta(hours=24)}
    })

if __name__ == "__main__":
    app.run(debug=True)
