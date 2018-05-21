import codecs
from sent_features import SentFeatures    
from weka.core.dataset import Instance, Instances, Attribute

# TO DO: create a CEFR_Classifier() with:
    # extract_features  (=SentenceFeature)
    # build dataset - support both WEKA and sklearn?
    # predict           (=classify_level())

def classify_level(sent, classifier, stats, params={}, match={}):
    """
    Classifies the CEFR level of 'sent'.
    2016 june - based on check_readability() in sent_match.py
    @ sent:     
    @ stats:    SentStatistics instance
    @ params:   parameters for SentMatch (HitEx)
    @ match:    SentMatch instance
    # TO DO: add argument for choosing bw WEKA and sklearn
             adapt to both sents and texts
             in- vs cross-domain setups 
    """
    sent_feats = SentFeatures(sent, stats, params)
    fs = sent_feats.features
    feature_names = fs.keys()
    # set the order of training attributes for values
    with codecs.open("auxiliaries/feature_names.txt") as f:
        train_fn = [l.strip("\n") for l in f.readlines()]
    f_list = [fs[tfn] for tfn in train_fn]

    # create Instance, attributes and a dummy dataset (required for prediction)
    inst = Instance.create_instance(f_list)
    attributes = []
    for feat_n in train_fn:
        attributes.append(Attribute.create_numeric(feat_n))
    attributes.append(Attribute.create_nominal("level", ["A1", "A2", "B1", "B2", "C1"]))
    dataset = Instances.create_instances("readability", attributes, 0)
    dataset.add_instance(inst)
    dataset.class_is_last()

    # make prediction
    cefr_mapping = {"A1":1.0, "A2":2.0, "B1":3.0, "B2":4.0, "C1":5.0}
    trg_cefr_fl = cefr_mapping[params["target_cefr"]]
    for instance in dataset:
        pred = classifier.classify_instance(instance)
        pred_cefr =  pred+1
        #if pred_cefr < 1 or pred_cefr > 5:
        level_diff = pred_cefr - trg_cefr_fl     # negative value = easier than target
        nominal_level = [k for k,v in cefr_mapping.items() if v == pred_cefr][0]
            
    return (level_diff, nominal_level, fs) #return also fs -> for detailed info in webservice