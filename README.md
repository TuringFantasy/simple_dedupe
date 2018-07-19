# Simple Deduplication

Given some image database linked to a users database, identify potential duplicate users and expose them via API.

## Getting Started

### Docker

* Have Docker
* `docker build -t dedupe .`
* `docker run -ti --rm -p 5000:5000 dedupe`
* In another prompt `curl localhost:5000/duplicates` to build the match index.

### No Docker (highly recommend using Docker though)

* Have python
* `pip install -r requirements.txt`
* `python main.py`
* In another prompt `curl localhost:5000/duplicates` to build the match index.

## Database

Replicate a simple database just using a JSON

## Image Database

JSON mapping imagefiles to user unique IDs

## API

* `/duplicates` (GET): Ask for any potential duplicates
* `/duplicate/<id>` (GET): Ask if user with `id` is or has any potential duplicates
* `/users` (GET): Get all users
* `/user/<id>` (GET): Get a user by an `id`

# What is really happening

The users.json and images.json simulate user and image databases (maybe a pg table and a mongodb, respectively). When you run the container (or execute `main.py`), a flask API powered by gunicorn is started. Immediately, one should request `localhost:5000/duplicates` to construct the SIFT matches index. In a production environment, this would likely be continuously evaluated with a hadoop cluster against millions of users and millions of images. 

Once you have the index, queries will be much faster as the API caches the index on the filesystem. You can also request if a specific user is a possible duplicate by `id` (hint, users `4` and `7` are duplicates, they have the same driver's license). 

The notion of deduplication centers upon creating a similarity threshhold for aliases and corresponding metadata across a domain of users. In this simple example, only one piece of information is considered: the "similarity" of users identifying documents to one another. One powerful option is Scale-Invariant Feature Extraction. SIFT is a powerful algorithmic form of feature engineering on a given corpus, and excellent at comparisons in low-cpu environments.  Essentially, SIFT determines key points and a standard description of said key points for a given image (learn more about how SIFT works [here](https://docs.opencv.org/3.4.1/da/df5/tutorial_py_sift_intro.html)). Then, a pattern matcher examines the number of strong matches (i.e. low distance) each image has to one another, and computes an image-size adjusted index for fair comparison across all images regardless of resolution. Thus, more matches on the index between a given two images, the greater liklihood that they are either pictures taken of the same document, or the same document uploaded twice (the latter case applies to `id`s 4 and 7.) 

This is just one aspect of deduplication given a domain of users. Distance algorithms should be applied to all text data in the users database (literal pattern matches to find name + dob + ssn + location dupes). OCR and entity extraction should be performed on all identifying documents to yield additional text-based duplication estimates.

Test test again

