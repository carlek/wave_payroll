from configparser import ConfigParser
from flask_sqlalchemy import SQLAlchemy

from app import application

########################
# database specification
########################

# Read config file
config = ConfigParser()
config.read('payroll_db.conf')

# MySQL configurations
application.config['SQLALCHEMY_DATABASE_URI'] = \
    'mysql+pymysql://' + config.get('DB', 'user') + ':' + config.get('DB', 'password')\
    + '@' + config.get('DB', 'host') + '/' + config.get('DB', 'db')

application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy()
db.init_app(application)

# create all tables
#from app import models
#with application.app_context():
#    db.session.create_all()
#    db.session.commit()

