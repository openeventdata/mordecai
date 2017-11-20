import json
import numpy as np
import jsonlines
from pandas import DataFrame
import os
import re
import keras
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation
from keras.optimizers import SGD
from collections import Counter
import sklearn
import pandas as pd

import spacy
nlp = spacy.load('en_core_web_lg', parser=False)

from mordecai import geoparse

geo = geoparse.Geoparse(verbose = True)

def entry_to_matrix(prodigy_entry):
    """
    Take in a line from the labeled json and return a vector of labels and a matrix of features
    for training.

    Two ways to get 0s:
        - marked as false by user
        - generated automatically from other entries when guess is correct

    Rather than iterating through entities, just get the number of the correct entity directly.
    Then get one or two GPEs before and after.
    """
    doc = prodigy_entry['text']
    doc = nlp(doc)
    geo_proced = geo.process_text(doc, require_maj=False)

    # find the geoproced entity that matches the Prodigy entry
    ent_text = np.asarray([gp['word'] for gp in geo_proced]) # get mask for correct ent
    #print(ent_text)
    match = ent_text == entry['meta']['word']
    #print("match: ", match)
    anti_match = np.abs(match - 1)
    #print("Anti-match ", anti_match)
    match_position = match.argmax()

    geo_proc = geo_proced[match_position]

    iso = geo.cts[prodigy_entry['label']] # convert country text label to ISO
    feat = geo.features_to_matrix(geo_proc)
    answer_x = feat['matrix']
    label = np.asarray(feat['labels'])

    if prodigy_entry['answer'] == "accept":
        answer_binary = label == iso
        answer_binary = answer_binary.astype('int')
        #print(answer_x.shape)
        #print(answer_binary.shape)


    elif prodigy_entry['answer'] == "reject":
        # all we know is that the label that was presented is wrong.
        # just return the corresponding row in the feature matrix,
        #   and force the label to be 0
        answer_binary = label == iso
        answer_x = answer_x[answer_binary,:] # just take the row corresponding to the answer
        answer_binary = np.asarray([0]) # set the outcome to 0 because reject

    # NEED TO SHARE LABELS ACROSS! THE CORRECT ONE MIGHT NOT EVEN APPEAR FOR ALL ENTITIES

    x = feat['matrix']
    other_x = x[anti_match,:]
    #print(other_x)
    #print(label[anti_match])
    # here, need to get the rows corresponding to the correct label

    #    print(geo_proc['meta'])
        # here's where we get the other place name features.
        # Need to:
        #  1. do features_to_matrix but use the label of the current entity
        #     to determine 0/1 in the feature matrix
        #  2. put them all into one big feature matrix,
        #  3. ...ordering by distance? And need to decide max entity length
        #  4. also include these distances as one of the features

    #print(answer_x.shape[0])
    #print(answer_binary.shape[0])
    try:
        if answer_x.shape[0] == answer_binary.shape[0]:
            return (answer_x, answer_binary)
    except:
        pass

    #return (answer_x, answer_binary)

            # If it's accept, convert the label of the correct one to 1, the others to 0, return all
            # If it's reject, convert the label of the presented one to 0, and DELETE the rows in the
            #   matrix/vector. If the presented one is false, we don't know if the other, non-presented
            #   ones were correct or not.

            # return the text labels, too, so we can look at per-country accuracy later.

    #    feat_list.append(feat)

error_count = 0
with jsonlines.open('geo_annotated/geo_country_db.jsonl') as reader:
    X = []
    Y = []
    for obj in reader:
        if obj['answer'] != 'ignore':
            try:
                x, label = entry_to_matrix(obj) # change to return matrices/vectors
                X.append(x)
                Y.append(label)
            except Exception as e:
                error_count += 1
                pass

print(error_count)

# format numpy
Y = np.hstack(Y)
Y = np.asarray(Y).astype(int)

X = np.vstack(X)
X_df = DataFrame(X)

# train/test split
msk = np.random.rand(len(X_df)) < 0.7
X_train = X_df[msk].as_matrix()
X_test = X_df[~msk].as_matrix()
y_train = Y[msk]
y_test = Y[~msk]


model = Sequential()
model.add(Dense(512, activation='relu', input_dim=X_train.shape[1]))
model.add(Dropout(0.5))
model.add(Dense(512, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(512, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(1, activation='sigmoid'))

#sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
model.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])

model.fit(X_train, y_train,
          epochs=15,
          batch_size=128)

score = model.evaluate(X_test, y_test, batch_size=12)
print(score)

y_predicted = model.predict(X_test)

print(sklearn.metrics.classification_report(y_pred = y_predicted>0.5, y_true = y_test))

model.save("country_model_updated_script.h5")

