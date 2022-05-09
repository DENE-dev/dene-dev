from google.cloud import datastore
from datetime import datetime, timezone, timedelta

import hashlib
import random
import json


# This code is based on the code found at https://github.com/timothyrjames/cs1520 with permission from the instructor

# Everyone will likely have a different project ID. Put yours here so the
# datastore stuff works
_PROJECT_ID = 'roommate-tinder0'
_USER_ENTITY = 'roommate_user'
_CHATROOM_ENTITY = 'chatroom'
_RELATIONSHIP_ENTITY = 'roommate_relationship'
_MESSAGE_COOKIE_ENTITY = 'num_messages_cookie'

MAX_LIKED_TIME = timedelta(days=30)


relationship_types = {
    "no_relationship": 0,
    "first_liked_second": 1,
    "second_liked_first": 2,
    "first_ignored_second": 3,
    "second_ignored_first": 4,
    "both_ignored": 5,
    "first_liked_second_ignored": 6,  # First likes the second user but second is ignoring the first user.
    "second_liked_first_ignored": 7,
    "matched": 8
}


class User(object):
    def __init__(self, username, email='', about='', firstname='', lastname='', age='', gender='', state='', city='', address='', bio='', avatar=''):
        self.username = username
        self.email = email
        self.about = about
        self.firstname = firstname
        self.lastname = lastname
        self.age = age
        self.gender = gender
        self.state = state
        self.city = city
        self.address = address
        self.bio = bio
        self.avatar = avatar

    def to_dict(self):
        return {
            'username': self.username,
            'email': self.email,
            'about': self.about,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'age': self.age,
            'gender': self.gender,
            'bio': self.bio,
            'avatar': self.avatar
        }


class Relationship(object):
    def __init__(self, first_username, second_username, relationship_type, relationship_date):
        self.first_username = first_username
        self.second_username = second_username
        self.relationship_type = relationship_type
        self.relationship_date = relationship_date


def _get_client():
    """Returns the datastore client"""
    return datastore.Client(_PROJECT_ID)


def _load_key(client, entity_type, entity_id=None, parent_key=None):
    """Load a datastore key using a particular client, and if known, the ID.  Note
    that the ID should be an int - we're allowing datastore to generate them in
    this example."""
    key = None
    if entity_id:
        key = client.key(entity_type, entity_id, parent=parent_key)
    else:
        # this will generate an ID
        key = client.key(entity_type)
    return key


def _load_entity(client, entity_type, entity_id, parent_key=None):
    """Load a datstore entity using a particular client, and the ID."""
    key = _load_key(client, entity_type, entity_id, parent_key)
    entity = client.get(key)
    return entity


# TODO: Change this to load the user in the same way a relationship is loaded.
def load_user(username, passwordhash):
    """Load a user based on the passwordhash; if the passwordhash doesn't match
    the username, then this should return None."""
    client = _get_client()
    q = client.query(kind=_USER_ENTITY)
    q.add_filter('username', '=', username)
    q.add_filter('passwordhash', '=', passwordhash)
    for user in q.fetch():
        return User(username=user['username'], email=user['email'], about=user['about'], firstname=user['firstname'], lastname=user['lastname'], age=user['age'], gender=user['gender'], state=user['state'], city=user['city'], address=user['address'], bio=user['bio'], avatar=user['avatar'])
    return None

def load_chatroom(current_user, other_user):
    """Load a chatroom based on the hash of the two usernames; if the hash doesn't match
    the username, then this should return None."""

    client = _get_client()
    q1 = client.query(kind=_CHATROOM_ENTITY)
    q2 = client.query(kind=_CHATROOM_ENTITY)

    #generate hash from combination of two usernames
    keyString1 = current_user + other_user
    keyString2 = other_user + current_user
    code1 = keyString1.encode('utf-8')
    code2 = keyString2.encode('utf-8')
    key1 = hashlib.sha256(code1).hexdigest()
    key2 = hashlib.sha256(code2).hexdigest()

    #hash should be one of two values depending on name order
    q1.add_filter('key', '=', key1)
    q2.add_filter('key', '=', key2)

    for chatroom in q1.fetch():
        return chatroom
    for chatroom in q2.fetch():
        return chatroom
    return None

def save_message(current_user, other_user, message):
    """save JSON object with timestamp, message, and the user who sent the message"""

    client = _get_client()
    chatroom = load_chatroom(current_user, other_user)

    current_time = datetime.now(timezone.utc)
    epoch_ms = current_time.timestamp() * 1000   #utc ms timestamp
    #time_str = current_time.strftime("%m %d/%Y, %H:%M:%S")
    dump = json.dumps({"time": str(epoch_ms), "from_user": current_user, "message": message})
    chatroom['messages'].append(dump)
    client.put(chatroom)

