# -*- coding: utf-8 -*-

import math as m
from auxiliaries.dset_proc_aux import *
from kelly import get_kelly_info, get_svalex_info, get_svalex2_info, cefr_scale
from word_pic import get_mutual_info
from auxiliaries.dset_prep_aux import clean_value
from auxiliaries.match_aux import add_keyword_info


class SentStatistics():
    """
    Collects statistical information about a Sentence instance 
    (see 'ling_unit.py'). Links to tag sets referred to in: 
    - morpho-syntactic: http://spraakbanken.gu.se/korp/markup/msdtags.html
    - dependency relations: http://stp.lingfil.uu.se/~nivre/swedish_treebank/dep.html

    Args:
      sent (instance): a Sentence instance
      kelly_list (list): the loaded Kelly word list (see kelly.py)
      parameters (dict): sentence search parameters passed as a dictionary

    Attributes:
      sent: see above
      stats: the object that will be filled with the statistical information
      modal_verb_list: a list of verbs usable as modal (auxiliary) verbs
      kelly_list: see above
      params: see 'parameters' above

    Yields:
      A container for statistical information for a sentence.
    """
    def __init__(self, sent, parameters={}):

        self.sent = sent
        self.stats = {"voc_cefr": {"A1":0, "A2":0, "B1":0, "B2":0, 
                                   "C1":0, "C2":0, "?":0, "-":0},
                      "voc_cefr_svalex2": {"A1":0, "A2":0, "B1":0, "B2":0, 
                                   "C1":0, "?":0, "-":0}}
        self.modal_verb_list = [u"kunna", u"måste", u"skola", u"vilja", u"böra", u"få"]
        self.params = parameters
        self.sent.level = "B1"  # for a fixed level

    def get_len_stats(self,t):
        """
        Collects lenght-based statisctics. 

        Arg: 
          t: a Token instance
        """
        #Long words
        if len(t.word) > 6:
            put_feature_value(self.stats, "long_w", 1)

        #Extra-long words
        if len(t.word) > 13:
            put_feature_value(self.stats, "xlong_w", 1)
 
        #Total length of characters per token
        put_feature_value_list(self.stats, "tok_len", len(t.word))

        return self.stats

    def get_kelly_stats(self,t,kelly_list):
        """
        Collects information from the Kelly word list including:
        the CEFR level for all categories and frequency only for 
        lexical categories (nouns, verbs, adjectives, adverbs).
        The information is added to the 'stats' attribute.

        Arg: 
          t: a Token instance
        """
        if self.params: #for sent_match
            v = get_kelly_info(kelly_list, t, self.params.get("target_cefr",""))
        else:
            v = get_kelly_info(kelly_list, t, self.sent.level)
        #except AttributeError:
        #    v = get_kelly_info(self.kelly_list, t, self.text_level)
        cefr = v[1]
        self.stats["voc_cefr"][cefr] += 1.0
        if t.pos in ["NN", "VB"] and (v[0] == "above"):
            put_feature_value(self.stats, "diff_NNVB", 1.0)
        if t.pos in ["NN", "JJ","VB", "AB"]:
            freq_kelly = v[2]
            if freq_kelly:
                log_freq_kelly = m.log(freq_kelly) #following Coh-metrix
            else:
                log_freq_kelly = 0.0
            put_feature_value_list(self.stats, "voc_freq_kelly", log_freq_kelly)
        #token of a suitable CEFR level according to Kelly?
        if v[0] == "above":      #or v == "not in kelly" or v == "no lemma"?
           put_feature_value_list(self.stats,"diff_voc", t.word)
        return self.stats

    def get_svalex_stats(self,t, svalex_list):
        """
        Collects frequency information from the SVALex or SweLLex lists.

        Arg: 
          t:           a Token instance
          svalex_list: a pickled version of the SVALex or SweLLex list
        """
        if t.pos in ["NN", "VB", "JJ", "AB"]:
            svalex_info = get_svalex_info(svalex_list, t, self.params.get("target_cefr","any"))
            svalex_fr,out_of_svalex = svalex_info[0], svalex_info[1]
            put_feature_value_list(self.stats,"svalex_fr", svalex_fr)
            if out_of_svalex:
                put_feature_value_list(self.stats,"out_of_svalex", t.word)
        return self.stats

    def get_svalex2_stats(self, t, svalex2_list):
        """
        Collects information from the version of the SVALex or SweLLex lists where
        frequency distributions were mapped to CEFR levels.

        Args: 
          t:            a Token instance
          svalex2_list: a pickled version of the SVALex or SweLLex list mapped to CEFR levels 
        """
        if self.params:
            diff_info, level = get_svalex2_info(t, svalex2_list, self.params.get("target_cefr","B1"))
        else:
            diff_info, level = get_svalex2_info(t, svalex2_list, self.sent.level)
        self.stats["voc_cefr_svalex2"][level] += 1.0
        if t.pos in ["NN", "VB"] and (diff_info == "above"):
            put_feature_value(self.stats, "diff_NNVB_svalex2", 1.0)
        if diff_info == "above": 
           put_feature_value_list(self.stats,"diff_voc_svalex2", t.word)
        return self.stats

    def get_morpho_synt_stats(self,s,t,i):
        """
        Gathers information based on part-of-speech and morpho-syntactic tags.

        Args:
          s: an instance of the Sentence class
          t: an instance of the Token class
          i: current index of token in the sentence 
        """ 
        put_feature_value_list(self.stats,"pos_unigr", t.pos)

        #Verbs
        
        if t.pos == "VB":

            if not self.stats["finite"]:
                if ("INF" not in t.msd) and ("SUP" not in t.msd) and ("PRF" not in t.msd):
                    # only modal verb as finite verb without VG not allowed
                    if t.lemma: 
                        if t.lemma[0] in self.modal_verb_list: #få, ska sometimes non-modal use
                            try:
                                ch_deprel = [tt.deprel for tt in self.stats["heads"][t.ref]]
                                if "VG" in ch_deprel:
                                    put_feature_value_list(self.stats, "finite", 1.0)
                            except KeyError:
                                pass
                        else:
                            put_feature_value_list(self.stats, "finite", 1.0)
                    else:
                        put_feature_value_list(self.stats, "finite", 1.0)


            if t.deprel not in ["VG", "SP"]: #SP e.g. är öppen
                put_feature_value(self.stats, "main_verb", 1.0)
            if t.lemma:
                # check next word if verb (also non-modal use of those verbs) 
                if t.lemma[0] in self.modal_verb_list:
                    try:
                        if s.nodes[i+1].deprel == "VG":
                            put_feature_value_list(self.stats, "modal_verb", t.word)
                    except IndexError:  
                        for w in s.nodes[i:]:
                            if (w.pos == "VB" and w.deprel == "VG" 
                                and w.depheadid == t.ref):
                                put_feature_value_list(self.stats, "modal_verb", t.word)
        
                if "SFO" in t.msd:
                    if t.lemma[0][-1] == "s": # e.g. finns
                        put_feature_value_list(self.stats, "sverb", t.word)
                    else:
                        put_feature_value(self.stats, "passive", 1.0)
                if t.msd[:6] == "PC.PRF":
                    put_feature_value(self.stats, "perf_pc", 1.0)
                if t.msd[:6] == "PC.PRS":
                    put_feature_value(self.stats, "pres_pc", 1.0)
                if "PRT" in t.msd:
                    put_feature_value(self.stats, "past_VB", 1.0)
                elif "PRS" in t.msd:
                    put_feature_value(self.stats, "pres_VB", 1.0)
                elif "SUP" in t.msd:
                    put_feature_value(self.stats, "sup_VB", 1.0)
                if "IMP" in t.msd:
                    put_feature_value(self.stats, "imp_VB", 1.0)
                if "KON" in t.msd:
                    put_feature_value(self.stats, "konj_VB", 1.0)


        if t.word in ["han", "hon", "det", "den"]:
            put_feature_value(self.stats, "PN_3SG", 1.0)

        if t.pos == "NN" and ("NEU" in t.msd):
            put_feature_value(self.stats, "neu_NN", 1.0)

        # Relative strucutres (pronouns etc.)
        if t.pos in ["HA", "HD", "HP", "HS"]:
            if s.nodes[-1].word != "?": # to exclude interrogative use of those 
                                        # (but indirect questions not handled...)
                put_feature_value(self.stats, "rel_str", 1.0)

        return self.stats

    def deprel_stats(self,t,root_ref, verb_args):
        """
        Collects syntactic information based on the lenght and the direction 
        of dependencies.

        Args:
          t: a Token instance
          root_ref: position (index) of ROOT element in the sentence
        """

        put_feature_value_list(self.stats,"deprel_unigr", t.deprel)

        if t.pos == "VB":
            verb_args[t.ref] = []   
        
        if t.depheadid == None or t.depheadid == '':
            put_feature_value_list(self.stats, "dep_len", 0.0)
        else:
            dep_len = int(t.ref)-int(t.depheadid)
            put_feature_value_list(self.stats, "dep_len", abs(dep_len))
            if dep_len < 0:
                put_feature_value(self.stats, "left_arc", 1.0)
            if dep_len > 0:
                put_feature_value(self.stats, "right_arc", 1.0)
            #Collecting verbal arguments (all - restrict to pronouns and nouns?)
            if t.depheadid in verb_args:
                verb_args[t.depheadid].append(t)
        
        self.stats["verb_args"] = verb_args

        if root_ref:
            if t.depheadid == root_ref:
                root_dep_len = int(root_ref)-int(t.ref)
                put_feature_value_list(self.stats, 
                    "root_dep_len", abs(root_dep_len))

        return self.stats

    def get_semantic_stats(self,t):
        """
        Gets semantic information, based only on number of senses
        for now, since no word-sense disambiguation is used.

        Arg: 
          t: a Token instance
        """
        # nr of senses per word and noun
        put_feature_value_list(self.stats, "senses/w", len(t.saldo))
        if t.pos == "NN":
            put_feature_value_list(self.stats, "nn_senses/nn", len(t.saldo))
        return self.stats 

    def get_sentmatch_stats(self, t, all_tokens, word_pictures):
        if t.word == self.params["query_w"]:                 # note: only suitable for wordform search
            put_feature_value(self.stats, "keyword_count", 1.0)
        if not t.word.isalpha():
            put_feature_value_list(self.stats, "non_alpha", t.word)
        elif t.word.isalpha() and not t.lemma:
            put_feature_value_list(self.stats, "non_lemmatized", t.word)
        if t.deprel in ["ES", "FS", "SS", "FP", "SP", "VS"]: # logical, dummy, other subjects + compl.s
            self.stats["has_subject"] = True
        if t.deprel == "NA":                                 # negation adverbials
            put_feature_value_list(self.stats, "neg_form", t.word)
        if "AN" in t.msd:
            put_feature_value_list(self.stats,"abbrev",t.word)
        if "PM" in t.msd:
            put_feature_value_list(self.stats,"proper_name",t.word)
        if t.deprel ==  "ROOT":
            put_feature_value_list(self.stats, "roots", t)
        #add_keyword_info(t, self.stats, self.params)
        mi,used_rel_lemma = get_mutual_info(t, all_tokens, self.stats, word_pictures)
        put_feature_value_list(self.stats,"used_rel_lemmas",used_rel_lemma)
        put_feature_value_list(self.stats,"MI",mi)
        return self.stats

    def get_stats_SWE(self, kelly_list, svalex_list, svalex2_list, word_pictures={}, use_deprel=True,use_ngrams=False):
        """
        Gathers statistical information from different linguistic levels
        for a sentence based on information specific to the Korp pipeline 
        tags for Swedish (as of June 2015) and the Swedish Kelly wordlist.

        Arg:
          kelly_list:   Kelly word list
          svalex_list:  only normalized frequencies
          svalex2_list: n. frequencies mapped to CEFR levels
          use_deprel:   whether to use dependency relation tags
          use_ngrams:   whether to collect ngrams (uni- and bigrams),
                        see 'get_ngrams()' in 'feat_aux.py' 
        """
        s = self.sent
        root_ref = check_root(s)

        tokens = []

        verb_args = {} #{"verb1": {arg1_pos:"PN", arg1_deprel:"SS", etc.},..}
        self.stats["finite"] = []
        self.stats["heads"] = {}
        self.stats["keyword"] = {}
        self.stats["has_subject"] = 0
        self.stats["used_rel_lemmas"] = [] 

        # Collect the position ('ref') of the dependency head of each token
        # +1 compared to regular indexes, string type
        for tkn in s.nodes:
            if tkn.deprel == "ROOT":
                put_feature_value_list(self.stats["heads"], tkn.ref, tkn) #"ROOT"
            else:
                put_feature_value_list(self.stats["heads"], tkn.depheadid, tkn)

        for i,t in enumerate(s.nodes):

            mapped_token = map_Token_to_dict(t)  #just a fix, see dset_proc_aux.py
            tokens.append(mapped_token)

            #get statistics from different liguistic levels
            self.stats = self.get_len_stats(t)
            self.stats = self.get_kelly_stats(t, kelly_list)
            if svalex_list:
                self.stats = self.get_svalex_stats(t, svalex_list)
            if svalex2_list:
                self.stats = self.get_svalex2_stats(t, svalex2_list)
            self.stats = self.get_semantic_stats(t)
            self.stats = self.get_morpho_synt_stats(s,t,i)
            if self.params:
                self.stats = self.get_sentmatch_stats(t,s.nodes,word_pictures)
            
            #add lemma unigrams
            lm_ngram = get_lemma_ngrams(s, t, i, "uni")
            if lm_ngram:
                put_feature_value_list(self.stats,"lemma_unigr", lm_ngram)

            if use_ngrams: #bi- and trigrams 
                self.stats = get_ngrams(self.stats,s,t,i)

            if use_deprel:
                self.stats = self.deprel_stats(t,root_ref, verb_args)

        #fix for JSON serialization issue with the Token class
        self.stats["tokens"] = s.nodes  # retain a copy of Token instances
        s.nodes = tokens                # change Token instances to 'dict'-s
        
        return self.stats

    def print_statistics(self):
        print "Statisctics for:'" + self.sent.words + "'"
        for k,v in self.stats.iteritems():
            print k + ": \t",v 
