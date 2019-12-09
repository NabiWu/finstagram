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

        query = """SELECT * FROM photo JOIN person ON ( username = photoPoster)
                   WHERE photoID IN(
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
        # print(photo)
        OwnerofPhoto = photo["photoPoster"]
        PhotoID = photo["photoID"]
        filepath = photo["filepath"]
        ts = photo["postingdate"]
        firstName = photo["firstName"]
        lastName = photo["lastName"]
        item = dict(name=OwnerofPhoto, ID=PhotoID, filepath=filepath, ts=ts, firstName = firstName, lastName = lastName)
        data.append(item)

    data = sorted(data, key=lambda item: item['ts'], reverse=True)
    return render_template('home.html', username=user, posts=data)
    return render_template("home.html", username=session["username"])


@app.route("/upload", methods=["GET"])
@login_required
def upload():
    username = session['username']
    # should throw exception if username not found

    cursor = connection.cursor();
    query = """ SELECT groupName 
                    FROM friendgroup
                    WHERE groupOwner = %s
         """
    cursor.execute(query, (username))
    data = cursor.fetchall()
    cursor.close()
    print(data)


    return render_template("upload.html", group_list=data)

@app.route("/uploadImage", methods=["GET","POST"])
@login_required
def upload_image():
    # grabs information from the forms
    photoPoster = session['username']
    filePath = request.form['filePath']
    caption = request.form['caption']
    allFollowers = request.form['allFollowers']
    # groupName = request.form['groupName']
    # cursor used to send queries
    cursor = connection.cursor()

    ins = 'INSERT INTO photo(postingdate, photoPoster, filePath, caption, allFollowers) VALUES(%s, %s, %s, %s, %s)'
    cursor.execute(ins, (time.strftime('%Y-%m-%d %H:%M:%S'), photoPoster, filePath, caption, allFollowers))

    query = 'SELECT * FROM photo WHERE photoPoster = %s AND filePath = %s'
    cursor.execute(query, (photoPoster, filePath))
    data = cursor.fetchall()



    if (allFollowers == '0'):

        groupName = request.form['groupName']
        ins = 'INSERT INTO SharedWith(groupOwner, groupName, photoID) VALUES(%s, %s, %s)'
        cursor.execute(ins, (photoPoster, groupName, data[0]['photoID']))

    connection.commit()
    cursor.close()
    return redirect(url_for("home"))


@app.route("/addComment")
@login_required
def addComment():

    return render_template("addComment.html")




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


@app.route("/additionalPicInfo", methods=["GET"])
@login_required
def additionalPicInfo():
    return render_template("additionalPicInfo.html")

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




@app.route("/followUser", methods=["GET","POST"])
@login_required
def followUser():
    return render_template('followUser.html')



@app.route("/followUserAuth", methods=["POST"])
def followUserAuth():
    if request.form:
        requestData = request.form
        follower = session['username']
        followee = requestData["followee"]

        #hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s"
            cursor.execute(query, (followee))
            data = cursor.fetchone()
            if not data:
                error = "Cannot find that user"
                return render_template("followUser.html", error=error)

            follow = "INSERT INTO Follow (username_followed, username_follower, followstatus) VALUES (%s, %s, 0)"
            cursor.execute(follow, (followee, follower))
            return redirect(url_for("home"))

    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)


@app.route('/followRequest')
def followRequest():
    # check that user is logged in
    username = session['username']
    # should throw exception if username not found

    cursor = connection.cursor();
    query = 'SELECT DISTINCT username_follower FROM Follow WHERE username_followed = %s AND followstatus = 0'
    cursor.execute(query, (username))
    data = cursor.fetchall()
    cursor.close()
    return render_template('followRequest.html', user_list=data)


@app.route('/acceptFollow', methods=["GET", "POST"])
def acceptFollow():
    follower = request.args['follower']
    username = session['username']
    cursor = connection.cursor();
    query = 'UPDATE Follow SET followstatus = 1 WHERE username_follower = %s AND username_followed = %s'
    cursor.execute(query, (follower, username))
    data = cursor.fetchall()
    cursor.close()
    return render_template('followRequest.html')

@app.route('/declineFollow', methods=["GET", "POST"])
def declineFollow():
    follower = request.args['follower']
    username = session['username']
    cursor = connection.cursor()
    query = 'DELETE FROM Follow WHERE username_follower = %s AND username_followed = %s'
    cursor.execute(query, (follower, username))
    data = cursor.fetchall()
    cursor.close()
    return render_template('followRequest.html')


@app.route('/tagOnMyImg')
def tagOnMyImg():
    # check that user is logged in
    username = session['username']
    # should throw exception if username not found

    cursor = connection.cursor();
    query = """SELECT photoID FROM photo WHERE photoID IN(
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
                	                                     WHERE member_username = %s))) """
    cursor.execute(query, (username,username,username))
    data = cursor.fetchall()
    cursor.close()
    return render_template('tagOnMyImg.html', photo_list=data)


@app.route('/showTagList', methods=["GET", "POST"])
def showTagList():
    myPhotoID = request.args['myPhotoID']
    cursor = connection.cursor();

    # myq = 'SELECT * FROM photo WHERE photoID = %s'
    # cursor.execute(myq, (myPhotoID))
    #
    # if cursor.fetchone()["allFollowers"] == 1:
    #     print(1)


    query = """ SELECT username
                FROM person
                WHERE username NOT IN (
	            SELECT username
                FROM tagged
                WHERE photoID = %s)
    """
    cursor.execute(query, (myPhotoID))
    data = cursor.fetchall()
    # dictionary = {'username':session['username'] , 'photo' : myPhotoID }
    # data.append(dictionary)
    for line in data:
            line['photo'] = myPhotoID
    # print(data)
    cursor.close()
    return render_template('showTagList.html', userName=data)



@app.route('/startTag', methods=["GET", "POST"])
def startTag():
    username = session['username']
    taggedPerson = request.args['taggedPerson']
    # print(taggedPerson)
    photo = request.args['photo']
    # print(photo)
    cursor = connection.cursor();
    if (taggedPerson == username):
       query = 'INSERT INTO Tagged(username, photoID, tagstatus) VALUES (%s, %s , 1);'
    else:
        query = 'INSERT INTO Tagged(username, photoID, tagstatus) VALUES (%s, %s , 0);'
    cursor.execute(query, (taggedPerson, photo))
    data = cursor.fetchall()
    cursor.close()
    return render_template('showTagList.html')





@app.route('/tagRequest')
def tagRequest():
    # check that user is logged in
    username = session['username']
    # should throw exception if username not found

    cursor = connection.cursor();
    query = 'SELECT DISTINCT photoID FROM Tagged WHERE username = %s AND tagstatus = 0'
    cursor.execute(query, (username))
    data = cursor.fetchall()
    cursor.close()
    return render_template('tagRequest.html', tag_list=data)



@app.route('/acceptTag', methods=["GET", "POST"])
def acceptTag():
    photo = request.args['photo']
    username = session['username']
    cursor = connection.cursor();
    query = 'UPDATE Tagged SET tagstatus = 1 WHERE photoID = %s AND username = %s'
    cursor.execute(query, (photo, username))
    data = cursor.fetchall()
    cursor.close()
    return render_template('tagRequest.html')



@app.route('/declineTag', methods=["GET", "POST"])
def declineTag():
    photo = request.args['photo']
    username = session['username']
    cursor = connection.cursor();
    query = 'DELETE FROM Tagged WHERE username = %s AND photoID = %s'
    cursor.execute(query, (username, photo))
    data = cursor.fetchall()
    cursor.close()
    return render_template('tagRequest.html')


@app.route('/likePhoto', methods=["GET", "POST"])
def likePhoto():
    username = session['username']
    cursor = connection.cursor();

    query = """
              SELECT photoID FROM photo WHERE photoID IN(
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
                	                                     WHERE member_username = %s))) AND photoID NOT IN (
                	                                     SELECT photoID
                	                                     FROM Likes
                	                                     WHERE username = %s)
    """
    cursor.execute(query, (username, username, username, username))
    data = cursor.fetchall()
    # print(data)
    cursor.close()
    return render_template('likePhoto.html', photo_list = data)



@app.route('/chooseOneToLike', methods=["GET", "POST"])
def chooseOneToLike():
    username = session['username']
    id = request.args['id']
    rate = request.args['rate']



    cursor = connection.cursor();

    query = 'INSERT INTO Likes(username, photoID, liketime, rating) VALUES (%s, %s , %s, %s);'
    cursor.execute(query, (username, id, time.strftime('%Y-%m-%d %H:%M:%S'), rate))
    data = cursor.fetchall()
    cursor.close()
    return redirect(url_for("home"))


@app.route('/ImgTagInfo')
def ImgTagInfo():
    # check that user is logged in
    username = session['username']
    # should throw exception if username not found

    cursor = connection.cursor();
    query = """SELECT photoID FROM photo WHERE photoID IN(
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
                	                                     WHERE member_username = %s))) """
    cursor.execute(query, (username,username,username))
    data = cursor.fetchall()
    cursor.close()
    return render_template('ImgTagInfo.html', photo_list=data)



@app.route('/ImgLikeInfo')
def ImgLikeInfo():
    # check that user is logged in
    username = session['username']
    # should throw exception if username not found

    cursor = connection.cursor();
    query = """SELECT photoID FROM photo WHERE photoID IN(
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
                	                                     WHERE member_username = %s))) """
    cursor.execute(query, (username,username,username))
    data = cursor.fetchall()
    cursor.close()
    return render_template('ImgLikeInfo.html', photo_list=data)



@app.route('/getTagInfo', methods=["GET", "POST"])
def getTagInfo():
    myPhotoID = request.args['myPhotoID']
    username = session['username']
    cursor = connection.cursor()
    query = """
                SELECT * 
                FROM photo AS p 
                JOIN tagged AS t 
                ON p.photoID = t.photoID
                NATURAL JOIN person
                WHERE p.photoID = %s
