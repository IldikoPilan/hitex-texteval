import re
import codecs
from dset_proc_aux import *

def is_keyword_within_position(kw, target_edge, proportion):
    #Get target_edge (start/end) and proportion (0.1-0.9) from UI of experiment with parameters
    #eg. "start" 0.2 -> keyword in first 20% of the sentence 
    try:
        position = float(kw.match.start) / kw.sentence.length
    except AttributeError:
         return True
    if target_edge == "start":
        if position <= proportion:
            return True
        else:
            return False
    elif target_edge == "end":
        if position >= 1-proportion:
            return True
        else:
            return False
    else:
        print "Invalid target-edge value"    

def out_of_length_range(sent_len, min_len, max_len):
    #Exclude some frequent puctuation marks from the word count -> maybe not necessary
    #cleaned_sent = re.split('[,.\s]', sent) #improve pattern?
    #words = [w for w in cleaned_sent if len(w) > 0] # char level!
    if min_len <= sent_len <= max_len:
        return False
    else:
        return True

def add_keyword_info(sent_match): #t, stats, params,
    for t in sent_match.stats["tokens"]:  
        if int(t.ref) == sent_match.kwic.match.end:
            #print int(t.ref), sent_match.kwic.match.end
            sent_match.stats["keyword"]["word"] = t.word
            sent_match.stats["keyword"]["lemma"] = t.lemma
            sent_match.stats["keyword"]["msd"] = t.msd
            sent_match.stats["keyword"]["pos"] = t.pos
            sent_match.stats["keyword"]["lex"] = t.lex 
            sent_match.stats["keyword"]["saldo"] = t.saldo
            sent_match.stats["keyword"]["ref"] = t.ref
            sent_match.stats["keyword"]["deprel"] = t.deprel 

def split_keyword_context(sent_match):
    try:
        ref = int(sent_match.stats["keyword"]["ref"])
    except KeyError: #AttributeError
        ref = 1 #int(sent_match.stats["keyword"]["ref"])
    sent_match.sent_left = " ".join(sent_match.sent.words.split(" ")[:ref-1]) #sent_match.sent.words.split(" ")[ref:]
    sent_match.sent_right = " ".join(sent_match.sent.words.split(" ")[ref:])
        

def load_list(path_to_list, delimiter="\t"):
    """
    Loads a list from a file and returns a nested list of its lines, the items
    of each line being split along the specified delimiter with the new line
    character removed from the end of each line.
    Args:
        path_to_list: path of the file to open 
        delimiter:  the character used to separate the items on a line
    """
    with codecs.open(path_to_list) as f:
        opened = f.readlines()
    item_list =[]
    for line in opened:
        if line[0] != "#":
            l_lst = line.split(delimiter)
            item_list.append([el.strip("\n") for el in l_lst])
    return item_list