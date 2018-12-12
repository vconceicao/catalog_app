from flask import Flask, render_template,request, redirect, url_for, jsonify, flash, session as login_session, make_response
from database_setup import Category, Item
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item
import random
import string
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
import httplib2
import json
import requests


CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']





app = Flask('__name__')
engine = create_engine('sqlite:///catalog.db',  connect_args={'check_same_thread': False}, echo=True)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()



@app.route('/')
def main():
	#returns all categories and lastest items'
	#categories = [{'title':'Soccer'}, {'title':'Vinicius'}, {'title':'November'}]
	#items = [{'title': 'SnowBoard'},  {'title': 'SnowBoard2'}, {'title': 'SnowBoard3'}, {'title': 'SnowBoard4'}]

	items = session.query(Item).all()
	categories = session.query(Category).all()
	return render_template('lastest_items.html', categories = categories, items=items)
	
@app.route('/login')
def showLogin():
	state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
	login_session['state'] = state
	return render_template('login.html', STATE=state)

@app.route('/gconnect', methods=['POST'])	
def gconnect():
	if request.args.get('state')!=login_session['state']:
		response = make_response(json.dumps('Invalid statues'), 401)
		response.headers['Content-Type']='application/json'
		return response
	code = request.data
	try:
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)
	except FlowExchangeError:
		response = make_response(json.dumps('Failed to upgrade the auth code'), 401)
		response.headers['Content-Type']='application/json'
		return response
		
	access_token = credentials.access_token
	print access_token
	print 'olha '
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
	h = httplib2.Http()
	result=json.loads(h.request(url, 'GET')[1])
	print result
	
	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')), 500)
		response.headers['Content-Type']='application/json'
		return
	
	gplus_id = credentials.id_token['sub']
	
	
	
	#verify that the access token is used for the intended user.
	if result['user_id'] != gplus_id:
		response = make_response('Token user ID doesnt match given user ID', 401)
		response.headers['Content-Type']= 'application/json'
		return response
		
	#verify that the access token is valid for this app
	if result['issued_to']!= CLIENT_ID:
		response = make_response('Token client does not match the app', 401)
		response.headers['Content-Type']= 'application/json'
		return response
		
	
	stored_access_token = login_session.get('access_token') 
	stored_gplus_id = login_session.get('gplus_id')
	
	if stored_access_token is not None and gplus_id==stored_gplus_id:
		response = make_response(json.dumps('Current user already connected.'),200)
		response.headers['Content-Type']= 'application/json'
		return response
	
		
	# Store the access token in the session for later use.
	login_session['access_token'] = credentials.access_token 
	login_session['gplus_id'] =  gplus_id
	
	userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
	params = {'access_token': credentials.access_token, 'alt': 'json'}
	answer = requests.get(userinfo_url, params=params) 
	
	data =  answer.json()
	
	
	
	
	login_session['username'] = data['name'] 
	login_session['picture'] = data['picture']  
	
	output =''
	output += '<h1>Welcome, '
	output += login_session['username']
	output += '! </h1>'
	output += '<img src="'
	output += login_session['picture']
	output += '" style="width:300px; height:300px"'	
	
	flash('You are now logged in as %s' %login_session['username'] )
	print 'done'
	return output


