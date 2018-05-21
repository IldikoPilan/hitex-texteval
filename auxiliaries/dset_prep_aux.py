# -*- coding: utf-8 -*-
import re

"""
Small auxiliary (help) functions for cleaning / transforming 
data and values.
"""

def ustr(us):
    "Transforms the encoding of a string if necessary."
    if not us:
        return "NONE"
    return us.encode("utf-8")

def clean_value(t,attr):
    """Cleans the value of attribute 'attr'
    and returns a list with the cleaned elements.
    E.g. "|gå..1|gå..10|gå..8:2|" transformed into
    [gå..1, gå..10.., gå..8] 
    Needed in the case of certain Korp values.
    Arg:
      attr (str): the attribute of Token that needs to be cleaned
    """
    try:
        value_lst = t[attr].split('|')            # for JSON object
    except TypeError: # AttributeError
        value_lst = t.attrib[attr].split('|')     # for XML files
    p = r":[0-9]*"
    cln_values = filter(None,[re.sub(p,"",v) for v in value_lst])
    return cln_values

def find_buggy_sent(sent):
    """A simple filter for sentences with potentially incorrect
    annotation (e.g. sentence tokenizer problems etc.)
    """
    buggy_sent = False
    if sent.words == '"' or sent.words == ')':
        buggy_sent = True
    #check inital capital letter 
    elif sent.words[0] == '"' or not sent.words[0].isupper(): 
        buggy_sent = True
    #check sentence-ending punctuation
    elif sent.words[-1] not in ['.', "!", "?", ")"]:
        buggy_sent = True 
    else: 
        for tkn in sent.nodes:
            #check undesirable symbols
            if tkn.word in [":", "*", "/", "XX"]:   
                buggy_sent =True
            elif tkn.word.isupper():
                buggy_sent =True
    #ADD: if no ROOT element in the sentence? 
    return buggy_sent

def get_label(korp_xml):
    """Returns the second element of an underscore-separated filename.
    This will be used as label (category) for the dataset instances in
    the ItemCollector class. Adapted to handle both CEFR levels and context dependency.
    """
    label = korp_xml.split("_")[1]
    if label == "easy-fiction":
        result = "B1"
    elif label == "ord-fiction":
        result = "C1"
    elif label == "dep":
        result = "context_dep"
    elif label == "indep":
        result = "context_indep"
    else:
        result = label
    return result