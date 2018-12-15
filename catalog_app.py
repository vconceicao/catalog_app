from flask import Flask, render_template,request, redirect, url_for, jsonify, flash, session as login_session, make_response
from database_setup import Category, Item
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
import random
import string
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
import httplib2
import json
import requests

# Google Client ID
CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']


app = Flask('__name__')
engine = create_engine('sqlite:///catalogwithusers.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()



@app.route('/')
def main():
	"""
	Returns all categories and lastest items added'
	"""
	items = session.query(Item).order_by("id desc")
	categories = session.query(Category).all()
	return render_template('lastest-items.html', categories = categories, items=items, login_session = login_session)
	
@app.route('/login')
def showLogin():
	"""
  Renders the login page.
  """
	state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
	login_session['state'] = state
	return render_template('login.html', STATE=state)

@app.route('/gconnect', methods=['POST'])	
def gconnect():
	"""
  Collects data from Google Sign In API and put it into login session.
  """
  
  # Validates state token
	if request.args.get('state')!=login_session['state']:
		response = make_response(json.dumps('Invalid statues'), 401)
		response.headers['Content-Type']='application/json'
		return response
	
	# Obtain authorization code	
	code = request.data
	
	
	
	try:
		# Upgrade the authorization code into a credentials object
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)
	except FlowExchangeError:
		response = make_response(json.dumps('Failed to upgrade the auth code'), 401)
		response.headers['Content-Type']='application/json'
		return response
		
	
	# Check that the access token is valid.	
	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
	h = httplib2.Http()
	result=json.loads(h.request(url, 'GET')[1])
	
	# If there's an error in the result, abort.
	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')), 500)
		response.headers['Content-Type']='application/json'
		return
		
	
	
	#verify that the access token is used for the intended user.
	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
		response = make_response('Token user ID doesnt match given user ID', 401)
		response.headers['Content-Type']= 'application/json'
		return response
		
	#verify that the access token is valid for this app
	if result['issued_to']!= CLIENT_ID:
		response = make_response('Token client does not match the app', 401)
		response.headers['Content-Type']= 'application/json'
		return response
		
	
	#verify if the user is already connected	
	stored_access_token = login_session.get('access_token') 
	stored_gplus_id = login_session.get('gplus_id')
	if stored_access_token is not None  and gplus_id==stored_gplus_id:
		response = make_response(json.dumps('Current user already connected.'),200)
		response.headers['Content-Type']= 'application/json'
		return response
	
		
	# Store the access token in the session for later use.
	login_session['access_token'] = credentials.access_token 
	login_session['gplus_id'] =  gplus_id
	
	
	# Get data from the user and put it into the session
	userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
	params = {'access_token': credentials.access_token, 'alt': 'json'}
	answer = requests.get(userinfo_url, params=params) 
	
	data =  answer.json()
	
	login_session['username'] = data['name'] 
	login_session['picture'] = data['picture']  
	login_session['email'] = data['email']
	
	
	user_id =  getUserID(login_session.get('email'))
	
	if not user_id:
		user_id = createUser(login_session)
	
	login_session['user_id'] = user_id
	
	#Shows the  user picture and name and redirect it to the main page
	output =''
	output += '<h1>Welcome, '
	output += login_session['username']
	output += '! </h1>'
	output += '<img src="'
	output += login_session['picture']
	output += '" style="width:300px; height:300px">'	
	
	flash('You are now logged in as %s' %login_session['username'] )
	print 'done'
	return output



