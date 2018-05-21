# -*- coding: utf-8 -*-

import os
cwd = os.getcwd()
if cwd == '/export/cgi-bin_sb/larkalabb':
    activate_this = os.path.join(cwd, 'venv/bin/activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))

import json
import operator
import random
import urllib
import numpy
import cPickle
import time
import word_pic
import ling_complexity as lc
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
      korp_time            time taken to retrieve sentences from Korp

    Yields:
      A list of KWICs transformable into a list of SentMatch instances. 
    """
    def __init__(self, parameters, criteria):
        # Construct query
        parameters["query_w"] = parameters["query_w"].decode("utf-8")
        if parameters["query_type"] == "lemma":
            if parameters.get("query_pos"):
                korp_query = (u'[(lemma contains "%s") & (pos = "%s")]' % 
                              (parameters["query_w"], 
                               parameters["query_pos"]))
            else:
                korp_query = (u'[lemma contains "%s"]' % 
                              parameters["query_w"])
        elif parameters["query_type"] == "wordform":
            if parameters.get("query_pos"):
                korp_query = (u'[word = "%s" & (pos = "%s")]' % 
                              (parameters["query_w"], 
                               parameters["query_pos"]))
            else:
                korp_query = u'[word = "%s"]' % parameters["query_w"]
        elif parameters["query_type"] == "cqp":
            korp_query = parameters["query_w"]
        else:   # fix for a front-end bug
            parameters["query_type"] = "cqp"
            korp_query = parameters["query_w"]

        # Initializing attributes
        self.korp_query = korp_query
        self.params = parameters
        self.criteria = criteria
        self.positive_crit = ["MI", "typicality"] #"svalex_fr"
        self.rset = []
        self.bad_results = []
        self.kwics = []
        self.korp_time = ""
        
        # Getting and randomizing KWICs
        end = 2000 
        seed = parameters.get("random_seed", "")
        
        if len(self.params["corpus_list"]) > 4:
            if seed:
                random.seed(seed)

            # Randomization for corpus selection
            random.shuffle(self.params["corpus_list"])  
            corpora = self.params["corpus_list"][:4] 
        else:
            corpora = self.params["corpus_list"]
        search = korp_search(corpora, korp_query, 0, end, seed)
        self.korp_time = str(round(float(search.time), 2))
        #print search.corpus_hits
        self.kwics = search.kwics # If no Korp results, it equals to []

        # Randomization of KWICs
        if seed:
            random.seed(seed)
        random.shuffle(self.kwics) 
        
        # Check if sufficient nr of sents to process
        try:     
            self.kwics = self.kwics[:self.params["max_kwics"]]                                     
        except IndexError:
            self.kwics = self.kwics
        
    def load_wordlists(self):
        # Load word lists
        if "HitEx" in cwd:
            voc_list_folder = cwd + "/word_lists/"
        elif "2017" in cwd:
            voc_list_folder = "/Library/WebServer/CGI-Executables/trunk/HitEx/word_lists/"
        else:
            voc_list_folder = cwd + "/HitEx/word_lists/"

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

        wordlists = {"demon_pronouns":demon_pronouns, #"weather_verbs":weather_verbs
                      "anaph_adv":anaph_adv, "sensitive_voc":sensitive_voc, 
                      "speaking_verbs":speaking_verbs, "kelly_list": kelly_list, 
                      "svalex_list": svalex_list,"word_pictures":word_pictures}
        return wordlists
 
    def get_classifier(self):
        # Loading classifier #TO DO: update models (eval data)
        #saved_clf = "indepsent_classifier_logreg.pkl" 
        saved_clf = "sent_sup_eval2015.pkl"
        if "HitEx" in cwd:
            classifier_folder = "classifiers/"
        else:
            classifier_folder = "HitEx/classifiers/"
        with open(classifier_folder + saved_clf, 'rb') as fid:
            classifier = cPickle.load(fid)
        return classifier
      
    def check_sentences(self, wordlists):
        # Process and controll sentences
        sents = [] 
        candidates = []
        if "readability" in self.criteria:
            CEFR_ML = True
        else: 
            CEFR_ML = False
        text = "" # no raw text to annotate since Korp sentences used
        try:
            ref_level = lc.set_ref_level(self.params["target_cefr"])        
        except KeyError:
            ref_level = "B1" #TO DO: change to "" once model without this info added
            self.params["target_cefr"] = "B1"
        produced_by = "expert"
        analysis_level = "indep_sent"
        ws_type = "hitex" 
        collected_items = [kwic.sentence for kwic in self.kwics]
        # Transforming Sentence instances into a Dataset instance with extracted 
        # statistics (feature_values only extracted if CEFR_ML)
        dset_inst, feature_values = lc.analyze_lg_complexity(text, ref_level, 
            produced_by, analysis_level, CEFR_ML, ws_type, collected_items, self.params, wordlists)
        for i,kwic in enumerate(self.kwics):
            statistics = dset_inst.stats_objects[i]
            sent_match = SentMatch(kwic, statistics, self.params, self.criteria)
            if "well_formedness" in self.criteria:
                sent_match.check_wellformedness()
            if "isolability" in self.criteria:
                sent_match.check_isolability(wordlists["demon_pronouns"], 
                                             wordlists["anaph_adv"])
            if "sensitive_voc" in self.criteria:
                sent_match.check_sensitive_voc(wordlists["sensitive_voc"])
            if "readability" in self.criteria:
                classifier = self.get_classifier()
                sent_match.check_readability(classifier, feature_values[i]) #CHECK i
            #if "informativity" in self.criteria:
            #    sent_match.check_informativity()
            if "typicality" in self.criteria:
                sent_match.check_typicality()
            if "other_criteria" in self.criteria:
                sent_match.check_other_criteria(wordlists["speaking_verbs"])
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
        # check whether the sentence is a good or bad match
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
            is_bad = [] # TO DO: Use it to sort bad sents, minimize violations
            for param, v in match.items():
                if param in filters:
                    if param not in self.positive_crit:
                        is_bad.append(v[0])
            if is_bad:
                # Option to keep bad sents and return in case not enough good ones
                if self.params["preserve_bad"]: 
                    match_score = -len(is_bad)
                    self.bad_results.append((match_score, corpus, position, 
                         sent, left, keyword, right, tokens, match))
            else:
                self.rset.append(item)
        return self.rset

    def rank_bad_sents(self): #TO DO: change to:sort_set
        """ Sort filtered KWICs minimizing the amount of violations of the 
        selection criteria.
        """
        if self.bad_results:
            self.bad_results = sorted(self.bad_results, key=lambda bad: bad[0], 
                               reverse=True)[:self.params["maxhit"]]
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
            # Sort per criteria
            sorted_sents_per_criteria = {}
            for sent in self.rset:  #empty if all sents bad
                match = sent[-1]
                sent_id = sent[2]
                # Add each ranker with 0 value to influence their rank
                # positively when not displaying undesirable phenomena
                for ranker in rankers:
                    if ranker not in match:
                        match[ranker] = (0.0, "no violations")
                for k,v in match.items():
                    if k in rankers:
                        score = v[0]    # v = (score, info) per criteria
                        if k in self.positive_crit:
                            score = -score    # To enable the same ascending sorting
                                              # as for other criteria
                        elif type(score) == bool:
                            score = 1.0
                        # Keeping only sents with 1 CEFR level difference
                        # Exact level match first, then easier and then harder sentences
                        if k == "readability" and abs(score) <= 1:
                            if score == -1:
                                score = 1.0
                            elif score == 1:
                                score = 2.0 # more difficult sentences ranked lower
                            if k in sorted_sents_per_criteria:
                                sorted_sents_per_criteria[k].append((score, sent))
                            else:
                                sorted_sents_per_criteria[k] = [(score, sent)]
                        elif k != "readability" and "readability" in rankers: #TO DO: necessary?
                            if (abs(match["readability"][0]) <= 1):
                                #print sent[3], match["readability"][0]
                                if k in sorted_sents_per_criteria:
                                    sorted_sents_per_criteria[k].append((score, sent))
                                else:
                                    sorted_sents_per_criteria[k] = [(score, sent)]
                        elif k == "readability" and abs(score) > 1:
                            pass
                        else:
                            if k in sorted_sents_per_criteria:
                                sorted_sents_per_criteria[k].append((score, sent))
                            else:
                                sorted_sents_per_criteria[k] = [(score, sent)]

            # Sum up rank position per criteria
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
                        # Assign maximum obtainable points (nr criteria * nr good sents) - 
                        # sum of obtained position (index sum) as match score
                        sent_info2 = [info for info in sent[1:]]
                        ranking_match_score = len(rankers)*len(sorted_result)-index_sum
                        sent_info2.insert(0,ranking_match_score)
                        updated_sent = tuple(sent_info2)
                        ranked_sents.append(updated_sent)
        else:
            ranked_sents = self.rset
        self.rset = ranked_sents

    def create_set(self):
        wordlists = self.load_wordlists()
        candidates = self.check_sentences(wordlists)
        if not candidates:
            self.rset = {"Error": "No sentence containing the searched term was found."}
        else:
            self.sort_criteria_by_scoring_type()
            good_sents = self.filter_sents(candidates)
            nr_sents_requested = self.params["maxhit"]
            if good_sents:
                if self.sorted_criteria["rankers"]:
                    self.rank_sents()
                if len(good_sents) < nr_sents_requested:
                    # less good sentences than required, complement set with suboptimal ones
                    if self.params.get("preserve_bad") in ["true", True, 1, "1"]:
                        nr_missing_items = nr_sents_requested - len(good_sents)
                        self.rank_bad_sents()
                        self.rset = self.rset + self.bad_results[:nr_missing_items] #TO DO: do in sorting func! and note which ones
                else:
                    self.rset = self.rset[:nr_sents_requested]
            elif not good_sents and self.params.get("preserve_bad") in ["true", True, 1, "1"]:
                #print "No sentence satisfied all the criteria, ranking less optimal sentences..."
                self.rank_bad_sents()
                if len(self.bad_results) < nr_sents_requested:
                    self.rset = self.bad_results
                else:
                    self.rset = self.bad_results[:nr_sents_requested]
            else:
                self.rset = {"Error": "No sentence matched the indicated criteria.\
                Try using less strict criteria or retaining suboptimal sentences."}
        return self.rset

    def to_obj(self): 
        """
        Converts the list of KWICs and the associated match information to a 
        JSON object.
        TO DO: do it earlier instead of creating a tuple.
        """
        data = []
        if "Error" not in self.rset:
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
                table["match_info"] = item[8]
                table["time"] = {"korp_time":self.korp_time}
                data.append(table)
        else:
            data = self.rset
        return data

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
                if type(vv) == list:
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
            return "Error: No matching sentences found. Try again with a different set up."

    def __len__(self):
        return len(self.rset)

    def __getitem__(self, i):
        return self.rset[i]

    def save_set_with_info():
        """ TO DO: Save created JSON objects to file.
        """
        pass
