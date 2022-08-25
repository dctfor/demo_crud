# app.py

# Required imports
import os, logging, uuid, pathlib, requests, hmac, hashlib
from collections.abc import Mapping
from functools import wraps
import google.cloud.logging

from flask import Flask, request, jsonify, render_template, Blueprint, url_for, session, abort, redirect
from flask_jwt import JWT, jwt_required, current_identity
from flask_cors import CORS
from firebase_admin import credentials, firestore, initialize_app
# from google.oauth2 import id_token
# from google_auth_oauthlib.flow import Flow
# from pip._vendor import cachecontrol
# import google.auth.transport.requests

# app = Flask("GCP_FLSK_FRBS")  #naming our application
# app.secret_key = "christianlopez.mx"  #it is necessary to set a password when dealing with OAuth 2.0

# #   Params necesary for working with the google OAuth
# os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  #this is to set our environment to https because OAuth 2.0 only supports https environments
# GOOGLE_CLIENT_ID = "410342830455-ellv6s7gi13mhcd1cgpuaqk1qnpjts7l.apps.googleusercontent.com"  #enter your client id you got from Google console
# # GOOGLE_CLIENT_ID = "362896790228-enbe8d57gn1s1npbl29vikd8dppmhiti.apps.googleusercontent.com"  #enter your client id you got from Google console
# client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")  #set the path to where the .json file you got Google console is

# #   This is for the Google OAuth for login in with the googleaccount
# flow = Flow.from_client_secrets_file(  #Flow is OAuth 2.0 a class that stores all the information on how we want to authorize our users
#     client_secrets_file=client_secrets_file,
#     scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],  #here we are specifing what do we get after the authorization
#     redirect_uri="http://127.0.0.1:8080/callback"  #and the redirect URI is the point where the user will end up after the authorization
# )

#init logger
# client = google.cloud.logging.Client()
# client.setup_logging()

# # Commented logging format as in gcloud logging is ignored
# LOGGING_FORMAT = "[%(filename)s:%(lineno)d] %(message)s"
# logging.basicConfig(format=LOGGING_FORMAT)
lg = logging.getLogger(__name__)


# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret'

#The blueprint for raw APIs in flask
bp = Blueprint('apisv1', __name__, url_prefix='/api/v1')
#The blueprint to connect VUE w/ flask APIs
demo = Blueprint('demov1', __name__, url_prefix='/api/v1/vue')

# Look forward the file in a secret related in Google Run
cred = credentials.Certificate('key.json')
# cred = credentials.Certificate(os.getenv("firebase"))
default_app = initialize_app(cred)
db = firestore.client()

# For current flask-only crud
fire_db = db.collection('demo') 

# For implementing a UI w/ CRUD (in VUE.js)
user_db = db.collection('users') 
contact_db = db.collection('contacts') 
department_db = db.collection('departments')

# For logging sing-ups / logins
oauth2_db = db.collection('log_oauth2') 

class simple_user:
    id=0
    def __init__(self, id, username="dummy"):
        self.id = id
        self.username = username

def authenticate(username, password):
    lg.info(f"FLASK Server - Authenticating {username}")
    user = user_db.where('username', '==', username).get()
    if user:
        # lg.info(f"User > > > {user}")
        user = user[0].to_dict()
        lg.info(f"PostUser > > > {user}")
        if user["password"] == hashlib.md5(password.encode('utf-8')).hexdigest():
            lg.info(f"Entered pass > > > {hashlib.md5(password.encode('utf-8')).hexdigest()}")
            return simple_user(user["id"],user["username"])

def identity(payload):
    print(f'payload {payload}')
    user = user_db.where('id', '==', payload['identity']).get()
    print(f'user {user}')
    return user[0]

jwt = JWT(app, authenticate, identity)


def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)

@app.route("/site-map")
@jwt_required()
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
@jwt_required()
def debug_response(code=200):
    lg.info("running debug_response")
    if code == 404:
        return render_template('Error404.html'), 404
    if code == 500:
        return render_template('Error500.html'), 500
    return "", code

@bp.route('/', methods=['GET'])
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
def department_delete(id=None):
    lg.info("running department delete")
    try:
        # Check for ID in URL query
        todo_id = request.args.get('id') if id is None else id
        department_db.document(todo_id).delete()
        return jsonify({"success": True}), 200
    except Exception as e:
        return f"An Error Occurred: {e}", 500


# For adding OAuth process [WIP]

def login_is_required(function):  #a function to check if the user is authorized or not
    def wrapper(*args, **kwargs):
        if "google_id" not in session:  #authorization required
            return abort(401)
        else:
            return function()

    return wrapper


@app.route("/login")  #the page where the user can login
def login():
    authorization_url, state = flow.authorization_url()  #asking the flow class for the authorization (login) url
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")  #this is the page that will handle the callback process meaning process after the authorization
def callback():
    # lg.info(request.json)
    flow.fetch_token(authorization_response=request.url)
    id = None
    # if "id" not in request.json:
    #     id = str(uuid.uuid4())[:8]
    #     request.json['id'] = id
    # else:
    #     id = request.json['id']
    # if oauth2_db.document(id).get().to_dict() is None:
    #     oauth2_db.document(id).set(request.json)
    # if not session["state"] == request.args["state"]:
    #     abort(500)  #state does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    print(id_info)
    print(type(id_info))
    print(dir(id_info))
    # oauth2_db
    # id = str(uuid.uuid4())[:8]
    # request.json['id'] = id
    session["data"] = id_info
    session["google_id"] = id_info.get("sub")  #defing the results to show on the page
    session["name"] = id_info.get("name")
    return redirect("/protected_area")  #the final page where the authorized users will end up


@app.route("/logout")  #the logout page and function
def logout():
    session.clear()
    return redirect("/")


@app.route("/")  #the home page where the login button will be located
def index():
    return "Hello World <a href='/login'><button>Login</button></a>"


@app.route("/protected_area")  #the page where only the authorized users can go to
@login_is_required
def protected_area():
    return f"Hello {session['data']}! <br/> <a href='/logout'><button>Logout</button></a>"  #the logout button 





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
    # TODO: Fix the Cors to be route specific
    cors = CORS(app, resources={r"*":{"origins":"*"}})
    # Create blueprint for prefix all the current apis
    app.run(threaded=True, host='0.0.0.0', port=port)