from flask import Flask
from flask import jsonify
from flask import abort
from flask import request

from markov import Markov

import csv
import random
import os
import re
import urllib 
from nltk.corpus import stopwords

app = Flask(__name__)
#app.config.from_object('slack_webhooks.default_settings')
#app.config.from_envvar('SLACK_WEBHOOKS_SETTINGS')
app.debug=True

class WebFactionMiddleware(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = '/slack_webhooks'
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
    'pkqk': 'AJ',
    'the_richey': "PR",
    'SarahPrag': "SP"
}

#@app.errorhandler(404)
#def not_found(error):
#    return make_response(jsonify({'error': 'Not found'}), 404)

stopwords_to_remove = set(stopwords.words("english"))

def strip_non_alphanumeric(from_string):
    return re.sub(r'([^\s\w]|_)+', '', from_string)

def get_bag_of_words(from_string):
    bag_of_words = set(strip_non_alphanumeric(from_string).lower().split()) - stopwords_to_remove
    return bag_of_words

def quote_as_string(quote):
    quote_string = ""
    i = 0
    for quote_by in quote['by']:
        quote_text = quote['quotes'][i]
        if len(quote_string) > 0:
            quote_string += "\n"
        quote_string += "*"+ quote_by + "* - \""+ quote_text +"\""
        i = i + 1
    print quote_string
    return quote_string

@app.route('/searchquote', methods=["POST"])
def search_quotes():
    if len(request.form) > 0:    
        quote_text = request.form['text'] #.encode('utf-8', 'replace')
    elif request.json is not None:
        quote_text = request.json['text']
    else:
        abort(400)

    index_of_search_term = quote_text.find("quote")
    index_of_search_term += len("quote about")

    search_term = quote_text[index_of_search_term:len(quote_text)].strip()

    if search_term is None or len(search_term) == 0:
        return jsonify({'text': "Unable to find a search term"})
    
    # remove all punctuation for processing and make it all upper case for searching
    #search_term = strip_non_alphanumeric(search_term).upper()
   # search_bag = set(search_term.split())
    search_bag = get_bag_of_words(search_term)
    print search_bag

    number_of_matched_words = 0

    best_match_quote = None
    best_match_word_bag = set()

    for quote in quotes:
        print quote['quotes']
        quote_to_compare = "\n".join(quote['quotes'])
        print "comparing "+ quote_to_compare
        compare_bag = get_bag_of_words(quote_to_compare)
        intersection_bag = compare_bag.intersection(search_bag)
        if number_of_matched_words < len(intersection_bag):
            number_of_matched_words = len(intersection_bag)
            best_match_quote = quote


    if best_match_quote is not None:
        quote_string = quote_as_string(best_match_quote)
        print "returning quote: "+ quote_string
        return jsonify({'text': quote_string})

    print "Unable to find a matching quote"
    return jsonify({'text': "Cannot find any quotes that match the search "+ search_term})


@app.route('/quote', methods = ["POST"])
def get_quote():
    # get the quote info from the form
    quoter = re.sub('(?i)' + re.escape('quote'), "", request.form['text'])
  #  quoter = .replace("quote", "")

    # work out which initials/name to look for
    if len(quoter) > 0:
        quoter = str(quoter).strip()
    if quoter == "me":
        quoter = quoters[request.form['user_name']]
    elif quoters.get(quoter) is not None:
        quoter = quoters[quoter]
    
    print quoter

    # filter the quotes to include only the quoter, if a specific quoter 
    # has been requested
    if len(quoter) == 0:
        filtered_quotes = quotes
    else:
        filtered_quotes = filter(lambda t: quoter in t['by'], quotes)

    print filtered_quotes
    
    # if there are quotes to search, selet a random one,
    # otherwise return a nice message saying there are no quotes
    if len(filtered_quotes) > 0:
        quote = random.choice(filtered_quotes)
        quote_string = quote_as_string(quote)
        print "returning quote: "+ quote_string
        return jsonify({'text': quote_string})

    return jsonify({'text': "Cannot find any quotes by "+ quoter})


@app.route('/quotes', methods = ["POST"])
def create_quote():
    # get the text either from the form data (posted from Slack)
    # or from the POST data (curl or some other means)
    if len(request.form) > 0:    
        quote_text = request.form['text'] #.encode('utf-8', 'replace')
    elif request.json is not None:
        quote_text = request.json['text']
    else:
        abort(400)

    # find everything that is between quotes - this is the quote  -and then
    # remove the quotes from the text
    matches=re.findall(r'\"(.+?)\"',quote_text)
    quote = ""
    for match in matches:
        quote_text = quote_text.replace(match, "")
        if len(quote) > 0:
            quote += "\n"
        quote += match

    # remove all punctuation except for whitespace and any bot text to leave
    # only the quoter information
    quote_by = strip_non_alphanumeric(quote_text)
    quote_by = re.sub('(?i)' + re.escape('addquote'), "", quote_by)
    quote_by = quote_by.strip()

    print quote
    print quote_by
    quote_obj = {
        'quote': quote.split("\n"),
        'by': quote_by.split('\n')
    }
    #add quote to list
    quotes.append(quote_obj)

    #write quote to csv file for future usage
    with open('webapps/slack_webhooks/slack_webhooks/quoteboard.csv', 'ab') as csvfile:
        quote_writer = csv.writer(csvfile, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        quote_writer.writerow([quote_by, quote])

    # add quote to markov file for use in quote generation
    with open('webapps/slack_webhooks/slack_webhooks/markov.txt', 'ab') as markovfile:
        if quote[-1] != '.' and quote[-1] != '!' and quote[-1] != '?':
            quote += '. '
        else:
            quote += ' '
        markovfile.write(quote)

    # look to see if we can replace initils with a name in the return text
    for name, initials in quoters.iteritems():
        if initials == quote_by:
            quote_by = name
            break

    # return a nice message so everyone knows it worked
    #return_quote = "Quoth *"+ quote_by +"* \" "+ quote +" \""
    return ""

@app.route('/genquote', methods = ["POST"])
def generate():
    # create a markov chain and generate random markov text to return
    markov = Markov(open('webapps/slack_webhooks/slack_webhooks/markov.txt'))
    rand_int = random.randint(3,7)
    new_quote = markov.generate_markov_text(rand_int)
    return jsonify({"text": new_quote})

def init_db():
    #initialise the db by reading in all of the existing quotes
    print "initing db"
    print os.getcwd()
    quotes_text = ""
    with open('webapps/slack_webhooks/slack_webhooks/quoteboard.csv') as csvfile:
        quote_reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in quote_reader:
            quote_text = row[1]
            all_quotes = quote_text.split("\n")
            all_quoters = row[0].split("\n")
            quote = {
                'quotes': all_quotes,
                'by': all_quoters
            }
            quotes.append(quote)
            if quote_text[-1] != '.' and quote_text[-1] != '!' and quote_text[-1] != '?':
                quote_text += '. '
            else:
                quote_text += ' '

            quotes_text += quote_text
    with open('webapps/slack_webhooks/slack_webhooks/markov.txt', 'wb') as markovfile:
        markovfile.write(quotes_text)

init_db()

if __name__ == "__main__":
    app.run(debug = True)
