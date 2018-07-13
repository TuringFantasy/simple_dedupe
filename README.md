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

