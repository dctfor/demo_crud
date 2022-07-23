# app.py

# Required imports
import os, logging
import google.cloud.logging

from flask import Flask, request, jsonify, render_template, Blueprint
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
app.config.from_object(__name__)
cors = CORS(app, resources={r"/api/*":{"origins":"*"}})

# Create blueprint for prefix all the current apis
bp = Blueprint('apisv1', __name__, template_folder='templates')
app.register_blueprint(bp, url_prefix='/api/v1')

# Look forward the file in a secret related in Google Run
cred = credentials.Certificate(os.getenv("firebase"))
default_app = initialize_app(cred)
db = firestore.client()
fire_db = db.collection('demo')

@app.route('/map')
def map_urls():
    lg.info(app.url_map)
    return str(app.url_map)

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
        json={'id': '1U3H9FSIC7WK', 'some_text': 'I think this is string, ergo this is text'}
    """
    try:
        id = request.json['id']
        if fire_db.document(id).get().to_dict() is None:
            fire_db.document(id).set(request.json)
            return jsonify({"success": True}), 200
        return jsonify({"success": False, "reason": "ID already exists"}), 400
    except Exception as e:
        return f"An Error Occurred: {e}"

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
        return f"An Error Occurred: {e}"

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
        return f"An Error Occurred: {e}"

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
        return f"An Error Occurred: {e}"

#This is the error handling section
@app.errorhandler(404)
def page_not_found(e):
    lg.info("running page_not_found")
    print("running page_not_found")
    '''
        page_not_found()... not sure why we got a request for a non existing url 
    '''
    return render_template('Error404.html'), 404

@app.errorhandler(500)
def server_error(e):
    lg.info("running server_error")
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
    app.run(threaded=True, host='0.0.0.0', port=port)