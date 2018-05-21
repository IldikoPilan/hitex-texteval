# -*- coding: utf-8 -*-

"""
Functions for assessing the well-formedness of a sentence. 
"""

from __future__ import division
from auxiliaries.dset_proc_aux import *

def has_root(sent_match):
    """Checks wether the sentence has a dependency root.
    """
    if "roots" not in sent_match.stats.keys():
        put_feature_value_list(sent_match.match, "no_root", (True, "no dependency root"))

def check_sent_start(sent_match):
    """ Checks sentence beginning for capital letters.
    """ 
    if sent_match.stats["tokens"][0].word in [u"”", '"', "'", "-", u"–", "("]:
        if not sent_match.stats["tokens"][1].word[0].isupper():
            put_feature_value_list(sent_match.match, "sent_tokenization", (True, "no initial capital"))
            #return
    elif not sent_match.stats["tokens"][0].word[0].isupper(): #and not sent_match.stats["tokens"][0].word.isdigit()
        put_feature_value_list(sent_match.match, "sent_tokenization", (True, "no initial capital"))
        #return

def check_sent_end(sent_match):
    """ Checks sentence end for major delimiters.
    """
    sent_end = sent_match.stats["tokens"][-1]
    if sent_end.word in [u"”", '"', "'", ")"]:
        if sent_match.stats["tokens"][-2].word not in [".", "!", "?"]: #!= "MAD"
            put_feature_value_list(sent_match.match, "sent_tokenization", (True, "ends with: '%s'" % sent_match.stats["tokens"][-2].word))   
    elif sent_end.word not in [".", "!", "?"]: #"MAD" and sent_match.stats["tokens"][-1].word not in [":", "..."]
        put_feature_value_list(sent_match.match, "sent_tokenization", (True, "ends with: '%s'" % sent_end.word))
    #ends with period, but second last word is abbreviation:
    elif sent_end.word == "." and "AN" in sent_match.stats["tokens"][-2].msd.split("."):
        put_feature_value_list(sent_match.match, "sent_tokenization", (True, "ends with: '%s'" % sent_match.stats["tokens"][-2].word))

def check_sent_tokenization(sent_match):
    """ Checks whether the sentence is correctly tokenized.
    """
    check_sent_start(sent_match)
    check_sent_end(sent_match)

def get_bad_lexica_percentage(sent_match, thresholds):
    """ Checks whether the percentage of non-alpha tokens and unrecognized 
    lemmas is within the specified threshold.
    """
    criteria = ["non_alpha", "non_lemmatized"]
    for criterion in criteria:
        if criterion == "non_lemmatized":
            #exclude punctuation marks from non lemmatized items (already counted in non alpha)
            value = len(sent_match.stats.get(criterion, []))
        else:
            value = len(sent_match.stats.get(criterion, []))
        if value > 0:
            corr_value = 0
            # needed for (.) added manually as sentence ending punctuation as 
            # sentence tokenization work-around in Korp annotation lab,
            # present only in the development data
            if "".join([t.word for t in sent_match.stats["tokens"]][-3:]) == "(.)":
                corr_value = 2
            try:
                percentage = (value / len(sent_match.sent.nodes)-corr_value) * 100
            except AttributeError:
                percentage = (value / len(sent_match.sent.sentence.nodes)-corr_value) * 100
            if percentage > thresholds[criterion]:
                crit_str = " ".join(criterion.split("_"))
                message = "%d %s tokens: %s" % (value,crit_str, ", ".join(sent_match.stats.get(criterion, [])))  #nr of tokens per categgory
                put_feature_value_list(sent_match.match, criterion, (percentage, message))
    
def check_ellipsis(sent_match):
    """ Checks whether the sentence is elliptic, i.e. lacks the 
    subject or a finite verb.
    """
    # No subject required with imperative or passive
    if sent_match.stats.has_key("imp_VB") or sent_match.sent[-1]["word"] == "?": #or sent_match.stats.get("passive", 0.0)
        has_subject = True 
    elif sent_match.stats["has_subject"]:
        has_subject = True
    else:
        has_subject = False
    if not sent_match.stats["finite"]: #or not has_subject
        put_feature_value(sent_match.match, "elliptic", (True, "no finite verb")) #no finite verb
    elif not has_subject:
        put_feature_value(sent_match.match, "elliptic", (True, "no subject"))