from flask import Blueprint, request, jsonify, abort
from sqlalchemy import text
from models import ALLOWED_TERMS, Audit
from auth_jwt import jwt_required_decorator, get_jwt_user_identity
from DBConn import db, REFLECTED_TABLES, UTILIZATORI, AUDIT_LOG, PRODUSE, SPECIFICATII, DEPOZIT, STOC, COMENZI
api_bp = Blueprint('api', __name__)

@api_bp.route('/manual', methods=['POST', 'GET', 'PUT', 'DELETE'])
@jwt_required_decorator()
def manual_query():
  user_id = get_jwt_user_identity()

  if request.is_json:  # If it's not JSON, check for query parameters
    data = request.get_json()
  else:
    data = request.args

  sql_code = None
  # Allowed terms from configuration
  allowed_terms = ALLOWED_TERMS
  # Extract query parameters from the GET or JSON request
  for term in allowed_terms:
    if term in data:
      sql_code = data[term]
      break

  if sql_code is None:
    return jsonify({'message': 'No valid query provided. Allowed terms: ' + ', '.join(allowed_terms)}), 400

  # Check the type of SQL query based on HTTP method
  action = None
  if request.method == 'GET':
    if 'select' not in sql_code.lower():
      return jsonify({'message': 'Only SELECT queries are allowed for GET requests'}), 400
      action = 'SELECT'
  elif request.method == 'POST':
    if 'insert' not in sql_code.lower():
      return jsonify({'message': 'Only INSERT queries are allowed for POST requests'}), 400
    action = 'INSERT'
  elif request.method == 'PUT':
    if 'update' not in sql_code.lower():
      return jsonify({'message': 'Only UPDATE queries are allowed for PUT requests'}), 400
    action = 'UPDATE'
  elif request.method == 'DELETE':
    if 'delete' not in sql_code.lower():
      return jsonify({'message': 'Only DELETE queries are allowed for DELETE requests'}), 400
    action = 'DELETE'

  try:
    # Execute the SQL query
    result = db.session.execute(text(sql_code))
    Audit.log(user_id=user_id, action=action, details=sql_code)

    if request.method == 'GET':
      entries = [dict(row._mapping) for row in result]
      db.session.commit()  # Commit the audit log before returning data
      return jsonify({'entries': entries}), 200
    else:
      db.session.commit()  # Commit the query and audit log
      return jsonify({'message': 'Query executed successfully'}), 200

  except Exception as e:
    db.session.rollback()
    return jsonify({'message': 'Error executing SQL', 'error': str(e)}), 500


@api_bp.route('/read', methods=['POST', 'GET'])
def read_table():
  if request.is_json:
    data = request.get_json()
  else:
    data = request.args

  table_name = data.get('Table')
  if not table_name:
    return jsonify({'error': "Missing 'Table' key in request."}), 400

  table_class = REFLECTED_TABLES.get(table_name)
  if not table_class:
    return jsonify({'error': f"Table '{table_name}' does not exist or is not reflected."}), 404

  try:
    entries = db.session.query(table_class).all()
    data = [{col: getattr(row, col) for col in row.__table__.columns.keys()} for row in entries]
    return jsonify({'table': table_name, 'entries': data}), 200
  except Exception as e:
    return jsonify({'error': f"Error reading from table '{table_name}'", 'details': str(e)}), 500



"""
def get_model_by_name(name):
    models = {
        'User': User,
        'AuditLog': AuditLog,
        'Produs': Produs,
        'Specificatie': Specificatie,
        'Depozit': Depozit,
        'Stoc': Stoc,
        'Comanda': Comanda,
    }
    return models.get(name)

# Metodă to_dict pentru serializarea obiectelor SQLAlchemy
def model_to_dict(model):
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}

# Adaugă metoda to_dict fiecărui model
User.to_dict = model_to_dict
AuditLog.to_dict = model_to_dict
Produs.to_dict = model_to_dict
Specificatie.to_dict = model_to_dict
Depozit.to_dict = model_to_dict
Stoc.to_dict = model_to_dict
Comanda.to_dict = model_to_dict

# Endpoint pentru a citi toate tabelele disponibile
@api_bp.route('/read', methods=['GET'])
@jwt_required_decorator
def read_all_tables():
    tables = ['User', 'AuditLog', 'Produs', 'Specificatie', 'Depozit', 'Stoc', 'Comanda']
    return jsonify({'tables': tables})

# Endpoint pentru a citi toate înregistrările dintr-un tabel specific
@api_bp.route('/read/<string:table>', methods=['GET'])
@jwt_required_decorator
def read_table(table):
    model = get_model_by_name(table)
    if model is None or table not in ALLOWED_TERMS:
        abort(404, description=f"Tabelul '{table}' nu există sau accesul nu este permis.")

    records = model.query.all()
    results = [record.to_dict() for record in records]
    # Înregistrează acțiunea de audit
    log_audit(action=f"Read all from {table}", details=f"User accessed table {table}", user_id=get_jwt_user_identity())
    return jsonify(results)

# Endpoint pentru a citi o înregistrare specifică pe baza ID-ului
@api_bp.route('/read/<string:table>/<int:id>', methods=['GET'])
@jwt_required_decorator
def read_table_by_id(table, id):
    model = get_model_by_name(table)
    if model is None or table not in ALLOWED_TERMS:
        abort(404, description=f"Tabelul '{table}' nu există sau accesul nu este permis.")
    
    record = model.query.get(id)
    if record is None:
        abort(404, description=f"Inregistrarea cu ID '{id}' nu a fost găsită în tabelul '{table}'.")

    # Înregistrează acțiunea de audit
    log_audit(action=f"Read by ID from {table}", details=f"User accessed record ID {id} in table {table}", user_id=get_jwt_user_identity())
    return jsonify(record.to_dict())
"""
