import os
import random
import codecs
import numpy as np
import cPickle as pickle
from auxiliaries.dset_proc_aux import *
from sent_statistics import SentStatistics
from sent_features import SentFeatures
from auxiliaries.arff_aux import sk_to_arff, correct_arff
from korp_classes import match, structs, kwic

class Dataset:
    """
    A container for Text or Sentence objects collected from a corpus.

    Attributes:
      analysis_level (str): 'text' or 'sent' (see ItemCollector class)
      dset_type (str):      e.g. 'all' (see ItemCollector class)
      self.dset_path        path where dataset will be saved
      items (list):         the list of Text or Sentence objects
      nr_items_detailed (int): nr of items per level and source in dataset
      nr_items (int): 
      nr_tokens (int): for sentence-level data -> nr of tokens in dataset
                          for text-level data     -> nr of sentences in dataset
      info (str):        quantitative information about the dataset
      stats_objects:    nested list of dicts, a container for statistics info 

    Args:
      analysis_level (str): see above
      dset_type (str):      see above
    """ 
    def __init__(self, path, analysis_level, dset_type):    
        self.dset_path = path #e.g. ...dataset/sent/all/
        self.analysis_level = analysis_level
        self.dset_type = dset_type

    def get_set(self, collector, collected_items=[]):
        """
        Collects Text or Sentence objects from a corpus using an ItemCollector
        if no collected_items are provided.
        The order of items is randomized (not ordered per level or source 
        of origin). Already collected items can also be passed, then only
        class attributes are created.

        Args:
          collector (class): an ItemCollector (or its inherited) class
          collected_items (): a list of Sentence objects
        """
        if collected_items:
            #dset = collected_items
            items_per_source_per_level = {"unknown" : {"Korp" : collected_items}}
        else:
            items_per_source_per_level = collector.collect_items() #collector
        
        #create a dataset from items
        items_per_level = {}
        nr_items_per_source_per_level = {}
        for cefr_lvl, sources in items_per_source_per_level.items():
            if cefr_lvl != "C2":
                items_per_level[cefr_lvl] = [itm for source,itms in
                  items_per_source_per_level[cefr_lvl].items() for itm in itms]
                nr_items_per_source_per_level[cefr_lvl] = {
                  source: len(itms) for source,itms in 
                  items_per_source_per_level[cefr_lvl].items()}
        dset = [itm for itm_lst in items_per_level.values() for itm in itm_lst]
        #random.shuffle(dset)

        #Create class attributes
        self.items = dset
        self.nr_items = len(self.items)
        try:
            self.nr_tokens = {}
            self.nr_tokens_per_level = {}
            for level,items in items_per_level.items():
                self.nr_tokens_per_level[level] = 0
                for item in items:
                    self.nr_tokens_per_level[level] += item.length_in_tokens
                    self.nr_tokens = item.length    # in nr sentences
        except AttributeError:
            self.nr_tokens = sum([sent.length for sent in self.items])
            self.nr_tokens_per_level = {} #TO DO
        self.nr_items_detailed =  nr_items_per_source_per_level
        self.info = {"Item amount": self.dset_type, 
                    "Type of items": self.analysis_level,
                    "Nr instances": self.nr_items,
                    "Nr tokens": self.nr_tokens,
                    "Nr tokens per level": self.nr_tokens_per_level,
                    "Nr of items per level": self.nr_items_detailed}
        return self.items

    def __getitem__(self, i):
        return self.items[i]

    def print_info(self):
        """Prints quantitative information about the dataset"""
        print
        print "--- Dataset information ---"
        for k, v in self.info.items():
            print "%s: \t" % k,
            if type(v) == dict:
                print "\n"
                for k2,v2 in v.items():
                    print "%s: \t" % k2
                    if type(v2) == int:
                        print v2
                    else:
                        for k3,v3 in v2.items():
                            try:
                                print "\t" + k3,"\t",v3
                            except:
                                pass

            else:
                print v

    def save_set(self,dset_file):
        """Saves the dataset to a file. It creates a directory equivalent 
        to the value of 'self.analysis_level' with a subfolder equivalent 
        to 'self.dset_type'.

        Arg:
          dset_file (str): file name (.pkl) in which to save the items 
        """
        if not os.path.exists(self.dset_path+self.analysis_level):
            os.mkdir(self.dset_path+self.analysis_level)
        if not os.path.exists(self.dset_path+self.analysis_level+"/"+self.dset_type):
            os.mkdir(self.dset_path+self.analysis_level+"/"+self.dset_type)
        os.chdir(self.dset_path+self.analysis_level+"/"+self.dset_type+"/")
        
        with open(dset_file, "wb") as f:
            pickle.dump(self, f)

        #TO DO: return split sets: test and train data for lg model features
        #add args: test_set_file="", split=20 (% of split for test)
        #use separate script to create lg models
        #use the models in extract_features


    def load_set(self,dset_file):
        """Loads the dataset. The attributes and methods of the pickled 
        objects will be all functional.
        
        Arg:
          dset_file (str): file name (.pkl) in which items are saved
        """
        os.chdir(self.dset_path+self.analysis_level+"/"+self.dset_type+"/")
        with open(dset_file, "rb") as f:
            dset = pickle.load(f)
        return dset

    def get_statistics(self, kelly_list, svalex_list, svalex2_list, parameters={}, wordlists={}):
        self.stats_objects = []
        for item in self.items:
            if self.analysis_level in ["sent", "indep_sent"]:
                statistics = SentStatistics(item, parameters).get_stats_SWE(kelly_list, svalex_list, svalex2_list, wordlists["word_pictures"])
                self.stats_objects.append(statistics)
            elif self.analysis_level == "text" or self.analysis_level == "single_text":
                stats_per_sent = []
                for sent_item in item.sents:
                    statistics = SentStatistics(sent_item).get_stats_SWE(kelly_list, svalex_list, svalex2_list)
                    stats_per_sent.append(statistics)
                self.stats_objects.append(stats_per_sent)

    def extract_features(self, num_label=False, arff_labels="{A1, A2, B1, B2, C1}",
                         save_info=True, with_relevance=False, parameters={}):
        """
        Extracts features for all items in a dataset. For text level datasets
        values are averaged over all sentences in the text. The information
        can be saved into files using the 'save_info' argument. The file 
        types include:
        .data file:     feature values per instance (usable in sklearn);
        .target file:   output labels to predict (usable in sklearn);
        .txt files:     the actual sentences and feature names.
        
        Args:
          kelly_list (list): the loaded Kelly list (see kelly.py)
          modal_verb_list (list): verbs usable as modal (auxiliary) verbs
          num_label (bool): 'True' for numerical labels
                            'False' for categorical labels (A1,A2 etc.), 
          arff_labels (str): categorical labels to use in the .arff file 
          save_info (bool): whether to save information to files
          with_relevance (bool): for SentMatch, whether to use GDEX ranking 
                                 before feature extraction

        Returns:
          a nested list of sorted (float) feature values for the whole dataset 
        """
        #dset_items = self.load_set(dset_file)
        features_data = []  # feature values transformed into a string for each instance
        feature_values = [] # feature values as floats - used when not saved to file
        saved_sents = ""
        saved_sent_list = []
        labels = []
        count = 1
        nr_items_per_level = {k:0 for k, v in cefr_scale.items()}
        
        for i,item in enumerate(self.items):
            if self.analysis_level in ["sent", "indep_sent"]:
                sent = item.words
                #if 3 < item.length < 35:          # to control length of sents to include
                #if not (sent in saved_sent_list): # to remove duplicate items
                saved_sent_list.append(sent)
                #print "Extracting features for item nr. %d" % count
                #print sent
                sent_feats = SentFeatures(item, self.stats_objects[i], parameters)
                fs = sent_feats.features
                feature_values.append([fs[fn] for fn in sorted(fs)]) 
                if save_info:
                    f_list = [(fn, fs[fn]) for fn in fs.keys()]
                    feature_n, f_row = feat_info_to_str(f_list, add_id=False)
                    features_data.append(f_row)
                if item.level not in ["context_dep", "context_indep"]:
                    nr_items_per_level[item.level] += 1
                labels.append(item.level)
                
                try:
                   saved_sents += "%d\t%s\t%s\t%s\t%s\t%s\n" % (count, 
                       item.level, sent, item.text_id, item.sent_id, item.sources)
                except AttributeError:
                   saved_sents += "%d\t%s\t%s\t%s\t%s\n" % (count, 
                        item.level, sent, item.sent_id, "unknown")

            elif self.analysis_level == "text" or self.analysis_level == "single_text":
                #TEXT LEVEL ADAPTATION - averaging all sent. level values
                text = []
                saved_sent_list.append(item)
                #print "Extracting features for item nr. %d" % count
                all_sent_f_list = {}
                text_len_tkns = 0
                stats_per_sent = []
                for j, sent_item in enumerate(item.sents):
                    text_len_tkns += sent_item.length
                    text.append(sent_item.words)
                    #print sent_item.words
                    sent_feats = SentFeatures(sent_item, self.stats_objects[i][j], {})
                    fs = sent_feats.features
                    #summing sent. values
                    for kk, vv in fs.items(): #sort
                        put_feature_value(all_sent_f_list, kk, vv)
                
                #taking the average
                f_list_text = [(fn2, all_sent_f_list[fn2]/float(len(text))) 
                               for fn2 in sorted(all_sent_f_list)]
                feature_values.append([fval for fname, fval in f_list_text])
                
                feature_n, f_row = feat_info_to_str(f_list_text, add_id=False)
                features_data.append(f_row)
                nr_items_per_level[item.level] += 1
                labels.append(item.level)
                text_str = " ".join(text)
                saved_sents += "%d\t%s\t%s\t%s\t%s\n" % (count, item.level, 
                          text_str.decode("utf-8"), item.text_id, item.sources)
            
            else:
                print "unmatched analysis level: ", self.analysis_level
            count += 1

        #for lvl,nr in nr_items_per_level.items():
        #   print "Nb of %s items: %d" % (lvl, nr)
        #print "Size of whole dataset: %d" % (count-1)

        if save_info:
            self.dset_path = self.dset_path+self.analysis_level+"/"+ self.dset_type+"/"
            data_file_n = self.dset_path+self.analysis_level+"_rdby.data"
            target_file_n = self.dset_path+self.analysis_level+"_rdby.target"
            feat_file_n = self.dset_path+self.analysis_level+"_feature_names.txt"
            sents_file_n = self.dset_path+self.analysis_level+"_rdby_sents.txt"
            arff_file_n = self.dset_path+self.analysis_level+'_rdby_features.arff'
            
            with codecs.open(data_file_n, "w", "utf-8") as dataf:
                dataf.write("\n".join(features_data))

            with codecs.open(target_file_n, "w", "utf-8") as targetf:
                targetf.write("\n".join(labels))
            
            with codecs.open(sents_file_n, "w", "utf-8") as f:
                try:
                    f.write(saved_sents.decode("utf-8"))
                except UnicodeEncodeError:
                    f.write(saved_sents)

            with codecs.open(feat_file_n, "w", "utf-8") as fn_f:
                fn_f.write("\n".join(feature_n))

            sk_to_arff(data_file_n, target_file_n, arff_file_n, 
                       self.analysis_level, feat_file_n, 
                       num_label, arff_labels)

        return np.array(feature_values)
