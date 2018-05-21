# -*- coding: utf-8 -*-

import json
import httplib, urllib
from korp_classes import search_result


def call_korp(params):
    """ Makes a Korp concordance API request.
    """
    KORP_SERVER = "demosb.spraakdata.gu.se"
    KORP_SCRIPT = "/cgi-bin/korp/korp.cgi"
    conn = httplib.HTTPConnection(KORP_SERVER)
    param_enc = urllib.urlencode(params)
    conn.request("GET", KORP_SCRIPT + "?" + param_enc)
    #print "executing GET " + KORP_SCRIPT + "?" + param_enc
    response = conn.getresponse()
    if response.status == 200:
        response_str = response.read()
        #print "response = |" + response_str + "|"
        out = json.loads(response_str)
    else:
        print "response = None"
        out = None
    conn.close()
    #print "out =", str(out)

    if out.has_key('ERROR'):
        print "Korp call error for this query:"
        print "|" + param_enc + "|"
        print "result:", out
        exit(1)

    return out

def korp_search(corpora, cqpexpr, start, end, seed):
    clist = ','.join(corpora)
    #print "clist =", clist
    return search_result(call_korp({'command':'query', 
                                    'corpus':clist,
                                    'defaultcontext':'1 sentence',
                                    'cqp':cqpexpr.encode('utf-8'),
                                    'show':'ref,word,pos,msd,lemma,dephead,deprel,saldo,lex,suffix',
                                    'start':start,
                                    'indent':'8',
                                    'sort':'random',
                                    'random_seed': seed,
                                    'end':end,
                                    'show_struct':'sentence_id'}))
