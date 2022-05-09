from flask import Response, render_template, make_response, request, session, redirect, url_for
from email.utils import parseaddr
from main import app
import datetime
import data

# Part of this code is based on the code found at https://github.com/timothyrjames/cs1520 with permission from the instructor

# Dictionary that contains the messages that will be displayed on error.html.
error_codes = {
	"match_not_found": "There were no roommates that matched your preferences. Try a more broad search."
}

@app.route('/')
@app.route('/index.html')
def root():
	return render_template('index.html', page_title='Home')


@app.route('/signup.html')
def signup():
	return render_template('signup.html', page_title='Sign Up')


@app.route('/signin.html')
def signin():
	return render_template('signin.html', page_title='Sign In')


@app.route('/editprofile.html')
def editprofile():
	return render_template('editprofile.html', page_title='Edit Profile')


@app.route('/signin_user', methods=['POST'])
def signin_user():
	username = request.form.get('username')
	password = request.form.get('password')
	passwordhash = data.get_password_hash(password)
	user = data.load_user(username, passwordhash)
	if user:
		session['user'] = user.username
		return redirect(url_for('profile_page', username=username))
	else:
		# return show_login_page()
		return redirect('/signin.html')


@app.route('/logout')
def logout_user():
	session.pop('user', None)
	return redirect(url_for('root'))


@app.route('/profile/<username>')
def profile_page(username):
	user = data.load_public_user(username)
	current_user = session['user']
	is_owner = False  # Checks if the user is looking at his own profile
	if current_user == user.username:
		is_owner = True
	liked_dict = data.get_liked_users(current_user)
	is_liked = False
	if username in liked_dict:
		is_liked = True
	return render_template('profile.html', page_title=username, name_text=("{} {}".format(user.firstname, user.lastname)), gender_text=user.gender, age_text=str(user.age), state_text=user.state, city_text=user.city, about_text=user.about, bio_text=user.bio, other_username=user.username, is_owner=is_owner, is_liked=is_liked, avatar=user.avatar)


@app.route('/browse')
def browse():
	return render_template('browse.html', page_title="Browse")


# TODO: Ensure that the username is unique
@app.route('/register', methods=['POST'])
def register_user():
	username = request.form.get('username')
	password1 = request.form.get('password1')
	password2 = request.form.get('password2')
	email = request.form.get('email')
	errors = []
	if password1 != password2:
		errors.append('Passwords do not match.')
	email_parts = parseaddr(email)
	if len(email_parts) != 2 or not email_parts[1]:
		errors.append('Invalid email address: ' + str(email))
	user = data.User(username, email)
	if errors:
		# return show_page('/signup.html', 'Sign Up', errors=errors)
		pass
	else:
		passwordhash = data.get_password_hash(password1)
		data.save_new_user(user, passwordhash)
		session['user'] = user.username
		return redirect('/editprofile.html')


# TODO: Redirect to the signup page if the user is not signed in.
# TODO: Fill in each text area with what the user already has so the information is not wiped each time.
@app.route('/updateprofile', methods=['POST'])
def update_profile():
	firstname = request.form.get('firstname')
	lastname = request.form.get('lastname')
	age = request.form.get('age')
	gender = request.form.get('gender')
	state = request.form.get('state')
	city = request.form.get('city')
	about = request.form.get('about')
	bio = request.form.get('bio')
	avatar = request.form.get('avatar')
	username = session['user']
	data.save_user_profile(username=username, firstname=firstname, lastname=lastname, age=age, gender=gender, state=state, city=city, about=about, bio=bio, avatar=avatar)
	return redirect(url_for('profile_page', username=username))


@app.route('/likeuser/<other_username>')
def like_user(other_username):
	username = session['user']
	data.like_user(username, other_username)
	return "success", 200


@app.route('/unlikeuser/<other_username>')
def unlike_user(other_username):
	username = session['user']
	data.unlike_user(username, other_username)
	return "success", 200


@app.route('/findmatch')
def find_match():
	other_username = data.make_match(session['user'])
	if other_username:
		return redirect(url_for('profile_page', username=other_username))
	else:
		return redirect(url_for('error_page', error_type="match_not_found"))


@app.route('/matches')
def match_list():
	username = session['user']
	liked_users = data.get_liked_users(username)
	matched_usernames = []
	waiting_usernames = []
	for user in liked_users.keys():
		if username in data.get_liked_users(user).keys():
			matched_usernames.append(user)
		else:
			waiting_usernames.append(user)
	return render_template('matchlist.html', page_title="My Matches", current_user=username, matches=matched_usernames, num_matches=len(matched_usernames), waiting=waiting_usernames, page_index=0)



@app.route('/chat/', methods=['GET','POST'])
def load_chatroom():
	username = session['user']
	current_user = request.args.get('user')
	other_user = request.args.get('other')

	chatroom = data.load_chatroom(user, other)
	if chatroom is None:
		data.save_new_chatroom(user, other)
		chatroom = data.load_chatroom(user, other)
	feed = chatroom['messages']
	
	if request.method == 'POST':

		now = datetime.datetime.now().replace(microsecond=0).time()
		message = u'[%s %s] %s' % (now.isoformat(), username, request.form['message'])
		app.logger.info('Message: %s', message)
		
		data.save_message(current_user, other_user, message)
		feed.append(message)

	return render_template('chatroom.html', page_title="Chat", current_user=user, other_user=other, messages=feed)

@app.route('/stream/<user>/<other>', methods=['GET','POST'])
def stream(user, other):

	def pushData(message):
		yield message
	if request.method == 'POST':
		username = session['user']
		now = datetime.datetime.now().replace(microsecond=0).time()
		message = u'[%s %s] %s' % (now.isoformat(), username, request.form['message'])
		return Response(pushData(message), mimetype="text/event-stream")
	return redirect('/chat/'+user+'/'+other)

@app.route('/error')
def error_page():
	value = request.args['error_type']
	return render_template('error.html', page_title="Error", error_message=error_codes[value])


@app.route('/addsampleusers/')
def add_sample_users():
	num = int(request.args.get('num', '50'))
	if num is not None and num > 1000:
		num = 1000  # Caps the maximum number
	if session['user'] == 'admin':  # Only allow the admin to do this.
		data.create_data(num=num, state=request.args.get('state', 'PA'), city=request.args.get('city', 'Pittsburgh'))
	return "success", 200