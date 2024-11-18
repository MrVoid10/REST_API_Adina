from flask import Flask, request, render_template
from DBConn import init_db
from auth_jwt import init_jwt
from models import SSL_CONTEXT


from Blueprints.api import api_bp
from Blueprints.login_register import login_register_bp
app = Flask(__name__)
#CORS(app)
app.config['DEBUG'] = False
# Inițializează JWT
jwt = init_jwt(app)

# Inițializează baza de date
init_db(app)

@app.before_request
def log_request_info():
  if app.debug:
    print(f'Request: {request.method} {request.url}')
    print(f'Headers: {request.headers}')
    print(f'Body: {request.get_data()}')

@app.after_request
def log_response_info(response):
  if app.debug:
    print(f'Response: {response.status}')
    print(f'Headers: {response.headers}')
    print(f'Body: {response.get_data()}')
  return response

app.register_blueprint(login_register_bp, url_prefix='/')
app.register_blueprint(api_bp, url_prefix='/')

@app.route('/')
@app.route('/home')
def home():
  if request.method == 'GET':
    return render_template('index.html')

if __name__ == '__main__':
  app.run(ssl_context=SSL_CONTEXT)