"""
    cursor.execute(query, (myPhotoID))
    data = cursor.fetchall()
    # print(data)
    cursor.close()
    return render_template('ImgTagTable.html', photo_list=data)


@app.route('/getLikeInfo', methods=["GET", "POST"])
def getLikeInfo():
    myPhotoID = request.args['myPhotoID']
    username = session['username']
    cursor = connection.cursor()
    query = """
                SELECT * FROM photo 
                NATURAL JOIN likes
                WHERE photoID = %s
"""
    cursor.execute(query, (myPhotoID))
    data = cursor.fetchall()
    # print(data)
    cursor.close()
    return render_template('ImgLikeTable.html', photo_list=data)


@app.route("/comment", methods=["POST"])
@login_required
def comment():
    # user should input photoID
    photoID = request.form["photoID"]
    # get comment string
    commentStr = request.form["commentStr"]
    username = session["username"]

    # cursor to interact with database
    cursor = connection.cursor()

    query = "INSERT INTO comment(commentStr, ts, photoID, username) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (commentStr, time.strftime('%Y-%m-%d %H:%M:%S'), photoID, username))
    connection.commit()
    cursor.close()
    error = "An unknown error occurred. Please try again."
    return redirect(url_for("home"))


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

@app.route('/readComment')
def readComment():
    # check that user is logged in
    username = session['username']
    # should throw exception if username not found

    cursor = connection.cursor();
    query = """SELECT photoID FROM photo WHERE photoID IN(
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
                	                                     WHERE member_username = %s))) """
    cursor.execute(query, (username,username,username))
    data = cursor.fetchall()
    cursor.close()
    return render_template('readComment.html', photo_list=data)


@app.route('/showComments', methods=["GET", "POST"])
def showComments():
    myPhotoID = request.args['myPhotoID']
    cursor = connection.cursor();


    query = """ SELECT commentStr
                FROM comment
                WHERE photoID = %s
	            
    """
    cursor.execute(query, (myPhotoID))
    data = cursor.fetchall()
    # dictionary = {'username':session['username'] , 'photo' : myPhotoID }
    # data.append(dictionary)
    for line in data:
            line['photo'] = myPhotoID
    # print(data)
    cursor.close()
    return render_template('showCommentList.html', comment=data)





@app.route('/manageGroup')
def manageGroup():
    # check that user is logged in
    username = session['username']
    # should throw exception if username not found

    cursor = connection.cursor();
    query = """ SELECT groupName 
                FROM friendgroup
                WHERE groupOwner = %s
     """
    cursor.execute(query, (username))
    data = cursor.fetchall()
    cursor.close()
    print(data)
    return render_template('manageGroup.html', group_list=data)



@app.route('/showAddList', methods=["GET", "POST"])
def showAddList():

    cursor = connection.cursor()
    username = session['username']
    groupName = request.args['groupName']


    query = """ SELECT username_follower
                FROM Follow
                WHERE username_followed = %s AND followstatus = 1 AND username_follower NOT IN (
	            SELECT member_username
                FROM BelongTo
                WHERE groupName = %s AND owner_username = %s)
    """
    cursor.execute(query, (username, groupName, username))
    data = cursor.fetchall()
    for line in data:
            line['groupName'] = groupName

    # print(data)
    cursor.close()
    return render_template('showAddList.html', userName=data)




@app.route('/startAdd', methods=["GET", "POST"])
def startAdd():
    username = session['username']
    print(1)
    addedPerson = request.args['addedPerson']
    print(2)
    groupName = request.args['groupName']
    print(3)
    # print(taggedPerson)

    # print(photo)
    cursor = connection.cursor();

    query = 'INSERT INTO BelongTo(member_username, owner_username, groupName) VALUES (%s, %s , %s);'
    cursor.execute(query, (addedPerson, username,groupName))
    data = cursor.fetchall()
    cursor.close()
    return render_template('showAddList.html')















if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()
