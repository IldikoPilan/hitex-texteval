# -*- coding: utf-8 -*-

"""
Default parameter settings for the HitEx (sentence selection)
web-service, tuned for detecting exercise items.
"""
#TO DO: add dictionary example setup 

default_parameters = { # parameter values to use for the criteria below
    "query_type": "", # type of search (wordform or cqp or lemma)
    "query_w" : "",   # search expression (e.g. u"huset", [lemma contains "språk"] [deprel = "SS"].decode("utf-8"))
    "query_pos" : "", # part of speech to use for query wordform or lemma (e.g.# "NN")
    "corpus_list":["rom99","flashback-resor","gp2013","gp2d","attasidor","lasbart","suc3","talbanken"],
                      # corpus to search in (any Korp corpora with the same ID)
    # additional options: ["attasidor","lasbart","talbanken","rom99",
    #                      "familjeliv-allmanna-fritid","flashback-mat",
    #                      "flashback-resor","wikipedia-sv" "sweachum","sweacsam","BLOGGMIX2012"]
    "max_kwics": 80,       # nr KWICs to process (limited for efficiency reasons)
    "maxhit": 10,          # maximum number of matches to return
    "target_edge" : "end", # to which edge the keyword should be close to
    "proportion" : 50,     # within which percentage of the sent the keyword should appear
    "target_cefr" : "B1",  # 'any' not supported - omit readability to obtain the same effect
    "voc_thr" : 0,         # percentage of words above the target CEFR level
    "min_len" : 6,         # minimum length of the sentence
    "max_len" : 20,        # maxumum length of the sentence
    "non_alpha_thr": 30,   # maximum amount of non_aphabetical tokens in percent
    "non_lemmatized_thr": 30, # maximum amount of non-aphabetical tokens in percent
    "lex_to_func_thr": "",    # maximum amount of non-lemmatized tokens in percent
    "sensitive_voc_cats": ["all"], # categories of sensitive vocabulary 
                                   # options: ["sex", "violence", "other", "religion", "secretion"],
    "preserve_bad":True}   # whether to retain and show also sentences assessed as bad 

default_criteria = {
    "well_formedness":{"root":"filter",                # sentence has a dependency root
                       "sent_tokenization":"filter",   # complete sentence beginning and end
                       "elliptic":"filter",            # presence of subject and finite verb 
                       "non_alpha":"filter",           # amount of non-aphabetical tokens
                       "non_lemmatized":"filter"},     # amount of non-lemmatized tokens
    "isolability":{"struct_conn":"filter",  # structural connectives (conjuctions and subjunctions)
                   "yn_answer":"filter",    # answer to yes/no questions
                   "anaphora-PN":"filter",  # pronominal anaphora
                   "anaphora-AB":"filter"}, # adverbial anaphora (time or place)
    "readability":"filter",     # language learning (CEFR) level
    "typicality": "ranker",     # measures  lexicographers' mutual information score (word co-occurrence)
    "sensitive_voc": "filter",  # sensitive vocabulary (profanaties etc.)
    "other_criteria":{"length":"filter",       # sentence length
                     "proper_name":"ranker",   # proper names
                     "repkw":"filter",         # keyword repetition
                     "kw_position":"",         # position of keyword
                     "modal_verb":"",          # modal verbs
                     "participle":"",          # participles
                     "sverb":"",               # S-verbs (reciprocal, passive)
                     "interrogative":"filter", # interrogative sentence
                     "neg_form":"",            # negative formulations
                     "abbrev":"filter",        # abbreviations
                     "direct_speech":"filter", # direct speech
                     "diff_voc_kelly":"filter",# difficult vocabulary based on the Kelly list
                     "svalex_fr":"",           # word frequency from SVALex list
                     "out_of_svalex":"filter"} # words not in SVALex
                     }