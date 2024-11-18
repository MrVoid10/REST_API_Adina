from flask import Blueprint, request, jsonify, abort
from sqlalchemy import text
from models import ALLOWED_TERMS, AuditLog, MODEL_MAPPING
from auth_jwt import jwt_required_decorator, get_jwt_user_identity
from DBConn import db

api_bp = Blueprint('api', __name__)

# Helper function to convert model instances to dictionaries
def model_to_dict(model):
  """Converts SQLAlchemy model to dictionary for JSON serialization."""
  return {column.name: getattr(model, column.name) for column in model.__table__.columns}

@api_bp.route('/crud', methods=['POST', 'GET', 'PUT', 'DELETE'])
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
    AuditLog.log_action(user_id=user_id, action=action, details=sql_code)
    result = db.session.execute(text(sql_code))

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

@api_bp.route('/read', methods=['GET'])
@api_bp.route('/read/<string:table>', methods=['GET'])
@api_bp.route('/read/<string:table>/<int:id>', methods=['GET'])
@jwt_required_decorator()
def read_table(table=None, id=None):
  if request.is_json:
    data = request.get_json()
  else:
    data = request.args

  if table is None:
    table_name = data.get('Table')  # Pentru cererile GET cu parametru în query
  else:
    table_name = table  # Pentru rutele GET cu parametru URL

  if not table_name:
    return jsonify({'error': "Missing 'Table' key in request."}), 400

  model_class = MODEL_MAPPING.get(table_name)
  if not model_class:
    return jsonify({'error': f"Table '{table_name}' does not exist."}), 404

  try:
    if id is None:
      # Citim toate înregistrările din tabel
      entries = db.session.query(model_class).all()
      data = [model_to_dict(row) for row in entries]
      # Înregistrează acțiunea de audit
      AuditLog.log_action(action=f"Read all from {table_name}", details=f"User accessed all records from table {table_name}", user_id=get_jwt_user_identity())
    else:
      # Citim înregistrarea cu ID-ul specificat
      record = model_class.query.get(id)
      if record is None:
        return jsonify({'error': f"Record with ID '{id}' not found in table '{table_name}'."}), 404
      data = model_to_dict(record)
      # Înregistrează acțiunea de audit
      AuditLog.log_action(action=f"Read by ID from {table_name}", details=f"User accessed record ID {id} from table {table_name}", user_id=get_jwt_user_identity())

    return jsonify({'table': table_name, 'entries': data}), 200
  except Exception as e:
    return jsonify({'error': f"Error reading from table '{table_name}'", 'details': str(e)}), 500

@api_bp.route('/write', methods=['POST'])
@jwt_required_decorator()
def write_table():
  if request.is_json:
    data = request.get_json()
  else:
    return jsonify({'error': 'Request must be JSON.'}), 400

  table_name = data.get('Table')
  table_data = data.get('Data')  # Here we get the data for the record

  if not table_name or not table_data:
    return jsonify({'error': "Missing 'Table' or 'Data' in the request."}), 400

  model_class = MODEL_MAPPING.get(table_name)
  if not model_class:
    return jsonify({'error': f"Table '{table_name}' does not exist."}), 404

  try:
    # Create a new instance of the model with the provided data
    new_record = model_class(**table_data)

    # Add the record to the session and commit
    db.session.add(new_record)
    db.session.commit()

    # Log the action in AuditLog
    AuditLog.log_action(action=f"Inserted into {table_name}", details=f"User added a new record to {table_name}", user_id=get_jwt_user_identity())

    return jsonify({'message': f"New record successfully added to {table_name}."}), 201

  except Exception as e:
    db.session.rollback()
    return jsonify({'error': f"Error writing to table '{table_name}'", 'details': str(e)}), 500

@api_bp.route('/delete/<string:table>', methods=['DELETE'])
@api_bp.route('/delete/<string:table>/<int:id>', methods=['DELETE'])
@jwt_required_decorator()
def delete_from_table(table, id=None):
  if request.is_json:  # If it's JSON, get data from JSON body
    data = request.get_json()
  else:  # If it's not JSON, get data from query parameters
    data = request.args

  model_class = MODEL_MAPPING.get(table)
  if not model_class:
    abort(404, description=f"Tabelul '{table}' nu există sau accesul nu este permis.")
  
  try:
    if id is None:
      # Delete all records from the table
      db.session.query(model_class).delete()
      action_details = f"User deleted all records from table {table}"
    else:
      # Delete a specific record by ID
      record = model_class.query.get(id)
      if not record:
        abort(404, description=f"Inregistrarea cu ID '{id}' nu a fost găsită în tabelul '{table}'.")
      db.session.delete(record)
      action_details = f"User deleted record ID {id} from table {table}"

    db.session.commit()
    
    # Inregistrează acțiunea de audit
    AuditLog.log_action(action=f"Deleted from {table}", details=action_details, user_id=get_jwt_user_identity())
    
    if id:
      return jsonify({'message': f"Record with ID {id} successfully deleted from {table}."}), 200
    else:
      return jsonify({'message': f"All records successfully deleted from {table}."}), 200
  except Exception as e:
    db.session.rollback()
    return jsonify({'error': f"Error deleting from table '{table}'", 'details': str(e)}), 500
