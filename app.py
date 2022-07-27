# app.py

# Required imports
import os, logging, uuid

import google.cloud.logging

from flask import Flask, request, jsonify, render_template, Blueprint, url_for
from flask_cors import CORS
from firebase_admin import credentials, firestore, initialize_app

#init logger
client = google.cloud.logging.Client()
client.setup_logging()

# # Commented logging format as in gcloud logging is ignored
# LOGGING_FORMAT = "[%(filename)s:%(lineno)d] %(message)s"
# logging.basicConfig(format=LOGGING_FORMAT)
lg = logging.getLogger(__name__)


# Initialize Flask app
app = Flask(__name__)

#The blueprint for raw APIs in flask
bp = Blueprint('apisv1', __name__, url_prefix='/api/v1')
#The blueprint to connect VUE w/ flask APIs
demo = Blueprint('demov1', __name__, url_prefix='/api/v1/vue')

# Look forward the file in a secret related in Google Run
cred = credentials.Certificate(os.getenv("firebase"))
default_app = initialize_app(cred)
db = firestore.client()

# For current flask-only crud
fire_db = db.collection('demo') 

# For implementing a UI w/ CRUD (in VUE.js)
contact_db = db.collection('contacts') 
department_db = db.collection('departments')


def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


@app.route("/site-map")
def site_map():
    links = []
    for rule in app.url_map.iter_rules():
        # Filter out rules we can't navigate to in a browser
        # and rules that require parameters
        if has_no_empty_params(rule):
            url = url_for(rule.endpoint, **(rule.defaults or {}))
            links.append((url, rule.endpoint))
    # links is now a list of url, endpoint tuples
    return ' '.join(map(str,links))

# Sanity check route | health-ping
@bp.route('/ping', methods=['GET'])
def ping_pong():
    lg.info("running ping_pong")
    return jsonify('pong!'), 200
    
    
# Sanity check route | health-ping
@bp.route('/error500', methods=['GET'])
def error_raise():
    raise Exception("Sorry, it's not you, it's me")
    return "", 200

# Api for testing/debugging response codes
@bp.route('/testcode/<code>', methods=['GET'])
def debug_response(code=200):
    lg.info("running debug_response")
    if code == 404:
        return render_template('Error404.html'), 404
    if code == 500:
        return render_template('Error500.html'), 500
    return "", code

@bp.route('/', methods=['GET'])
def im_root():
    lg.info("running im_root")
    """
        im_root() : This is the root url for the project that
        most of times
    """
    url = request.url_root 
    data = {'url': url}
    return render_template('index.html', data=data), 418 #this error code is just kinda an easter egg :)


@bp.route('/add', methods=['POST'])
def create():
    lg.info("running create")
    """
        create() : Add document to Firestore collection with request body.
        Ensure you pass a custom ID in the first level of the json as part 
        of json body in post request.
        i.e: 
        json={'id': '1', 'desc': 'Hey, ima desc in this app!'}
        json={'id': '1U3H9FSI', 'some_text': 'I think this is string, ergo this is text'}
    """
    try:
        if "id" not in request.json:
            id = str(uuid.uuid4())[:8]
            request.json['id'] = id
        else:
            id = request.json['id']
        if fire_db.document(id).get().to_dict() is None:
            fire_db.document(id).set(request.json)
            return jsonify({"success": True}), 200
        return jsonify({"success": False, "reason": "ID already exists"}), 400
    except Exception as e:
        return f"An Error Occurred: {e}", 500

@bp.route('/list', methods=['GET'])
@bp.route('/list/<id>', methods=['GET'])
def read(id=None):
    lg.info("running read")
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
        return f"An Error Occurred: {e}", 500

@bp.route('/update', methods=['POST', 'PUT'])
def update():
    lg.info("running update")
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
        return f"An Error Occurred: {e}", 500

@bp.route('/delete', methods=['GET', 'DELETE'])
@bp.route('/delete/<id>', methods=['GET', 'DELETE'])
def delete(id=None):
    lg.info("running delete")
    """
        delete() : Delete a document from Firestore collection.
    """
    try:
        # Check for ID in URL query
        todo_id = request.args.get('id') if id is None else id
        fire_db.document(todo_id).delete()
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occurred: {e}", 500


# these are for the CRUD in VUE.js

