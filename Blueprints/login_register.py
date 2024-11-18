from flask import Blueprint, request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from DBConn import db
from models import User, AuditLog 
from auth_jwt import create_access_token

login_register_bp = Blueprint('login_register', __name__)

@login_register_bp.route('/register', methods=['GET', 'POST'])
def register():
  if request.method == 'GET':
    return render_template('register.html')
    
  if request.is_json:
    data = request.get_json()
  else:
    data = request.args

  # Retrieve username and password from data
  username = data.get('username')
  password = data.get('password')

  if not username or not password:
    return jsonify({'message': 'Username și parola sunt necesare'}), 400

  existing_user = db.session.query(User).filter_by(username=username).first()
  if existing_user:
    return jsonify({'message': 'Username-ul există deja'}), 409

  hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    
  try:
    # Assuming 'username' and 'password' are columns in the User model
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    access_token = create_access_token(identity=new_user.id)
    
    # Logăm acțiunea de înregistrare
    AuditLog.log_action(user_id=new_user.id, action='register', details=f'User {username} registered.')

    return jsonify({
      'message': 'User înregistrat cu succes!',
      'access_token': access_token
    }), 201
  except Exception as e:
    db.session.rollback()
    return jsonify({'message': 'A apărut o eroare la înregistrare', 'error': str(e)}), 500

@login_register_bp.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'GET':
    return render_template('login.html')

  if request.is_json:
    data = request.get_json()
  else:
    data = request.args

  username = data.get('username')
  password = data.get('password')

  # Query the User model directly, nu mai folosim reflectarea tabelelor
  user = db.session.query(User).filter_by(username=username).first()
  if not user or not check_password_hash(user.password, password):
    return jsonify({'message': 'Credențiale invalide'}), 401

  access_token = create_access_token(identity=user.id)

  # Logăm acțiunea de autentificare
  AuditLog.log_action(user_id=user.id, action='login', details=f'User {username} logged in.')
  
  return jsonify({'access_token': access_token}), 200
