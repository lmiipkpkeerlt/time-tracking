#!/usr/bin/env python3
import os
import sqlite3

DATABASE = '/Users/mlip/bin/time-tracking.db'

def confirm(message: str):
    while True:
        user_input = input(f'{message} (y/n): ').lower()
        if user_input in {'y', 'n'}:
            return user_input == 'y'
        else:
            print('Invalid input. Please enter "y" or "n".')

def validate_date_format(date: str):
    from datetime import datetime
    try: datetime.strptime(date, '%Y-%m-%d'); return True
    except ValueError: return False

def init_db():
    if os.path.exists(DATABASE):
        print(f'database {DATABASE} already exists')
        return
    con = sqlite3.connect(DATABASE)
    con.cursor().execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            salary INT,
            allocated INT
        )
    ''')
    con.cursor().execute('''
        CREATE TABLE IF NOT EXISTS hours (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            amount INTEGER NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')
    con.commit(); con.close(); print(f'initialized database {DATABASE}')

def create_backup_db(dest: str):
    import shutil
    if not os.path.exists(DATABASE):
        print(f'database {DATABASE} does not exist')
        return
    if os.path.exists(dest):
        if confirm('destination file already exists, overwrite it?'): pass
        else: print('exiting...'); exit(0)
    shutil.copy(DATABASE, dest)
    print(f'backed up database to {dest}')

def create(project: str, salary: int, total_hours: int):
    project = project.lower(); con = sqlite3.connect(DATABASE); cursor = con.cursor()
    cursor.execute('SELECT * FROM projects WHERE name = ?', (project, ))
    if cursor.fetchone():
        print(f'project {project} already exists')
        con.close(); return
    cursor.execute('INSERT INTO projects (name, salary, allocated) VALUES (?, ?, ?)', [project, salary, total_hours])
    con.commit(); con.close()
    print(f'created project {project}')

def remove(project: str):
    project = project.lower(); con = sqlite3.connect(DATABASE); cursor = con.cursor()
    cursor.execute('SELECT * FROM projects WHERE name = ?', (project,))
    if not cursor.fetchone():
        print(f'project {project} does not exist')
        con.close(); return
    # TODO flag as removed instead?
    cursor.execute('DELETE FROM projects WHERE name = ?', (project,))
    con.commit(); con.close()
    print(f'removed project {project}')

def list():
    con = sqlite3.connect(DATABASE); cursor = con.cursor()
    cursor.execute('''
        SELECT projects.name, COALESCE(SUM(hours.amount), 0) as total_hours
        FROM projects
        LEFT JOIN hours ON projects.id = hours.project_id
        GROUP BY projects.id, projects.name
    ''')
    if not (ps := cursor.fetchall()):
        print('no projects founds')
        con.close(); return
    print('project\t\thours')
    print('---------------------')
    [print(f'{p[0]}\t\t{p[1]}') for p in ps]
    con.close()

def add_hours(project: str, n: int, date: str = None):
    project = project.lower(); con = sqlite3.connect(DATABASE); cursor = con.cursor()
    cursor.execute('SELECT * FROM projects WHERE name = ?', (project,))
    if not (p := cursor.fetchone()):
        print(f'no project named {project}')
        con.close(); return
    if date is not None:
        if validate_date_format(date):
            cursor.execute('INSERT INTO hours (project_id, date, amount) VALUES (?, ?, ?)', [p[0], date, n])
        else:
            print(f'date "{date}" not correctly formatted, use "YYYY-MM-DD"')
            con.close(); return
    elif date is None:
        cursor.execute('INSERT INTO hours (project_id, date, amount) VALUES (?, CURRENT_DATE, ?)', [p[0], n])
    con.commit(); con.close()
    print(f'added {n} hours to {project}')

def show_project(project: str):
    project = project.lower(); con = sqlite3.connect(DATABASE); cursor = con.cursor()
    cursor.execute('''
        SELECT projects.name, COALESCE(SUM(hours.amount), 0), projects.salary, projects.allocated as total_hours
        FROM projects
        LEFT JOIN hours ON projects.id = hours.project_id
        WHERE projects.name = ?
        GROUP BY projects.id, projects.name
    ''', (project,))
    if not (p := cursor.fetchone()):
        print(f'no project named {project}')
        con.close(); return
    cursor.execute('''
        SELECT hours.date, hours.amount
        FROM projects
        LEFT JOIN hours ON projects.id = hours.project_id
        WHERE projects.name = ?
    ''', (project,))
    if len(hs := cursor.fetchall()) >= 1:
        print(f'date\t\thours')
        print(f'---------------------')
        [print(f'{h[0]}\t{h[1]}') for h in hs]
        print(f'---------------------')
    if p[3] != None and p[2] != None and p[1] != 0:
        print(f'hours: {p[1]}/{p[3]}')
        print(f'avg {p[3]*p[2] / p[1]} dkk/hour')
    else:
        print(f'hours: {p[1]}')
    con.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='''
        time-tracking <project> to view a project.
        time-tracking <project> <hours> to add hours to a project.
    ''')
    parser.add_argument('project', nargs='?')
    parser.add_argument('hours', nargs='?')
    hours_conditional = parser.add_argument_group('optional arguments when adding hours')
    hours_conditional.add_argument('-date', help='specify date when adding hours')
    parser.add_argument('-new', help='create a new project') 
    new_conditional = parser.add_argument_group('optional arguments when creating a project')
    new_conditional.add_argument('-salary', help='specify salary')
    new_conditional.add_argument('-total', help='specify total amount of hours allocated for a project')
    parser.add_argument('-rm', help='remove an existing project') 
    parser.add_argument('-backup', help='backup database file to BACKUP')
    parser.add_argument('-init', action='store_true', help='initialize the database')
    parser.add_argument('-ls', action='store_true', help='list all existing projects')
    args = parser.parse_args()

    if args.new: create(args.new, args.salary, args.total)
    elif args.rm:
        if confirm(f'remove project {args.rm}?'): remove(args.rm)
        else: print('exiting...'); exit(0)
    elif args.ls: list()
    elif args.init: init_db()
    elif args.backup: create_backup_db(args.backup)
    elif args.project is not None and args.hours is not None: add_hours(args.project, args.hours, args.date)
    elif args.project is not None and args.hours is None: show_project(args.project)
    else: parser.print_help()