@app.route('/gdisconnect')
def gdisconnect():
	
	"""
    Check the access token to revoke it and delete login session variables.
  """
	access_token = login_session.get('access_token')
	print access_token
	if access_token is None:
		response = make_response(json.dumps('User is already disconnected'), 400)
		response.headers['Content-Type'] = 'application/json'
		return response
	
	#delete session variables
	del login_session['access_token']
	del login_session['gplus_id']
	del login_session['username']
	del login_session['email']
	del login_session['picture']	

	#revoke access token
	url = ('https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token )
	h = httplib2.Http()
	result=h.request(url, 'GET')[0]

	#Checks the result and redirect the user to the main if the result is ok
	if result['status'] == '200' :
		flash('User succesfully disconnected')
		return redirect(url_for('main'))
	else:
		response = make_response(json.dumps('Something went wrong'), 400)
		response.headers['Content-Type'] = 'application/json'
		return response
	
	
@app.route('/catalog/<category_title>/items')
def getItems(category_title):
	"""
	Return all categories and all items of the selected category
	"""
	categories = session.query(Category).all()
	category = session.query(Category).filter_by(title=category_title).one()
	items = session.query(Item).filter_by(category_id = category.id).all()
	return render_template('selected-items.html',category_title = category_title, categories = categories, items=items, login_session= login_session)


@app.route('/catalog/<category_title>/<item_title>')
def getItem(category_title, item_title):
	
	"""
	Return the selected item and its details
	"""
	item = session.query(Item).filter_by(title = item_title).one()
	isCreator = login_session.get('user_id') == item.user_id
	
	return render_template('item-details.html', item=item, isCreator = isCreator, login_session = login_session)

@app.route('/catalog/item/new', methods= ['GET', 'POST'])
def add_item():
	"""
	Return the page the add an item or the method to save the item in the database depending
	on the http method.
	"""
	categories = session.query(Category).all()
	
	
	if 'username' not in login_session:
		return redirect('/login')
	
				
	if request.method == 'POST':
		#Get form values
		title = request.form['item_title']
		description = request.form['item_description']
		category_id = request.form['category_id']
		user_id = login_session.get('user_id')
		
		
		#Save the item in the database
		session.add(Item(title=title, description=description, category_id=category_id, user_id=user_id))
		session.commit()
		
		flash('A new item %s was added! ' % title)

		return redirect(url_for('main'))
		
		
	else:
		#Return the page to add an item
		return render_template('add-item.html', categories = categories, login_session=login_session)

@app.route('/catalog/<item_title>/edit', methods=['GET', 'POST'])
def edit_item(item_title):
	
	"""
	Returns the page to edit an item, Otherwise the method to update the item 
	depending on the http method
	"""
	if 'username' not in login_session:
		return redirect('/login')
	
	
	#Retrieve the item selected
	item = session.query(Item).filter_by(title = item_title).one()
	categories = session.query(Category).filter(Category.id != item.category.id).all()
	
	if item.user.id != login_session['user_id']:
		return 'Not Allowed'
	
	
	if request.method=='POST':
		#Get the form data
		title = request.form['item_title']
		description = request.form['item_description']
		category_id = request.form['category_id']
		
		category = session.query(Category).filter_by(id=category_id).one()
			
		item.title = title
		item.description = description
		item.category_id = category_id
		
		#Save the updated item into the database
		session.add(item)
		session.commit()
		flash('The item was edited!')
			
		return redirect(url_for('getItems', category_title = category.title, login_session=login_session))
		
	else:
		#Return the page to edit an item
		return render_template('edit-item.html', item=item, categories = categories, login_session=login_session)

@app.route('/catalog/<item_title>/delete', methods=['GET', 'POST'])
def remove_item(item_title):

	"""
	Handles the deleting of item
	"""

	if 'username' not in login_session:
		return redirect('/login')
	
	#Retrieve the selected item
	item = session.query(Item).filter_by(title = item_title).one()
	category_title =  item.category.title
	
	if item.user.id != login_session['user_id']:
		return 'Not Allowed'
	
	
	if request.method == 'POST':
		#Removes the item from the database
		session.delete(item)
		session.commit()
		flash('The item was removed')
		return redirect(url_for('getItems', category_title = category_title))
	
	else:
		#Returns the page to delete an item
		return render_template('delete_item.html', item_title=item.title, login_session=login_session)

@app.route('/catalog/catalog.json')
def api_json():
		"""
    Returns all Categories and its items in JSON.
    """
		categories = session.query(Category).all()
		json_response = []
		for cat in categories: 
				json_category =  cat.serialize
				all_items = session.query(Item).filter_by(category_id = cat.id).all()
				json_items= []
				for i in all_items:
					json_items.append(i.serialize)
				
				json_category['items'] = json_items
				
				json_response.append(json_category)		
		return jsonify(Category = json_response)

	
@app.route('/catalog/catalog.json/<item_title>')	
def api_json_item(item_title):
	"""
  Returns a selected item in JSON form
  """
	item = session.query(Item).filter_by(title=item_title).one()
	
	return jsonify(Item = item.serialize)

def createUser(login_session):
	"""
	Creates a new user based in the session data given by Google Sign In Api
	"""
	newUser = User(username=login_session.get('username'), picture = login_session.get('picture'), email=login_session.get('email'))
	session.add(newUser)
	session.commit()
	
	user = session.query(User).filter_by(email=newUser.email).one()
	return user.id

def getUserInfo(user_id):
	"""
	Returns an user object based on its id
	"""
	user =session.query(User).filter_by(id=user_id).one()
	return user
	
def getUserID(user_email):
	"""
	Return an user id by an given email
	"""
	try:
		user =session.query(User).filter_by(email=user_email).one()
		return user.id
	except:
		return None
		
		
if __name__ == '__main__':
	app.secret_key = 'super secret key'
	app.debug = True
	app.run(host='0.0.0.0', port=5000)
	
