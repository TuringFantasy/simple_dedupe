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
    """
    Use Scale Invariant Feature Transformation to isolate key points in two images, 
    then use a brute force matcher to find k=2 matches across the images, keeping only
    low distance (i.e. stronger) matches, then weighting the count of those matches against 
    image sizes, and storing that resulting index value along with the original test image ids.

    Iterate over all images linked to users by UID field "id" to determine SIFT match index values
    across all images to one another.

    Params
    --------
    users (list of dicts) : get_db_users()
    images (list of dicts) : get_db_images()

    Returns
    --------
    match_counts (list of dicts) : 
    [
        {
            "id":
            "duplicate_id":
            "match_index":
        }
    ]
    
    """
    sift = cv.xfeatures2d.SIFT_create()                                     # init SIFT analyzer in 2d space

    # create a memory-heavy 2d array mapping cv image attributes, image ID, and image size in KB across all images
    image_ingests = list(map(lambda image: [cv.imread(image['image'], 0), image['id'], os.stat(image['image']).st_size / 1000], images))

    match_counts = []
    for image in image_ingests:
        kp1, des1 = sift.detectAndCompute(image[0], None)                   # Create key points array and matching descriptor  
        for other_image in image_ingests:                                   #  array using SIFT algorithm
            if image[1] != other_image[1]:                                  # Only check images that are not the key image
                kp2, des2 = sift.detectAndCompute(other_image[0], None)
                bf = cv.BFMatcher()                                         # init Brute Force matcher
                matches = bf.knnMatch(des1, des2, k=2)                      # get k = 2 best matches
                good = []
                for m, n in matches:
                    if m.distance < 0.75*n.distance:                        # reject matches with too high of distance
                        good.append([m])                                    #  i.e., weak matches
                obj = {
                    "id": image[1],
                    "duplicate_id": other_image[1],
                    "match_index": len(good) / (image[2] * other_image[2])
                }
                match_counts.append(obj)
    return match_counts

def _test_threshhold(item):
    """
    Given an item, compare its match index against the weighted threshhold.

    Params
    ---------
    item (dict): {
        "id": <some_id>
        "duplicate_id": <some_other_id>
        "match_index": number of strong SIFT matches between <some_id> and <some_other_id> 
                       weighted by image sizes
    }
    """
    return int(item["match_index"]) > DUPLICATE_WEIGHT_THRESHHOLD

@app.route('/duplicate/<id_value>', methods=['GET'])
def retrieve_duplicate(id_value):
    """
    Contacts SIFT Matches database to determine if a given user (by id)
    has a possible duplicate match in the users database, given their 
    identifying documents, a fixed match threshhold, and match weighting
    by image resolution.
    
    Params
    --------
    id_value (str) : id for which duplication should be checked

    Returns
    --------
    {
        "id": param(id_value)
        "duplicate": True | False
        "duplicate_id": [<duplicate id(s)if one or more exists>] | []
    }
    """
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
    Contact SIFT matches database to calculate SIFT distance matches
    for key points on identifying documents attached to users in the users database.
    Report back flagged users given a fixed match threshhold and match weighting
    by image resolution.

    If SIFT Matches database does not yet exist, create it (takes a little while, depending 
    on available processing power)
    
    NOTE: This does not compress the JSON payload to consolidate duplicate IDs 
    in to a graph-like structure, like the "/duplicate/<id_value>" endpoint does. This is 
    computationally costly across N users, whereas the single user endpoint substantially 
    reduces runtime complexity.

    Returns
    ---------
    [
        {
            "id": <id>,
            "duplicate": True,
            "duplicate_id": <duplicate_id>
        },
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