# auth_jwt.py
import json
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta

# Citește setările din fișierul settings.json
with open('settings.json', 'r') as f:
  config = json.load(f)

JWT_SECRET_KEY = config['jwt_secret_key']

def init_jwt(app):
  app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
  app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
  jwt = JWTManager(app)
  return jwt

def generate_token(identity):
  return create_access_token(identity=identity)

def jwt_required_decorator():
  return jwt_required()

def get_jwt_user_identity():
  return get_jwt_identity()
