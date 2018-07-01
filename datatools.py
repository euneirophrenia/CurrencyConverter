import xml.etree.ElementTree as eTree
from dateutil import parser
from datetime import timedelta

import threading
import sqlite3

from errors import InvalidUsage

_conn_ = sqlite3.connect('./rates.db')
_cursor_ = _conn_.execute('select * from rates')

# dynamically find the headers in the DB (not hard coded values)
db_known_currencies = [description[0] for description in _cursor_.description][1:] #the first value is the date (ignored)
_conn_.close()


# Abstract base class for others
class RateProvider:

    def get(self, src, dst, date):
        raise NotImplementedError

    def convert(self, amount, src_curr, dst_curr, date):
        # No magic here, return the amount times the conversion factor
        return amount * self.get(src_curr, dst_curr, date)


class XMLRateProvider(RateProvider):
    """This class does stuff on the provided XML file.
    It parses it, it keeps it in memory and uses it to respond to queries.
    It is tightly coupled to that particular XML format, but does its job.
    """

    def __init__(self, src):
        self.rates = {}
        self.date_lists = []
        self.lock = threading.RLock()  # to prevent erroneous update when using the file

        # Load from the specified file
        self.load(src)

    def load(self, src):
        with self.lock:
            tree = eTree.parse(src)

            # Find all elements with the 'time' attribute (in the provided XML are the daily sets for the rates)
            self.date_lists = tree.findall('.//*[@time]')

            # Parse the raw XML fields into a more convenient repr, a dictionary ~
            # { <date_string> :
            #               { <currency> : <rate> }
            # }
            # i.e. for each day, a dictionary where KEY = currency and VALUE = rate
            self.rates.clear()

            for day in self.date_lists:
                dayrate = {r.attrib['currency']: float(r.attrib['rate']) for r in day}
                dayrate['EUR'] = 1  # EUR is omitted in the file since there everything is relative to EUR

                self.rates[day.attrib['time']] = dayrate

    # This method should retrieve the desired conversion rate
    def get(self, src, dst, date):
        dateobj = parser.parse(date)

        # if we're talking about a weekend (Sat = 5 or Sunday = 6), then use the ratings from the previous Friday (4)
        # On weekends markets don't update
        # We go back to Friday (4) using the python date objects and then go back to well-formatted strings
        if dateobj.weekday() > 4:
            date = (dateobj.date() - timedelta(days=dateobj.weekday() - 4)).strftime('%Y-%m-%d')

        with self.lock:
            if date in self.rates:
                if dst in self.rates[date] and src in self.rates[date]:
                    return self.rates[date][dst] / self.rates[date][src]   # Convert from SRC to DST

                else:
                    raise InvalidUsage("Unmanaged or unknown currencies.")

            else:
                raise InvalidUsage("Unmanaged date {0}".format(date))

    def save(self, dbpath='./rates.db'):
        conn = sqlite3.connect(dbpath)

        raw_placeholder = "("
        raw_placeholder += "?, " * (len(db_known_currencies))
        raw_placeholder += "?)"  # create a (?,?,?,?,?...) which will be used to properly format the sql query.
        # Ugly, probably could be rewritten in some 1-liner

        count = 0  # just for some statistics

        # create the tuples for insertion in DB
        for date in self.rates:
            # if there's no entry for this date, create it and save it
            if conn.execute("select * from rates where date = ?", (date,)).fetchone() is None:
                datum = [date]
                try:
                    for n in db_known_currencies:
                        datum.append(self.rates[date][n])
                    conn.execute("insert into rates values %s " % raw_placeholder, datum)
                    count+=1
                except KeyError:
                    continue

        conn.commit()
        conn.close()
        print('Saved ', count, 'new entries.')


class DBRateProvider(RateProvider):
    # This provider always searches the DB for the rates and returns them

    def __init__(self, src):
        self.connection = sqlite3.connect(src)

    def get(self, src, dest, date):
        if dest not in db_known_currencies:
            raise InvalidUsage("Unknown currency %s " % dest, 400)
        if src not in db_known_currencies:
            raise InvalidUsage("Uknown currency %s " % src, 400)

        # todo: cache results
# I know, I'm just formatting the currency strings instead of using SQLite substitution, but for 2 reasons:
#   1. A normal substitution (select ?,? from rates where date =?) would not work since would turn into nonsense, like
#         select 'EUR', 'GBP' from rates where date = ?, which instead of returning the actual values returns the names!
#   2. I only format strings that I already checked that are among the ones managed by the DB (see above)
#           So, no SQL injection possible (plus, they are sort-of validated from the beginning)
        cursor = self.connection.execute("select %s, %s from rates where date = ?" % (src, dest) , (date,))
        res = cursor.fetchone()

        if res is None:
            raise InvalidUsage("Unmanaged date %s " % date, 400)

        return float(res[1])/float(res[0])


