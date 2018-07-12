from flask import Flask
from flask import request
from flask import jsonify
from flask import g

from flask_script import Manager
from flask_cors import CORS

import json

import cv2 as cv
import numpy

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "./"
CORS(app)
manager = Manager(app)

def GunicornServer():

    from gunicorn.app.base import Application

    class FlaskApplication(Application):
        def init(self, parser, opts, args):
            return {
                'bind': '{0}:{1}'.format('0.0.0.0', 5000),
                'workers': 5,
                'timeout': 10,
                'loglevel': 'info',
                'preload_app': 'false'
            }

        def load(self):
            return app

    application = FlaskApplication()
    return application.run()

def get_db_users():
    """
    Fetch users from DB (JSON)
    """
    with open("users.json", 'r') as db:
        users = json.load(db)
    return users

def get_db_images():
    """
    Fetch all image locations from DB (JSON)

    Returns
    --------
    list of dicts : [
                        {
                            "id": <id>,
                            "image": </path/to/image>
                        }
                    ]
    """
    with open("images.json", 'r') as file_db:
        images = json.load(file_db)
    return images

@app.route('/duplicates', methods=['GET'])
def handle_duplicates():
    """
    Report back all duplicates, if any are found

    Returns
    ---------
    [
        {
            "id": <id>
            "duplicate": True
        }
    ]
    """
    users = get_db_users()
    images = get_db_images()

    sift = cv.xfeatures2d.SIFT_create()

    image_ingests = list(map(lambda image: [cv.imread(image['image'], 0), image['id']], images))

    match_counts = []
    for image in image_ingests:
        kp1, des1 = sift.detectAndCompute(image[0], None)
        for other_image in image_ingests:
            if image[1] != other_image[1]:
                kp2, des2 = sift.detectAndCompute(other_image[0], None)
                bf = cv.BFMatcher()
                matches = bf.knnMatch(des1, des2, k=2)
                good = []
                for m, n in matches:
                    if m.distance < 0.75*n.distance:
                        good.append([m])
                obj = {
                    "base": image[1],
                    "compare": other_image[1],
                    "match_count": len(good)
                }
                match_counts.append(obj)

    return jsonify(match_counts), 200

@app.route('/users', methods=['GET'])
def get_users():
    """
    Deliver all users in JSON form

    Returns
    ---------
    [
        {
            "id": <id>,
            "name": <user's name>
        },
        {
            "id": <id-2>,
            "name": <user 2's name>
        }
    ]
    """
    users = get_db_users()
    return jsonify(users), 200

@app.route('/user/<id_value>', methods=['GET'])
def get_user(id_value):
    """
    Return a given user by ID
    
    Params
    ---------
    id_value (int) : ID of user

    Returns
    ---------
    {
        "id": <id>
        "name": <name of user>
    }

    """
    users = get_db_users()
    correct_user = next((item for item in users if str(item['id']) == id_value))
    return jsonify(correct_user), 200

if __name__ == '__main__':    
    manager.add_command("runserver", GunicornServer())
    manager.run()    