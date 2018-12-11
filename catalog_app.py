from flask import Flask, render_template,request, redirect, url_for, jsonify, flash
from database_setup import Category, Item
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item


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
	
