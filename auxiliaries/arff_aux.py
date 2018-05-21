import codecs
import random
import arff
from dset_proc_aux import cefr_scale

def correct_arff(arff_file, labels):
    """
    Corrects the nominal category definition of the output label
    in an arff file created with the arff package.
    Args:
      labels: output labels as a string enclosed in curly brackets
              e.g. '{lab1, lab2, lab3}'
    """
    with open(arff_file) as f:
        arff_data = f.readlines()
    new_arff = []
    for i,line in enumerate(arff_data):
        if line[0] == "@":
            line_items = line.split(" ")
            if len(line_items) > 1:
                if line_items[1] == "level":
                    line_to_change = i
                    new_line = line_items[0] +" "+ line_items[1] + " " + labels + "\n"
                    new_arff.append(new_line)
                else:
                    new_arff.append(line)
            else:
                new_arff.append(line)
        else:
            new_arff.append(line)

    updated_arff = "".join(new_arff)
    with open(arff_file,"w") as f:
        f.write(updated_arff)

def sk_to_arff(data_file, target_file, arff_file, analysis_level, 
               feature_n_file,num_label,arff_labels):
    """Transforms feature values from 'data_file' and 'target_file' to arff format 
    usable in Weka using the arff package (http://code.google.com/p/arff/downloads/list)
    and writes the result to 'arff_file'.

    Args:
      data_file:    file containing the extracted feature values for each instance
      target_file:  file containing the output label for each instance
      arff_file:    the name of the file where to save the arff formatted result
      analysis_level:   'sent' or 'text' depending on the level of the readability analysis
      feature_n_file:   a .txt file with  the name of each feature
      num_label (bool): 'True' for numerical labels (usable for regression)
                        'False' for categorical labels (A1,A2 etc., for classification)     
      arff_labels (str): categorical labels to use in the .arff file 
    """
    with open(feature_n_file) as f:
        fn_str = f.read()
    feature_names = fn_str.split("\n")
    feature_names.append("level") # level in the same file if arff format
    new_data = []
    with open(data_file) as data_f:
        data = [l for l in data_f]
    labels = []
    with open(target_file) as target_f:
        target_f = codecs.open(target_file)
        for l in target_f: #change type in file manually to {A1, A2, B1, B2 C1} to get nominal values
            lbl = l.strip("\n")
            if num_label:
                labels.append(cefr_scale[lbl])       #for the integer equivalent
            else:
                labels.append(lbl)
    for i, line in enumerate(data):
        #id_nb = i+1
        new_line_floats = []
        for fv in line.split(" "):
            new_line_floats.append(float(fv))
        #new_line_floats.insert(0,id_nb)        #to add IDs
        new_line_floats.append(labels[i])
        new_data.append(new_line_floats)
    #print "Nr of features: ", len(new_data[0])
    #header = new_data[0]
    random.shuffle(new_data)
    arff.dump(arff_file, new_data, relation='readability', names=feature_names)
    
    if not num_label:
        correct_arff(arff_file, arff_labels)

def sk_to_arff_loadless(feature_names, data):
    #feature names including level
    arff_data = [feature_names]


