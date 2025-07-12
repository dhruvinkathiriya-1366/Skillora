from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from flask_cors import CORS
import hashlib

app = Flask(__name__)
app.secret_key = 'skillora_secret_key'
CORS(app)

client = MongoClient("mongodb+srv://jenillakkad18:Jenillakkad@cluster0.ijy4moh.mongodb.net/skillora?retryWrites=true&w=majority&appName=Cluster0")
db = client['skillora']
users = db['users']

@app.context_processor
def inject_user():
    if "email" in session:
        return {"user": users.find_one({"email": session["email"]})}
    return {"user": None}

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/members")
def members():
    all_users = users.find({}, {"password": 0})
    return render_template("browse.html", users=all_users)

@app.route("/join")
def join():
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = users.find_one({"email": email})
        if user and check_password_hash(user["password"], password):
            session["email"] = email
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid login credentials", "error")
            return redirect(url_for("login"))
    return redirect(url_for("join"))

@app.route("/register", methods=["POST"])
def register():
    email = request.form["email"]
    name = request.form["name"]
    password = generate_password_hash(request.form["password"])
    if users.find_one({"email": email}):
        flash("User already exists.", "error")
        return redirect(url_for("join"))
    avatar = gravatar_url(email)

    users.insert_one({
        "email": email,
        "name": name,
        "password": password,
        "avatar" : avatar,
        "skills_offered": [],
        "skills_wanted": [],
        "availability": "Flexible",
        "swap_requests": []
    })
    flash("Registration successful! Please log in.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "email" not in session:
        flash("Login required", "error")
        return redirect(url_for("login"))
    user = users.find_one({"email": session["email"]})
    return render_template("dashboard.html", user=user)

@app.route("/send_request/<to>")
def send_request(to):
    if "email" not in session:
        flash("Please login to send request", "error")
        return redirect(url_for("login"))
    from_user = session["email"]
    if users.find_one({"email": to, "swap_requests": {"$elemMatch": {"from": from_user}}}):
        flash("Already requested!", "error")
        return redirect(url_for("members"))
    users.update_one({"email": to}, {"$push": {"swap_requests": {"from": from_user, "status": "pending"}}})
    flash("Request sent!", "success")
    return redirect(url_for("members"))

@app.route("/logout")
def logout():
    session.pop("email", None)
    flash("Logged out", "success")
    return redirect(url_for("home"))

@app.route("/upload_avatar", methods=["POST"])
def upload_avatar():
    if "email" not in session:
        return redirect(url_for("login"))

    file = request.files['avatar']
    if file:
        avatar_path = f"static/uploads/{session['email']}_avatar.png"
        file.save(avatar_path)
        users.update_one({"email": session["email"]}, {"$set": {"avatar": avatar_path}})
        flash("Avatar updated!", "success")
    return redirect(url_for("dashboard"))

@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "email" not in session:
        return redirect(url_for("login"))

    name = request.form["name"]
    availability = request.form["availability"]
    bio = request.form["bio"]

    users.update_one({"email": session["email"]}, {"$set": {
        "name": name,
        "availability": availability,
        "bio": bio
    }})
    flash("Profile updated!", "success")
    return redirect(url_for("dashboard"))

@app.route("/update_skills", methods=["POST"])
def update_skills():
    if "email" not in session:
        return redirect(url_for("login"))

    skills_offered = [s.strip() for s in request.form["skills_offered"].split(',')]
    skills_wanted = [s.strip() for s in request.form["skills_wanted"].split(',')]

    users.update_one({"email": session["email"]}, {"$set": {
        "skills_offered": skills_offered,
        "skills_wanted": skills_wanted
    }})
    flash("Skills updated!", "success")
    return redirect(url_for("dashboard"))

@app.route("/accept_request/<email>", methods=["POST"])
def accept_request(email):
    if "email" not in session:
        return redirect(url_for("login"))

    users.update_one(
        {"email": session["email"], "swap_requests.from": email},
        {"$set": {"swap_requests.$.status": "accepted"}}
    )
    flash(f"Accepted request from {email}", "success")
    return redirect(url_for("dashboard"))

@app.route("/decline_request/<email>", methods=["POST"])
def decline_request(email):
    if "email" not in session:
        return redirect(url_for("login"))

    users.update_one(
        {"email": session["email"], "swap_requests.from": email},
        {"$set": {"swap_requests.$.status": "declined"}}
    )
    flash(f"Declined request from {email}", "error")
    return redirect(url_for("dashboard"))


def gravatar_url(email, size=150):
    hash_email = hashlib.md5(email.strip().lower().encode('utf-8')).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash_email}?d=identicon&s={size}"

if __name__ == "__main__":
    app.run(debug=True)
