import csv
import os
import random
import codecs

"""
Reads information from the Kelly word list.
"""

global cefr_scale
cefr_scale = {"A1":1, "A2":2, "B1":3, "B2":4, "C1":5, "C2":6} #"easy":3, "hard":6

def process_csv(csv_file):
    """
    Loads a word list from a tab-separated CSV file.

    Arg:
     csv_file (str): file name (or absolute path if not in folder)

    Yields:
      A list of dictionaries each of which corresponds to a row.
      eg. Kelly {'Swedish items for translation': 'toppen', 'Grammar': '', 'Source': 'T2', 
      'WPM': '0.04', 'CEFR levels': 'C2', 'Examples': '', 'Word classes': 'adjective', 
      'Raw freq': '', 'ID': '8424'}
    """
    csv_f = open(csv_file)
    csv_extract = csv.DictReader(csv_f, delimiter="\t") # dialect='excel'
    csv_list = []                                      
    for row in csv_extract:
        u_row = {}
        for k,v in row.iteritems():
            if type(v) == str:
                u_row[k] = v.decode("utf-8")
            else:
                u_row[k] = v
        csv_list.append(u_row)
    return csv_list

def get_kelly_info(kelly_list, token, item_level):
    """
    Gets information for token from the Kelly list including
    the CEFR level and frequency of a lemma.

    Args:
      kelly_list (list): the loaded Kelly list
      token:             a Token instance
      item_level (str): proficiency level of item from the annotated corpus
    
    Yields:
      a tuple of (textual_info, level, word-per-million (WPM) frequency)
    """ 
    if token.pos == "MID" or token.pos == "MAD" or token.pos == "PAD":
        return ("punctuation", "A1", 1000000)       #like the manual additions -> change?
    
    if not token.lemma:    #or token.lemma == "|" 
        return ("no lemma", "-", 0)  #not ?
    else:
        lemma = token.lemma
        for row in kelly_list:
            #raw_fr_defaults = {"a1":503611, "a2":4952.5,"b1":2018, "c1":402.5, "c2":1} #means for level ranges, except for C1, C2
            if row['Swedish items for translation'] in lemma:
                cefr = row['CEFR levels']
                freq = float(row['WPM'])   #or row['Raw freq']? - but no raw fr values for manual additions
                if item_level not in ["context_dep", "context_indep"]:
                    if item_level.lower() == "any":
                        return ("at cefr", cefr, freq)
                    elif cefr == item_level:
                        return ("at cefr", cefr, freq)
                    elif cefr_scale[cefr] < cefr_scale[item_level]:
                        return ("below", cefr, freq) 
                    elif cefr_scale[cefr] > cefr_scale[item_level]:
                        return ("above", cefr, freq)
                else:
                    return ("", cefr, freq) 
        #print "Not found: " + lemma 
        return ("not in kelly", "?", 0)

def get_svalex_info(svalex_list, token, item_level):
    """
    Collects frequency values from the SVALex vocabulary list for a token
    (only for lexical categories, i.e. nouns, verbs, adverbs and adjectives).
    Frequency values for each level are collected and summed up to the CEFR 
    level indicated by 'item_level'. Information about a token not being in  
    SVALex is also returned.
    """
    summed_freq = 0.0
    out_of_svalex = True
    if token.pos in ["NN", "VB", "AB", "JJ"]:
        if token.lemma:
            try:
                lvl_int = cefr_scale[item_level]
            except KeyError:
                lvl_int = 5
            lvl_lowcase = item_level.lower()
            lvls = [k for k,v in cefr_scale.iteritems() if v <= lvl_int]
            for row in svalex_list:
                if row["word"] in token.lemma and token.pos == row["tag"][:2]:
                    out_of_svalex = False
                    if lvl_lowcase == "any" or lvl_lowcase == "" or lvl_lowcase == "c1":
                        summed_freq = float(row["total_freq@total"])
                    else:
                        freqs = [float(row["level_freq@" + lvl.lower()]) for lvl in lvls]
                        summed_freq = sum(freqs)
    else:
        out_of_svalex = False
    return (summed_freq, out_of_svalex)