def save_new_chatroom(current_user, other_user):
    """Save the chatroom details to the datastore."""

    client = _get_client()
    entity = datastore.Entity(_load_key(client, _CHATROOM_ENTITY))

    #generate hash from combination of two usernames
    keyString = current_user + other_user
    code = keyString.encode('utf-8')
    key = hashlib.sha256(code).hexdigest()

    entity['key'] = key
    entity['messages'] = []
    client.put(entity)

def load_num_messages(current_user):
    """Load current stored number of received messages."""

    client = _get_client()
    q = client.query(kind=_MESSAGE_COOKIE_ENTITY)

    #generate hash from combination of two usernames
    keyString = current_user
    code = keyString1.encode('utf-8')
    key = hashlib.sha256(code).hexdigest()

    #hash should be one of two values depending on name order
    q.add_filter('key', '=', key1)

    for cookie in q.fetch():
        return cookie
    return None

def save_num_messages(current_user, num_messages):
    """save JSON object with timestamp, message, and the user who sent the message"""

    client = _get_client()
    cookie = load_num_messages(current_user)
    chatroom['num_messages'] = num_messages
    client.put(chatroom)

def save_new_message_cookie(current_user, num_messages):
    """Save the updated number of received messages."""

    client = _get_client()
    entity = datastore.Entity(_load_key(client, _MESSAGE_COOKIE_ENTITY))

    #generate hash from combination of two usernames
    keyString = current_user
    code = keyString.encode('utf-8')
    key = hashlib.sha256(code).hexdigest()

    entity['key'] = key
    entity['num_messages'] = num_messages
    client.put(entity)

def load_public_user(username):
    """Returns a user object that contains information that anyone can view."""
    user = _load_entity(_get_client(), _USER_ENTITY, username)
    if user:
        return User(username=user['username'], about=user['about'], firstname=user['firstname'], lastname=user['lastname'], age=user['age'], gender=user['gender'], state=user['state'], city=user['city'], address=user['address'], bio=user['bio'], avatar=user['avatar'])
    else:
        return ''


def save_user_profile(username, firstname, lastname, age, gender, city, state, address, about, bio, avatar):
    """Save the user profile info to the datastore."""
    client = _get_client()
    user = _load_entity(client, _USER_ENTITY, username)
    user['firstname'] = firstname
    user['lastname'] = lastname
    user['age'] = age
    user['gender'] = gender
    user['state'] = state
    user['city'] = city
    user['address'] = address
    user['about'] = about
    user['bio'] = bio
    user['avatar'] = avatar
    client.put(user)


def get_current_date():
    return datetime.now(timezone.utc)


def get_date_string(date):
    return date.isoformat(' ', 'seconds')


def is_liked(username, other_username):
    """Checks if the current user likes other_username."""
    sorted_usernames = sort_users(username, other_username)
    relationship = get_relationship(sorted_usernames)

    username_prefix = 'first'
    other_username_prefix = 'second'
    if (sorted_usernames[2] == 1):  # Checks which order the usernames are in.
        username_prefix = 'second'
        other_username_prefix = 'first'

    if relationship is None:
        return False
    elif (relationship['relationship_type'] == relationship_types['matched']):
        return True
    elif (relationship['relationship_type'] == relationship_types['{}_liked_{}'.format(username_prefix, other_username_prefix)]):
        return True
    elif (relationship['relationship_type'] == relationship_types['{}_liked_{}_ignored'.format(username_prefix, other_username_prefix)]):
        return True
    else:
        return False


def is_like_expired(old_date_string):
    """Checks how long ago the like was made"""
    old_date = datetime.strptime(old_date_string, "%Y-%m-%d %H:%M:%S")
    current_date = get_current_date()
    difference = current_date - old_date
    return difference > MAX_LIKED_TIME


def sort_users(username, other_username):
    """Returns a tuple with the usernames in order, the index of the current user, and the ID of the relationship."""
    if (username < other_username):
        user_tuple = username, other_username, 0, ('{} {}'.format(username, other_username))
        return user_tuple
    else:
        user_tuple = other_username, username, 1, ('{} {}'.format(other_username, username))
        return user_tuple


def get_relationship(sorted_usernames):
    relationship_id = sorted_usernames[3]
    client = _get_client()
    relationship = _load_entity(client, _RELATIONSHIP_ENTITY, relationship_id)
    return relationship


