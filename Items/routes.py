from Items import app, mongodb_client
from flask import jsonify, make_response, render_template, request, redirect, flash, url_for

from bson import ObjectId

from Items import db
from datetime import datetime
ITEMS_PER_PAGE = 10

# page should start from 0
@app.route("/items/<int:page>", methods = ['GET'])
def get_items(page):
    skip = (page - 1) * ITEMS_PER_PAGE
    try:
        items = list(db.Items.find({}).sort("date_created", -1).skip(skip).limit(ITEMS_PER_PAGE))
        for item in items:
            item["_id"] = str(item["_id"])
        response_data = {"items": items}

    # Return JSON response
        response = make_response(jsonify(response_data))
        response.headers["Content-Type"] = "application/json"
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route("/items/<string:item_id>", methods = ['GET'])
def get_item_by_id(item_id):
    item_id_object = ObjectId(item_id)
    try:
        item = db.Items.find_one({"_id": item_id_object})
        if item is None:
            return "Item does not exist", 404
        item["_id"] = str(item["_id"])


    # Return JSON response
        response = make_response(jsonify(item))
        response.headers["Content-Type"] = "application/json"
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route("/items/search", methods = ['GET'])
def search_item_by_titel():
    query = request.form.get('title')
    try:
        items = list(db.Items.find({"title":{'$regex' : '.*' + query + '.*'}}).sort("date_created", -1))
        for item in items:
            item["_id"] = str(item["_id"])
        response_data = {"items": items}


    # Return JSON response
        response = make_response(jsonify(response_data))
        response.headers["Content-Type"] = "application/json"
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route("/items", methods = ['POST'])
def create_item():
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    response_data = {
        "title": request.form.get('title'),
        "description": request.form.get('description'),
        "price": request.form.get('price'),
        "user_id": request.form.get('user_id'),
        "date_created": datetime.utcnow()
    }

    file = request.files['image']

    try:
        # Store the file in GridFS
        file_id = mongodb_client.save_file(file.filename, file)

        # Add file_id to the item data
        response_data['image'] = str(file_id)

        result = db.Items.insert_one(response_data)
        inserted_id = str(result.inserted_id)
        response_data['_id'] = inserted_id

        response = make_response(jsonify(response_data))
        response.headers["Content-Type"] = "application/json"
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    
       


@app.route("/items/<string:item_id>", methods = ['DELETE'])
def delete_item(item_id):
    try:
        item = db.Items.find_one_and_delete({"_id": ObjectId(item_id)})
        if item is None:
            return "Item does not exist", 404
        item["_id"] = str(item["_id"])


    # Return JSON response
        response = make_response(jsonify(item))
        response.headers["Content-Type"] = "application/json"
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/items/<string:item_id>", methods = ['PATCH'])
def update_item_by_id(item_id):
    item_id_object = ObjectId(item_id)
    try:
        # Retrieve updated data from the request form
        updated_data = {}
        for key, value in request.form.items():
            # Ignore fields with empty values
            if value and key != 'user_id':
                updated_data[key] = value
        if 'image' in request.files:
            file_id = mongodb_client.save_file(request.files['image'].filename, request.files['image'])
            updated_data['image'] = str(file_id)


        item = db.Items.update_one({"_id": item_id_object}, {'$set': updated_data})
        if item.modified_count > 0:
            # Fetch the updated document from the database
            item = db.Items.find_one({'_id': ObjectId(item_id)})
            item["_id"] = str(item["_id"])
            response = make_response(jsonify(item))
            response.headers["Content-Type"] = "application/json"
            return response, 200
        else:
            # Return response indicating no updates were made
            return jsonify({'message': 'No updates made'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500