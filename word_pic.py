# -*- coding: utf-8 -*-

import codecs
from kelly import process_csv, get_svalex_info
from call_korp import call_korp

def collect_lex_items(lexical_resources, target_tags):
    """
    Collects items from the provided lexical resoures with the
    specified target POS tags. Duplicates are removed, POS tags
    are normalized to the same (Korp pipeline) tags  
    """
    tag_mapping = {"noun":"NN", "verb":"VB"}
    items = []
    for lex_res in lexical_resources.keys():
        for row in lexical_resources[lex_res]:
            for tag in target_tags[lex_res]:
                if lex_res == "kelly":
                    if row["Word classes"] == tag:
                        new_line = [row["Swedish items for translation"].split("(")[0].strip(" "),
                                    tag_mapping[tag], lex_res]
                        if new_line not in items:
                            items.append(new_line)
                elif lex_res == "svalex":
                    if row["tag"][:2] == tag:
                        new_line = [row["word"], tag, lex_res]
                        lemma_pos = [itm[:2] for itm in items]
                        if new_line[:2] not in lemma_pos:
                            items.append(new_line)
                        else:
                            dupl_ind = lemma_pos.index(new_line[:2])
                            if items[dupl_ind][2] != lex_res:
                                items[dupl_ind][2] += "," + lex_res
    result = ["\t".join(el) for el in items]
    return result

def save_lex_items(filename, location, content_to_save):
    with codecs.open(location + filename, "w", "utf-8") as f:
        f.write("\n".join(content_to_save))

def load_lex_items(filename, location):
    with codecs.open(location + filename, "r", "utf-8") as f:
        return f.readlines()

def add_f_content(filename, location, line):
    with codecs.open(location + filename, "a", "utf-8") as f:
        f.write(line)

def get_word_pic(query_word, corpora):
    clist = ','.join(corpora)
    return call_korp({"command": "relations",
                      "word" : query_word, #e.g. ge..vb.1, ta_upp..vbm.1
                      "type" : "lemgram",
                      "corpus":clist})

def save_word_pics(kelly_svalex, corpora, filename, location):
    """
    kelly_svalex: the list of items loaded from a file
    """
    result = {}
    add_f_content(filename, location, "lemma\tPOS\tsource\tdep_rel\trel_type\trel_lemma\trel_POS\tMI\n")
    for ll in kelly_svalex[8000:]: #use slices at a time
        lemma,pos,source = tuple(ll.split("\t"))
        if "_" in lemma:    #multiword expressions
            query_word = lemma + ".." + pos.lower() +"m.1"
        else:
            query_word = lemma + ".." + pos.lower() +".1"
        print "QUERY: ", query_word.encode("utf-8")
        try:
            word_pic_info = get_word_pic(query_word.encode("utf-8"), corpora)["relations"]
            for rel in word_pic_info:
                relation = rel["rel"]
                mi = rel["mi"]
                if mi > 50 and relation in ["SS", "OBJ", "AT"]:
                    if rel["dep"] == query_word:
                        rel_lemma = rel["head"]
                        rel_type = "has head"   #associated lemma is head of query word
                        rel_POS = rel["headpos"]
                    else:
                        rel_lemma = rel["dep"]
                        rel_type = "has dep"
                        rel_POS = rel["deppos"]
                    if relation == "OBJ":
                        relation = "OO" #also other obj relations?
                    rel_info = [lemma,pos,source.strip("\n"),relation,rel_type,rel_lemma,rel_POS,str(mi)]
                    #print rel_info
                    #filter dublicate information
                    if not result.has_key((rel_lemma,lemma,rel_type)):
                        result[(lemma,rel_lemma,rel_type)] = rel_info
                        rel_info_line = "\t".join(rel_info) + "\n"
                        #print rel_info_line.encode("utf-8")
                        add_f_content(filename, location, rel_info_line)

        except KeyError:
            pass
    return result

def load_word_pics(word_pics_file, location):
    """
    Output: (lemma, POS):  [{"lemma":"xxx", ... "rel_lemma":"yyy"}, {...}]
    """
    with codecs.open(location + word_pics_file, "r", "utf-8") as f:
        lines = f.readlines()
    word_pics = {}
    keys = lines[0].split("\t")
    for line in lines[1:]:
        line_els = line.split("\t")
        line_obj = {}
        for i,el in enumerate(line_els):
            line_obj[keys[i].strip("\n")] = el.strip("\n") #e.g. {"lemma":"vara", "pos":"VB", ... "MI": "123.45"}
        lemma,pos = line_els[0], line_els[1]
        if (lemma,pos) in word_pics:
            word_pics[(lemma,pos)].append(line_obj)
        else:
            word_pics[(lemma,pos)] = [line_obj]
    return word_pics

