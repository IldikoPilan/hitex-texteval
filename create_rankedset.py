# -*- coding: utf-8 -*-

"""
Example use of the MatchingSet class.
"""

from matching_set import MatchingSet
import weka.core.jvm as jvm

def create_mset_json(parameters, criteria):
    jvm.start()
    ms = MatchingSet(parameters, criteria)
    ms.create_set()
    url = ms.get_url()
    j = ms.to_json()
  
    return (ms, j, url)

scoring_type = ["filter", "rank"] # "skip" - do not include key if not selected!

parameters = { 
  "query_type": "lemma", # wordform or cqp or lemma
  "query_w" : u'bröd',   # u"huset", [deprel = "SS" & lemma contains "språk"].decode("utf-8")
  #"query_w" : '[ref = "01" & pos = "NN" & lemma contains "dörr"]'.decode("utf-8"),
  #"query_w" :'[msd = "VB.INF.AKT" &]'.decode("utf-8"),
  "query_pos" : "NN",
  #"corpus_list":["ROM99","GP2012","LASBART"], #randomly pick one of them? "BLOGGMIX2012"
  "corpus_list":["rom99","gp2010","gp2011","gp2012","gp2013","gp2d","attasidor","lasbart","suc3","talbanken"], #"wikipedia-sv" "sweachum","sweacsam"
  "max_kwics": 40,       # nr KWICs to process (limited for efficiency reasons)
  "maxhit": 10,          # maximum number of matches to return
  "target_edge" : "end", # to which edge the keyword should be close to
  "proportion" : 50,     # within which percentage of the sent the keyword should appear
  "target_cefr" : "A1",
  "voc_thr" : 0,         # percentage of words above the target CEFR level
  "min_len" : 6,
  "max_len" : 20, 
  "non_alpha_thr": 30,
  "non_lemmatized_thr": 30,
  #"lex_to_func_thr": 0.8,
  "sensitive_voc_cats": ["all"], # ["sex", "violence", "other", "religion", "secretion"],
  "preserve_bad":True
}
 
criteria = {
  "well_formedness":{"root":"filter", "sent_tokenization":"filter", 
                    "elliptic":"filter", "non_alpha":"filter", 
                    "non_lemmatized":"filter"}, 
                    # or "filter" / "ranker" instead of {} -> -1 point per subcriteria
  "isolability":{"struct_conn":"filter", "yn_answer":"filter", 
                 "anaphora-PN":"filter", "anaphora-AB":"filter"}, # or "filter" / "ranker" instead of {}
  "readability":"filter", #TO DO: debug 'ranker' here?
  "typicality": "ranker",
  "sensitive_voc": "filter",
  "other_criteria":{"length":"filter",
                     "proper_name":"filter",
                     "repkw":"filter",
                    # "kw_position":"filter",
                    # "modal_verb":"filter",
                    # "participle":"filter",  same as korp
                    # "sverb":"filter",       same as korp
                     "interrogative":"filter",
                    # "neg_form":"filter",
                     "abbrev":"filter",
                     "direct_speech":"filter",
                     "diff_voc_kelly":"rank",
                     "svalex_fr":"filter",
                     "out_of_svalex":"filter"}}

#well_formedness_cr = criteria["well_formedness"].keys()
#["has_root", "sent_tokenization", "elliptic", "mostly_alpha", "mostly_lemmatized"]
#isolability_cr = criteria["isolability"].keys()
#["struct_conn", "yn_answers", "anaph_pn", "anaph_adv"]

mset,json_ms,url = create_mset_json(parameters, criteria)
print mset
mset.print_match_info()
#print json_ms
print url