# models.py
import json
from DBConn import db

with open('settings.json', 'r') as f:
  config = json.load(f)
ALLOWED_TERMS = config['allowed_terms']
SSL_CONTEXT = (config['ssl_context']['cert'], config['ssl_context']['key'])

class User(db.Model):
  __tablename__ = 'Utilizatori'  # Specificăm numele tabelului în baza de date
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(50), unique=True, nullable=False)
  password = db.Column(db.String(255), nullable=False)

  # Poți adăuga o relație pentru a accesa logurile de audit
  audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

class AuditLog(db.Model):
  __tablename__ = 'AuditLog'  # Specificăm numele tabelului în baza de date

  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('Utilizatori.id'), nullable=False)  # Corectăm referința la tabelul Utilizatori
  action = db.Column(db.String(50), nullable=False)
  timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
  details = db.Column(db.Text, nullable=True)

  @classmethod
  def log_action(cls, user_id, action, details):
    """Log the action in the AuditLog table."""
    audit_log = cls(user_id=user_id, action=action, details=details)
    db.session.add(audit_log)
    db.session.commit()
    db.session.flush()

# alte tabele din baza de date
class Produs(db.Model):
  __tablename__ = 'Produse'
  ProdusID = db.Column(db.Integer, primary_key=True)
  Nume = db.Column(db.String(100), nullable=False)
  Categorie = db.Column(db.String(50))
  Pret = db.Column(db.Numeric(10, 2))
  Descriere = db.Column(db.Text)

  specificatii = db.relationship('Specificatie', backref='produs', lazy=True)
  stocuri = db.relationship('Stoc', backref='produs', lazy=True)
  comenzi = db.relationship('Comanda', backref='produs', lazy=True)

class Specificatie(db.Model):
  __tablename__ = 'Specificatii'
  SpecificatieID = db.Column(db.Integer, primary_key=True)
  ProdusID = db.Column(db.Integer, db.ForeignKey('Produse.ProdusID'), nullable=False)
  Tip_Specificatie = db.Column(db.String(100))
  Specificatie = db.Column(db.String(100))

class Depozit(db.Model):
  __tablename__ = 'Depozit'
  DepozitID = db.Column(db.Integer, primary_key=True)
  Locatie = db.Column(db.String(100))
  Capacitate = db.Column(db.Integer)

  stocuri = db.relationship('Stoc', backref='depozit', lazy=True)

class Stoc(db.Model):
  __tablename__ = 'Stoc'
  StocID = db.Column(db.Integer, primary_key=True)
  ProdusID = db.Column(db.Integer, db.ForeignKey('Produse.ProdusID'), nullable=False)
  DepozitID = db.Column(db.Integer, db.ForeignKey('Depozit.DepozitID'), nullable=False)
  Cantitate = db.Column(db.Integer)

class Comanda(db.Model):
  __tablename__ = 'Comenzi'
  ComandaID = db.Column(db.Integer, primary_key=True)
  ProdusID = db.Column(db.Integer, db.ForeignKey('Produse.ProdusID'), nullable=False)
  Cantitate = db.Column(db.Integer)
  DataComanda = db.Column(db.Date)

def log_audit(action, details, user_id=None):
  try:
    audit_log = AuditLog(user_id=user_id, action=action, details=details)
    db.session.add(audit_log)
    db.session.commit()
  except Exception as e:
    db.session.rollback()
    print(f"Error logging audit: {e}")

MODEL_MAPPING = {
        'Utilizatori': User,
        'AuditLog': AuditLog,
        'Produs': Produs,
        'Specificatie': Specificatie,
        'Depozit': Depozit,
        'Stoc': Stoc,
        'Comanda': Comanda,
    }