def get_mutual_info(token, all_tokens, stats, word_pictures):
    mi_score = 0.0
    used_rel_lemma = ""
    if token.pos in ["NN","VB"] and token.lemma:
        for lemma_pos, wps in word_pictures.items():
            if lemma_pos == (token.lemma[0],token.pos): #TO DO: check all lemmas not just [0]?
                for wp in wps:
                    is_lemgram = True
                    rel_item = wp["rel_lemma"].split(".")
                    if len(rel_item) < 2:       # wordforms (non lemmatized tokens): 'pågatåg'
                        is_lemgram = False
                    rel_lemma = wp["rel_lemma"] # lemgram ('lex') e.g. roll..n.1
                    
                    #token as dependent
                    if wp["rel_type"] == "has head" and wp["dep_rel"] == token.deprel:
                        head = all_tokens[int(token.depheadid)-1]
                        if is_lemgram and head.lex:
                            if rel_lemma == head.lex[0] and (rel_item[0],wp["rel_POS"]) not in stats["used_rel_lemmas"]: #and wp["rel_POS"] == head.pos
                                #print rel_lemma.encode("utf-8") + " (dep - l)"
                                mi_score = float(wp["MI"])
                                used_rel_lemma = (rel_item[0], wp["rel_POS"])
                            elif head.suffix:
                                if rel_lemma == head.suffix[0] and (rel_item[0],wp["rel_POS"]) not in stats["used_rel_lemmas"]: #and wp["rel_POS"] == head.pos
                                    #print rel_lemma.encode("utf-8") + " (dep - l - suffix)"
                                    mi_score = float(wp["MI"])
                                    used_rel_lemma = (rel_item[0], wp["rel_POS"])
                        elif rel_lemma == head.word and wp["rel_POS"] == head.pos:
                                #print rel_lemma.encode("utf-8") + " (dep - wf)"
                                mi_score = float(wp["MI"])
                    
                    #token as head
                    if wp["rel_type"] == "has dep":
                        if "heads" in stats:
                            for h, deps in stats["heads"].items(): #dict not list {"head_ref": [list of child nodes]}
                                if h == token.ref:
                                    for d in deps:
                                        if d.deprel == wp["dep_rel"]:
                                            if is_lemgram and d.lemma and d.lex:
                                                #print d.lemma[0].encode("utf-8"), d.deprel, d.pos, rel_lemma.encode("utf-8")
                                                if d.lex[0] == rel_lemma and (rel_item[0],wp["rel_POS"]) not in stats["used_rel_lemmas"]:
                                                    mi_score = float(wp["MI"])
                                                    used_rel_lemma = (rel_item[0], wp["rel_POS"])
                                                    #print "\t", rel_lemma.encode("utf-8") + " (head - l)"
                                                elif d.suffix:
                                                    #print d.suffix
                                                    if d.suffix[0] == rel_lemma and (rel_item[0],wp["rel_POS"]) not in stats["used_rel_lemmas"]:
                                                        #print "\t", rel_lemma.encode("utf-8") + " (head - l - suffix)"
                                                        mi_score = float(wp["MI"])
                                                        used_rel_lemma = (rel_item[0], wp["rel_POS"])
                                            elif d.word == rel_lemma and d.pos == wp["rel_POS"]:
                                                mi_score = float(wp["MI"])
                                                used_rel_lemma = (rel_lemma, wp["POS"])
                                                #print rel_lemma.encode("utf-8") + " (head - wf)"

    return (mi_score,used_rel_lemma) #TO DO: check why MI for different senses are still repeated



#------------ function calls --------------------

# #1. Create Kelly-SVALex list of nouns and verbs 
# kelly = process_csv("/media/phd/DEVELOPMENT/rdby_exp/scripts/kelly_sv.csv")
# svalex = process_csv("/media/phd/DEVELOPMENT/rdby_exp/scripts/SVALex_final.csv")
# lexical_resources = {"kelly": kelly, "svalex": svalex}
# target_tags = {"kelly": ["noun", "verb"], "svalex": ["NN", "VB"]}
# #l = collect_lex_items(lexical_resources, target_tags)
filename = "kelly_svalex_NN_VB.txt"
location = "/media/phd/DEVELOPMENT/rdby_exp/scripts/auxiliaries/"
# #save_lex_items(filename, location, l)

wp_file = "word_pics.csv"
# #add_f_content(wp_file, location, "YEYY")

# query_word = "ge..vb.1"
wp_corpora = ["rom99,bloggmix2014,gp2013,attasidor,lasbart,suc3,wikipedia-sv,talbanken"]
# aspects for selection: a variety of genres, manually annotated, recent for up-to-date language
# easy-to-read texts for finding more common patterns 
#wp = get_word_pic(query_word, corpora)
#print wp["relations"][0]["head"]

##kelly_svalex = load_lex_items(filename, location)
#for l in kelly_svalex[:10]:
#   print l.encode("utf-8")
### r = save_word_pics(kelly_svalex,wp_corpora, wp_file, location)

#wps = load_word_pics(wp_file, location)
#for k,v in wps.items():
#    if k[0] == "vara":
#        print k[0].encode("utf-8"), v