#svalex = process_csv("/media/phd/DEVELOPMENT/rdby_exp/scripts/SVALex_final.csv")
#for row in svalex[:10]:
#    print row["word"], row["tag"][:2]

def get_svalex2_info(token, L2_word_list, target_cefr):
    "Processes L2 word lists (SVALex and SweLLex) with CEFR level mappings."
    if token.lemma:
        lemma = token.lemma[0]
        k = (lemma, token.pos)
        if k in L2_word_list:
            level = L2_word_list[k]
            if cefr_scale[target_cefr] > cefr_scale[level]:
                r = ("above", level)
            elif target_cefr == level:
                r = ("at cefr", level)
            else:
                r = ("below", level)
        else:
            r = ("OOV", "?")
    elif token.pos in ["RG", "RO", "MID", "MAD", "PAD"]:
        if target_cefr == "A1":
            r = ("at cefr", "A1")
        else:
            r = ("above", "A1")
    #TODO: manual fix for "som" etc with no SALDO lemma?
    else:
        r = ("no lemma", "-")
    return r


def get_candidate_words(svalex_list, pos, cefr, nr_candidates, mwe=False):
    """ Get a number of candidate words from SVALex for a certain CEFR level.
    @ svalex_list:   the loaded word list
    @ pos:           part of speech of word
    @ nr_candidates: number of candidate words to return
    @ cefr:          desired CEFR level of words
    @ mwe:           whether candidate items should be multi-word expressions 
    """
    candidate_items = []
    target_cefr = cefr.lower()
    avg_freq_thr = {"a1":50, "a2":55, "b1":54, "b2":55, "c1":58}
    for item in svalex_list:
        valid_candidate = False
        item_pos = item["tag"][:2]
        if item_pos == pos:
            if not mwe:
                if len(item["word"]) > 1: 
                    if len(item["tag"]) > 2:
                        if item["tag"][2] != "M":
                            valid_candidate = True
                    else:
                        valid_candidate = True
            else:
                if len(item["tag"]) > 2:
                    if item["tag"][2] == "M":
                        valid_candidate = True

            if valid_candidate:
                freq = float(item["level_freq@"+target_cefr])
                if item["nb_doc@"+target_cefr] > 1:
                    if mwe:
                        if freq:
                            candidate_items.append(item["word"])
                    else:
                        if freq >= avg_freq_thr[target_cefr]:
                            candidate_items.append(item["word"])
    random.shuffle(candidate_items)
    print "Randomly selecting lemmas out of %d candidates (POS: %s, CEFR: %s)..." % (len(candidate_items),pos,target_cefr.upper())
    #for candidate_item in candidate_items:
    #    print candidate_item.encode("utf-8"),
    #print "\n"
    try:
        return candidate_items[:nr_candidates]
    except IndexError:
        return candidate_items

