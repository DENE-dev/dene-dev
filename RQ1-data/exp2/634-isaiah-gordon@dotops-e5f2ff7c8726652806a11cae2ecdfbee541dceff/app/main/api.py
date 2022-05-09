from flask import request, current_app, make_response
from . import interface, secrets
import jwt
import json
from functools import wraps
import datetime
import pytz
from app.email_module import email_master

from app.sql import sql_master as database


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        try:
            token = request.headers.get('token')
        except:
            return 'Authentication token is required.'

        try:
            decoded_token = jwt.decode(token, current_app.config['SECRET_KEY'])

        except:
            return 'Invalid authentication token.'

        return f(decoded_token, *args, **kwargs)

    return decorated


@interface.route('/')
def index():
    return 'Welcome to the Dotops API!'


# Route for handling the login page logic
@interface.route('/generate_token/<store_number>')
def generate_token(store_number):
    auth = request.authorization

    if auth and (auth.username != secrets.api_user or auth.password != secrets.api_password):
        return make_response('Could not verify!', 401, {'WWW-Authenticate' : 'Basic realm="Login Required'})

    elif auth and (auth.username == secrets.api_user and auth.password == secrets.api_password):
        token = jwt.encode({'store': store_number, 'issuer': auth.username, 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1095)}, current_app.config['SECRET_KEY'])

        return token

    return make_response('Authorization is required!', 401, {'WWW-Authenticate': 'Basic realm="Login Required'})


