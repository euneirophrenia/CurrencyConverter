from flask import Flask
from flask import request
from flask import jsonify

from datatools import *

from dateutil import parser
import re


non_alpha = re.compile(r"[^a-z]", re.IGNORECASE)  # a regex to match any non-alpha char, compiled since it's used a lot

app = Flask(__name__)


def currency_parser(string):
    # removing any non alpha-numeric char, i could also remove numeric, but not 100% sure.
    # Anyway this should be enough to prevent funky shit going in the query
    return non_alpha.sub('', string)


def float_parser(string):
    try:
        return float(string)  # just try to parse the float
    except ValueError:
        raise InvalidUsage("Invalid numeric format (please use the '.' for decimals and omit currency signs)", 400)


def date_parser(string):
    # this should perform enough checks on its own and then output a well formatted date
    # notice that the parser.parse() accepts also strings like 2018-5-15 ( != 2018-05-15 )
    # the obj.strftime(%Y-%m-%d) ensures that the output is in the "2018-05-15" format (i.e. the month is 0-padded)
    try:
        obj = parser.parse(string)
        return obj.strftime('%Y-%m-%d')
    except ValueError:
        raise InvalidUsage("Invalid date format" , 400)


# a map of argument - parsing function, not really necessary but concise IMHO
endpoint_params = {'amount' : float_parser,
                   'src_currency' : currency_parser, 'dest_currency' : currency_parser,
                   'reference_date' : date_parser
                   }


# This handles the various parameter related exceptions, triggering whenever a "InvalidUsage" exception arises
# It returns a JSON with an HTTP response code customizable when throwing the exception
@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


# Main page, not important, may as well be discarded.
@app.route('/')
def landing():
    return 'Currency Converter'


# Proper service endpoint, not really doing anything, just returns the expected JSON
@app.route('/convert')
def endpoint():
    # DB Rate provider, created 1 for each request because it won't work across different processes..
    provider = DBRateProvider('./rates.db')

    params = {k : request.args.get(k, type=endpoint_params[k]) for k in endpoint_params.keys()}

    result = {'amount' : provider.convert(params['amount'], params['src_currency'],
                                          params['dest_currency'], params['reference_date']),
              'currency' : params['dest_currency']}

    return jsonify(result)


if __name__ == '__main__':
    app.run()