@demo.route('contacts/add', methods=['POST'])
def contact_create():
    lg.info("running contact create")
    try:
        if "id" not in request.json:
            id = str(uuid.uuid4())[:8]
            request.json['id'] = id
        else:
            id = request.json['id']
        if contact_db.document(id).get().to_dict() is None:
            lg.info("[CONTACT CREATE] ID " + id)
            request.json['created_at']={".sv": "timestamp"}
            contact_db.document(id).set(request.json)
            return jsonify({"success": True}), 200
        return jsonify({"success": False, "reason": "ID already exists"}), 400
    except Exception as e:
        return f"An Error Occurred: {e}", 500

@demo.route('contacts', methods=['GET'])
@demo.route('contacts/<id>', methods=['GET'])
def contact_read(id=None):
    lg.info("running contact read")
    try:
        # Check if ID was passed to URL query or from actual url path
        todo_id = request.args.get('id') if id is None else id
        if todo_id:
            todo = contact_db.document(todo_id).get()
            return jsonify(todo.to_dict()), 200
        else:
            all_todos = [doc.to_dict() for doc in contact_db.stream()]
            return jsonify(all_todos), 200
    except Exception as e:
        return f"An Error Occurred: {e}", 500

@demo.route('contacts/update', methods=['POST', 'PUT'])
def contact_update():
    lg.info("running contact update")
    try:
        id = request.json['id']
        lg.info("[CONTACT UPDATE] ID " + id)
        contact_db.document(id).update(request.json)
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occurred: {e}", 500

@demo.route('contacts/delete', methods=['GET', 'DELETE'])
@demo.route('contacts/delete/<id>', methods=['GET', 'DELETE'])
def contact_delete(id=None):
    lg.info("running contact delete")
    try:
        # Check for ID in URL query
        c_id = request.args.get('id') if id is None else id
        lg.warn("[CONTACT DELETE] ID " + c_id)
        contact_db.document(c_id).delete()
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occurred: {e}", 500

#   For creating the departments

@demo.route('departments/add', methods=['POST'])
def department_create():
    lg.info("running department create")
    try:
        if "id" not in request.json:
            id = str(uuid.uuid4())[:8]
            request.json['id'] = id
        else:
            id = request.json['id']
        if department_db.document(id).get().to_dict() is None:
            department_db.document(id).set(request.json)
            return jsonify({"success": True}), 200
        return jsonify({"success": False, "reason": "ID already exists"}), 400
    except Exception as e:
        return f"An Error Occurred: {e}", 500

@demo.route('departments', methods=['GET'])
@demo.route('departments/<id>', methods=['GET'])
def department_read(id=None):
    lg.info("running department read")
    try:
        # Check if ID was passed to URL query or from actual url path
        todo_id = request.args.get('id') if id is None else id
        if todo_id:
            todo = department_db.document(todo_id).get()
            return jsonify(todo.to_dict()), 200
        else:
            all_todos = [doc.to_dict() for doc in department_db.stream()]
            return jsonify(all_todos), 200
    except Exception as e:
        return f"An Error Occurred: {e}", 500

@demo.route('departments/update', methods=['POST', 'PUT'])
def department_update():
    lg.info("running department update")
    try:
        id = request.json['id']
        department_db.document(id).update(request.json)
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occurred: {e}", 500

@demo.route('departments/delete', methods=['GET', 'DELETE'])
@demo.route('departments/delete/<id>', methods=['GET', 'DELETE'])
def department_delete(id=None):
    lg.info("running department delete")
    try:
        # Check for ID in URL query
        todo_id = request.args.get('id') if id is None else id
        department_db.document(todo_id).delete()
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occurred: {e}", 500




#This is the error handling section
def page_not_found(e):
    lg.warn("running page_not_found")
    print("running page_not_found")
    '''
        page_not_found()... not sure why we got a request for a non existing url 
    '''
    return render_template('Error404.html'), 404

def server_error(e):
    lg.error("running server_error")
    print("running server_error")
    '''
        server_error()... ammm Houston, we have a problem here
    '''
    return render_template('Error500.html'), 500



#The magic happens here
port = int(os.environ.get('PORT', 8080))
if __name__ == '__main__':
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, server_error)
    app.register_blueprint(bp)
    app.register_blueprint(demo)
    cors = CORS(app, resources={r"/api/*":{"origins":"*"}})
    # Create blueprint for prefix all the current apis
    app.run(threaded=True, host='0.0.0.0', port=port)