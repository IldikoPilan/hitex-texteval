"""
Classes for mapping Korp keyword in context (kwic) search results into
Python objects.
Author: Richard Johansson
Contributor: Ildiko Pilan
"""
import random
from ling_units import Sentence

class match:
    """ 
    The 'match' attribute of a KWIC in the search reasults.
    """ 
    def __init__(self, t):
        self.position = int(t['position'])
        self.start = int(t['start'])
        self.end = int(t['end'])
    def __str__(self):
        return "(" + str(self.position) + ", " + str(self.start) + ", " + str(self.end) + ")"

class structs:
    """ 
    The 'struct' attribute of a KWIC in the search reasults.
    """ 
    def __init__(self, t):
        self.sentence_id = t['sentence_id']
    def __str__(self):
        return "(" + str(self.sentence_id) + ")"

class kwic:
    """ A corpus example (KWIC) from the search reasults' 'kwic'.
    """
    def __init__(self, t):
        #self.index = None
        self.source = t
        self.corpus = t['corpus']
        try:
            self.match = match(t['match'])
        except KeyError:        #to handle corpora outside Korp
            self.match = ""
        try:
            self.structs = structs(t['structs'])
        except KeyError:
            self.structs = "-"
        self.sentence = Sentence(t['tokens'], kwic_json=True)
    def __str__(self):
        return "[KWIC: match = " + str(self.match) + ": " + str(self.sentence) + "]"
    def get_source(self):
        return self.source

class search_result:
    """ 
    Korp KWIC search reasult mapped.
    """
    def __init__(self, t):
        if not t.has_key('kwic'):
            print "Error: no kwic"
            print t
            exit(1)
        else:
            self.kwics = map(kwic, t['kwic'])
            self.corpus_hits = t['corpus_hits']
            self.time = t['time']
            if t.has_key('hits'):
                self.nhits = int(t['hits'])