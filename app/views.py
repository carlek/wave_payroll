from flask import render_template, request, jsonify
from sqlalchemy.sql import func, extract, select, label

from app import application
from app.database import db
from app.models import Payrollfile, Worklog, Employee, Payscale

import re
from os import linesep
from tempfile import mkstemp
from calendar import isleap


###################
# utility functions
###################

def extract_info(filename):
    """
    extract info from file, return report_id, payroll_data, # records
    """
    with open(filename) as infile:
        input_records = infile.readlines()

    # remove header and extract report id
    del input_records[0]
    report_id = input_records.pop(len(input_records) - 1).split(',')[1]

    # create payroll data
    payroll_data = []
    n_records = len(input_records)
    for r in range(n_records):
        # date, hours, employee id, job group
        payroll_data.append(input_records[r].strip(linesep).split(','))

    return report_id, payroll_data, n_records


def add_payrollfile_record(f, report_id):
    """
    save a record of reportid:upload in payrollfile table
    """
    # save a tempfile with identifiable prefix
    save_filename = mkstemp(prefix='payroll-')[1]
    f.save(save_filename)
    payrollentry = Payrollfile(report_id=report_id, upload_file=save_filename)
    db.session.add(payrollentry)
    db.session.commit()


def add_worklog_records(payroll_data):
    """
    add payroll upload data to worklog table
    """
    for (date, hours, employee_id, job_group) in payroll_data:
        # ensure employee exists in order to maintain foreign key integrity
        # TODO: consider a better way to enter employee records
        if None is db.session.query(Employee).filter_by(id=employee_id).first():
            db.session.add(Employee(id=employee_id))
            db.session.commit()
        (d,m,yyyy) = date.split('/')
        sqldate = "%s-%s-%s" % (yyyy, m, d)
        worklog = Worklog(date=sqldate, employee_id=employee_id, hours=float(hours), job_group=job_group)
        db.session.add(worklog)
    db.session.commit()


########################
# API endpoints
########################

@application.route('/')
def hello():
    return 'Hello from Flask'


@application.route('/payroll')
def hello_payroll():
    return 'Hello from Payroll'


@application.route('/payroll/upload', methods=['GET', 'POST'])
def upload_payroll():
    """
    upload payroll data, ensure uniqueness, optionally display raw upload data
    """
    if request.method == 'GET':
        return render_template('upload.html')

    if request.method == 'POST':
        # extract info from input file
        f = request.files['file']
        (report_id, payroll_data, n_records) = extract_info(f.filename)

        # add records only if report is new
        if None is db.session.query(Payrollfile).filter_by(report_id=report_id).first():
            add_payrollfile_record(f, report_id)
            add_worklog_records(payroll_data)
        else:
            return "File not uploaded - Report Id: %s exists in the database." % report_id

        # check box for display
        display = request.form.getlist('display')
        if display == [u'yes']:
            return render_template('reportid.html', n_rows=n_records, n_cols=4, report_id=report_id, payroll_data=payroll_data)
        else:
            return 'File Uploaded - Report Id: %s' % report_id


@application.route('/payroll/report', methods=['GET'])
def payroll_report():
    """
    display payroll report from all database records
    """
    # get first two weeks of month  1st -> 15th
    biweekly_first = db.session.query(Worklog.employee_id,
                      func.year(Worklog.date)+'/'+func.month(Worklog.date)+'/1 - '+\
                      func.year(Worklog.date)+'/'+func.month(Worklog.date)+'/15',
                      func.sum(Worklog.hours * Payscale.hourly_rate))\
                .filter(extract('day', Worklog.date) < 16 )\
                .join(Payscale, Worklog.job_group==Payscale.job_group)\
                .order_by(Worklog.employee_id, Worklog.date)\
                .group_by(Worklog.employee_id,
                          func.year(Worklog.date),
                          func.month(Worklog.date))

    # get second two weeks of month, 16th -> 'monthend' (correct day# inserted later)
    biweekly_second = db.session.query(Worklog.employee_id,
                      func.year(Worklog.date)+'/'+func.month(Worklog.date)+'/16 - '+\
                      func.year(Worklog.date)+'/'+func.month(Worklog.date)+'/monthend',
                      func.sum(Worklog.hours * Payscale.hourly_rate))\
                .filter(extract('day', Worklog.date) > 15 )\
                .join(Payscale, Worklog.job_group==Payscale.job_group)\
                .order_by(Worklog.employee_id, Worklog.date)\
                .group_by(Worklog.employee_id,
                          func.year(Worklog.date),
                          func.month(Worklog.date))

    # combine them and for second two weeks put in the correct monthend
    records_all = []

    # first half of month is already correct (1st -> 15th)
    for r in biweekly_first:
        records_all.append(r)

    # total days for each month (leap year will be considered later)
    days_in_month = {'1':'31', '2':'28', '3':'31', '4':'30', '5':'31', '6':'30',
                     '7':'31', '8':'31', '9':'30', '10':'31', '11':'30', '12':'31'}

    # second half of month needs a little more to handle 'monthend'
    regex = re.compile('^(\d+)\/.*\/(\d+)\/monthend$')
    for r in biweekly_second:
        pay_period = r[1]
        year_month = regex.findall(pay_period)
        if len(year_month) > 0:
            [(year, month)] = year_month
            num_days = days_in_month[month]
            if month == '2' and isleap(int(year)):
                num_days = '29'
            # create record with correct monthend day#
            r = (r[0], r[1].replace('monthend', num_days), r[2])

        records_all.append(r)

    return render_template('report.html', n_rows=len(records_all), report_data=records_all)


@application.route('/payroll/reportid', methods=['GET', 'POST'])
def display_reportid():
    """
    display requested report_id
    """
    if request.method == 'GET':
        return render_template('display.html')

    if request.method == 'POST':
        report_id = request.form.get('report_id')
        payrollfile =  db.session.query(Payrollfile).filter_by(report_id=report_id).first()
        if payrollfile is None:
            return "Report Id: %s not found." % report_id
        else:
            (report_id, payroll_data, n_records) = extract_info(payrollfile.upload_file)
            return render_template('reportid.html', n_rows=n_records, n_cols=4, report_id=report_id, payroll_data=payroll_data)
