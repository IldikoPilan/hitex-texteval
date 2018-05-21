from __future__ import division
import math as m
from auxiliaries.dset_proc_aux import *

class SentFeatures:
    """
    Computes and stores feature values based on statistical information
    from SentStatistics. Most values are smoothed with minimum
    addition smoothing (see dset_proc_aux.py).

    Args:
      sent (instance):  a Sentence instance; a sentence from the corpus or a 
                        keyword-in-context (kw) item.
      stats (instance): a SentStatistic instance, result of the
                        SentStatistics.get_stats_SWE() method
      params

    Attributes:
      stats: see above
      sent:  see above
      features: the object containing the extracted feature values

    Yields:
    Returns a feature dictionary {"feature1":value1, "feature2":value2 ...} 
    for the Sentence instance used as input.

    """
    def __init__(self, sent, stats, params):
        self.stats = stats
        self.sent = sent
        self.features = {}

        sm_sentlen = smooth(float(self.sent.length), self.sent.length)
        
        pos_unigr_d = {}
        for pos in self.stats["pos_unigr"]:
            put_feature_value(pos_unigr_d, pos, 1.0)

        deprel_unigr_d = {}
        for deprel in self.stats["deprel_unigr"]:
            put_feature_value(deprel_unigr_d, deprel, 1.0)

        nb_lexical_words = 0.0
        nb_func_words = 0.0
        nb_punct = 0.0
        for pos, count2 in pos_unigr_d.items():
            if pos in ["NN", "JJ","VB", "AB"]:
                nb_lexical_words += count2
            elif pos in ["MAD", "MID"]:         # punctuation
                nb_punct += count2
            elif pos not in ["PM", "UO", "Kod"]:# prop names, foreign words not counted as func. words
                nb_func_words += count2
        sm_nb_lexical_words = smooth(nb_lexical_words, sm_sentlen)
        sm_nb_func_words = smooth(nb_func_words, sm_sentlen)
        sm_nb_punct = smooth(nb_punct, sm_sentlen)
        try:
            tok_len_no_punct = [len(tok.word) for tok in self.sent.nodes if tok.pos not in ["MAD", "MID"]]
        except AttributeError:
            tok_len_no_punct = [len(tok["word"]) for tok in self.sent.nodes if tok["pos"] not in ["MAD", "MID"]]
        sm_nb_words = smooth(len(tok_len_no_punct), float(sm_sentlen))
        sent_len_no_punct = sm_sentlen - sm_nb_punct    #almost equivalent of sm_nb_words, only the minimum addition value is missing 

        nominal_cats = (smooth(pos_unigr_d.get("NN", 0.0), sm_sentlen) + 
                        smooth(pos_unigr_d.get("PP", 0.0), sm_sentlen) +
                        smooth(pos_unigr_d.get("PC", 0.0), sm_sentlen))     # Participle
        verbal_cats = (smooth(pos_unigr_d.get("PN", 0.0), sm_sentlen) +
                        smooth(pos_unigr_d.get("PS", 0.0), sm_sentlen) +    # Possessive
                        smooth(pos_unigr_d.get("HP", 0.0), sm_sentlen) +    # Interrogative/Relative Pronoun
                        smooth(pos_unigr_d.get("AB", 0.0), sm_sentlen) +
                        smooth(pos_unigr_d.get("VB", 0.0), sm_sentlen))

        #SURFACE / SHALLOW / TRADITIONAL features

        self.features["sent_len_no_punct"] = sent_len_no_punct
        self.features["avg_tok_len_no_punct"] = smooth(sum(tok_len_no_punct), sm_sentlen) / self.features["sent_len_no_punct"]
        self.features["nr_characters"] = sum(self.stats["tok_len"])
        self.features["LIX"] = sm_nb_words+(smooth(self.stats.get("long_w", 0.0), sm_sentlen) / self.features["sent_len_no_punct"]) * 100  #half of LIX
        self.features["nr_wlen>13"] = smooth(self.stats.get("xlong_w", 0.0), sm_sentlen)
        
        #LEXICAL (Vocab load)

        sm_nr_types = smooth(get_nr_types(self, "word"), sm_sentlen)
        self.features["sqrt_ttr"] = sm_nr_types / m.sqrt(sm_sentlen)
        self.features["bilog_ttr"] = m.log(sm_nr_types) / m.log(sm_sentlen)
        self.features["lex_density_senl"] = sm_nb_lexical_words / sm_sentlen
        self.features["lex_density_funw"] = sm_nb_lexical_words / sm_nb_func_words

        # Kelly - freq
        if sum(self.stats.get("voc_freq_kelly", [0.0])) > 0:
            self.features["avg_kelly_log_fr"] = sum(self.stats.get("voc_freq_kelly", [0.0])) / float(len(self.stats.get("voc_freq_kelly", [0.0001])))
        else:
            self.features["avg_kelly_log_fr"] = 0.0

        for cefr_lev in self.stats["voc_cefr_svalex2"].keys(): 
            self.features[cefr_lev+"_voc_inc_svalex2"] = get_incidence_score(self.stats["voc_cefr_svalex2"][cefr_lev], sm_sentlen)
            #cefr_lev '?' when not in word list, '-' when no lemma for a word form

        if not self.sent.level:
            self.sent.level = params["target_cefr"]
            #self.sent.level = "B1"     # to set a deafault value
            
        # Svalex / SweLLex - incidence scores per CEFR level 
        self.features["diff_w_inc_svalex2"] = get_incidence_score(sum([count for level, count in self.stats["voc_cefr_svalex2"].iteritems() 
                                                            if level not in ["?", "-"] and (cefr_scale[level] > cefr_scale[self.sent.level])]), sm_sentlen)
        self.features["diff_NNVB_inc_svalex2"] = get_incidence_score(self.stats.get("diff_NNVB_svalex2", 0.0), sm_sentlen)

        #SEMANTIC / IDEA (CONCEPTUAL) density

        self.features["simple_nomr_NNtoVB"] = adjust_ratio("NN", "VB", sm_sentlen, pos_unigr_d) #smooth(pos_unigr_d.get("NN", 0.0), sm_sentlen) / smooth(pos_unigr_d.get("VB", 0.0), sm_sentlen) 
        self.features["nom_ratio"] =  nominal_cats / verbal_cats
        self.features["avg_senses/w"] = smooth(sum(self.stats["senses/w"]), sm_sentlen) / sm_nb_words
        self.features["nn_senses/nn"] = smooth(sum(self.stats.get("nn_senses/nn", [0.0])), sm_sentlen) / smooth(pos_unigr_d.get("NN", 0.0), sm_sentlen)

        #STRUCTURAL
        
        #modifier features
        pre_mod = smooth(deprel_unigr_d.get("AT", 0.0), sm_sentlen)
        post_mod = smooth(deprel_unigr_d.get("ET", 0.0), sm_sentlen)
        self.features["pre_mod_inc"] = get_incidence_score(deprel_unigr_d.get("AT", 0.0), sm_sentlen)
        self.features["post_mod_inc"] =get_incidence_score(deprel_unigr_d.get("ET", 0.0), sm_sentlen)
        all_mod = pre_mod + post_mod
        self.features["modif_v"] = all_mod / sm_nb_lexical_words #lexical feat in Vajjala & Meurers

        #verb-related features
        self.features["pres_PCtoVB"] = smooth(self.stats.get("pres_pc", 0.0), sm_sentlen) / smooth(self.stats.get("main_verb", 0.0), sm_sentlen)
        self.features["past_PCtoVB"] = smooth(self.stats.get("perf_pc", 0.0), sm_sentlen) / smooth(self.stats.get("main_verb", 0.0), sm_sentlen)
        self.features["past_VBtoVB"] = smooth(self.stats.get("past_VB", 0.0), sm_sentlen) / smooth(self.stats.get("main_verb", 0.0), sm_sentlen)
        self.features["pres_VBtoVB"] = smooth(self.stats.get("pres_VB", 0.0), sm_sentlen) / smooth(self.stats.get("main_verb", 0.0), sm_sentlen)
        self.features["sup_VBtoVB"] = smooth(self.stats.get("sup_VB", 0.0), sm_sentlen) / smooth(self.stats.get("main_verb", 0.0), sm_sentlen)
        self.features["MVBtoVB"] = smooth(len(self.stats.get("modal_verb", [])), sm_sentlen) / smooth(self.stats.get("main_verb", 0.0), sm_sentlen)
        self.features["SverbtoVBs"] = smooth(len(self.stats.get("sverb", [])), sm_sentlen) / smooth(self.stats.get("main_verb", 0.0), sm_sentlen)
        self.features["Sverb_inc"] = get_incidence_score(len(self.stats.get("sverb", [])), sm_sentlen)

        #variational scores (Vajjala and Meurers)
        self.features["nn_v"] = smooth(pos_unigr_d.get("NN", 0.0), sm_sentlen) / sm_nb_lexical_words
        self.features["vb_v"] = smooth(pos_unigr_d.get("VB", 0.0), sm_sentlen) / sm_nb_lexical_words   
        self.features["adj_v"] = smooth(pos_unigr_d.get("JJ", 0.0), sm_sentlen) / sm_nb_lexical_words   
        self.features["adv_v"] = smooth(pos_unigr_d.get("AB", 0.0), sm_sentlen) / sm_nb_lexical_words

        #incidence scores (Coh metrix)
        self.features["nn_inc"] = get_incidence_score(pos_unigr_d.get("NN", 0.0), sm_sentlen)   
        self.features["vb_inc"] = get_incidence_score(pos_unigr_d.get("VB", 0.0), sm_sentlen)     
        self.features["adj_inc"] = get_incidence_score(pos_unigr_d.get("JJ", 0.0), sm_sentlen)   
        self.features["adv_inc"] = get_incidence_score(pos_unigr_d.get("AB", 0.0), sm_sentlen) 
        self.features["PL_inc"] = get_incidence_score(pos_unigr_d.get("PL", 0.0), sm_sentlen) #use only for particles! ref in K.H.Muhlenbock 2013
        self.features["SN_inc"] = get_incidence_score(pos_unigr_d.get("SN", 0.0), sm_sentlen)
        self.features["alljnc_inc"] = (get_incidence_score(pos_unigr_d.get("SN", 0.0), sm_sentlen) 
                                    + get_incidence_score(pos_unigr_d.get("KN", 0.0), sm_sentlen))
        self.features["rel_cl_inc"] = get_incidence_score(deprel_unigr_d.get("EF", 0.0), sm_sentlen)
        self.features["rel_str_inc"] = get_incidence_score(self.stats.get("rel_str", 0.0), sm_sentlen)
        self.features["PA_inc"] = get_incidence_score(deprel_unigr_d.get("PA", 0.0), sm_sentlen)
        self.features["UA_inc"] = get_incidence_score(deprel_unigr_d.get("UA", 0.0), sm_sentlen)
                 
        self.features["PNtoNN"] = adjust_ratio("PN", "NN", sm_sentlen, pos_unigr_d) 
        self.features["PNtoPP"] = adjust_ratio("PN", "PP", sm_sentlen, pos_unigr_d)
        self.features["PN_3SG_inc"] = get_incidence_score(self.stats.get("PN_3SG", 0.0), sm_sentlen)
        self.features["neuNN_inc"] = get_incidence_score(self.stats.get("neu_NN", 0.0), sm_sentlen)
        self.features["func_words_inc"] = get_incidence_score(nb_func_words, sm_sentlen)
        self.features["punct_inc"] = get_incidence_score(nb_punct, sm_sentlen)

        #dep lens
        self.features["avg_dep_len"] = sum(self.stats["dep_len"]) / self.sent.length
        self.features["l_dep_arcs"] = smooth(self.stats.get("left_arc", 0.0), sm_sentlen) / smooth(float(len(self.stats["dep_len"])-1), sm_sentlen) #out of all arcs (excluding same position
        self.features["r_dep_arcs"] = smooth(self.stats.get("right_arc", 0.0), sm_sentlen) / smooth(float(len(self.stats["dep_len"])-1), sm_sentlen)
        self.features["max_root_dep_len"] = max(self.stats.get("root_dep_len", [0]))
        self.features["dep_lens>5"] = len([dep_len for dep_len in self.stats["dep_len"] if dep_len > 5])
        
    def print_features(self):
        print "Features for:'" + self.sent.words + "'"
        for k,v in self.features.iteritems():
            print k + ": \t",v 

#Test runs - for sentences only - needs to be updated!
# svalex_list = process_csv("/media/phd/DEVELOPMENT/rdby_exp/scripts/SVALex_final.csv")
# for i,kw in enumerate(coctaill_instances.items):
#     if i < 3:
#         proc_sent = SentStatistics(kw.sentence)
#         sentence = proc_sent.sent.words #fix also for Text
#         print sentence
                
#         print "about to start stats"

#         st = proc_sent.get_stats_SWE(kelly_list, svalex_list,True,True)
#         proc_sent.print_statistics()
        
#         f = SentFeatures(kw, st)
#         f.print_features()
        
#         for name, val in proc_sent.features.items():
#             if name == "avg_senses/w":
#                 print name,val
#                 print proc_sent.stats["senses/w"]
