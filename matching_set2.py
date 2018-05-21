# -*- coding: utf-8 -*-

import os
activate_this = os.path.join("/export/cgi-bin_sb/larkalabb", 'venv/bin/activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

import json
import operator
import random
import urllib
import numpy
import cPickle
import time
#from weka.classifiers import Classifier
#import weka.core.serialization as serialization
import word_pic
from call_korp import korp_search
from sent_statistics import SentStatistics
from sent_match import SentMatch
from auxiliaries.match_aux import load_list
from kelly import process_csv

class MatchingSet():
    """ Makes a Korp (http://spraakbanken.gu.se/korp) search based on 
    the query defined in 'parameters' and returns a list of corpus 
    hits, i.e. KWICs (KeyWord In Context). With the create_set method 
    a list of KWICs sorted based on the degree of matching the criteria 
    can be obtained.

    Args:
      parameters (dict): search parameters         
      criteria (dict):   criteria to use and the associated scoring type
                         (filter or ranker)

    Attributes:
      kwics (list):        KWICs mapped to a kwic instance
      korp_query (tuple):  query used for the KWIC web-service of Korp 
      params (dict):       see above
      criteria (dict):     see above
      positive_crit (list):criteria that are positively correlated with
                           the goodness of a sentence
      rset (list):         KWICs (SentMatch instances) matching the 
                           selection criteria
      bad_results (list):  suboptimal KWICs (SentMatch instances) 

    Yields:
      A list of KWICs transformable into a list of SentMatch instances. 
    """
    def __init__(self):
        pass

    def initialize(self, parameters, criteria):
            
        #Construct query
        if parameters["query_type"] == "lemma":
            if "query_pos" in parameters:
                korp_query = (u'[(lemma contains "%s") & (pos = "%s")]' % 
                              (parameters["query_w"], 
                               parameters["query_pos"]))
            else:
                korp_query = (u'[lemma contains "%s"]' % 
                              parameters["query_w"])
        elif parameters["query_type"] == "wordform":
            if "query_pos" in parameters:
                korp_query = (u'[word = "%s" & (pos = "%s")]' % 
                              (parameters["query_w"], 
                               parameters["query_pos"]))
            else:
                korp_query = u'[word = "%s"]' % parameters["query_w"]
        elif parameters["query_type"] == "cqp":
            korp_query = parameters["query_w"]

        #Initializing attributes
        self.korp_query = korp_query
        self.params = parameters
        self.criteria = criteria
        self.positive_crit = ["MI", "typicality"] #"svalex_fr"
        self.rset = []
        self.bad_results = []
        
        #Getting and randomizing KWICs
        end = 2000 
        seed = ""
        random_seeds = {"A1":1, "A2":2, "B1":3, "B2":4, "C1":5}
        if len(self.params["corpus_list"]) > 4:
            corp_seed = random_seeds[self.params["target_cefr"]]
            random.seed(corp_seed)
            #randomization for corpus selection
            random.shuffle(self.params["corpus_list"])  
            if self.params["target_cefr"][0] == "A":
                    corpora = ["attasidor", "lasbart"]
                    extra_corpora = [c for c in self.params["corpus_list"] 
                                     if c not in corpora][:2]
                    corpora += extra_corpora
            else:   #B1 level
                corpora = self.params["corpus_list"][:4] 
        else:
            corpora = self.params["corpus_list"]
        search = korp_search(corpora, korp_query, 0, end, seed)
        print search.corpus_hits
        self.kwics = search.kwics
        if not self.kwics:
            return "Error: no example sentence found, \
                    try a different search term."
        #randomization of KWICs
        #random.seed(9)
        random.shuffle(self.kwics) 
        try:
            # Check if sufficient nr of sents to process  
            self.kwics = self.kwics[:self.params["max_kwics"]]                                     
        except IndexError:
            self.kwics = self.kwics
        
    def load_wordlists(self):
        # Load word lists
        location = os.getcwd() 
        voc_list_folder = location + "/../word_lists/"

        kelly_list = process_csv(voc_list_folder + "kelly_sv.csv")
        svalex_list = process_csv(voc_list_folder + "SVALex_final.csv")
        word_pictures = word_pic.load_word_pics("word_pics.csv", voc_list_folder)
        
        #loaded_weather =  load_list(voc_list_folder + "weather_verbs.txt")
        #weather_verbs = [l[0].decode("utf-8") for l in loaded_weather]

        anaphoric_expr_f = voc_list_folder + "anaphoric_expr.txt"
        anaphoric_expr = load_list(anaphoric_expr_f) 
        demon_pronouns = [l[0].decode("utf-8") for l in anaphoric_expr if l[1] == "PN"]
        anaph_adv = [l[0].decode("utf-8") for l in anaphoric_expr if l[1] == "AB"]

        path_to_list = voc_list_folder + "sensitive_voc.txt"
        sensitive_voc = load_list(path_to_list)

        speaking_verbs =  load_list(voc_list_folder + "speaking_verbs.txt")

        word_lists = {"demon_pronouns":demon_pronouns, #"weather_verbs":weather_verbs
                      "anaph_adv":anaph_adv, "sensitive_voc":sensitive_voc, 
                      "speaking_verbs":speaking_verbs, "kelly_list": kelly_list, 
                      "svalex_list": svalex_list,"word_pictures":word_pictures}
        return word_lists
    
    def get_classifier(self):
        # setting things up for machine learning classification
        pred_type = "classif" #TO DO: move to parameters and handle regression + text level
        if pred_type == "classif":
            classifier = Classifier(jobject=serialization.read("classifiers/cefr_sent.model"))
        else:
            classifier = Classifier(jobject=serialization.read("classifiers/cefr_sent_REGR.model"))
        return classifier
     
    saved_clf = "indepsent_classifier_logreg.pkl" #TO DO: model build with old sklearn version
    #hitex_path = os.getcwd()
    os.chdir("/export/cgi-bin_sb/larkalabb/HitEx/classifiers/")
    with open(saved_clf, 'rb') as fid:
        classifier = cPickle.load(fid)
      
    def check_sentences(self, classifier, word_lists):
        # Process each sentence
        sents = [] 
        candidates = []
        for kwic in self.kwics:
            statistics = SentStatistics(kwic.sentence, self.params).get_stats_SWE(
                                        word_lists["kelly_list"], 
                                        word_lists["svalex_list"], 
                                        word_lists["word_pictures"])
            sent_match = SentMatch(kwic, statistics, self.params, self.criteria)
            if "well_formedness" in self.criteria:
                sent_match.check_wellformedness()
            if "isolability" in self.criteria:
                sent_match.check_isolability(word_lists["demon_pronouns"], 
                                             word_lists["anaph_adv"])
            if "sensitive_voc" in self.criteria:
                sent_match.check_sensitive_voc(word_lists["sensitive_voc"])
            if "readability" in self.criteria:
                sent_match.check_readability(classifier)
            #if "informativity" in self.criteria:
            #    sent_match.check_informativity()
            if "typicality" in self.criteria:
                sent_match.check_typicality()
            if "other_criteria" in self.criteria:
                sent_match.check_other_criteria(word_lists["speaking_verbs"])
            match = sent_match.match
            match_score = ""
            sent = sent_match.sent.words
            # Filtering duplicates
            if sent not in sents:
                sents.append(sent)
                candidates.append((match_score, kwic.corpus, 
                                  sent_match.kwic.match.position,
                                  sent, sent_match.sent_left, 
                                  sent_match.stats["keyword"], 
                                  sent_match.sent_right, 
                                  kwic.sentence.nodes, match))
        return candidates

    def sort_criteria_by_scoring_type(self):
        """ Sorts selection criteria based on scoring type 
        (filters or rankers).
        """
        filters = []
        rankers = []
        for criteria,scoring in self.criteria.items():
            if scoring == "filter":
                filters.append(criteria)
            elif scoring == "ranker":
                rankers.append(criteria)
            elif type(scoring) == dict:
                for subcriteria, subscoring in scoring.items():
                    if subscoring == "filter":
                        filters.append(subcriteria)
                    elif subscoring == "ranker":
                        rankers.append(subcriteria)
        self.sorted_criteria = {"filters":filters, "rankers":rankers}
        return self.sorted_criteria

    def filter_sents(self, candidates):
        # check whether sentence is a good or bad match
        filters = self.sorted_criteria["filters"]
        for item in candidates:
            match_score = item[0] 
            corpus = item[1] 
            position = item[2] 
            sent = item[3] 
            left = item[4] 
            keyword = item[5] 
            right = item[6] 
            tokens = item[7] 
            match = item[8]
            is_bad = [] #use it to sort bad sents, minimize violations
            for param, v in match.items():
                if param in filters:
                    if param not in self.positive_crit:
                        is_bad.append(v[0])
            if is_bad:
                #option to keep bad sents and return in case not enough good ones
                if self.params["preserve_bad"]: 
                    match_score = -len(is_bad)
                    self.bad_results.append((match_score, corpus, position, 
                         sent, left, keyword, right, tokens, match))
            else:
                self.rset.append(item)
        return self.rset

    def rank_bad_sents(self): #change to:sort_set
        """ Sort filtered KWICs minimizing the amount of violations of the 
        selection criteria.
        """
        if self.bad_results:
            self.bad_results = sorted(self.bad_results, key=lambda bad: bad[0], 
                               reverse=True)[:self.params["maxhit"]]
        else:
            print "Error: empty relevance set, try a different search."
        return self.bad_results

    def rank_sents(self, ranking_type="absolute"):
        """Sorts sentences based on the numeric and boolean values per 
        criteria. A per-sentence score is computed by summing up the 
        ranks. This is used to compute the final match score:
        nr criteria * nr non-filtered sents - per-sentence score

        @ ranking_type (str): absolute: maximizing all positive criteria
                                        and minimizing negative ones
                              relative: TO DO, rank based on one criteria 
        """
        rankers = self.sorted_criteria["rankers"]
        result = {}
        if ranking_type == "absolute":
            # sort per criteria
            sorted_sents_per_criteria = {}
            for sent in self.rset:  #empty if all sents bad
                match = sent[-1]
                sent_id = sent[2]
                # add each ranker with 0 value to influence thier rank
                # positively when not displaying undesirable phenomena
                for ranker in rankers:
                    if ranker not in match:
                        if ranker == "readability":
                            match[ranker] = (0.0, self.params["target_cefr"])
                        else:
                            match[ranker] = (0.0, "")
                for k,v in match.items():
                    if k in rankers:
                        score = v[0]    # v = (score, info) per criteria
                        if k in self.positive_crit:
                            score = -score    # to enable the same ascending sorting
                                              # as for other criteria
                        elif type(score) == bool:
                            score = 1.0
                        # keeping only sents with 1 CEFR level difference
                        # exact level first, then easier and then harder sentences
                        if k == "readability" and abs(score) <= 1:
                            if score == -1:
                                score = 1.0
                            elif score == 1:
                                score = 2.0
                            if k in sorted_sents_per_criteria:
                                sorted_sents_per_criteria[k].append((score, sent))
                            else:
                                sorted_sents_per_criteria[k] = [(score, sent)]
                        elif k != "readability" and "readability" in rankers:
                            if (abs(match["readability"][0]) <= 1):
                                #print sent[3], match["readability"][0]
                                if k in sorted_sents_per_criteria:
                                    sorted_sents_per_criteria[k].append((score, sent))
                                else:
                                    sorted_sents_per_criteria[k] = [(score, sent)]
                        else:
                            if k in sorted_sents_per_criteria:
                                sorted_sents_per_criteria[k].append((score, sent))
                            else:
                                sorted_sents_per_criteria[k] = [(score, sent)]

            # sum up rank position per criteria
            for criteria, sents in sorted_sents_per_criteria.items():
                sorted_sents = sorted(sents) #list of tuples (value, sent_info)
                for i,s in enumerate(sorted_sents):
                    sent_id = s[1][2]
                    if sent_id in result:
                        result[sent_id] += i
                    else:
                        result[sent_id] = i
            
            sorted_result = sorted(result.items(), key=operator.itemgetter(1))
            ranked_sents = []
            for s_id,index_sum in sorted_result:
                for sent in self.rset:
                    if s_id == sent[2]:
                        #assign maximum obtainable points (nr criteria * nr good sents) - 
                        #sum of obtained position (index sum) as match score
                        sent_info2 = [info for info in sent[1:]]
                        ranking_match_score = len(rankers)*len(sorted_result)-index_sum
                        sent_info2.insert(0,ranking_match_score)
                        updated_sent = tuple(sent_info2)
                        ranked_sents.append(updated_sent)
        else:
            # TO DO: ranking based on 1 criteria
            ranked_sents = []

        self.rset = ranked_sents

        #return ranked_sents

    def create_set(self):
        word_lists = self.load_wordlists()
        classifier = self.get_classifier()
        candidates = self.check_sentences(classifier, word_lists)
        self.sort_criteria_by_scoring_type()
        filtered_sents = self.filter_sents(candidates)
        nr_sents_requested = self.params["maxhit"]
        if filtered_sents:
            self.rank_sents()
            if len(filtered_sents) < nr_sents_requested:
                # less good sentences than required, complement set with suboptimal ones
                if self.params["preserve_bad"]:
                    nr_missing_items = nr_sents_requested - len(filtered_sents)
                    self.rank_bad_sents()
                    self.rset = self.rset + self.bad_results[:nr_missing_items] #do in sorting func! and note which ones
            else:
                self.rset = self.rset[:nr_sents_requested]
        elif not filtered_sents and self.params["preserve_bad"]:
            print "No sentence satisfied all the criteria, ranking less optimal sentences..."
            self.rank_bad_sents()
            if len(self.bad_results) < nr_sents_requested:
                self.rset = self.bad_results
            else:
                self.rset = self.bad_results[:nr_sents_requested]
        else:
            return "No sentences found that matched the selected \
                    criteria. Try using less strict criteria or retaining \
                    suboptimal sentences."

    def to_json(self): 
        """
        Converts the list of KWICs and the associated match information to a 
        JSON object.
        """
        data = []
        for i,item in enumerate(self.rset):
            table = {}
            table["rank"] = i+1
            table["score"] = item[0]
            table["corpus"] = item[1]
            table["kwic_position"] = item[2]
            table["sent"] = item[3]
            table["sent_left"] = item[4]
            table["keyword"] = item[5]
            table["sent_right"] = item[6]
            table["tokens"] = item[7] 
            table["match_info"] = item[8]   #prev version's 'relevance_dict'
            data.append(table)
        return json.dumps(data, sort_keys=True, indent=4)

    def get_url(self):
        """
        Returns the URL used for the Korp search.
        """
        KORP_SERVER = "demosb.spraakdata.gu.se"
        KORP_SCRIPT = "/cgi-bin/korp/korp.cgi"
        clist = ','.join(self.params["corpus_list"])

        query_params = {'command':'query', 
                        'corpus':clist,
                        'defaultcontext':'1 sentence',
                        'cqp':urllib.pathname2url(self.korp_query.encode("utf-8")), 
                        'show':'ref,word,pos,msd,lemma,dephead,deprel,saldo,lex,suffix',
                        'start':0,
                        'indent':'8',
                        'sort':'random',
                        'random_seed': "", #only when reproducability needed (e.g. eval)
                        'end':2000,
                        'show_struct':'sentence_id'}
        count = 0
        param_str = ""
        for k, v in query_params.iteritems():
            count += 1
            if count == len(query_params.keys()):
                param_str += k + "=" + str(v)
            else:
                param_str += k + "=" + str(v) + "&"

        return KORP_SERVER + KORP_SCRIPT + "?" + param_str

    def print_match_info(self):
        """Prints detailed information about a matching sentence and 
        the match values. 
        """
        print "------ MATCHING CORPUS HITS --------\n"
        for item in self.rset:
            print "{0:^12}{1:^12}{2}".format("SCORE", "CORPUS", "SENT")
            print "{0:^12}{1:^12}{2}".format(item [0], item[1], item[3])
            #col_width = max([len(crit_name) for crit_name in item[-1].keys()]) + 2 #padding
            padding = "¯" * 82
            print padding
            print "{0:<18}{1}{2:<10}{1}{3:40}".format("SCORE", " | ", "VALUE", "DETAILS")
            print padding
            for kk, vv in item[-1].items():
                if kk in self.sorted_criteria["filters"]:
                    kk = kk + " (F)"
                else:
                    kk = kk + " (R)"
                # TO DO: add criteria_to_print arg
                #if type(criteria_to_print) == list:
                    # for cr in criteria_to_print:
                    #     if kk == cr and vv[0]:
                    #         print kk.ljust(col_width), vv.ljust(col_width)
                    #         print "{0:<20}{1:^5.2f}".format(kk, vv) #improve
                #if criteria_to_print == "all":
                if type(vv) == list:
                    #for vvv in vv:
                        #if vv[0] == True:  indicates bad sentences
                        try:
                            print "{0:<18}{1}{2:<10}{1}{3:40}".format(kk, " | ", True, ", ".join([vvv[1] for kkk, vvv in vv]).encode("utf-8"))
                        except IndexError:
                            print vv
                else:
                    if type(vv[0]) == float:
                        print "{0:<18}{1}{2:<10.2f}{1}{3:40}".format(kk, " | ", vv[0], vv[1])
                    else:
                        try:
                            print "{0:<18}{1}{2:<10}{1}{3:40}".format(kk, " | ", vv[0], str(vv[1]).decode("utf-8"))
                        except UnicodeEncodeError: #UnicodeError
                        #    print vv
                            print "{0:<18}{1}{2:<10}{1}{3:40}".format(kk, " | ", vv[0], str(vv[1]))
            print padding

    def __str__(self):
        if self.rset:
            s = "SCORE CORPUS POSITION SENT\n"
            s = "{0:^12}{1:^15}{2:<12}{3}\n".format("SCORE", "CORPUS", "POSITION", "SENT")
            for (score,corpus,kwic_position, sent, sent_left, keyword, sent_right, tokens, rd) in self.rset:
                s += "{0:^12}{1:^15}{2:<12}{3}\n".format(score,corpus,kwic_position, sent)
            return s
        else:
            return "Error: Empty relevance set. Try again with a different set up."

    def __len__(self):
        return len(self.rset)

    def __getitem__(self, i):
        return self.rset[i]

    def save_set_with_info():
        """ TO DO: Save created JSON objects to file.
        """
        pass
