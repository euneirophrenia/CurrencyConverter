import sqlite3
from dateutil import parser
from datetime import timedelta, datetime
from datatools import XMLRateProvider

import argparse
from urllib.request import urlopen

argparser = argparse.ArgumentParser()
argparser.add_argument('--update', '-u', help="update mode (do not delete existing)", action="store_true")
argparser.add_argument('--reset', '-r', help="reset mode (delete existing)", action="store_true")
argparser.add_argument('--create', '-c', help="create a DB from zero", action="store_true")

argparser.add_argument('--remote-source', '-s', help="the remote file to download", type=str,
                       default="https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml")
argparser.add_argument('--local-source', '-l', help="name of the local XML file to write", type=str,
                       default="eurofxref.xml")

argparser.add_argument('--db-path', '-d', help="path to the db", type=str, default="./rates.db")
argparser.add_argument('--schema', help="the .sql file with the db schema (needed in creation mode)", type=str, default='./dbschema.sql')


args = argparser.parse_args()

db_path = args.db_path  # a little shortcut

#  --------------------  SCRIPT to setup the rates db -----------------------
#  It is intended to run once a day in update mode, to download everyday's updated rates and add them to the DB.
#  It is meant to run once at the very beginning of time in reset mode, to setup the initial values,
#  if not using a ready-made DB.
#
# --------------------------------------------------------------------------

if args.create:
    dbfile = open(db_path, 'w+')
    dbfile.close()
    _s = open(args.schema)
    script = _s.read()
    _s.close()


connection = sqlite3.connect(db_path)

if args.create:
    connection.executescript(script)
    connection.commit()

if args.reset:
    connection.execute('delete from rates')
    connection.commit()

# -----------------------------------------------------

# Then, provide starting data from the XML fetching the latest XML file

# Download the file
xml_file = open(args.local_source, "w")
xml_file.write(urlopen(args.remote_source).read().decode('utf-8'))
xml_file.close()

# Load the file and save it to DB.
# We could be more efficient, but I value the high level expressivity in keeping things divided.
xml = XMLRateProvider(args.local_source)
xml.save(db_path)

# ----------------------------------------------------

# Then, fill the gaps (weekends, holidays, .... ) -------

cursor = connection.execute('select * from rates')

# dynamically find the headers in the DB (not using hard coded values, they would be ~32 names, plus they may change)
headers = [description[0] for description in cursor.description]

# Ugly trick to create a string like "(?,?,?,?,?,...)" which will be used to properly format the sql query.
# Could (should?) probably be written with a 1-liner but, hey. What do I know
raw_placeholder = "("
raw_placeholder += "?, " * (len(headers) -1)
raw_placeholder += "?)"

# Find the oldest day and the latest day managed
ref_date = connection.execute('select min(Date) from rates').fetchone()[0]
end = connection.execute('select max(Date) from rates').fetchone()[0]

# get either the max date in the db or today's date in update mode (on weekends, max date will be less then today)
if args.update:
    end = max(datetime.now().strftime('%Y-%m-%d'), end)

# Fill the gaps in between start date and end date
while ref_date != end:
    datum = connection.execute('select * from rates where Date = ?', (ref_date,)).fetchone()
    nextday = (parser.parse(ref_date).date() + timedelta(days=1)).strftime('%Y-%m-%d')
    nextdatum = connection.execute('select * from rates where Date = ?', (nextday,)).fetchone()
    if nextdatum is None:
        print('Filling gap for ', nextday)
        datum = list(datum)
        datum[0] = nextday
        connection.execute('insert into rates values %s' % raw_placeholder, datum)
        connection.commit()

    ref_date = nextday

connection.close()

# END ----------------------------------------------------
