# -*- coding: utf-8 -*-

"""
Functions for assessing the context-independence of a sentence.
Two sub-aspects included: 
    discourse structure (root + dialogue answer)
    anaphora (pronouns, determinative structures, adverbs) 
"""

from auxiliaries.dset_proc_aux import *

# DISCOURSE STRUCTURE

def check_root_POS(sent_match, roots):
    """ Check the part of speech of the dependency root(s).
    """
    context_indep = False
    # Check non-verbal roots and sentence initial tokens
    root_pos = [r.pos for r in roots]
    if "VB" in root_pos or "MID" in root_pos: # sents starting with -
        try:
            if sent_match.sent.nodes[0]["word"] in ["Men", "Och", "Eller", "Samt", "Utan", "Ty"]:
                context_indep = False
                put_feature_value(sent_match.match, "struct_conn", 
                                                   (True, "conjunction in isolation"))
            else:
                context_indep = True 
        except AttributeError:
            if sent_match.sent.sentence.nodes[0]["word"] in ["Men", "Och", "Eller", "Samt", "Utan", "Ty"]:
                context_indep = False
                put_feature_value(sent_match.match, "struct_conn", 
                                                   (True, "conjunction in isolation"))
            else:
                context_indep = True 
    else:
        for root2 in roots:
        # Conjuctions and adverbs only under certain conditions
            if root2.pos in ["AB", "KN"]: 
                if root2.pos == "AB":
                    for child in sent_match.stats["heads"][root2.ref]:
                        # e.g. 'dvs'
                        if child.deprel in ["MS", "+F"]:
                            context_indep = True
                        else:
                            put_feature_value(sent_match.match, "struct_conn", 
                                               (True, "adverb as root"))
                elif root2.pos == "KN":
                    clauses = sum([1 for t in sent_match.stats["heads"][root2.ref] \
                                   if t.deprel in ["MS", "+F"]])
                    conjuncts = sum([1 for t in sent_match.stats["heads"][root2.ref] \
                                     if t.deprel == "CJ"])

                    # Require a mininum of 2 clauses or conjuncts
                    for child in sent_match.stats["heads"][root2.ref]:
                        if clauses > 1 or conjuncts > 1 or (conjuncts + clauses) > 1:   #added length constraint in Feb 2015
                            context_indep = True
                    if root2.word in [u"Antingen", u"Varken", u"Både", u"Såväl", u"Vare", u"Dels"]:
                        context_indep = True

                    if not context_indep:
                        put_feature_value(sent_match.match, "struct_conn", 
                                               (True, "struct. connective in isolation: %s" % root2.word.encode("utf-8")))                   
            #TO DO: also PM or NN if followed by a relative clause?
    return context_indep


def is_yn_answer(sent_match, dialogue_answ_pattern):
    """ Check for yes-no answers.
    """
    context_indep = True
    try:
        if sent_match.stats["tokens"][0].pos == "MID":
            pattern = tuple([sent_match.stats["tokens"][0].pos, sent_match.stats["tokens"][1].pos, sent_match.stats["tokens"][2].pos])
        else:
            pattern = tuple([sent_match.stats["tokens"][0].pos, sent_match.stats["tokens"][1].pos])
    except IndexError:
        pattern = ""
    if pattern in dialogue_answ_pattern:
        put_feature_value(sent_match.match, "yn_answer", (True, ""))
        context_indep = False
    return context_indep

# ANAPHORA

def check_anaphora_PN(tok, j, sent_match, normalized_w, demon_pronouns):
    """ Check pronominal anaphora. 
    TO DO: substitute rule-based with statistical approach? (SUC-CORE)
    """
    context_indep = False
    # Pronouns are unresolved anaphoras?
    if tok.pos == "PN":
        # "Det" as dummy subject (formal subject  + cleft)
        if normalized_w == "det" and tok.deprel == "FS":
            context_indep = True
        # "Som" in following 4 tokens
        elif "som" in [t.word for t in sent_match.stats["tokens"][int(tok.ref):int(tok.ref)+3]]:
            context_indep = True
        else:
            # Antecedents? (no children, no sisters)
            # (proper names and nouns that agree in gender and number)
            # TO DO: restrict? (SN, KN mother in common etc - see notes)
            pn_props = tok.msd.split(".")
            pn_gender, pn_nr = pn_props[1], pn_props[2]
            antecedent_candidates = []
            for prev_w in sent_match.stats["tokens"][:j]:
                if prev_w.pos == "PM":
                    antecedent_candidates.append(prev_w.word)
                if prev_w.pos == "NN":
                    nn_prop = prev_w.msd.split(".")
                    if pn_gender == nn_prop[1] and pn_nr == nn_prop[2]:
                        antecedent_candidates.append(prev_w.word)
                if prev_w.pos == "IE" and normalized_w == "det":
                    antecedent_candidates.append(prev_w.word)
            if not antecedent_candidates:
                put_feature_value_list(sent_match.match, "anaphora-PN", (True, tok.word))
            else:
                put_feature_value_list(sent_match.stats, "resolved?_anaphora-PN", (True, tok.word))
    return context_indep

