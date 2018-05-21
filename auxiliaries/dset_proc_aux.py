"""
Smaller help functions used in SentStatistics and
SentFeatures.
"""

cefr_scale = {"A1":1, "A2":2, "B1":3, "B2":4, "C1":5, "C2":6} #"easy":3, "hard":6

def put_feature_value(d, f, v):
    try:
        d[f] += v
    except KeyError:
        d[f] = v

def put_feature_value_list(d, f, v):
    try:
        d[f].append(v)
    except KeyError:
        d[f] = [v]

def check_root(sent):
    """Checks if a sentence annotated with dependency relations
    has a 'ROOT' tag.
    """
    sent_deprels = []
    for tkn in sent.nodes:
        sent_deprels.append(tkn.deprel)
        if tkn.deprel == "ROOT":
            root_ref = tkn.ref
        # except AttributeError:
        #     sent_deprels.append(tkn["deprel"])
        #     if tkn["deprel"] == "ROOT":
        #         root_ref = tkn["ref"]
        
    if "ROOT" not in sent_deprels:  #consider those sents bugs?
        root_ref = 0
        #print "no root among deprels", sent_deprels
    return root_ref

def get_lemma_ngrams(s, t, i, ngram_size):
    """
    Collects ngrams of lemmas for sentence 's'. Only the first lemma is 
    saved if there are more lemmas available. If no lemma is available 
    for token 't', the word form is taken and this is marked with an '*'
    following the word form.
    Returns a string if 'ngram_size' is 'uni', a tuple otherwise.

    Args:
      s: an instance of the Sentence class
      t: an instance of the Token class
      i: current index of token in the sentence
      ngram_size: 'uni', 'bi' or 'tri' 
    """
    ngrams = {"uni":1, "bi":2, "tri":3}
    if i < s.length-(ngrams[ngram_size]-1):
        lemma_ngrams = []
        for j in range(ngrams[ngram_size]):
            if s.nodes[i+j].lemma:
                lemma_ngrams.append(s.nodes[i+j].lemma[0])   #only keeps the first lemma
            else:
                lemma_ngrams.append(s.nodes[i+j].word + "*") #no lemma, word form* instead
        if len(lemma_ngrams) > 1:
            return tuple(lemma_ngrams)
        return lemma_ngrams[0]  #or better to keep them all?
    else:
        return []

def get_ngrams(stats,s,t,i):
    """
    Extract bi- and trigrams of lemmas, POS and dependency relation
    (deprel) tags. Unigrams are extracted by default in SentStatistics. 
    """
    #lemma ngrams
    ngram_sizes = ["bi", "tri"]
    for ngram_size in ngram_sizes:
        lm_ngram = get_lemma_ngrams(s, t, i, ngram_size)
        if lm_ngram:
            put_feature_value_list(stats,"lemma_" + ngram_size + "gr", lm_ngram)

    #POS and deprel bigrams
    if i < s.length-1:
        put_feature_value_list(stats,"deprels_bigr", (t.deprel,s.nodes[i+1].deprel))
        put_feature_value_list(stats,"pos_bigr", (t.pos,s.nodes[i+1].pos))
    
    #POS and deprel trigrams
    if i < s.length-2:
        put_feature_value_list(stats,"deprels_trigr", (t.deprel, s.nodes[i+1].deprel, s.nodes[i+2].deprel))
        put_feature_value_list(stats,"pos_trigr", (t.pos, s.nodes[i+1].pos, s.nodes[i+2].pos))

    return stats

def get_nr_types(proc_sent, info_type):
    "Get unique word or POS types from a SentFeatures instance."
    if type(proc_sent.sent.nodes[0]) == dict:
        if info_type == "word":
            types = set([t["word"] for t in proc_sent.sent.nodes])
        elif info_type == "pos":
            types = set([t["pos"] for t in proc_sent.sent.nodes])
    else:
        if info_type == "word":
            types = set([t.word for t in proc_sent.sent.nodes])
        elif info_type == "pos":
            types = set([t.pos for t in proc_sent.sent.nodes])
    return len(types)

def smooth(item_count, nr_tokens, type="min"): #change type of smoothing? NLTK if freq dists
    """Smoothes  counts. If type is set to 'ele', Expected Likelihood Estimation
    smoothing is performed (count multiplied by 0.5), otherwise minimum addition
    smoothing is done (count multiplied by 1/sentence length)."""
    if type == "ele":
        smoothed_count = item_count + nr_tokens * 0.5
    else:
        smoothed_count = item_count + (1 / nr_tokens)
    return smoothed_count

def adjust_ratio(cat1,cat2, sm_sentlen, pos_unigrs):
    """
    Return 0 as a result for a ratio in case the count of 
    any of the two categories is 0. Without this adjustment, 
    the smoothed ratio would be too high in these cases.
    """
    cat1_count = pos_unigrs.get(cat1, 0.0)
    cat2_count = pos_unigrs.get(cat2, 0.0)
    if cat1_count == 0.0 or cat2_count == 0.0:
        return 0.0
    else:
        return smooth(cat1_count, sm_sentlen) / smooth(cat2_count, sm_sentlen)

def get_incidence_score(cat_count, nr_words, smoothed=True):
    "Computes an incidence score of a given category per 1000 words."
    if smoothed:
        score = 1000 / nr_words * smooth(cat_count, nr_words)
    else: 
        score = 1000 / nr_words * lg_cat_d.get(lg_cat, 0.0) #buggy
    return score

def feat_info_to_str(feat_list, add_id=False):
    """
    Transform feature names and values into a string.
    """
    #add part handling texts with a all_sent_f_list as + arg
    #feat_list = [(fn, fs[fn]) for fn in features.keys()]
    feat_list.sort()
    feature_n = [el[0] for el in feat_list]
    float_fs = [] #needed?
    float_fs = map(lambda x: str(float(x[1])), feat_list)

    if add_id:
        feature_n.insert(0, "id")
        float_fs.insert(0,str(count))
    
    f_row = " ".join(float_fs)

    return (feature_n, f_row)

def map_Token_to_dict(t):
    """
    Quick & dirty fix for JSON serialization issues with
    the Token class: mapping Token instance to a dict
    """
    token_info = {}
    token_info["word"] = t.word
    token_info["lemma"] = t.lemma
    token_info["msd"] = t.msd
    token_info["pos"] = t.pos
    token_info["saldo"] = t.saldo
    token_info["ref"] = t.ref
    token_info["deprel"] = t.deprel
    token_info["lex"] = t.lex
    #token_info["dephead"] = t.dephead #not JSON serializable
                                       #not returned in web-service response,
                                       #but value used in sent_statistics
                                       #(copy of Token objects retained)
    try:
        token_info["suffix"] = t.suffix
    except AttributeError:
        token_info["suffix"] = ""
    return token_info