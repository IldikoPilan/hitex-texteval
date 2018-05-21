# -*- coding: utf-8 -*-

""" 
CEFR level classifier for Swedish as a second language.
Both learner and expert written texts can be assessed.
Sentence level analysis can also performed.
"""
from __future__ import division, with_statement
import os
import codecs
import cPickle
import json
import sys
import numpy as np

# activate Virtualenv to access Python packages installed there
cwd = os.getcwd()
if cwd == '/export/cgi-bin_sb/larkalabb/HitEx' or cwd == '/export/cgi-bin_sb/larkalabb':
    activate_this = os.path.join("/export/cgi-bin_sb/larkalabb", 'venv/bin/activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))
elif cwd == '/export/cgi-bin_sb/larkadev/HitEx' or cwd == '/export/cgi-bin_sb/larkadev':
    activate_this = os.path.join("/export/cgi-bin_sb/larkadev", 'venv/bin/activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))

from sklearn import svm
import call_sparv
from kelly import process_csv, cefr_scale
from ling_units import Text
from dataset import Dataset
from item_collector import ItemCollector
from auxiliaries.dset_proc_aux import put_feature_value as addict
from auxiliaries.dset_proc_aux import put_feature_value_list as addict_list

global hitex_path
if "HitEx" in cwd:
    hitex_path = cwd + "/"
#elif "2017" in cwd:
#    hitex_path = "/Library/WebServer/CGI-Executables/trunk/HitEx/"
else: 
    hitex_path = cwd + "/HitEx/"    # when run as web-service through the .cgi file(s)

def set_ref_level(ref_level):
    """ 
    Sets reference level, defaulting to B1 if no level is provided.
    """
    if ref_level:
        level = ref_level
    else:
        level = "B1" 
    return level

def create_dataset(dset_path, analysis_level, dset_type, input_files, 
                   dset_file, level, collected_items=[], parameters={}, wordlists={}):
    """
    Processes the input text, creates a Dataset instance of it and extracts
    statistics to be used as input for feature extraction. 
    @ dset_path:       path to dataset
    @ analysis_level:  'text', 'single_text' or 'sentence'
    @ dset_type:       type of dataset 'all' (or 'balanced')
    @ input_files:     Sparv annotated XML files
    @ dset_file:       pickle (.pkl) file containing a Dataset instance
    @ level:           reference CEFR level
    @ collected_items: a list of kwic instances
    @ parameters:      HitEx parameters for sentence search
    @ wordlists:       wordlists to use
    """
    if not collected_items:
        collector = ItemCollector(dset_path, analysis_level, 
                                  dset_type, input_files, level)

    else:
        collector = "" # no collector needed if collected_items are provided

    dset_inst = Dataset(dset_path,analysis_level,dset_type)
    dset_inst.get_set(collector, collected_items)

    # load lists
    kelly_list = process_csv(hitex_path + "word_lists/kelly_sv.csv")
    #TO DO: keep only the other version of SVALex?
    svalex_list = process_csv(hitex_path + "word_lists/SVALex_final.csv") # check if necessary
    svalex2_list =  cPickle.load(codecs.open(hitex_path + "/word_lists/svalex.pkl")) #mapped SVALex

    dset_inst.get_statistics(kelly_list, svalex_list, svalex2_list, parameters, wordlists)
    #dset_inst.save_set(dset_file)
    return dset_inst

def load_classifier(produced_by, analysis_level="text"):
    """ 
    Loads a saved classifier based on who the text was written by 
    ('produced_by'): 'learners' or 'experts'. 
    """
    os.chdir(hitex_path + "classifiers/")
    if produced_by == "learner":
        saved_clf = "text_writing.pkl"
    elif produced_by == "expert":
        saved_clf = "text_reading.pkl"
    elif analysis_level == "sent":
        saved_clf = "sent_sup_eval2015.pkl"        
    with open(saved_clf, 'rb') as fid:
        loaded_clf = cPickle.load(fid)
    return loaded_clf

def classify(loaded_clf, instance):
    """
    Classifies instance with a previously saved classifier 
    (SVM from scikit-learn). Returns the predicted CEFR level 
    represented with a corresponding integer value.
    @ loaded_clf:  unpickled classifier object 
    @ instances:   list of extracted feature values for 1 
    instance
    """
    #ord_cefr_preds = []
    #for instance in instances:
    #if instance.shape[0] == 1:
    #     instance.reshape(1, -1)    #for single sample
    pred = loaded_clf.predict(instance)[0]
    conv_lbl = {"A1":1, "A2":2, "B1":3, "B2":4, "C1":5, "C2":6}
    pred_cefr = [k for k,v in conv_lbl.items() if v == pred][0]
    #    ord_cefr_preds.append(pred_cefr) 
    return pred_cefr #ord_cefr_preds

def compute_stats(dset_inst, feature_values):
    """ 
    Computes statistics for dataset instances. Features must be
    extracted before using instance as argument. 
    @ dset_inst:      a Dataset instance
    @ feature_values: extracted feature values 
    """
    stats = dset_inst.stats_objects
    
    # frequent words without lemmas:
    sparv_fix = ["som", "än", "att",
                "många", "fler", "flera", "flest", "flesta"]

    l2_lists = {}
    for lname in ["svalex", "swell"]:
        with codecs.open(hitex_path + "word_lists/" + lname +".pkl") as f:
            l = cPickle.load(f)
            l2_lists[lname] = l
    
    avg_stats = {}
    for text in stats:
        summed_stats = {"svalex_CEFR":{}, "swell_CEFR":{}, "levelled_text":[]}
        nr_sents = len(text)
        # compute stats per sentence
        for sent_stats in text:
            tokens = sent_stats["tokens"]
            nr_tokens = len(sent_stats["tokens"])
            addict(summed_stats,"nr_tokens", nr_tokens)
            avg_tok_len = sum(sent_stats["tok_len"]) / len(sent_stats["tok_len"])
            addict(summed_stats,"avg_tok_len", avg_tok_len)
            addict(summed_stats, "long_tokens", sent_stats.get("long_w", 0))
            avg_dep_len = round(sum(sent_stats["dep_len"]) / nr_tokens, 2) # length of dependency arcs
            addict(summed_stats,"avg_dep_len", avg_dep_len)
            
            # Kelly - only amount saved in SentStatistics, not the actual tokens
            if "kelly_CEFR" in summed_stats:
                for k,v in sent_stats["voc_cefr"].items():
                    addict(summed_stats["kelly_CEFR"], k, int(v))
            else:
                summed_stats["kelly_CEFR"] = sent_stats["voc_cefr"]
            
            # CEFR from SweLL and SVALex
            for token in tokens:
                #print token.word, token.lemma, token.pos
                token_info = [token.word]
                #print token.word.encode("utf-8"), token.pos
                summed_stats["punct"] = 0
                if token.pos in ["MID", "MAD", "PAD"]:
                    addict(summed_stats, "punct", 1)
                for listname, l2_list in sorted(l2_lists.items()):
                    if token.lemma:
                            lemma = token.lemma[0]
                            k = (lemma, token.pos) 
                            if k in l2_list:
                                level = l2_list[k]
                            else:
                                level = "?"
                    elif token.pos in ["RG", "RO"] or token.word in sparv_fix:
                        # digits & some simple words without lemma from Sparv counted as A1
                        level = "A1"
                    elif token.pos in ["MID", "MAD", "PAD"]:
                        # punctuation - skip coloring in GUI
                        level = ""
                    else:
                        level = "-" # non-lemmatized tokens, same for both resources
                    token_info.append(level)
                    if level:
                        addict_list(summed_stats[listname + "_CEFR"],level,token.word)
                summed_stats["levelled_text"].append(tuple(token_info)) #word, svalex_CEFR, swell_CEFR
        
        # average over sentences
        for k, v in summed_stats.items():
            if type(v) == int and "avg" in k:
                avg_stats[k] = round(v / nr_sents, 2)
            elif type(v) == list: #levelled_text
                avg_stats[k] = v
            elif type(v) == dict and "CEFR" in k:
                avg_stats[k] = {}
                for cefr, words in v.items():
                    try:
                        avg_stats[k][cefr] = len(words)
                    except TypeError:   #kelly_CEFR
                        avg_stats[k][cefr] = int(words)
        nr_words = summed_stats["nr_tokens"] - summed_stats["punct"]
        avg_stats["LIX"] = int((nr_words / nr_sents) + \
                           (summed_stats["long_tokens"] *100 / nr_words))

        avg_stats["nominal_ratio"] = round(list(feature_values)[41], 2) # smoothed value
        avg_stats["PNtoNN"] = round(feature_values[13], 2)# smoothed value when non-zero
        avg_stats["nr_sents"] = nr_sents
        avg_stats["avg_sent_len"] = round(summed_stats["nr_tokens"] / nr_sents, 2)
        avg_stats["nr_tokens"] = summed_stats["nr_tokens"]
        avg_stats["avg_tok_len"] = round(summed_stats["avg_tok_len"] / nr_sents, 2)
        avg_stats["avg_dep_len"] = round(summed_stats["avg_dep_len"] / nr_sents, 2)
        avg_stats["non-lemmatized"] = avg_stats["svalex_CEFR"].get("-",0)
        for wl in ["kelly", "svalex", "swell"]:
            if "-" in avg_stats [wl + "_CEFR"]:
                del avg_stats[wl + "_CEFR"]["-"]
            #avg = round(sum([v for k,v in avg_stats[wl + "_CEFR"].items()])/avg_stats["nr_tokens"])
            #avg_stats["CEFR_" + wl + "_avg"] = [k for k,v in cefr_scale.items() if v == avg][0]
    return avg_stats

def analyze_lg_complexity(text, ref_level, produced_by, analysis_level, 
                          CEFR_ML, ws_type="", collected_items=[], parameters={}, wordlists={}, format="raw"):
    """ Analyzes a text for linguistic complexity in terms of CEFR levels
    and some human-interpretable indicators. Extracts feature values for 
    the input text. Feature set described in Pilán et al. (2015).
    @ text:            input text to analyse
    @ ref_level:       reference CEFR level targeted
    @ produced_by:     type of writer 'learner' or 'expert'
    @ analysis_level:  'text', 'single_text' or 'sentence'
    @ CEFR_ML:         weather to use machine learning based CEFR classification
    @ ws_type:         type of web-service, 'hitex' for HitEx, anything else 
                       defaults to TextEval
    @ collected_items: Sentence or Text instances
    @ parameters:      HitEx parameters for sentence search
    @ wordlists:       wordlists to use
    @ format:          input data format, 'raw' or 'xml' (for already annotated Sparv XML)
    """
    text_analysis = {}
    
    # selected features

    mask_sent = [False, False,  True, False, False, False,  True, False, False,
       False,  True,  True, False, False, False,  True, False, False,
       False, False, False, False, False,  True, False, False, False,
        True,  True,  True,  True, False, False, False, False,  True,
       False, False, False, False, False, False,  True, False,  True,
       False, False, False,  True, False,  True, False,  True, False,
        True,  True,  True, False,  True,  True]

    mask_text_expert = [False,  True,  True,  True,  True,  True,  True,  True,  True,
        True,  True,  True,  True,  True, False,  True,  True, False,
        True,  True,  True, False,  True,  True,  True,  True,  True,
        True,  True,  True,  True,  True,  True, False,  True,  True,
        False,  True,  True,  True,  True,  True,  True,  True,  True,
        True,  True,  True,  True,  True,  True,  True,  True,  True,
        True,  True,  True,  True,  True,  True]

    mask_text_learner = [False, False,  True, False,  True,  True,  True, False, False,
       False,  True, False,  True, False, False, False, False, False,
       False, False, False, False, False,  True, False, False,  True,
       False, False,  True,  True, False, False, False,  True,  True,
       False, False,  True,  True, False,  True, False,  True,  True,
       True, False, False,  True, False,  True, False,  True, False,
       False,  True,  True, False, False,  True]


    # Annotate with Sparv
    if ws_type != "hitex":  #texteval is default
        text = text.replace("\n","")
        if format == "raw":
            annotated_text = call_sparv.call_sparv(text)
            input_files = [annotated_text]
        else:
            #if type(text) == list:   # to do: enable multiple text analysis at a time
            #    input_files = text   # list of Sparv annotated XML responses (as strings)
            #else:
            input_files = [text] # for a single Sparv annotated text
    else:
        input_files = []
    
    # Process and classify text
    dset_path = hitex_path + "datasets/"
    dset_type = "all"
    dset_file = analysis_level + "_"+ dset_type + "_dset.pkl"
    #os.chmod(dset_path+analysis_level+"/"+dset_type+"/"+dset_file, 755)
    level = set_ref_level(ref_level)
    dset_inst = create_dataset(dset_path, analysis_level, dset_type, 
                               input_files, dset_file, level, collected_items, 
                               parameters, wordlists)

    num_label = False   # 'False' for categorical (A1,A2 etc.), 'True' for 
                        # numerical labels (1,2 etc.)
    with_relevance = False # GDEX type filtering - not relevant here
    save_info = False   # whether to save extracted features etc
    arff_labels ="{%s}" % level
    
    if ws_type == "hitex":
        # Skip CEFR level prediction if any level indicated
        if parameters.get("target_cefr", "any") == "any":
            CEFR_ML = False
        if CEFR_ML:
            feature_values = dset_inst.extract_features(num_label, arff_labels, save_info, 
                          with_relevance, parameters) 
        else:
            feature_values = []
        # using only k-best features
        # feature_values = np.array(feature_values)[:, mask_sent]    # for numpy >=v1.12
        mask_idx = [i for i,x in enumerate(mask_sent) if x]
        sel_feature_values = np.take(feature_values, mask_idx, axis=1) #np.delete(feature_values, mask_idx, 1)
        return (dset_inst, sel_feature_values)
    
    else: 
        # TextEval
        feature_values = dset_inst.extract_features(num_label, arff_labels, save_info, 
                          with_relevance, parameters)
        if CEFR_ML:
            loaded_clf = load_classifier(produced_by, analysis_level)
            if analysis_level == "sent":    #fix hardcoded 'single_text' in icall.cgi
                mask = mask_sent
            elif produced_by == "learner":
                mask = mask_text_learner
            else:
                mask = mask_text_expert
            #sel_feature_values = np.array(feature_values)[:, mask]  
            sel_feature_values = np.extract(mask, feature_values)
            cefr_level = classify(loaded_clf, sel_feature_values) 
            text_analysis["CEFR_ML"] = cefr_level 
        
        feat_val_list = list(feature_values[0])
        stats = compute_stats(dset_inst, feat_val_list)
        for k in stats:
            text_analysis[k] = stats[k]
        return text_analysis  

## Example run
# text = u"Du är hungrig. Han sover. De läser en bok."
# ref_level = "A1"  # level of test or student if known
#                   # used for features with prefix "diff_"
# produced_by = "learner" # learner or expert 
# analysis_level = "single_text"
# CEFR_ML = True
# result = analyze_lg_complexity(text, ref_level, produced_by, analysis_level,CEFR_ML)
# print result