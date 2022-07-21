# app.py

# Required imports
import os
from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, initialize_app

# Initialize Flask app
app = Flask(__name__)

# Look forward the file
cred = credentials.Certificate('key.json')
default_app = initialize_app(cred)
db = firestore.client()
fire_db = db.collection('demo')


@app.route('/', methods=['GET'])
def test_root():
    """
        create() : Add document to Firestore collection with request body.
        Ensure you pass a custom ID as part of json body in post request,
        e.g. json={'id': '1', 'title': 'Write a blog post'}
    """
    return jsonify({"success": True, "Test": True}), 200

@app.route('/add', methods=['POST'])
def create():
    """
        create() : Add document to Firestore collection with request body.
        Ensure you pass a custom ID as part of json body in post request,
        e.g. json={'id': '1', 'title': 'Write a blog post'}
    """
    try:
        id = request.json['id']
        if fire_db.document(id).get().to_dict() is None:
            fire_db.document(id).set(request.json)
            return jsonify({"success": True}), 200
        return jsonify({"success": False, "reason": "ID already exists"}), 400
    except Exception as e:
        return f"An Error Occurred: {e}"

@app.route('/list', methods=['GET'])
@app.route('/list/<id>', methods=['GET'])
def read(id=None):
    """
        read() : Fetches documents from Firestore collection as JSON.
        todo : Return document that matches query ID.
        all_todos : Return all documents.
    """
    try:
        # Check if ID was passed to URL query or from actual url path
        todo_id = request.args.get('id') if id is None else id
        if todo_id:
            todo = fire_db.document(todo_id).get()
            return jsonify(todo.to_dict()), 200
        else:
            all_todos = [doc.to_dict() for doc in fire_db.stream()]
            return jsonify(all_todos), 200
    except Exception as e:
        return f"An Error Occurred: {e}"

@app.route('/update', methods=['POST', 'PUT'])
def update():
    """
        update() : Update document in Firestore collection with request body.
        Ensure you pass a custom ID as part of json body in post request,
        e.g. json={'id': '1', 'title': 'Write a blog post today'}
    """
    try:
        id = request.json['id']
        fire_db.document(id).update(request.json)
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occurred: {e}"

@app.route('/delete', methods=['GET', 'DELETE'])
@app.route('/delete/<id>', methods=['GET', 'DELETE'])
def delete(id=None):
    """
        delete() : Delete a document from Firestore collection.
    """
    try:
        # Check for ID in URL query
        todo_id = request.args.get('id') if id is None else id
        fire_db.document(todo_id).delete()
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occurred: {e}"

port = int(os.environ.get('PORT', 8080))
if __name__ == '__main__':
    app.run(threaded=True, host='0.0.0.0', port=port)