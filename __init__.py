from flask import Flask
from flask import jsonify
from flask import abort
from flask import make_response
from flask import request

import csv
import random
import os
import re
import urllib 

app = Flask(__name__)
app.debug = True

class WebFactionMiddleware(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = '/webhooks'
        return self.app(environ, start_response)

app.wsgi_app = WebFactionMiddleware(app.wsgi_app)


quotes = []

quoters = {
    'fluffyemily' : 'ET',
    'geek_manager': 'MW',
    'pixeldiva': 'AC',
    'jcm': 'JM',
    'cackhanded': 'MNF',
    'rnalexander': 'RA',
    'nick': 'NS',
    'jabley': 'JA',
    'fatbusinessman': 'DT',
    'elly': 'EW',
    'pkqk': 'AJ'
}

#@app.errorhandler(404)
#def not_found(error):
#    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/quote', methods = ["POST"])
def get_quote():
    quoter = request.form['text'].replace("quote", "")
    print "|"+quoter+"|"
    if len(quoter) > 0:
        quoter = str(quoter).strip()
    if quoter == "me":
        quoter = quoters[request.form['user_name']]
    elif quoters.get(quoter) is not None:
        quoter = quoters[quoter]
    
    print quoter
    if len(quoter) == 0:
        filtered_quotes = quotes
    else:
        filtered_quotes = filter(lambda t: t['by'] == quoter, quotes)

    print filtered_quotes
    
    quote = random.choice(filtered_quotes)
    quote_string = "*"+ quote['by'] + "*: "+ quote['quote']
    print "returning quote: "+ quote_string
    return jsonify({'text': quote_string})


@app.route('/quotes', methods = ["POST"])
def create_quote():
    if len(request.form) > 0:    
        quote_text = request.form['text'] #.encode('utf-8', 'replace')
    elif request.json is not None:
        quote_text = request.json['text']
    else:
        abort(400)

   # print quote_text
    matches=re.findall(r'\"(.+?)\"',quote_text)
    quote = ""
    for match in matches:
        quote_text = quote_text.replace(match, "")
        if len(quote) > 0:
            quote += "\n"
        quote += match

    quote_text.replace("'", "")

    parts = quote_text.split(" ")
    #print parts
    quote_by = parts[-1]
    print quote
    print quote_by
    quote_obj = {
        'quote': quote,
        'by': quote_by
    }
    #add quote to list
    quotes.append(quote_obj)

    #write quote to csv file for future usage
    with open('webapps/slack_webhooks/slack_webhooks/quoteboard.csv', 'ab') as csvfile:
        quote_writer = csv.writer(csvfile, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        quote_writer.writerow([quote_obj['by'], quote_obj['quote']])

    for name, initials in quoters.iteritems():
        if initials == quote_by:
            quote_by = name
            break
    return_quote = "Quoth *"+ quote_by +"*: "+ quote
    return jsonify({"text": return_quote})


def init_db():
    #initialise the db by reading in all of the existing quotes
    print "initing db"
    print os.getcwd()
    with open('webapps/slack_webhooks/slack_webhooks/quoteboard.csv') as csvfile:
        quote_reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in quote_reader:
            quote = {
                'quote': row[1],
                'by': row[0]
            }
            quotes.append(quote)

init_db()

if __name__ == "__main__":
    app.run(debug = True)