def check_anaphora_AB(tok, sent_match, time_adv_antecedent):
    context_indep = False
    # Capture 'ago' (för ... sedan)
    if tok.word.lower() == "sedan":   
        try:
            if tok.deprel == "HD" \
                and sent_match.stats["tokens"][int(tok.depheadid)-1].word.lower() == u"för":
                context_indep = True
        except KeyError:
            context_indep = False
    # Time and place adverbials
    if tok.deprel in ["TA", "RA"]: #"AA" also below
        # Check for preceeding correlate
        # e.g. ... när du sedan söker...
        if tok.deprel == "TA" and time_adv_antecedent:
            context_indep = True
        
        # Children
        # e.g. "där på landet"
        try:
            clone = [t for t in sent_match.stats["heads"][tok.depheadid] \
                     if t.deprel == tok.deprel and t.ref != tok.ref]
        except KeyError:
            clone = []
        try:
            # E.g. då och då
            mwe = [t for t in sent_match.stats["heads"][tok.ref] if t.deprel == "HD"]
        except: 
            mwe = []
        if clone or mwe:
            context_indep = True

        if not context_indep:
            # Mother
            # e.g. det här huset
            adv_mother_ind = int(tok.depheadid)-1
            if sent_match.stats["tokens"][adv_mother_ind].pos == "DT" \
                                and sent_match.stats["tokens"][adv_mother_ind].deprel == "DT":
                context_indep = True
            elif sent_match.stats["tokens"][adv_mother_ind].pos == "VB" \
                                  and sent_match.stats["tokens"][adv_mother_ind].deprel == tok.deprel:
                if tok.deprel in ["RA", "TA"]: # AA might create overgeneralizaition
                    context_indep = True
            else:
                # Common grandmother with other time and place adverbials
                adv_granny_ref = sent_match.stats["tokens"][adv_mother_ind].depheadid
                if adv_granny_ref:
                    adv_granny_ind = int(adv_granny_ref)-1
                    if sent_match.stats["tokens"][adv_granny_ind].pos in ["KN", "SN"]:
                        try:
                            gr_children = sent_match.stats["heads"][adv_granny_ind]
                            for gr_ch in gr_children:
                                if gr_ch.deprel == tok.deprel:
                                    context_indep = True
                        except KeyError:
                            pass
        
        if not context_indep:
            put_feature_value_list(sent_match.match, "anaphora-AB1", 
                                   (True, "Referential time / place adv: %s" % tok.word))

    elif tok.deprel in ["+A", "CA", "AA"]:
        # Conjunctional, contrastive and other adverbials
        context_indep = False
        # Is the mother node an apposition?
        adv_mother_ind = int(tok.depheadid)-1
        if sent_match.stats["tokens"][adv_mother_ind].deprel in ["AN", "KN"]: #apposition
            context_indep = True
        
        # Conjunctional adverbial in sentence-initial position?
        konj_adv = [u"Dessutom",  u"Också",  u"Även",  u"Vidare",  
                    u"Därtill",  u"Likaså"                                # Additiva
                    u"Däremot", u"Emellertid", u"Ändå",  u"Istället",  
                    u"Dock"                                               # Adversativa
                    u"Alltså", u"Följaktligen",  u"Slutligen", u"Sålunda" # Konklusiva
                    u"Nämligen",                                          # Explanativa
                    u"Alternativt", u"Annars"]                            # Disjunktiva
        if sent_match.stats["tokens"][0].deprel == "A+" or     \
            sent_match.stats["tokens"][0].word in konj_adv or  \
            sent_match.sent.words[:14] == "Å andra sidan":
            context_indep = False
        
        # Grandmother
        # e.g. En sekunds tvekan eller dröjsmål eller ett till synes oskyldigt slarv kan 
        #      kosta dig   och även kamraterna livet .
        if not context_indep:
            if sent_match.stats["tokens"][adv_mother_ind].depheadid:
                try:
                    adv_granny_ind = int(sent_match.stats["tokens"][adv_mother_ind].depheadid)-1
                except TypeError:
                    print sent_match.stats["tokens"][adv_mother_ind].depheadid
            else: 
                adv_granny_ind = -1
            if adv_granny_ind >= 0:
                if sent_match.stats["tokens"][adv_granny_ind].pos == "KN":
                    context_indep = True
        
        # Sisters
        # e.g. Om du behöver gå igenom en hel serie röntgen- eller radiumbehandlingar  
        #      får du också    dessa utan särskild kostnad .
        if not context_indep:
            try:
                adv_sisters = sent_match.stats["heads"][tok.depheadid]
            except KeyError:
                adv_sisters = []
            if adv_sisters:
                if "SN" in adv_sisters or "KN" in adv_sisters:
                    context_indep = True

        if not context_indep:
            put_feature_value_list(sent_match.match, "anaphora-AB", #separate subtype before: AB2
                                   (True, "Conjunctional adv: %s" % tok.word))

    return context_indep

def check_anaphora(tok, j, sent_match, time_adv_antecedent, demon_pronouns, 
                   anaph_adv, anaphora_types_to_check):
    """ Check if sentence contains anaphoric expressions.
    """
    context_indep = False
    # Relative adverb as time adverbial?
    if tok.pos == "HA" and tok.deprel == "TA": 
        time_adv_antecedent = True       

    normalized_w = tok.word.lower()
    if normalized_w in demon_pronouns:
        # Pronouns
        if "anaphora-PN" in anaphora_types_to_check:
            if tok.pos == "PN":
                context_indep = check_anaphora_PN(tok, j, sent_match, normalized_w, demon_pronouns)
    # Adverbs
    elif normalized_w in anaph_adv and tok.pos in ["AB"]:
        if "anaphora-AB" in anaphora_types_to_check:
            context_indep = check_anaphora_AB(tok, sent_match, time_adv_antecedent)
    return context_indep