import os
import xml.etree.ElementTree as ET
from ling_units import Sentence, Text
from auxiliaries.dset_prep_aux import find_buggy_sent, get_label

class ItemCollector:
    """
    A collector of items: either Text instances containing Sentence instances 
    or a list of Sentence instances (if 'analysis_level' set to 'sent'). 
    For the latter, text-level information (e.g. level) is propagated 
    to each sentence and sentences with potential bugs are filtered. 
    Items are collected from XML files located in 'path'.

    Args:
      path (str):  absolute path to data file(s) (Krop XML files with 
                   linguistic annotation)
      analysis_level (str): type of linguistic unit of items
                    'sent'   scrambled sentences 
                    'text'   texts
      dset_type (str): use all available items or balance nr items
                'all'           all available texts / sentences will be included
                'balanced'      the same amount of texts / sentences per
                                book and per level
                'balanced-min-per-level'  takes the amount of items equivalent
                                          to the min number of items per book 
                                          per ONE level (for the level that 
                                          doesn't have enough items, copies are made)   
                'balanced-limited-INT' a specific number of texts / sentences 
                                       per book and level included equal to 
                                       'int' (copies are made if necessary 
                                       to arrive to the required amount)
      files (list): list of file names to use during collection
      genre (str):  the genre of the data if any         

    Attributes:
      path (str):           see above
      files (list):         see above
      genre (str):          see above    
      analysis_level (str): see above
      dset_type (str):      see above
      items (list):         list of collected items
      buggy_sents (list):   list of sentences filtered out with potential bugs  

    """
    def __init__(self, path_to_data, analysis_level="text", 
                 dset_type="all", files=[], genre="", level=""):
        self.path = path_to_data
        self.analysis_level = analysis_level
        self.dset_type = dset_type
        self.files = files
        self.genre = genre
        self.items = []
        self.level = level

    def standard_collect(self):
        """
        Collects items (texts or sentences) from an XML file with 
        linguistic annotation produced with the Korp pipeline. The 
        XML file is supposed to have a root tag (e.g. <corpus>) 
        containing <text> elements. Returns a list of Text or 
        Sentence objects.
        """

        items_per_source_per_level = {}
        for korp_xml in self.files:
            if self.level:
                label = self.level
            else:
                label = "B1"
                #label = get_label(korp_xml) # change
            if items_per_source_per_level.get(label, {}):
                #if more than one file contains items of the same level 
                pass
            else:
                items_per_source_per_level[label] = {}
            try:    
                tree = ET.parse(self.path + korp_xml) # XML in file
                root = tree.getroot() #<corpus>
            except IOError:
                root = ET.fromstring(korp_xml)[1] # XML as string
                
            for element in root:
                if element.tag == "text" or self.analysis_level == "single_text":
                    text = element
                    try:
                        source_name = text.attrib["source"]
                    except KeyError:
                        source_name = "unknown"
                    text_genre = self.genre
                    text_obj = Text(text, source_name, label, text_genre)
                    if items_per_source_per_level[label].has_key(source_name):
                        items_per_source_per_level[label][source_name].append(text_obj)
                    else:
                        items_per_source_per_level[label][source_name] = [text_obj]
                elif element.tag == "paragraph" and "sent" in analysis_level:
                    for sent in element:
                        if label in ["context_dep", "context_indep"]:
                            sent_obj = Sentence(sent, level=label)
                        else:
                            sent_obj = Sentence(sent)
                        source_name = korp_xml.split("_")[0]
                        sent_obj.words = sent_obj.words.decode("utf-8") # Added aug 6 - check compatibility
                        if len(sent_obj.nodes) > 3:
                            if items_per_source_per_level[label].has_key(source_name):
                                items_per_source_per_level[label][source_name].append(sent_obj)
                            else:
                                items_per_source_per_level[label][source_name] = [sent_obj]
                        else:
                            "filtered sent: ", sent_obj.words.encode("utf-8")
                else:
                    print "XML tag '%s' not recognized by the Collector" % element.tag
        return items_per_source_per_level #{'level': {'source': [Text1, Text2]}}
        

    def balance_items(self, items_per_book_per_level):
        """
        Balances the number of items collected per level and / or book.  
        """
        del items_per_book_per_level["C2"]
        mins_per_level = {}   # minimum amount of items per level
        for level3,books3 in items_per_book_per_level.items():
            mins_per_level[level3] = sorted(set([len(item_list) for book_name, item_list in books3.items()]))[0]          
        
        abs_min = min([mins for mins in mins_per_level.values()])
        for lv,m in mins_per_level.items():
            if m == abs_min:
                abs_min_lvl = lv # CEFR level with the fewest item per book per level

        limited_items = {}      # items per book per level
        amount_per_lvl = abs_min * len(items_per_book_per_level[abs_min_lvl])
        limits_b_l = {}
        for level2, items_per_book in items_per_book_per_level.items():
            nr_bk_l = len(items_per_book_per_level[level2])
            #choosing type of balancing
            if self.dset_type[:22] == "balanced-min-per-level":  # balanced as for items per level and nr items across levels        
                limits_b_l[level2] = []
                if self.dset_type[:28] == "balanced-min-per-level-limit":
                    limit_v = int(self.dset_type.split("-")[-1])
                    remainder = limit_v%nr_bk_l
                    limit_b = limit_v / nr_bk_l
                else:
                    remainder = amount_per_lvl%nr_bk_l
                    limit_b = amount_per_lvl / nr_bk_l
                for i in range(nr_bk_l):                 
                    limits_b_l[level2].append(limit_b)
                if remainder:
                    c = 0
                    for j in range(remainder):
                        if j < nr_bk_l-1:    
                            limits_b_l[level2][j] += 1
                        else:
                            limits_b_l[level2][c] += 1
                            c += 1

            else:
                if self.dset_type == "balanced-min-per-book": #balanced as for items per level, but not balanced across levels
                    limit = mins_per_level[level2]
                elif self.dset_type[:14] == "balanced-limit":
                    limit = int(self.dset_type.split("-")[-1])
                else: #absolute min - quite small only 11 texts...
                    limit = abs_min

                #inflate the nr of items for books that don't have enough items                 
                for book2, item2 in items_per_book.items():
                    if len(item2) < limit:
                        multipl_factor = limit / len(item2) + 1
                        items_per_book_per_level[level2][book2] = items_per_book_per_level[level2][book2] * multipl_factor
                
            if self.dset_type[:22] == "balanced-min-per-level":
                limited_items[level2] = {}
                for ii, (book, itms) in enumerate(items_per_book_per_level[level2].items()):
                    if len(itms) < limits_b_l[level2][ii]:
                        multipl_factor = limits_b_l[level2][ii] / len(itms) + 1
                        duplicated_itms = items_per_book_per_level[level2][book] * multipl_factor
                        limited_items[level2][book] = duplicated_itms[:limits_b_l[level2][ii]]
                    else:
                        limited_items[level2][book] = itms[:limits_b_l[level2][ii]]
            else:
                limited_items[level2] = {book: itms[:limit] for book, itms in items_per_book_per_level[level2].items()}
        #items_per_book_per_level = limited_items
        return limited_items

    def decompose_texts_into_sents(self, items_per_book_per_level):
        """
        Transforms Text objects into separate Sentence objects.
        Sentences are filtered for potential bugs.

        Yields:
          e.g. {"A1":[sent1, sent2 etc]}
        """ 
        print "Decomposing texts into sentences"   
        buggy_sents = []
        bug_count = 0
        sents_per_book_per_level = {}
        for lvl, bks in items_per_book_per_level.items():
            sents_per_book_per_level[lvl] = {}
            for bk, txts in bks.items():
                for txt in txts:
                    for s in txt.sents:
                        buggy_sent = find_buggy_sent(s)
                        if not buggy_sent:
                            #Propagating information from texts to sentences
                            setattr(s,"book", txt.book)
                            setattr(s,"level", txt.level)
                            setattr(s,"text_id", txt.text_id)
                            setattr(s,"text_genre", txt.text_genre)
                            setattr(s,"text_topic", txt.text_topic)
                            
                            #Adding sentences
                            if 3 <= s.length <= 35:
                                if sents_per_book_per_level[lvl].has_key(bk):
                                    sents_per_book_per_level[lvl][bk].append(s)
                                else:
                                    sents_per_book_per_level[lvl][bk] = [s]                       
                        else:
                            print "--bug found in '%s'" % s.words
                            bug_count += 1
                            buggy_sents.append(str(bug_count)+ ", "+ s.words + ", " + txt.book)
        #Saving filtered sentences (bugs)
        self.buggy_sents = buggy_sents
        with open("buggy_sents.txt", "w") as f:
            f.write("\n".join(buggy_sents))  

        print bug_count 
        
        return sents_per_book_per_level 

    def collect_items(self):
        """
        Collects the items, balances their number if needed.
        Texts may be decomposed in sentences if needed.  
        """
        #COLLECTING ITEMS
        items_per_book_per_level = self.standard_collect()
                                               
        #TRANSFORM TEXS INTO SENTS
        if self.analysis_level == "sent":
            items_per_book_per_level = self.decompose_texts_into_sents(items_per_book_per_level)

        #BALANCING:
        if self.dset_type[:8] == "balanced":
            items_per_book_per_level = self.balance_items(items_per_book_per_level)
        
        self.items = items_per_book_per_level

        return items_per_book_per_level