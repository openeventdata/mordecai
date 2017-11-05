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
    """
    doc = prodigy_entry['text']
    doc = nlp(doc)
    geo_proced = geo.process_text(doc, require_maj=False)
    for geo_proc in geo_proced:
        if geo_proc['word'] == prodigy_entry['meta']['word']:
            #doc = nlp(doc)
            iso = geo.cts[prodigy_entry['label']] # convert country text label to ISO
            feat = geo.entry_for_prediction(geo_proc)
            x = feat['matrix']
            label = np.asarray(feat['labels'])

            if prodigy_entry['answer'] == "accept":
                binary = label == iso
                binary = binary.astype('int')
                #print(x.shape)
                #print(binary.shape)


            elif prodigy_entry['answer'] == "reject":
                # all we know is that the label that was presented is wrong.
                # just return the corresponding row in the feature matrix,
                #   and force the label to be 0
                binary = label == iso
                x = x[binary,:]
                binary = np.asarray([0])
        else:
            # here's where we get the other place name features.
            # Need to:
            #  1. do entry_for_prediction but use the label of the current entity
            #     to determine 0/1 in the feature matrix
            #  2. put them all into one big feature matrix,
            #  3. ...ordering by distance? And need to decide max entity length
            #  4. also include these distances as one of the features
            pass

            try:
                if x.shape[0] == binary.shape[0]:
                    return (x, binary)
            except:
                pass

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