def create_relationship(sorted_usernames):
    relationship_id = sorted_usernames[3]
    client = _get_client()
    entity = datastore.Entity(_load_key(client, _RELATIONSHIP_ENTITY, relationship_id))
    entity['first_username'] = sorted_usernames[0]
    entity['second_username'] = sorted_usernames[1]
    entity['relationship_type'] = relationship_types["no_relationship"]
    entity['relationship_date'] = get_date_string(get_current_date())
    return entity


def like_user(username, other_username):
    sorted_usernames = sort_users(username, other_username)
    relationship = get_relationship(sorted_usernames)

    if relationship is None:
        relationship = create_relationship(sorted_usernames)

    relationship_type = relationship['relationship_type']

    username_prefix = 'first'
    other_username_prefix = 'second'
    if (sorted_usernames[2] == 1):  # Checks which order the usernames are in.
        username_prefix = 'second'
        other_username_prefix = 'first'

    if (relationship_type == relationship_types['no_relationship']):
        relationship['relationship_type'] = relationship_types['{}_liked_{}'.format(username_prefix, other_username_prefix)]
    elif (relationship_type == relationship_types['{}_liked_{}'.format(other_username_prefix, username_prefix)]):
        relationship['relationship_type'] = relationship_types['matched']
    elif (relationship_type == relationship_types['{}_ignored_{}'.format(other_username_prefix, username_prefix)]):
        relationship['relationship_type'] = relationship_types['{}_liked_{}_ignored'.format(username_prefix, other_username_prefix)]
    elif (relationship_type == relationship_types['{}_ignored_{}'.format(username_prefix, other_username_prefix)]):
        relationship['relationship_type'] = relationship_types['{}_liked_{}'.format(username_prefix, other_username_prefix)]
    elif (relationship_type == relationship_types['both_ignored']):
        relationship['relationship_type'] = relationship_types['{}_liked_{}_ignored'.format(username_prefix, other_username_prefix)]
    elif (relationship_type == relationship_types['{}_liked_{}_ignored'.format(other_username_prefix, username_prefix)]):
        relationship['relationship_type'] = relationship_types['matched']

    relationship['relationship_date'] = get_date_string(get_current_date())

    save_relationship(relationship)


def save_relationship(relationship):
    client = _get_client()
    client.put(relationship)


def delete_relationship(relationship_id):
    client = _get_client()
    key = _load_key(client, _RELATIONSHIP_ENTITY, relationship_id)
    client.delete(key)


def unlike_user(username, other_username):
    sorted_usernames = sort_users(username, other_username)
    relationship = get_relationship(sorted_usernames)

    if relationship is None:
        return

    relationship_type = relationship['relationship_type']

    username_prefix = 'first'
    other_username_prefix = 'second'
    if (sorted_usernames[2] == 1):  # Checks which order the usernames are in.
        username_prefix = 'second'
        other_username_prefix = 'first'

    if (relationship_type == relationship_types['no_relationship']):
        delete_relationship(sorted_usernames[3])
        return
    elif (relationship_type == relationship_types['{}_liked_{}'.format(username_prefix, other_username_prefix)]):
        delete_relationship(sorted_usernames[3])
        return
    elif (relationship_type == relationship_types['matched']):
        relationship['relationship_type'] = relationship_types['{}_liked_{}'.format(other_username_prefix, username_prefix)]

    relationship['relationship_date'] = get_date_string(get_current_date())

    save_relationship(relationship)


def get_liked_users(username):
    client = _get_client()

    first_query = client.query(kind=_RELATIONSHIP_ENTITY)
    first_query.add_filter('relationship_type', '=', relationship_types['first_liked_second'])
    first_query.add_filter('first_username', '=', username)
    first_query_results = list(first_query.fetch(100))

    first_list = []
    for relationship in first_query_results:
        first_list.append(relationship['second_username'])

    second_query = client.query(kind=_RELATIONSHIP_ENTITY)
    second_query.add_filter('relationship_type', '=', relationship_types['second_liked_first'])
    second_query.add_filter('second_username', '=', username)
    second_query_results = list(second_query.fetch(100))

    second_list = []
    for relationship in second_query_results:
        second_list.append(relationship['first_username'])

    liked_list = first_list + second_list
    return liked_list


