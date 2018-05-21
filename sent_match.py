# -*- coding: utf-8 -*-
from __future__ import division

import codecs, os
#import classify_level - wEKA-based
import well_formedness
import context_independence
from auxiliaries.match_aux import *
import ling_complexity as lc


class SentMatch:
    """
    Computes and stores scores describing how well a KWIC (KeyWord In Context), 
    i.e. a corpus sentence containing a search keyword, satisfies a number of 
    search parameters and criteria. 

    Args:
      kwic (instance):   a Korp (kwic) sentence mapped to a kwic instance. 
      stats (instance):  a SentStatistic instance, result of the
                         SentStatistics.get_stats_SWE() method
      parameters (dict): search parameters passed as a dictionary
      criteria (dict):   list of filters and rankers to use

    Attributes:
      kwic (instance):  see above
      stats (instance): see above
      sent (instance):  a Sentence instance
      params (dict):    see above
      criteria (dict):  see above   
      match (dict):     match value tuples per search parameter
                        The first element is a boolean, True if a  
                        sentence is bad according to a criteria, False 
                        otherwise; the second member provides information.
      match_score (int):overall match score
      sent_left (str):  tokens to the left of the search keyword
                        (keyword specified in params)
      sent_right (str): tokens to the right of the search keyword

    Yields:
      An object with an overall match scores and detailed information for 
      a sentence based on the input parameters and criteria.   
    """
    def __init__(self, kwic, stats, parameters, criteria):
        self.kwic = kwic   #context dependency (CD) experiments
        self.stats = stats
        try: 
            self.sent = kwic.sentence # Sentence instance but .nodes changed 
                                      # to list of 'dict's (JSON serialization fix)
        except:
            self.sent = kwic
        self.params = parameters
        self.criteria = criteria    
        self.match = {}
        self.match_score = 0
        self.sent_left = ""
        self.sent_right = ""

        #print self.sent.words.encode("utf-8")

        #Creating keyword, sentence left and right attributes for exercise item generation
        add_keyword_info(self)
        split_keyword_context(self)

    def check_wellformedness(self):
        # WELL-FORMEDNESS
        if "root" in self.criteria["well_formedness"]:
            well_formedness.has_root(self)
        if "sent_tokenization" in self.criteria["well_formedness"]:
            well_formedness.check_sent_tokenization(self)
        if "non_alpha" in self.criteria["well_formedness"] or \
            "non_lemmatized" in self.criteria["well_formedness"]:
            thresholds = {"non_alpha":self.params["non_alpha_thr"], 
                          "non_lemmatized":self.params["non_lemmatized_thr"]}
            well_formedness.get_bad_lexica_percentage(self, thresholds)
        if "elliptic" in self.criteria["well_formedness"]:
            well_formedness.check_ellipsis(self)
            
        #TO DO: Discard sent if it doesn't satisfy one of the sub-criteria?

    def check_isolability(self, demon_pronouns, anaph_adv):
        # CONTEXT-INDEPENDENCE  
        context_indep = False
        time_adv_antecedent = False
        dialogue_answ = [("MID", "IN", "MID"), ("IN", "MID"), 
                         ("MID", "AB", "MID")] 
        if "roots" in self.stats and "struct_conn" in self.criteria["isolability"]:
            context_indep = context_independence.check_root_POS(self, self.stats["roots"])
        
        if "yn_answer" in self.criteria["isolability"]:
            context_indep = context_independence.is_yn_answer(self, dialogue_answ)
        
        anaphora_types_to_check = [k for k in self.criteria["isolability"] if k[:5] == "anaph"]
        if anaphora_types_to_check:
            for j,tok in enumerate(self.stats["tokens"]):
                context_indep = context_independence.check_anaphora(tok, j, self, 
                            time_adv_antecedent, demon_pronouns, 
                            anaph_adv, anaphora_types_to_check)
            if "anaphora-PN" in self.criteria["isolability"]:
                if "anaphora-PN" in self.match:
                    unresolved_pn = [word for (bool_val, word) in self.match["anaphora-PN"]]
                else:
                    unresolved_pn = []
                if "resolved?_anaphora-PN" in self.stats:
                    pn_with_ant_candidate = [word for bool_val, word 
                        in self.stats["resolved?_anaphora-PN"]]
                    adjusted_value = (len(unresolved_pn) - 
                                     (len(pn_with_ant_candidate) * 0.5))
                    self.match["anaphora-PN"] = (adjusted_value, 
                        "unresolved PNs: %s; PNs with antecedent candidates: \
                         %s" % (", ".join(unresolved_pn).encode("utf-8"),
                          ", ".join(pn_with_ant_candidate).encode("utf-8")))
                elif unresolved_pn:
                    self.match["anaphora-PN"] = (len(unresolved_pn), 
                                                 "unresolved PNs: %s" %
                             ", ".join(unresolved_pn).encode("utf-8"))
            if "anaphora-AB" in self.criteria["isolability"]:
                if "anaphora-AB" in self.match:
                    try:
                        self.match["anaphora-AB"] = \
                        (len(self.match["anaphora-AB"]), 
                         ", ".join([m for (b,m) in 
                         self.match["anaphora-AB"]]).encode("utf-8"))
                    except TypeError:
                        print self.match["anaphora-AB"].encode("utf-8")
            #TO DO: Discard sent if it doesn't satisfy one of the sub-criteria?
    
    def check_sensitive_voc(self, sensitive_voc):
        # Sensitive vocabulary (partial PARSNIPS)
        # PARSNIP = Politics Alcohol Religion Sex Narcotics 
        # Isms (e.g. communism or atheism) Pork
        if "sensitive_voc" in self.criteria:
            categories_to_filter = self.params["sensitive_voc_cats"] 
            
            #select the relevant subset of sensitive words
            voc_to_filter = []
            for l2 in sensitive_voc:
                if categories_to_filter == ["all"]:
                    voc_to_filter.append(l2[0].decode("utf-8"))
                else:
                    cat = l2[2].split(",")
                    for c in cat:
                        if c.strip(" ").strip("\n") in categories_to_filter: 
                            voc_to_filter.append(l2[0].decode("utf-8"))
            #check if any token matches any item in the sublist
            sens_voc_in_sent = []
            for tkn in self.sent:
                if tkn["lemma"]:
                    sensitive_w = []
                    for lm in tkn["lemma"]:
                        if lm in voc_to_filter or tkn["word"].lower() in voc_to_filter:
                            sensitive_w.append(True)
                        else:
                            sensitive_w.append(False)
                    # TO DO: incorporate Google's list? or another Swedish list?
                    # TO DO: sense-based version
                    if sum(sensitive_w):
                        sens_voc_in_sent.append(tkn["word"])
                elif tkn["word"].lower() in voc_to_filter:
                    sens_voc_in_sent.append(tkn["word"])
            if sens_voc_in_sent:
                put_feature_value(self.match, "sensitive_voc", 
                                  (len(sens_voc_in_sent), 
                                   ", ".join(sens_voc_in_sent).encode("utf-8")))

    def check_readability(self, classifier, instance):
        # READABLE - machine learning based, CICLING 2015 feaatures
        cefr_scale = {"A1":1, "A2":2, "B1":3, "B2":4, "C1":5, "C2":6}
        pred_cefr = lc.classify(classifier, instance)
        target_cefr = self.params["target_cefr"]
        if pred_cefr != target_cefr:
            level_diff = cefr_scale[pred_cefr]-cefr_scale[target_cefr]
            #level_diff > 0 = difficult sentences
        else:
            level_diff = 0
        if self.criteria["readability"] == "filter" and level_diff:
            put_feature_value(self.match, "readability", (level_diff, pred_cefr))
        elif self.criteria["readability"] == "ranker":
            put_feature_value(self.match, "readability", (level_diff, pred_cefr))

    #def check_informativity(self):
        # INFORMATIVE
        # if "lex_to_func" in self.criteria["informative"]:
        #     # Ratio of lexical tokens to non-lexical tokens
        #     nb_lexical_words = 0
        #     nb_func_words = 0
        #     for pos in self.stats["pos_unigr"]:
        #         #duplicate from sent_features:
        #         if pos in ["NN", "JJ","VB", "AB"]: #keep adverbs?
        #             nb_lexical_words += 1
        #         elif pos not in ["PM", "UO","MAD", "MID"]:# prop names, foreign words, punctuation not counted as func. words
        #             nb_func_words += 1

        #     if nb_func_words:
        #         lex_func_ratio = (nb_lexical_words / nb_func_words)
        #         diff_lex_func = -(lex_func_ratio - self.params["lex_to_func_thr"])
        #     else:
        #         diff_lex_func = nb_lexical_words    #if no func words
        #     self.match["lex_to_func"] = (diff_lex_func, lex_func_ratio)
        #     # diff_lex_func stands for the extent of the satisfaction of the criteria
        #     # below threshold (bad ratios) will result in negative values

    def check_typicality(self):
        # TYPICAL - based on Mutual Information value from Korp word pictures
        #mi_info = [str(el[0]) + ": " + str(el[1]) for el in 
        #           zip(self.stats["used_rel_lemmas"], 
        #               self.stats["MI"]) if el[1]]
        mi_info = "summed Lexicographers' Mutual Information score"
        self.match["typicality"] = (sum(self.stats["MI"]), mi_info)
        # TO DO: improve mi_info (add pair, not only single lemmas)

    # TO DO: valency (use verb_args from stats)

    def check_other_criteria(self, speaking_verbs_list):
        # EXTRA
        if "length" in self.criteria["other_criteria"]:   
            # Is the length of the sentence out of the desired length range?
            sent_len = int(self.sent.length)
            min_len = self.params["min_len"]
            max_len = self.params["max_len"]
            out_of_len = out_of_length_range(self.sent.length, min_len,
                                             max_len)
            if out_of_len:
                if sent_len < min_len:
                    diff = min_len - sent_len
                else:
                    diff = sent_len - max_len
                info = "%d tokens long" % self.sent.length
                self.match["length"] = (diff, info)
        
        # Is there keyword repetition?
        if "repkw" in self.criteria["other_criteria"]:
            if "keyword_count" in self.stats:
                kw_rep = self.stats["keyword_count"] - 1
                if kw_rep:
                    self.match["repkw"] = (kw_rep, "%d repetition(s)" % kw_rep)

        # Is the keyword's position out of the defined distance range from the chosen 
        #target sentence edge (start or end)?
        if "kw_position" in self.criteria["other_criteria"]:
            kw_in_pos = is_keyword_within_position(self.sent, #self.kwic
                        self.params["target_edge"], 
                        self.params["proportion"])
            if not kw_in_pos:
                self.match["kw_position"] = (not kw_in_pos, """search term not 
                    within %d\% of sentence %s""" % (self.params["proportion"], 
                    self.params["target_edge"]))

        # Is the sentence interrogative?
        if "interrogative" in self.criteria["other_criteria"]:
            if self.sent[-1]["word"] == "?":
                put_feature_value(self.stats, "interrogative", True)
                self.match["interrogative"] = (True, "")

        # Check for direct speech
        if "direct_speech" in self.criteria["other_criteria"]:
            speaking_verbs = [l[0].decode("utf-8") for l in speaking_verbs_list]
            direct_speech_patterns = [("MID", "VB", "PN"), ("MID", "VB", "PM"), 
                                      ("PAD", "VB", "PN"), ("PAD", "VB", "PM")]
            #TO DO: handle auxiliaries and modal verbs
            token_objs = self.stats["tokens"] # list of original Token instances 
                                              # from Sentence.nodes
            try:
                speaking = []
                for t in token_objs:
                    if t.lemma:
                        if t.lemma[0] in speaking_verbs:
                            speaking.append(t)
                if speaking:
                    for vb in speaking:
                        verb_idx = int(vb.ref)-1
                        try:
                            ds_candidate = (token_objs[verb_idx-1].pos,token_objs[verb_idx].pos, token_objs[verb_idx+1].pos)
                            if ds_candidate in direct_speech_patterns:
                                put_feature_value(self.match, "direct_speech", (True, ds_candidate))
                        except IndexError:
                            pass
            except IndexError:
                pass

        #Is the sentence negatively formulated?
        if "neg_form" in self.criteria["other_criteria"]:
            if "neg_form" in self.stats:
                neg_form = self.stats["neg_form"]
                if neg_form:
                    self.match["neg_form"] = (len(neg_form), ", ".join(neg_form).encode("utf-8"))

        #Are there modal verbs in the sentence?
        if "modal_verb" in self.criteria["other_criteria"]:
            if "modal_verb" in self.stats:
                mv = self.stats["modal_verb"]
                self.match["modal_verb"] = (len(mv), ", ".join(mv).encode("utf-8"))
        
        #Are there participles?
        if "participle" in self.criteria["other_criteria"]:
            pc = [t["word"] for t in self.sent if t["pos"] == "PC"]
            if pc:
                self.match["participle"] = (len(pc), ", ".join(pc).encode("utf-8"))

        #Are there s-verbs?
        if "sverb" in self.criteria["other_criteria"]:
            if "sverb" in self.stats:
                sverb = self.stats["sverb"]
                if sverb:
                    self.match["sverb"] = (len(sverb), ", ".join(sverb).encode("utf-8"))

        #Are there proper_names?
        if "proper_name" in self.criteria["other_criteria"]:
            if "proper_name" in self.stats:
                prop_name = self.stats["proper_name"]
                if prop_name: 
                    self.match["proper_name"] = (len(prop_name), ", ".join(prop_name).encode("utf-8"))

        #Are there abbreviations? (change to True/False in the fun above?)
        if "abbrev" in self.criteria["other_criteria"]:
            if "abbrev" in self.stats:
                abbrev = self.stats["abbrev"]
                if abbrev:
                    self.match["abbrev"] = (len(abbrev), ", ".join(abbrev).encode("utf-8"))

        # Information from Kelly
        if "diff_voc_kelly" in self.criteria["other_criteria"]:
            #Is the % of words above the target CEFR level 
            #above the chosen limit?
            if "diff_voc" in self.stats:
                nr_diff_voc = len(self.stats["diff_voc"])
                #TO DO: do as below for all criteria
                if self.criteria["other_criteria"]["diff_voc_kelly"] == "filter":
                    diff_voc_perc = (nr_diff_voc / self.sent.length) * 100
                    diff_voc = diff_voc_perc > self.params["voc_thr"]
                    if diff_voc:
                        self.match["diff_voc_kelly"] = (diff_voc, ", ".join(self.stats["diff_voc"]).encode("utf-8"))
                else:
                    self.match["diff_voc_kelly"] = (nr_diff_voc, ", ".join(self.stats["diff_voc"]).encode("utf-8"))

            #How many words are above the word frequency threshold?
            # try:
            #     kelly_fr = [float(fr < self.params["kelly_freq_thr"]) for 
            #             fr in self.stats["voc_freq_kelly"]]
            # except KeyError: #when no lexical tokens in sent
            #     kelly_fr = [0]
            # self.match["kelly_freq"] = (kelly_fr, "%d token(s)" % 
            #                             float(sum(kelly_fr)))

        # Information from SVALex - only lexical tokens checked
        if "svalex_fr" in self.criteria["other_criteria"]:
            # frequency WITHIN the target CEFR level (not AT level)
            avg_freq_thr = {"A1":50, "A2":55, "B1":54, "B2":55, "C1":58}
            if "svalex_fr" in self.stats:
                if self.criteria["other_criteria"]["svalex_fr"] == "filter":
                    avg_svalex_freq = avg_freq_thr[self.params["target_cefr"]] > \
                      (sum(self.stats["svalex_fr"]) / len(self.stats["svalex_fr"]))
                else:
                    avg_svalex_freq = sum(self.stats["svalex_fr"]) / \
                                          len(self.stats["svalex_fr"])
                if avg_svalex_freq:
                    #info = ", ".join([str(fr) for fr in self.stats["svalex_fr"]])
                    info = "average frequency (SVALex)"
                    self.match["svalex_fr"] = (avg_svalex_freq, info) 
        if "out_of_svalex" in self.criteria["other_criteria"]:
            # Is word in SVALex (at any level)?
            if "out_of_svalex" in self.stats:
                out_of_svalex = len(self.stats["out_of_svalex"])
                if out_of_svalex: #assume when ranking that if no key = 0
                    self.match["out_of_svalex"] = (out_of_svalex, 
                        ", ".join(self.stats["out_of_svalex"]).encode("utf-8"))

    
    #def __str__(self):
    #    return "Corpus: %s\nSent ID: %s\nSentence: %s\n" % (self.kwic.corpus, self.kwic.position, self.sent)
        #to do: visualize detailed match values