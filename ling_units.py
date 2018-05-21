# -*- coding: utf-8 -*-
"""
Classes to map: 
(i)  the output XML file from the Sparv pipeline or
(ii) a JSON object from the Korp keyword in context (KWIC) web-service 
to Python objects representing different linguistic units.
Author: Richard Johansson
Contributor: Ildiko Pilan
"""
from auxiliaries.dset_prep_aux import clean_value, ustr
import json

class Token:
    def __init__(self, t, kwic_json=False):
        """
        Arg:
          t: a <w> element from the Korp XML file
             or a 'token' attribute from a Korp JSON.
          kwic_json: whether the object to parse is JSON ('True') or XML ('False')
        """
        if t is not None:
            if kwic_json:
                try:
                    self.word = t['word']
                except KeyError:
                    self.word = ""
                try:
                    self.pos = t['pos']
                except KeyError:
                    self.pos = ""
                    #print self.word
                try:
                    self.msd = t['msd']
                except KeyError:
                    self.msd = ""
                try:
                    self.lemma = clean_value(t,'lemma')
                except KeyError:
                    self.lemma = []
                try:
                    self.lex = clean_value(t,'lex')
                except KeyError:
                    self.lex = []
                try:
                    self.saldo = clean_value(t,'sense') #Sparv v1: 'saldo'
                except KeyError:
                    self.saldo = []
                try:
                    self.ref = t['ref']
                except KeyError:
                    self.ref = ""
                try:
                    self.depheadid = t['dephead']
                except KeyError:
                    self.depheadid = ""
                try:
                    self.deprel = t['deprel']
                except KeyError:
                    self.deprel = ""
                try:
                    self.suffix = clean_value(t, 'suffix')
                except KeyError:
                    self.suffix = ""
            else:
                self.word = t.text                   #e.g. gick
                self.pos = t.attrib['pos']           #e.g. "VB"
                self.msd = t.attrib['msd']           #e.g. "VB.PRT.AKT"
                self.lemma = clean_value(t,"lemma")  #e.g. ["gå"] or just [""] or list of more lemmas
                self.lex = clean_value(t,"lex")      #e.g. ["gå..vb.1"]
                self.saldo = clean_value(t,'sense')  #e.g. [gå..1,gå..10,gå..8]
                self.ref = t.attrib['ref']           #e.g. "01"
                if "dephead" in t.attrib:
                    self.depheadid = t.attrib['dephead'] #e.g. "02"
                else:
                    self.depheadid = ""
                self.deprel = t.attrib['deprel']     #e.g. "ROOT" or "ET"
                try:
                    self.suffix = clean_value(t, 'suffix')
                except KeyError:
                    self.suffix = ""
            self.length = len(self.word)       
        else:
            self.ref = '0'
            self.deprel = None
            self.word = None
            self.pos = None
            self.lemma = None
            self.saldo = None
        self.deps = []

    def __repr__(self):
       if self.word:
           return "(" + ustr(self.ref) + ", " + ustr(self.word) + ", " + ustr(self.pos) + ", " + ustr(",".join(self.lemma)) + ", " + ustr(self.dephead.ref) + ")"
       else:
           return "(None)"
    
    def __str__(self):
        return "(" + ustr(self.word) + ")"

class Sentence:
    def __init__(self, sent_element, level="", source_name="", kwic_json=""):
        """
        Arg:
          sent_element: equal to <sentence> element from the Korp XML file
                        or a 'tokens' attribute from a Korp JSON.
          level (str):  difficulty level
          source_name (str): name of the source of the sentence (e.g. coursebook title)
          kwic_json: whether the object to parse is JSON ('True')or XML ('False')
        """
        self.level = level
        self.sources = source_name
        self.nodes = [] #Token(None)
        dhead_id_to_tkn = {}
        self.bug = False
        
        if not kwic_json: #sent_element is a kwic instance
            if sent_element.attrib.has_key("id"):
                self.sent_id = sent_element.attrib["id"]
        else:
            #print sent_element 
            self.sent_id = ""
        
        for w in sent_element:
            if kwic_json:
                tn = Token(w, kwic_json)
            else:
                tn = Token(w)
            self.nodes.append(tn)
            dhead_id_to_tkn[tn.ref] = tn

        #check if the token has a deapheadid, if not, set to 0 
        for n in self.nodes:
            if n.deprel:
                if n.depheadid:
                    if not dhead_id_to_tkn.has_key(n.depheadid):
                        #print n
                        #print "Error: no key"
                        #exit(1)
                        n.dephead = self.nodes[0]
                        self.bug = True
                    else:
                        n.dephead = dhead_id_to_tkn[n.depheadid]
                else:
                    n.dephead = self.nodes[0]
                n.dephead.deps.append(n)
        #if self.bug:
        #    for w2 in sent_element:
        #        print w2
        self.length = len(self.nodes)
        
        #create .words attribute
        out = ""
        for n in self.nodes:
            if n.word:
                out = out + n.word + u" "
        self.words = ustr(out.strip())

    def __str__(self):
        return "(Sen: " + self.words + ")"
    
    def __getitem__(self, i):
        return self.nodes[i]

    def __setattr__(self, name, value):
        self.__dict__[name] = value


class Text:
    def __init__(self, text, source_name, level, text_genre=""):
        """
        Arg:
          text: equal to <text> element from the Korp XML file
          source_name (str): name / id of the source of the sentence (e.g. coursebook title)
          level (str):  proficiency level
          text_genre (str): genre of the text, if any

        Attributes:
          source (str):   title / id of the source (or other source) of the text 
          level (str):  proficiency level of text
          text_id (str):unique text id from the corpus
          title (str):  text title
          text_topic:   text topic
          sents (list): list of Sentence objects
          length (int): the number of sentences in the text
        """
        self.sources = source_name          #ex 'corpus'
        self.level = level
        if text.attrib.has_key("id"):
            self.text_id = text.attrib["id"]
        else:
            self.text_id = ""
        if text.attrib.has_key("title"):
            self.title = text.attrib["title"]
        else:
            self.title = "*no title*"
        if text.attrib.has_key("topic"):
            self.text_topic = text.attrib["topic"].strip("|")
        else:
            self.text_topic = "*no topic*"
            #print "No topic for '%s' in '%s'" % (self.text_id, self.sources)
        self.text_genre = text_genre.strip("|") 
        #multiple topics and genres separated by '|'
        self.sents = []   #sent = one kwic from kwics list
        for paragraph in text:
            if paragraph.tag == "paragraph":
                for snt in paragraph:
                    self.sents.append(Sentence(snt, self.level))
            if paragraph.tag == "sentence":
                self.sents.append(Sentence(paragraph, self.level))
        self.length = len(self.sents)
        self.length_in_tokens = sum([sent.length for sent in self.sents])
    
    def __str__(self):
        """Prints the whole text and its title (if any)."""
        title = "TEXT: %s \n" % ustr(self.title) #.encode("utf-8")
        try:
            content = "\n".join([ustr(s.words) for s in self.sents])
        except:
            content = "\n".join([s.words for s in self.sents])
        return title + content

    def print_info(self):
        """Prints information about the text, not the text itself."""
        print "TEXT INFO:"
        print "\tLevel: \t%s\n \tsource: \t%s\n \tID: \t%s\n \tTopic: \t%s\n \tGenre: \t%s\n" \
        % (self.level, self.sources, self.text_id, self.text_topic, self.text_genre)

