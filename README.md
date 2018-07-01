# CurrencyConverter

A Flask backend providing a REST interface for currency conversion.

Once up, the server accepts GET requests in the form

```/convert?amount=<VALUE>&src_currency=<ISO_NAME>&dest_currency=<ISO_NAME>&date=<YYYY-mm-dd>```

It returns a JSON file in the form

```json
    {
        "amount" : 1234,
        "currency" : "<ISO_NAME>"
    }
```
If something goes wrong, it returns both a proper HTTP error code (typically 400, for bad requests) and a JSON explaining some more details on what went wrong.



## Setup

It is tested and developed with Python 3.4, using Flask 1.x and SQLite3.

No further packages needed.

Data are retrieved from [the EU Central bank official site](https://www.ecb.europa.eu/stats/eurofxref/) and kept in a local DB.

In order to keep everything up to date, a script to update the DB (i.e. to fetch the latest data and update the DB) must be allowed to run once a day, in background.

To do so, the script (`dbsetup.py`) must be invoked like this:

```
    python3 dbsetup.py --update
```

> use `--help` to check additional parameters and options

It can also be used to setup the db initially, invoking it with the `--create` option.

> At this current point in time, `dbsetup.py` is **not** called automatically, must be set up "by hand", using either `crond` (on Unix systems) or more python code. In a near future I will set it up myself to run periodically.


## Future improvements
- [ ] Optimize the code
- [ ] Automatically run the DB update once a day
- [ ] Create a local cache instead of querying the DB for every request
- [ ] Better paths management

## Potential developments
* Find out the most frequently used currencies and optimize the cache to keep their rates closer
* Develop a rate predictor based on the full time series (since 2001, the beginning of Euro)