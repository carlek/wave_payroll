
from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

###############################
# Payroll database table models
###############################

Base = declarative_base()
metadata = Base.metadata


class Employee(Base):
    __tablename__ = 'employee'
    id = Column(Integer, primary_key=True)


class Payrollfile(Base):
    __tablename__ = 'payrollfile'
    report_id = Column(Integer, primary_key=True)
    upload_file = Column(String(512), nullable=False)


class Payscale(Base):
    __tablename__ = 'payscale'
    job_group = Column(String(1), primary_key=True)
    hourly_rate = Column(Float, nullable=False)


class Worklog(Base):
    __tablename__ = 'worklog'
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    employee_id = Column(ForeignKey('employee.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, index=True)
    hours = Column(Float, nullable=False)
    job_group = Column(String(1), nullable=False, index=True)

    employee = relationship('Employee')


"""
the above was generated with
https://pypi.python.org/pypi/sqlacodegen

my previous version was handcoded:

from app.database import db

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)

class Payscale(db.Model):
    job_group = db.Column(db.String(1), primary_key=True)
    hourly_rate = db.Column(db.Float())

class Worklog(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'))
    hours = db.Column(db.Float)
    job_group = db.Column(db.String(1), db.ForeignKey('payscale.job_group'))

class Payrollfiles(db.Model):
    report_id = db.Column(db.Integer, primary_key=True)
    upload_file = db.Column(db.VARCHAR(512))

"""