def save_cand_lemmas(svalex_list, cefr_levels, target_pos, nr_candidates, filename, mwe=False):
    """ Save to a csv file randomly picked lemmas for more CEFR levels
    and parts of speech (POS) from SVALex. Duplicates across levels are
    removed.
    @ svalex_list:  the loaded word list
    @ cefr_levels:  levels to search lemmas for
    @ target_pos:   parts of speech to search lemmas for
    @ nr_candidates:number of candidate words to return
    @ filename:     path + name of the file in which to save results
    @ mwe:          whether candidate items should be multi-word expressions
    """
    suggested_lemmas = {}
    used_lemmas = []
    with codecs.open("/media/phd/DEVELOPMENT/evaluation_2015/eval_material/final/teachers/" + "eval_lemmas_v1.txt") as f:
        lines = f.readlines()
    eval_lemmas = [line.split("\t")[0].decode("utf-8") for line in lines[1:]]
    used_lemmas += eval_lemmas
    for pos in target_pos:
        suggested_lemmas[pos] = {}
        for cefr in cefr_levels:
            suggested_lemmas[pos][cefr] = get_candidate_words(svalex_list, 
                                            pos, cefr, nr_candidates*3, mwe)

    result = []
    for pos2, cefr_lemmas in suggested_lemmas.items():
        result.append(pos2)
        result.append(" \t" + "\t".join([cefr.upper() for cefr in cefr_levels]))
        rows = {}   #1: [A1_word, A2_word, B1_word ...]
        for i in range(nr_candidates):
            rows[str(i+1)] = []
        for cefr_lvl in cefr_levels:
            candies = cefr_lemmas[cefr_lvl]
            #print len(candies)
            duplicates = 0
            for j in range(nr_candidates):
                row_id = j+1 #-duplicates
                try:
                    candy = candies[j]
                except IndexError:
                    candy = "*"
                if row_id <= nr_candidates:
                    if candy not in used_lemmas:
                        rows[str(row_id)].append(candy)
                        if candy != "*":
                            used_lemmas.append(candy)
                        #print candy.encode("utf-8")
                    else:
                        rows[str(row_id)].append("*"+candy)
                    #    duplicates += 1
        for rowid,words in rows.items():
            diff = 5 - len(words) 
            if diff:
                for i in range(diff):
                    rows[rowid].append("*")
                    print rows[rowid]
        sorted_rows = sorted([int(k) for k in rows.keys()])
        for rowid2 in sorted_rows:
            result.append(str(rowid2) + "\t" + "\t".join(rows[str(rowid2)]))
        result.append("\n")
    with codecs.open(filename, "w", "utf-8") as f:
      output = "\n".join(result)
      f.write(output)
    return result

def load_cand_lemmas(filename):
    with codecs.open(filename) as f:
        lines = f.readlines()
    result = {}
    mapping = {1:"A1", 2:"A2", 3:"B1", 4:"B2", 5:"C1"}
    pos = ""
    for line in lines:
        line_el = line.split("\t")
        line_el[-1] = line_el[-1].strip("\n")
        if line_el:
            if line_el[0] in ["NN", "VB", "JJ"]:
                pos = line_el[0]
                lemmas_per_level = {"A1":[], "A2":[], "B1":[], "B2":[], "C1":[]}
                result[pos] = lemmas_per_level
            elif line_el[0].isdigit(): #and pos
                for i in range(1,6):
                    level = mapping[i]
                    try:
                        result[pos][level].append(line_el[i])
                        #print pos, level
                        #print result[pos][level]
                    except KeyError, IndexError:
                        pass
    return result

## Example runs

voc_list_folder = "/media/phd/DEVELOPMENT/HitEx/word_lists/"
#svalex_list = process_csv(voc_list_folder + "SVALex_final.csv")
## Get lemmas for one level and POS
## candies = get_candidate_words(svalex_list, "VB", "A1", 15, mwe=False)
## for candy in candies:
##     print candy.encode("utf-8")

## Get lemmas for more levels and POSs
cefr_levels = ["a1", "a2", "b1", "b2", "c1"]
target_pos = ["NN", "VB", "JJ"]
nr_candidates = 6
mwe = False
filename = "/media/phd/DEVELOPMENT/evaluation_2015/seed_lemmas.csv"
#TO DO : bug fix!
#save_cand_lemmas(svalex_list, cefr_levels, target_pos, nr_candidates, filename, mwe)

# filename = "/media/phd/DEVELOPMENT/evaluation_2015/seed_lemmas_SIMPLEW.csv"
# lemmas = load_cand_lemmas(filename)
# for pos,stuff in lemmas.items():
#     print pos,
#     for level,words in stuff.items():
#         print level
#         for w in words:
#             print w
#     print ""
#print lemmas["NN"]["A1"]