@interface.route('/find_next_game', methods=['GET'])
@token_required
def find_next_game(decoded_token):
    print('Checking the schedule for next game at {0}'.format(decoded_token['store']))

    utc_time = datetime.datetime.utcnow()

    seconds_since_midnight = (utc_time - utc_time.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    utc_delta = timedelta(seconds=seconds_since_midnight)

    utc_dt = datetime.datetime.utcnow()
    utc_day = utc_dt.strftime('%a')

    next_game = database.query("""
            SELECT id, start_time, end_time, product, stores
            FROM scheduled_games

            WHERE start_time = (
            SELECT MIN(start_time)
            FROM scheduled_games
            WHERE '{1}' <= start_time
            )
            
            AND status = 0
            AND day_of_week = '{0}'
            AND stores LIKE '%{2}%'
            
        """.format(utc_day, utc_delta, decoded_token['store']), return_dict=True)

    if not next_game:
        return make_response('', 200)

    next_game = next_game[0]

    next_game['start_time'] = str(next_game['start_time'])
    next_game['end_time'] = str(next_game['end_time'])
    next_game['stores'] = next_game['stores'].strip('][').split(', ')

    json_next_game = json.dumps(next_game)

    return make_response(json_next_game, 200)


@interface.route('/lookup_stores/<store_list>', methods=['GET'])
@token_required
def lookup_stores(self, store_list):

    sql_store_list = store_list.replace('[', '(').replace(']', ')')
    store_list = store_list.strip('][').split(', ')


    store_details = database.query("""
                SELECT store_number, store_name, store_short_name, store_image
                FROM store_profiles
                WHERE store_number IN {0}
            """.format(sql_store_list), return_dict=True)

    store_dict = {}
    for store in store_details:
        store_number = store.pop('store_number')
        store_dict[store_number] = store

    json_store_dict = json.dumps(store_dict)

    return make_response(json_store_dict, 200)


@interface.route('/add_score/<game_id>', methods=['POST'])
@token_required
def add_score(decoded_token, game_id):
    json_post = request.get_json()

    database.command("""
                UPDATE scheduled_games
                SET total_sold{0} = total_sold{0} + {1},
                transactions{0} = transactions{0} + {2}
                WHERE id = {3}
            """.format(json_post['score_index'], json_post['total_sold'], json_post['transactions'], game_id))

    return make_response('Success 200!', 200)


@interface.route('/get_score/<game_id>', methods=['GET'])
@token_required
def get_score(self, game_id):

    all_scores = database.query("""
                SELECT total_sold0, transactions0, total_sold1, transactions1, total_sold2, transactions2
                FROM scheduled_games
                WHERE id = {0}
            """.format(game_id), return_dict=True)

    json_all_scores = json.dumps(all_scores[0])

    return make_response(json_all_scores, 200)


def strfdelta(timedelta):

    seconds = timedelta.total_seconds()

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    as_time = datetime.datetime(2000, 1, 1, int(hours), int(minutes), int(seconds))
    string_time = as_time.strftime("%H:%M:%S")

    return string_time


@interface.route('/conclude_day', methods=['GET'])
@token_required
def conclude_day(self):

    # RECORD RESULTS
    utc_dt = datetime.datetime.utcnow()
    utc_day = utc_dt.strftime('%a')

    games_today = database.query("""
            SELECT *
            FROM scheduled_games

            WHERE day_of_week = '{0}'
            AND total_sold0 > 0
            AND total_sold1 > 0
            AND status = 0
        """.format(utc_day), return_dict=False)

    if len(games_today) != 2:
        return str('No games to conclude!')

    for x, game in enumerate(games_today):
        game_mod = list(game)
        del game_mod[0:2]

        game_mod[0] = utc_dt.strftime("%Y-%m-%d")
        game_mod[1] = strfdelta(game[3])
        game_mod[2] = strfdelta(game[4])

        games_today[x] = tuple(game_mod)

    database.command(
        """
            INSERT INTO game_records (
            date, start_time, end_time, product, stores,
            transactions0, total_sold0,
            transactions1, total_sold1,
            transactions2, total_sold2
            )
            VALUES {0}
        """.format(games_today[0])
    )

    # SEND EMAILS
    utc_now = pytz.utc.localize(datetime.datetime.utcnow())
    ast_now = utc_now.astimezone(pytz.timezone("America/Halifax"))

    store_details = database.query("""
                SELECT store_number, email, store_name
                FROM store_profiles
            """.format(), return_dict=True)

    for store_profile in store_details:
        store_number = store_profile['store_number']

        email_text_data = {
            # Per store
            'this_store_name': store_profile['store_name'],
            'date': ast_now.strftime('%A, %B %d, %Y'),

            'this_vic_name': store_profile['store_name'],
            'this_vic_total': 'N/A',

            'other_vic_name': 'Other Store',
            'other_vic_total': 'N/A',
        }

        # store_games : Games played by this store.
        # game_stores : Stores that played the current game.

        store_games = []
        game_number = 0
        for game in games_today:
            game_stores = game[4].strip('][').split(', ')

            if str(store_number) in game_stores:
                store_games.append(game)
            else:
                continue

            if game[5] < game[7]:
                score_order = game_stores
                score_order.reverse()
            else:
                score_order = game_stores

            game_times = [game[1], game[2]]
            utc_now = datetime.datetime.utcnow()

            for idx, time in enumerate(game_times):
                time_obj = datetime.datetime.strptime(time, '%H:%M:%S')
                datetime_obj = time_obj.replace(year=utc_now.year, month=utc_now.month, day=utc_now.day)
                utc_obj = pytz.utc.localize(datetime_obj)
                ast_time = utc_obj.astimezone(pytz.timezone("America/Halifax"))
                str_time = ast_time.strftime('%I:%M %p')
                game_times[idx] = str_time

            if score_order[0] == game_stores[0]:
                place_score_position = [1, 0]
            else:
                place_score_position = [0, 1]

            merge_text_data = {
                # Per game
                'product_': database.product_lookup(game[3], 'name'),
                'game_time_': game_times[0] + ' - ' + game_times[1],

                'first_store_name_': database.store_profile_lookup(score_order[0], 'store_name'),
                'first_store_total_sold_': [game[5], game[7]][place_score_position[0]],
                'first_store_transactions_': [game[6], game[8]][place_score_position[0]],

                'second_store_name_': database.store_profile_lookup(score_order[1], 'store_name'),
                'second_store_total_sold_': [game[5], game[7]][place_score_position[1]],
                'second_store_transactions_': [game[6], game[8]][place_score_position[1]]
            }

            game_number += 1
            defined_key_merge_text_data = {}

            for key in merge_text_data:
                merge_text_data[key] = str(merge_text_data[key])

            for key in merge_text_data:
                defined_key_merge_text_data[key + str(game_number)] = merge_text_data[key]

            email_text_data.update(defined_key_merge_text_data)

        if not store_games:
            continue

        else:

            images = {
                'front_page_image': 'https://media.tenor.com/images/1bcfaadb7ed926566b25b16f256a5d1f/tenor.gif',
                'advice_image': 'https://media.tenor.com/images/1bcfaadb7ed926566b25b16f256a5d1f/tenor.gif',

                'product_image_1': 'https://storage.googleapis.com/dotops.app/email_images/products/' + games_today[0][3] + '.png',
                'product_image_2': 'https://storage.googleapis.com/dotops.app/email_images/products/' + games_today[1][3] + '.png'
            }

            email_master.send_email(
                'isaiah.gordon.developer@gmail.com',
                utc_now.strftime('%H:%M:%S'),
                'app/email_module/email_templates/email_template.html',
                {'text': email_text_data, 'images': images}
            )

    return str('CODE 200')