# Simple Deduplication

Given some image database linked to a users database, identify potential duplicate users and expose them via API.

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