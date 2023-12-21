from Items import app, mongodb_client
from flask import jsonify, make_response, render_template, request, redirect, flash, url_for
import base64
from bson import ObjectId
import google.auth.crypt
import time
import requests
from google.auth import jwt
from Items import db
from datetime import datetime
ITEMS_PER_PAGE = 10

def verify_token(token):
    audience = "https://thriftustore-api-2ubvdk157ecvh.apigateway.user-microservice-402518.cloud.goog"
    # Public key URL for the service account
    public_key_url = 'https://www.googleapis.com/robot/v1/metadata/x509/jwt-182@user-microservice-402518.iam.gserviceaccount.com'
    
    # Fetch the public keys from the URL
    response = requests.get(public_key_url)
    public_keys = response.json()
    try:
        # Verify the JWT token using the fetched public keys
        print(token)
        #print(jwt.decode(token, certs=public_keys, audience=audience))
        decoded_token = jwt.decode(token, certs=public_keys, audience=audience)
        print(decoded_token)
        # The token is verified, and 'decoded_token' contains the decoded information
        return decoded_token
    except Exception as e:
        print(f"Error in decoding token: {str(e)}")
        return None

## TODO: need to check sign in for all requests
# pages should start from 1
@app.route("/items/<int:page>", methods = ['GET'])
def get_items(page):
    skip = (page - 1) * ITEMS_PER_PAGE
    try:
        items = list(db.Items.find({}).sort("date_created", -1).skip(skip).limit(ITEMS_PER_PAGE))
        for item in items:
            item["_id"] = str(item["_id"])
            file_id = ObjectId(item.get('image', None))
            
            if file_id:
                try:
                    # Retrieve image data from GridFS
                    file_data = db.fs.files.find_one({'_id': file_id})
                    image_data = db.fs.chunks.find_one({'files_id': file_id})
                    if file_data and image_data:
                        item['imageData'] = base64.b64encode(image_data['data']).decode('utf-8')  # Include image data in the item
                except Exception as e:
                    print(f"Error retrieving image data: {str(e)}")
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
        file_id = ObjectId(item.get('image', None)) 
        if file_id:
            try:
                # Retrieve image data from GridFS
                file_data = db.fs.files.find_one({'_id': file_id})
                image_data = db.fs.chunks.find_one({'files_id': file_id})
                if file_data and image_data:
                    item['imageData'] = base64.b64encode(image_data['data']).decode('utf-8')  # Include image data in the item
            except Exception as e:
                print(f"Error retrieving image data: {str(e)}")


    # Return JSON response
        response = make_response(jsonify(item))
        response.headers["Content-Type"] = "application/json"
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route("/items/search", methods = ['GET'])
def search_item_by_titel():
    query = request.args.get('title')
    try:
        items = list(db.Items.find({"title":{'$regex' : '.*' + query + '.*'}}).sort("date_created", -1))
        for item in items:
            item["_id"] = str(item["_id"])
            file_id = ObjectId(item.get('image', None))  
            if file_id:
                try:
                    # Retrieve image data from GridFS
                    file_data = db.fs.files.find_one({'_id': file_id})
                    image_data = db.fs.chunks.find_one({'files_id': file_id})
                    if file_data and image_data:
                        item['imageData'] = base64.b64encode(image_data['data']).decode('utf-8')  # Include image data in the item
                except Exception as e:
                    print(f"Error retrieving image data: {str(e)}")
        response_data = {"items": items}


    # Return JSON response
        response = make_response(jsonify(response_data))
        response.headers["Content-Type"] = "application/json"
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route("/items", methods = ['POST'])
def create_item():
    if 'Authorization' not in request.headers: return "Unauthorized user", 401

    token = request.headers.get('Authorization').split()[1]
    print(verify_token(token))
    if (verify_token(token)) is None:
        return "Unauthorized user", 401

    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    response_data = {
        "title": request.form.get('title'),
        "description": request.form.get('description'),
        "price": request.form.get('price'),
        #"user_id": request.form.get('user_id'),
        "user_id": str(verify_token(token)['id']),
        "date_created": datetime.utcnow(),
        "buyer_email": None,
        "rate": None
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
    if 'Authorization' not in request.headers: return "Unauthorized user", 401
    token = request.headers.get('Authorization').split()[1]
    if (verify_token(token)) is None:
        return "Unauthorized user", 401

    try:
        item = db.Items.find_one_and_delete({"_id": ObjectId(item_id), "user_id": str(verify_token(token)['id'])})
        if item is None:
            return "Item does not exist", 404
        item["_id"] = str(item["_id"])


    # Return JSON response
        response = make_response(jsonify(item))
        response.headers["Content-Type"] = "application/json"
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/items/<string:item_id>", methods = ['PUT'])
def update_item_by_id(item_id):
    if 'Authorization' not in request.headers: return "Unauthorized user", 401
    token = request.headers.get('Authorization').split()[1]
    if (verify_token(token)) is None:
        return "Unauthorized user", 401

    item_id_object = ObjectId(item_id)
    try:
        # Retrieve updated data from the request form
        updated_data = {}
        for key, value in request.form.items():
            # Ignore fields with empty values
            if value and key != 'user_id' and key != 'buyer_email':
                updated_data[key] = value
        if 'image' in request.files:
            file_id = mongodb_client.save_file(request.files['image'].filename, request.files['image'])
            updated_data['image'] = str(file_id)


        item = db.Items.update_one({"_id": item_id_object, "user_id": str(verify_token(token)['id'])}, {'$set': updated_data})
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
    
@app.route("/items/<string:item_id>/mark_as_sold", methods = ['PUT'])
def mark_item_as_sold(item_id):
    if 'Authorization' not in request.headers: return "Unauthorized user", 401
    token = request.headers.get('Authorization').split()[1]
    if (verify_token(token)) is None:
        return "Unauthorized user", 401

    item_id_object = ObjectId(item_id)
    buyer_email = request.form.get('buyer_email')
    try:
        # Retrieve updated data from the request form
        updated_data = {}
        updated_data["buyer_email"] = buyer_email

        item = db.Items.update_one({"_id": item_id_object, "user_id": str(verify_token(token)['id'])}, {'$set': updated_data})
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
    
@app.route("/items/<string:item_id>/rate", methods = ['PUT'])
def rate_item(item_id):
    if 'Authorization' not in request.headers: return "Unauthorized user", 401
    token = request.headers.get('Authorization').split()[1]
    if (verify_token(token)) is None:
        return "Unauthorized user", 401

    item_id_object = ObjectId(item_id)
    rate = int(request.form.get('rate'))
    if not (rate >= 1 and rate <= 5):
        return jsonify({'error': "The rate has to between 1 and 5."}), 500
    try:
        # Retrieve updated data from the request form
        updated_data = {}
        updated_data["rate"] = rate
        item = db.Items.update_one({"_id": item_id_object, "buyer_email": verify_token(token)['email']}, {'$set': updated_data})
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
    
@app.route("/avg_rate/<string:user_id>", methods = ['GET'])
def get_avg_rate(user_id):
    try:
        items = list(db.Items.find({"user_id": user_id}).sort("date_created", -1))
        rates = [item['rate'] for item in items if 'rate' in item and item['rate'] != None]
        average_rate = sum(rates) / len(rates) if len(rates) > 0 else None
        response = make_response(jsonify(average_rate))

        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/myItem", methods = ['GET'])
def get_my_items():
    if 'Authorization' not in request.headers: return "Unauthorized user", 401
    token = request.headers.get('Authorization').split()[1]
    if (verify_token(token)) is None:
        return "Unauthorized user", 401

    try:
        items = list(db.Items.find({"user_id": str(verify_token(token)['id'])}).sort("date_created", -1))
        for item in items:
            item["_id"] = str(item["_id"])
        response_data = {"items": items}

    # Return JSON response
        response = make_response(jsonify(response_data))
        response.headers["Content-Type"] = "application/json"
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/myWishlist", methods = ['POST'])
def add_to_my_wishlist():
    if 'Authorization' not in request.headers: return "Unauthorized user", 401
    token = request.headers.get('Authorization').split()[1]
    if (verify_token(token)) is None:
        return "Unauthorized user", 401

    response_data = {
        "item_id": ObjectId(request.form.get('item_id')),
        "user_id": str(verify_token(token)['id'])
    }
    try:
        result = db.Wishlist.insert_one(response_data)
        print(result)
        inserted_id = str(result.inserted_id)
        response_data['_id'] = inserted_id
        response_data['item_id'] = str(response_data['item_id'])

        response = make_response(jsonify(response_data))
        response.headers["Content-Type"] = "application/json"
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route("/myWishlist/<string:item_id>", methods = ['DELETE'])
def remove_from_my_wishlist(item_id):
    if 'Authorization' not in request.headers: return "Unauthorized user", 401
    token = request.headers.get('Authorization').split()[1]
    if (verify_token(token)) is None:
        return "Unauthorized user", 401

    try:
        item = db.Wishlist.find_one_and_delete({"user_id": str(verify_token(token)['id']), "item_id": ObjectId(item_id)})
        if item is None:
            return "Item does not exist", 404
        item["item_id"] = str(item["item_id"])
        item["_id"] = str(item["_id"])


    # Return JSON response
        response = make_response(jsonify(item))
        response.headers["Content-Type"] = "application/json"
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route("/myWishlist", methods = ['GET'])
def get_my_wishlist():
    if 'Authorization' not in request.headers: return "Unauthorized user", 401
    token = request.headers.get('Authorization').split()[1]
    if (verify_token(token)) is None:
        return "Unauthorized user", 401

    try:
        item_ids = list(map(lambda x: x["item_id"], list(db.Wishlist.find({"user_id": str(verify_token(token)['id'])}, {"item_id":1, "_id":0}).sort("date_created", -1))))
        items = list(db.Items.find({"_id": {"$in": item_ids}}))
        for item in items:
            item["_id"] = str(item["_id"])
        response_data = {"items": items}

    # Return JSON response
        response = make_response(jsonify(response_data))
        response.headers["Content-Type"] = "application/json"
        return response, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500