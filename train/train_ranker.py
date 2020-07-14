import plac
import mordecai
import random
import jsonlines
from tqdm import tqdm
import re
import numpy as np
import editdistance
import pandas as pd
import os
import json
import pickle

import keras
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation
from keras.optimizers import SGD
from keras.callbacks import EarlyStopping, ModelCheckpoint
import sklearn


geo = mordecai.Geoparser()
# Here's the format of the Prodigy labeled place picking data:
# ```
# {"text":"On July 15, state security services in Idleb arrested Mahmoud Barish, an opposition activist, for his dealings with the Damascus Declaration.",
# "spans":[{"start":39,"end":44}],
# "options":[
#   {"id":1,"text":"\"Idlib District\", a second-order administrative division in SYR, id: 169388"},
#   {"id":2,"text":"\"Idlib\", a seat of a first-order administrative division in SYR, id: 169389,
#   {"id":4,"text":"None/Other/Incorrect"}],
# "_input_hash":1212285619,"_task_hash":-1410881973,
# "accept":[2],
# "answer":"accept"}
# ```

def ingest_prodigy_ranks(filename):
    """
    Ingest Prodigy-labeled Mordecai data for place picking and produce training data
    for Keras.

    For each labeled example, match it to the output of Mordecai, and make sure there's an accepted answer
    from Prodigy.

    Parameters
    ----------
    filename: filepath, location of Prodigy data

    Returns
    -------
    X: list of matrices, Mordecai features.
      Each element in the list is a matrix of features for ranking (so 5 rows)
    Y: list of arrays of length 5, indicating correct location.
    """
    with jsonlines.open(filename) as reader:
        X = []
        Y = []
        i = 0
        accumulate = []
        for obj in reader:
            i = i+1
            if i % 250 == 0:
                print(i)
            # run the text through mordecai
            proced = geo.geoparse(obj['text'], verbose = True,)
            for proc in proced:
                # for each result, see if the spans overlap the labeled spans
                if proc['spans'][0]['start'] != obj['spans'][0]['start']:
                    # make sure we have the right entity
                    continue
                ent_word = proc['word']
                if not ent_word:
                    continue
                # if it all works, take the results.
                results = geo.query_geonames_country(ent_word, proc['country_predicted'])

            if obj['answer'] == 'accept':
                #start_char = obj['spans']['start']
                # get the geonames ids of the options
                geoids = [re.findall("id: (.+)", i['text']) for i in obj['options']]
                geoids = [i[0] for i in geoids if i]
                # get the correct of if any
                try:
                    correct = obj['accept'][0]
                    correct_id = str(geoids[correct - 1])
                except (KeyError, IndexError):
                    continue

            elif obj['answer'] != 'accept':
                correct_id = 4

            try:
                fl, meta = geo.features_for_rank(proc, results)
                # just look at the top 4 results by deterministic rule
                # This matches what went into the annotation task
                choices, sorted_meta, fl_subset = geo.format_for_prodigy(fl, meta, ent_word, return_feature_subset=True)
                result_ids = np.asarray([m['geonameid'] for m in sorted_meta])
                if obj['answer'] == 'accept':
                    labels = result_ids == correct_id
                elif obj['answer'] == 'reject':
                    # give rejects their own special category
                    # reject means the country was right but none of the options were.
                    labels = np.asarray([0, 0, 0, 0, 1])
                else:
                    # skip ignores
                    continue
                #print(labels)
                if labels.sum() == 0:
                    #print("No correct labels")
                    pass
                # if fewer than 4 options were presented for tagging,
                #   pad it out with 0s to length 4 + 1 (1 for the all wrong reject answer)
                labels = np.pad(labels, (0, 5 - len(labels)), 'constant')
                # pad the matrix with empty rows
                fl_pad = np.pad(fl_subset, ((0, 5 - fl_subset.shape[0]), (0, 0)), 'constant')
                # turn the matrix into a vector
                fl_unwrap = fl_pad.flatten()
                Y.append(labels)
                X.append(fl_unwrap)
            except Exception as e:
                print(e)
                #print(meta)
                continue
    return X, Y

def prep_data(X, Y, train_split):
    X_stack = np.vstack(X)
    X_stack.shape
    Y_stack = np.vstack(Y)
    Y_stack = Y_stack.astype(int)
    Y_stack.shape
    X_df = pd.DataFrame(X_stack)

    print("Using a cutpoint of ", train_split)
    np.random.seed(73071)
    msk = np.random.rand(len(X_df)) < train_split
    X_train = X_df[msk].as_matrix()
    X_test = X_df[~msk].as_matrix()
    y_train = Y_stack[msk]
    y_test = Y_stack[~msk]

    for i in [X_train, X_test, y_train, y_test]:
        print(i.shape)
    return X_train, X_test, y_train, y_test

def train_model(X_train, X_test, y_train, y_test, save_file):
    model = Sequential()
    model.add(Dense(128, activation='relu', input_shape = (X_train.shape[1],)))
    model.add(Dropout(0.3))
    model.add(Dense(128, activation='relu'))
    model.add(Dropout(0.3))
    model.add(Dense(128, activation='relu'))
    model.add(Dropout(0.3))
    model.add(Dense(y_train.shape[1], activation='softmax'))

    #sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
    model.compile(loss='categorical_crossentropy',
                  optimizer='rmsprop',
                  metrics=['accuracy'])

    callbacks = [EarlyStopping(monitor='val_loss', patience=50)]
    save_model = ModelCheckpoint(save_file, monitor='val_loss',
                                                 verbose=0, save_best_only=True,
                                                 save_weights_only=False)
    callbacks.append(save_model)

    model.fit(X_train, y_train,
              epochs=100,
              validation_split=0.2,
              callbacks = callbacks,
              batch_size=16)

    return model


@plac.annotations(
    input_file=("Location of Prodigy labeled output", "option", "i", str),
    train_split=("Fraction of data to use for training vs. validation", "option", "s", float),
    use_cache=("Use cached data?", "flag", "c"))
def main(input_file, train_split, use_cache):
    save_file = "rank_model_new.h5"
    if use_cache:
        print("Using saved data...")
        with open("ranker_X.pkl", "rb") as f:
            X = pickle.load(f)
        with open("ranker_y.pkl", "rb") as f:
            Y = pickle.load(f)
    else:
        print("Recalculating data...")
        X, Y = ingest_prodigy_ranks(input_file)
        #print("X.shape:", X.shape)
        #print("Y.shape:", Y.shape)
        with open("ranker_X.pkl", "wb") as f:
            pickle.dump(X, f)
        with open("ranker_Y.pkl", "wb") as f:
            pickle.dump(Y, f)
    X_train, X_test, y_train, y_test = prep_data(X, Y, train_split)
    model = train_model(X_train, X_test, y_train, y_test, save_file)
    score = model.evaluate(X_test, y_test)
    print(score)

    y_predicted = model.predict(X_test)
    print(sklearn.metrics.classification_report(y_pred = y_predicted>0.5, y_true = y_test))
    #model.save()

if __name__ == '__main__':
    plac.call(main)
