# Simple Deduplication

Given some image database linked to a users database, identify potential duplicate users and expose them via API.

## Getting Started

### Docker

* Have Docker
* `docker build -t dedupe .`
* `docker run -ti --rm -p 5000:5000 dedupe`

### No Docker

* Have python
* `pip install -r requirements.txt`
* `python main.py`

## Database

Replicate a simple database just using a JSON

## Image Database

JSON mapping imagefiles to user unique IDs

## API
<br>
`/duplicates` (GET): Ask for any potential duplicates
<br>
`/users` (GET): Get all users
<br>
`/user/<id>` (GET): Get a user by an `id`