@app.route('/gdisconnect')
def gdisconnect():


	access_token = login_session.get('access_token')
	print access_token
	if access_token is None:
		print 'Access toke is none'
	url = ('https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session.get('access_token'))
	h = httplib2.Http()
	result=h.request(url, 'GET')[0]
	print 'resultado %s' % result['status']
	if result['status'] == '200' :
	 del login_session['access_token']
	 del login_session['gplus_id']
	 del login_session['username'] 
	 del login_session['picture']
	
	 response = make_response(json.dumps('User successfully disconnected'), 200)
	 response.headers['Content-Type'] = 'application/json'
	 return response
	else:
		response = make_response(json.dumps('Something went wrong'), 400)
		response.headers['Content-Type'] = 'application/json'
		return response
	
	
@app.route('/catalog/<category_title>/items')
def getItems(category_title):
	#return 'Shows all categories and all items of %s' % category_title
	#categories = [{'title':'Soccer'}, {'title':'Vinicius'}, {'title':'November'}]
	categories = session.query(Category).all()
	category = session.query(Category).filter_by(title=category_title).one()
	items = session.query(Item).filter_by(category_id = category.id).all()
	return render_template('selected_items.html', categories = categories, items=items)


@app.route('/catalog/<category_title>/<item_title>')
def getItem(category_title, item_title):
	#return 'Shows the details of  %s' % item_title
	#item = Item(id=1, title="Hello", description = "Hello World klajsldjflajsjdlfjalsjdfljasldfjlasdjlfjasdlfjlasdjfjljsdflkj")
	item = session.query(Item).filter_by(title = item_title).one()
	return render_template('item_detail.html', item=item)

@app.route('/catalog/item/new', methods= ['GET', 'POST'])
def add_item():
	#return 'Adds an item'
	categories = session.query(Category).all()
	
	
	if 'username' not in login_session:
		return redirect('/login')
		
	if request.method == 'POST':
		#get form values
		
		title = request.form['item_title']
		description = request.form['item_description']
		category_id = request.form['category_id']
		
		category = session.query(Category).filter_by(id=category_id).one()
		
		session.add(Item(title=title, description=description, category=category))
		session.commit()
		flash('A new item %s was added! ' % title)
		#return redirect(url_for('getItems', category_title = category.title))
		return redirect(url_for('main'))
		
		
	else:
		
		return render_template('add_item.html', categories = categories)

@app.route('/catalog/<item_title>/edit', methods=['GET', 'POST'])
def edit_item(item_title):
	#return 'Edits %s' %item_title
	
	if 'username' not in login_session:
		return redirect('/login')
	
	
	item = session.query(Item).filter_by(title = item_title).one()
	categories = session.query(Category).filter(Category.id != item.category.id).all()
	
	if request.method=='POST':
		title = request.form['item_title']
		description = request.form['item_description']
		category_id = request.form['category_id']
		
		category = session.query(Category).filter_by(id=category_id).one()
		
	
		item.title = title
		item.description = description
		item.category = category
		
		session.add(item)
		session.commit()
		flash('The item was edited!')
			
		return redirect(url_for('getItems', category_title = category.title))
		
	else:
	
		return render_template('edit_item.html', item=item, categories = categories)

@app.route('/catalog/<item_title>/delete', methods=['GET', 'POST'])
def remove_item(item_title):
	print login_session
	if 'username' not in login_session:
		return redirect('/login')
	
	
	#return 'Removes %s' % item_title
	#item = Item(id=1, title="Hello", description = "Hello World klajsldjflajsjdlfjalsjdfljasldfjlasdjlfjasdlfjlasdjfjljsdflkj")
	item = session.query(Item).filter_by(title = item_title).one()
	category_title =  item.category.title
	if request.method == 'POST':
	
		session.delete(item)
		session.commit()
		flash('The item was removed')
		return redirect(url_for('getItems', category_title = category_title))
	
	else:
	
		return render_template('delete_item.html', item_title=item.title)

@app.route('/catalog/catalog.json')
def api_json():
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

#@app.route('/catalog/catalog.json/<category_title>')
def api_json_category(category_title):
	category = session.query(Category).filter_by(title=category_title).one()
	items = session.query(Item).filter_by(category_id = category.id).all()
	
	json_cat = category.serialize
	json_response = []
	json_items =[]
	
	for i in items:
		json_items.append(i)
	
	json_cat['items'] = json_items
	json_response.append(json_cat)
	
	return jsonify(Category = json_response)
	
@app.route('/catalog/catalog.json/<item_title>')	
def api_json_item(item_title):
	item = session.query(Item).filter_by(title=item_title).one()
	
	return jsonify(Item = item.serialize)
	


if __name__ == '__main__':
	app.secret_key = 'super secret key'
	app.debug = True
	app.run(host='0.0.0.0', port=5000)
	