def get_matched_users(username):
    client = _get_client()

    first_query = client.query(kind=_RELATIONSHIP_ENTITY)
    first_query.add_filter('relationship_type', '=', relationship_types['matched'])
    first_query.add_filter('first_username', '=', username)
    first_query_results = list(first_query.fetch(100))

    first_list = []
    for relationship in first_query_results:
        first_list.append(relationship['second_username'])

    second_query = client.query(kind=_RELATIONSHIP_ENTITY)
    second_query.add_filter('relationship_type', '=', relationship_types['matched'])
    second_query.add_filter('second_username', '=', username)
    second_query_results = list(second_query.fetch(100))

    second_list = []
    for relationship in second_query_results:
        second_list.append(relationship['first_username'])

    matched_list = first_list + second_list
    return matched_list


def make_match(username):
    """Matches with a random user in the same city and state."""
    client = _get_client()
    user = _load_entity(client, _USER_ENTITY, username)

    other_user_query = client.query(kind=_USER_ENTITY)
    other_user_query.add_filter('city', '=', user['city'])
    other_user_query.add_filter('state', '=', user['state'])
    other_user_results = list(other_user_query.fetch(100))

    other_user_list = []
    for potential_match in other_user_results:
        other_user_list.append(potential_match['username'])

    relationship = None
    for other_username in other_user_list:
        if (other_username == username):  # Skips if the current user was selected.
            continue
        sorted_usernames = sort_users(username, other_username)
        relationship = get_relationship(sorted_usernames)

        username_prefix = 'first'
        other_username_prefix = 'second'
        if (sorted_usernames[2] == 1):  # Checks which order the usernames are in.
            username_prefix = 'second'
            other_username_prefix = 'first'

        if relationship is None:
            relationship = create_relationship(sorted_usernames)
            relationship['relationship_type'] = relationship_types['{}_ignored_{}'.format(username_prefix, other_username_prefix)]  # Sets the status to ignored so the user is not shown next time.
        elif (relationship['relationship_type'] == relationship_types['no_relationship']):
            relationship['relationship_type'] = relationship_types['{}_ignored_{}'.format(username_prefix, other_username_prefix)]  # Sets the status to ignored so the user is not shown next time.
        elif (relationship['relationship_type'] == relationship_types['{}_liked_{}'.format(other_username_prefix, username_prefix)]):
            relationship['relationship_type'] = relationship_types['{}_liked_{}_ignored'.format(other_username_prefix, username_prefix)]  # Sets the status to ignored so the user is not shown next time.
        else:
            continue

        relationship['relationship_date'] = get_date_string(get_current_date())

        save_relationship(relationship)
        return other_username
    return ''


def get_all_locations():
    """Lookup all user locations for google maps"""
    client = _get_client()
    query = client.query(kind=_USER_ENTITY)

    results = list(query.fetch())
    return results


def save_new_user(user, passwordhash):
    """Save the user details to the datastore."""
    client = _get_client()
    entity = datastore.Entity(_load_key(client, _USER_ENTITY, user.username))
    entity['username'] = user.username
    entity['email'] = user.email
    entity['passwordhash'] = passwordhash
    entity['about'] = ''
    entity['firstname'] = ''
    entity['lastname'] = ''
    entity['age'] = ''
    entity['gender'] = ''
    entity['state'] = ''
    entity['city'] = ''
    entity['address'] = ''
    entity['bio'] = ''
    entity['avatar'] = ''
    client.put(entity)


def save_about_user(username, about):
    """Save the user's about info to the datastore."""
    client = _get_client()
    user = _load_entity(client, _USER_ENTITY, username)
    user['about'] = about
    client.put(user)


def create_data(num=50, state='PA', city='Pittsburgh'):
    """Populates Datastore with sample users. This can only be used by admins."""
    random_id = random.randint(0, 2147483647)

    for i in range(num):
        client = _get_client()
        entity = datastore.Entity(_load_key(client, _USER_ENTITY, 'sample_username{}_{}'.format(random_id, i)))
        entity['username'] = 'sample_username{}_{}'.format(random_id, i)
        entity['email'] = 'sample_email{}@example.com'.format(i)
        entity['passwordhash'] = get_password_hash(str(i))
        entity['about'] = 'Sample about section {}'.format(i)
        entity['firstname'] = 'First{}'.format(i)
        entity['lastname'] = 'Last{}'.format(i)
        entity['age'] = str(i)
        entity['gender'] = 'gender{}'.format(i)
        entity['state'] = state
        entity['city'] = city
        entity['address'] = str(random.randint(0, 6000)) + ' Forbes Avenue'
        entity['bio'] = 'Sample bio {}'.format(i)
        entity['avatar'] = 'mushroom.png'
        client.put(entity)


def get_password_hash(pw):
    """This will give us a hashed password that will be extremlely difficult to
    reverse.  Creating this as a separate function allows us to perform this
    operation consistently every time we use it."""
    encoded = pw.encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()