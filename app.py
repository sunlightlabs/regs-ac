import sys

try:
    import local_settings as settings
except ImportError:
    settings = type(sys)('settings')
sys.modules['settings'] = settings

import regs_models
from flamebroiler import Trie
from flask import Flask, request
import json
import re

# data structure

trie = Trie()

for agency in regs_models.Agency.objects().only('id', 'name'):
    data = "a|%s|%s" % (agency.id, agency.name if agency.name else agency.id)
    trie[agency.id.lower()] = data
    if agency.name:
        trie[agency.name.lower()] = data

for org in regs_models.Entity.objects(td_type="organization", stats__submitter_mentions__count__gte=5).only('id', 'aliases'):
    if org.aliases:
        data = "o|%s|%s" % (org.id, org.aliases[0])
        for alias in org.aliases:
            trie[alias.lower()] = data

# endpoint
app = Flask(__name__)

spaces = re.compile('(\W+)')
types = {'a': 'agency', 'o': 'organization'}

@app.route("/ac")
def ac():
    full_term = request.args.get('term', '')
    terms = spaces.split(full_term.strip())
    nterms = len(terms)
    out = []
    
    for tstart in xrange(0, nterms, 2):
        term = " ".join(terms[tstart:nterms:2]).lower()
        matches = trie.suffixes(term, max_matches=10 - len(out))
        if matches:
            pretty_term = "".join(terms[tstart:nterms])
            for match in matches:
                ms = match.split("|")
                out.append({
                    'term': pretty_term,
                    'type': types[ms[0]],
                    'id': ms[1],
                    'name': ms[2]
                })
        
        if len(out) >= 10:
            break

    return json.dumps({'matches': out})

if __name__ == '__main__':
    app.run()