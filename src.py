from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")

connection = pymysql.connect(host="localhost",
                             user="root",
                             password="",
                             db="finstagram",
                             charset="utf8mb4",
                             port=3306,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)


def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return dec


@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")


@app.route("/home")
@login_required
def home():
    user = session['username']
    data = []
    with connection.cursor() as cursor:
        query = """SELECT * FROM photo WHERE photoID IN(
                   SELECT DISTINCT photoID
                   FROM photo
                   WHERE photoPoster = %s OR photoID IN(
    	                                      SELECT DISTINCT photoID
		                                      FROM photo JOIN follow ON (photoPoster = username_followed)
                                              WHERE (allFollowers = True AND username_follower = %s AND followstatus = True)
    	                                      OR photoID IN( SELECT DISTINCT photoID
                	                                     FROM friendgroup AS F 
                	                                     JOIN belongto As B ON F.groupName = B.groupName AND F.groupOwner = B.owner_username 
                	                                     JOIN sharedwith AS S ON F.groupName = S.groupName AND F.groupOwner = S.groupOwner
                	                                     WHERE member_username = %s))) 
                """
        cursor.execute(query,(user, user, user))
        getPhoto = cursor.fetchall()
    for photo in getPhoto:
        print(photo)
        OwnerofPhoto = photo["photoPoster"]
        PhotoID = photo["photoID"]
        filepath = photo["filepath"]
        ts = photo["postingdate"]
        item = dict(name=OwnerofPhoto, ID=PhotoID, filepath=filepath, ts=ts)
        data.append(item)

    data = sorted(data, key=lambda item: item['ts'], reverse=True)
    return render_template('home.html', username=user, posts=data)


@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")


@app.route("/images", methods=["GET"])
@login_required
def images():
    query = "SELECT * FROM photo"
    with connection.cursor() as cursor:
        cursor.execute(query)
    data = cursor.fetchall()
    return render_template("images.html", images=data)


@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        #hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, plaintextPasword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)


@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        #hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["firstName"]
        lastName = requestData["lastName"]
        bio = requestData["bio"]

        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO person (username, password, firstName, lastName, bio) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query, (username, plaintextPasword, firstName, lastName, bio))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)

        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)


@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")


@app.route("/uploadImage", methods=["POST"])
@login_required
def upload_image():
    # grabs information from the forms
    photoPoster = session['username']
    filePath = request.form['filePath']
    caption = request.form['caption']
    allFollowers = request.form['allFollowers']

    # cursor used to send queries
    cursor = connection.cursor()


    ins = 'INSERT INTO photo(postingdate, photoPoster, filePath, caption, allFollowers) VALUES(%s, %s, %s, %s, %s)'
    cursor.execute(ins, (time.strftime('%Y-%m-%d %H:%M:%S'), photoPoster, filePath, caption, bool(allFollowers)))
    connection.commit()
    cursor.close()
    return render_template('home.html')

@app.route("/follow", methods=["GET"])
@login_required
def follow():
    return render_template("follow.html")

@app.route("/followUser", methods=["POST"])
@login_required
def followUser():

    return render_template('home.html')

@app.route("/comment", methods=["POST"])
@login_required
def comment():
    # get comment string from form
    userComment = request.form["comment"]
    username = session['username']
    # user should also input photoID 
    photoID = request.form["photoID"]

    # cursor to interact with database
    cursor = connection.cursor()
    
    insertion = "INSERT INTO comments(userComment, ts, photoID, username) VALUES (%s, %s, %s, %s)"
    cursor.execute(insertion, (userComment, time.strftime('%Y-%m-%d %H:%M:%S'), photoID, username))
    connection.commit()
    cursor.close()
    return render_template("images.html")


@app.route("/friendGroup", methods=["GET"])
@login_required
def friendGroup():
    return render_template("/friendGroup.html")


@app.route("/addFriendGroup", methods=["POST"])
@login_required
def addFriendGroup():
    # get new friendgroup name and description
    groupName = request.form["groupName"]
    description = request.form["description"]
    groupOwner = session["username"]

    try:
        with connection.cursor() as cursor:
            query = "INSERT INTO friendgroup(groupOwner, groupName, description) VALUES (%s, %s, %s)"
            cursor.execute(query, (groupOwner, groupName, description))
            connection.commit()
    except pymysql.err.IntegrityError:
        error = groupName + " already exists."
        return render_template("friendGroup.html", error=error)

    error = "An unknown error has occurred. Please try again."
    return render_template("friendGroup.html", error=error)
        

if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()
