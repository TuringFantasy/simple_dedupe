from flask import Flask
from flask import request
from flask import jsonify
from flask import g

from flask_script import Manager
from flask_cors import CORS

import json

import cv2 as cv
import numpy

import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "./"
CORS(app)
manager = Manager(app)

SIFT_OUTPUT_FILE = "sift_matches.json"
DUPLICATE_WEIGHT_THRESHHOLD = 3

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

def _sift_transform_images(users, images):

    sift = cv.xfeatures2d.SIFT_create()

    image_ingests = list(map(lambda image: [cv.imread(image['image'], 0), image['id'], os.stat(image['image']).st_size / 1000], images))

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
                    "id": image[1],
                    "duplicate_id": other_image[1],
                    "match_index": len(good) / (image[2] * other_image[2])
                }
                match_counts.append(obj)
    return match_counts

def _test_threshhold(item):
    return int(item["match_index"]) > DUPLICATE_WEIGHT_THRESHHOLD

@app.route('/duplicate/<id_value>', methods=['GET'])
def retrieve_duplicate(id_value):
    if os.path.isfile(SIFT_OUTPUT_FILE):
        with open(SIFT_OUTPUT_FILE, 'r') as sift_matches_db:
            match_counts = json.load(sift_matches_db)
        possible_users = list(filter(lambda user: (str(user['id']) == id_value or str(user['duplicate_id']) == id_value), match_counts))
        flagged_users = [item for item in possible_users if _test_threshhold(item)]
        if len(flagged_users) > 0:
            other_id_objs = list(filter(lambda user: str(user['id']) != id_value, flagged_users))
            other_id = [user['id'] for user in other_id_objs]
            response = {
                "id": id_value,
                "duplicate": True,
                "duplicate_id": other_id
            }
        else:
            response = {
                "id": id_value,
                "duplicate": False,
                "duplicate_id": []
            }
        return jsonify(response), 200
    else:
        return jsonify({"error": "No SIFT Match Index has been created. Please request GET on /duplicates to generate an index of SIFT Matches"}), 404

@app.route('/duplicates', methods=['GET'])
def handle_duplicates():
    """
    Report back all duplicates, if any are found

    Returns
    ---------
    [
        {
            "id": <id>,
            "duplicate": True,
            "duplicate_id": <duplicate_id>
        }
    ]
    """
    duplicate_guesses = []
    if os.path.isfile(SIFT_OUTPUT_FILE):
        with open(SIFT_OUTPUT_FILE, 'r') as sift_matches_db:
            match_counts = json.load(sift_matches_db)
        flagged_users = [item for item in match_counts if int(item["match_index"]) > DUPLICATE_WEIGHT_THRESHHOLD]
        duplicate_guesses = [dict(user, **{'duplicate': True }) for user in flagged_users]
    else:
        users = get_db_users()
        images = get_db_images()
        match_counts = _sift_transform_images(users, images)

        flagged_users = [item for item in match_counts if int(item["match_index"]) > DUPLICATE_WEIGHT_THRESHHOLD]
        duplicate_guesses = [dict(user, **{'duplicate': True }) for user in flagged_users]
        
        # save the sift matches in a JSON named "sift_matches.json" for faster lookup on future calls
        with open(SIFT_OUTPUT_FILE, 'w') as output:
            json.dump(match_counts, output)

    return jsonify(duplicate_guesses), 200

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