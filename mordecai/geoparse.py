import importlib
import keras
import pandas as pd
from elasticsearch_dsl.query import MultiMatch
from elasticsearch_dsl import Search, Q
import numpy as np
from collections import Counter

from . import utilities

import spacy
nlp = spacy.load('en_core_web_lg')

class Geoparse:
    def __init__(self, es_ip="localhost", es_port="9200"):
        self.cache = {}
        self.cts = utilities.country_list_maker()
        self.ct_nlp = utilities.country_list_nlp(self.cts)
        self.both_codes = utilities.make_country_nationality_list(self.cts)
        self.inv_cts = utilities.make_inv_cts(self.cts)
        self.conn = utilities.setup_es(es_ip, es_port)
        self.country_exact = False # flag if it detects a country
        self.fuzzy = False # did it have to use fuzziness?
        self.model = keras.models.load_model("/Users/ahalterman/MIT/Geolocation/mordecai/mordecai/data/country_model.h5")
        countries = pd.read_csv("nat_df.csv")
        nationality = dict(zip(countries.nationality,countries.alpha_3_code))
        self.both_codes = {**nationality, **self.cts}
        self.skip_list = utilities.make_skip_list(self.cts)
        self.training_setting = False # make this true if you want training formatted
    def country_mentions(self, doc):
        """
        Given a document, count how many times different country names and adjectives are mentioned.
        These are features used in the country picking phase.

        Parameters
        ---------
        doc: a spaCy nlp'ed piece of text

        Returns
        -------
        countries: dict, the top two countries (ISO code) and their frequency of mentions.
        """

        c_list = []
        for i in doc.ents:
            try:
                country = self.both_codes[i.text]
                c_list.append(country)
            except KeyError:
                pass

        count = Counter(c_list).most_common()
        try:
            top, top_count = count[0]
        except:
            top = ""
            top_count = 0
        try:
            two, two_count = count[1]
        except:
            two = ""
            two_count = 0

        #countries = {"country_1" : top,
        #             "freq_1" : top_count,
        #             "country_2": two,
        #             "freq_2" : two_count}
        countries = (top, top_count, two, two_count)
        return countries


    def clean_entity(self, ent):
        """
        Strip out extra words that often get picked up by spaCy's NER.

        To do: preserve info about what got stripped out to help with ES/Geonames
            resolution later.

        Parameters
        ---------
        ent: a spaCy named entity Span

        Returns
        -------
        new_ent: a spaCy Span, with extra words stripped out.

        """
        dump_list = ['province', 'the', 'area', 'airport', 'district', 'square',
                    'town', 'village', 'prison', "river", "valley", "provincial", "prison",
                    "region", "municipality", "state", "territory", "of", "in",
                    "county", "central"]
                    # maybe have 'city'? Works differently in different countries
                    # also, "District of Columbia". Might need to use cap/no cap
        keep_positions = []
        for word in ent:
            if word.text.lower() not in dump_list:
                keep_positions.append(word.i)

        keep_positions = np.asarray(keep_positions)
        try:
            new_ent = ent.doc[keep_positions.min():keep_positions.max()+1]
            # can't set directly
            #new_ent.label_.__set__(ent.label_)
        except ValueError:
            new_ent = ent
        return new_ent

    def most_common_geo(self, results):
        """
        Find the most common country name in ES/Geonames results

        Paramaters
        ----------
        results: dict, output of `query_geonames`

        Returns
        -------
        most_common: str, ISO code of most common country, or empty string if none
        """
        try:
            country_count = Counter([i['country_code3'] for i in results['hits']['hits']])
            most_common = country_count.most_common()[0][0]
            return most_common
        except IndexError:
            return ""
        except TypeError:
            return ""


    def most_alternative(self, results):
        """
        Find the placename with the most alternative names and return its country.
        More alternative names are a rough measure of importance.

        Paramaters
        ----------
        results: dict, output of `query_geonames`

        Returns
        -------
        most_alt: str, ISO code of country of place with most alternative names,
                    or empty string if none
        """
        try:
            alt_names = [len(i['alternativenames']) for i in results['hits']['hits']]
            most_alt = results['hits']['hits'][np.array(alt_names).argmax()]
            return most_alt['country_code3']
        except (IndexError, ValueError, TypeError):
            return ""


    def most_population(self, results):
        """
        Find the placename with the largest population and return its country.
        More population is a rough measure of importance.

        Paramaters
        ----------
        results: dict, output of `query_geonames`

        Returns
        -------
        most_pop: str, ISO code of country of place with largest population,
                    or empty string if none
        """

        try:
            populations = [i['population'] for i in results['hits']['hits']]
            most_pop = results['hits']['hits'][np.array(populations).astype("int").argmax()]
            return most_pop['country_code3']
        except Exception as e:
            print("Error in most_population: ", e)
            return ""


    def vector_picking(self, text):
        """
        Given a word, guess the appropriate country by word vector.

        Parameters
        ---------
        text: string, text to extract locations from.

        Returns
        -------
        country_picking: dict, with top two countries (ISO codes) and two measures of
                confidence for the first choice.
        """
        if not hasattr(text, "vector"):
            text = nlp(text)
        prebuilt_vec = [w.vector for w in self.ct_nlp]
        try:
            simils = np.dot(prebuilt_vec, text.vector)
        except Exception as e:
            #print("Vector problem, ", Exception, e)
            return {"country_1" : "",
                "confid_a" : 0,
                "confid_b" : 0,
                "country_2" : ""}
        ranks = simils.argsort()[::-1]
        best_index = ranks[0]
        confid = simils.max()
        confid2 = simils[ranks[0]] - simils[ranks[1]]
        #print(confid)
        #print(confid2)
        if confid == 0 or confid2 == 0:
            #print("Weird word??")
            return ""
        #print(cts[str(ct_nlp[ranks[1]])])
        country_code = self.cts[str(self.ct_nlp[ranks[0]])]
        country_picking = {"country_1" : country_code,
                "confid_a" : confid,
                "confid_b" : confid2,
                "country_2" : self.cts[str(self.ct_nlp[ranks[1]])]}
        return country_picking

    def get_first_back(self, results):
        """
        Get the country of the first two results back from geonames.

        Parameters
        -----------
        results: dict, elasticsearch results

        Returns
        -------
        top: tuple, first and second results' country name (ISO)
        """
        try:
            first_back = self.result['hits']['hits'][0]['country_code3']
        except (TypeError, IndexError):
            # usually occurs if no Geonames result
            first_back = ""
        try:
            second_back = self.result['hits']['hits'][1]['country_code3']
        except (TypeError, IndexError):
            second_back = ""

        top = (first_back, second_back)
        return top

    def country_finder(self, text):
        ct_list = self.cts.keys()
        if text in ct_list:
            return True
        else:
            return False


    def query_geonames(self, placename):
        """
        Wrap search parameters into an elasticsearch query to the geonames index
        and return results.
        Parameters
        ---------
        conn: an elasticsearch Search conn, like the one returned by `setup_es()`
        placename: string
                   the placename text extracted by NER system
        Returns
        -------
        out: The raw results of the elasticsearch query
        """
        # first first, try for country name
        if self.country_finder(placename):
            q = {"multi_match": {"query": placename,
                                 "fields": ['name', 'asciiname', 'alternativenames'],
                                "type" : "phrase"}}
            r = Q("match", feature_code='PCLI')
            res = self.conn.query(q).query(r)[0:5].execute()
            self.country_exact = True

        else:
            # first, try for an exact phrase match
            q = {"multi_match": {"query": placename,
                                 "fields": ['name^5', 'asciiname^5', 'alternativenames'],
                                "type" : "phrase"}}

            res = self.conn.query(q)[0:50].execute()

            # if no results, use some fuzziness, but still require all terms to be present.
            # Fuzzy is not allowed in "phrase" searches.
            if res.hits.total == 0:
                # tried wrapping this in a {"constant_score" : {"query": ... but made it worse
                q = {"multi_match": {"query": placename,
                                     "fields": ['name', 'asciiname', 'alternativenames'],
                                         "fuzziness" : 1,
                                         "operator":   "and"},
                        }
                self.fuzzy = True

                #print(conn.query(q).count())
                res = self.conn.query(q)[0:50].execute()


        es_result = utilities.structure_results(res)
        self.cache[placename] = es_result
        return es_result

    def query_geonames_country(self, placename, country):
        """
        """
        # first, try for an exact phrase match
        q = {"multi_match": {"query": placename,
                             "fields": ['name^5', 'asciiname^5', 'alternativenames'],
                            "type" : "phrase"}}
        r = Q("match", country_code3=country)
        res = self.conn.query(q).query(r)[0:50].execute()

        # if no results, use some fuzziness, but still require all terms to be present.
        # Fuzzy is not allowed in "phrase" searches.
        if res.hits.total == 0:
                # tried wrapping this in a {"constant_score" : {"query": ... but made it worse
            q = {"multi_match": {"query": placename,
                                 "fields": ['name', 'asciiname', 'alternativenames'],
                                     "fuzziness" : 1,
                                     "operator":   "and"},
                }
            r = Q("match", country_code3=country)
            res = self.conn.query(q).query(r)[0:50].execute()

        out = utilities.structure_results(res)
        return out


    def process_text(self, text, require_maj = True):
        if not hasattr(text, "ents"):
            text = nlp(text)
        # initialize the place to store finalized tasks
        task_list = []

        # get document vector
        doc_vec = self.vector_picking(text)['country_1']

        # get explicit counts of country names
        ct_mention, ctm_count1, ct_mention2, ctm_count2 = self.country_mentions(text)

        # now iterate through the entities, skipping irrelevant ones and countries
        for ent in text.ents:
            if not ent.text.strip():
                continue
            if ent.label_ not in ["GPE","LOC","FAC"]:
                continue
            # don't include country names (make a parameter)
            if ent.text.strip() in self.skip_list:
                continue

            #skip_list.add(ent.text.strip())
            ent_label = ent.label_ # destroyed by trimming
            ent = self.clean_entity(ent)

            # vector for just the solo word
            vp = self.vector_picking(ent)
            word_vec = vp['country_1']
            wv_confid = str(vp['confid_a'])

            ##### ES-based features
            # cache search results
            try:
                self.result = self.cache[ent.text]
            except KeyError:
                self.result = self.query_geonames(ent.text)

            # build results-based features
            most_alt = self.most_alternative(self.result)
            most_common = self.most_common_geo(self.result)
            most_pop = self.most_population(self.result)
            first_back, second_back = self.get_first_back(self.result)

            try:
                maj_vote = Counter([word_vec, most_alt,
                                    first_back, most_pop,
                                    ct_mention
                                    #doc_vec_sent, doc_vec
                                    ]).most_common()[0][0]
                    # add winning count/percent here? (both with and without missing)
            except Exception as e:
                print(ent, e)
                maj_vote = ""


            if not maj_vote:
                print("No majority vote for ", ent, [word_vec, most_alt, first_back, most_pop])
                maj_vote = ""

            # We only want all this junk for the labeling task. We just want to straight to features
            # and the model when in production.

            if True: #self.training_setting == True:
                # maybe skip later if it's slow...
                if not maj_vote and require_maj == True:
                    continue
                try:
                    start = ent.start_char - ent.sent.start_char
                    end = ent.end_char - ent.sent.start_char
                    iso_label = maj_vote
                    try:
                        text_label = self.inv_cts[iso_label]
                    except KeyError:
                        text_label = ""
                    task = {"text" : ent.sent.text,
                            "label" : text_label,
                            "word" : ent.text,
                            "spans" : [{
                                "start" : start,
                                "end" : end,
                                } # make sure to rename for Prodigy
                                    ],
                            "features" : {
                                    "maj_vote" : ent_label,
                                    "word_vec" : word_vec,
                                    "first_back" : first_back,
                                    #"doc_vec" : doc_vec,
                                    "most_alt" : most_alt,
                                    "most_pop" : most_pop,
                                    "ct_mention" : ct_mention,
                                    "ctm_count1" : ctm_count1,
                                    "ct_mention2" : ct_mention2,
                                    "ctm_count2" : ctm_count2,
                                    "wv_confid" : wv_confid
                                    #"places_vec" : places_vec,
                                    #"doc_vec_sent" : doc_vec_sent
                                    } }

                    task_list.append(task)
                except Exception as e:
                    print(ent.text,)
                    print(e)
        return task_list # rename this var

    # Two modules that call `process_text`:
    #  1. write out with majority vote for training
    #  2. turn into features, run model, return countries
    #  A third, standalone function will convert the labeled JSON from Prodigy into
    #    features for updating the model.

    def make_features(self, entry, label):
        # this one should only be called when updating the model
        word_vec = entry['features']['word_vec']
        first_back = entry['features']['first_back']
        most_alt = entry['features']['most_alt']
        most_pop = entry['features']['most_pop']

        inputs  = np.array([word_vec, first_back, most_alt, most_pop])
        x = inputs == label
        x = np.asarray((x * 2) - 1) # convert to -1, 1

        # get missing values
        exists = inputs != ""
        exists = np.asarray((exists * 2) - 1)

        # calculate some new stuff:
        top, top_count, two, two_count = country_mentions(text)
        counts = np.asarray([top_count, two_count])
        right = np.asarray([top, two]) == label
        right = right*2 - 1
        #print(right)
        right[counts == 0] = 0
        #print(right)

        # get correct values
        features = np.concatenate([x, exists, counts, right])
        return features

    def entry_for_prediction(self, entry):
        """
        Create features for all possible labels, return as matrix for keras
        """
        top = entry['features']['ct_mention']
        top_count = entry['features']['ctm_count1']
        two =  entry['features']['ct_mention2']
        two_count = entry['features']['ctm_count2']
        word_vec = entry['features']['word_vec']
        first_back = entry['features']['first_back']
        most_alt = entry['features']['most_alt']
        most_pop = entry['features']['most_pop']

        possible_labels = set([top, two, word_vec, first_back, most_alt, most_pop])
        possible_labels = [i for i in possible_labels if i]

        X_mat = []

        for label in possible_labels:
            inputs  = np.array([word_vec, first_back, most_alt, most_pop])
            x = inputs == label
            x = np.asarray((x * 2) - 1) # convert to -1, 1

            # get missing values
            exists = inputs != ""
            exists = np.asarray((exists * 2) - 1)

            counts = np.asarray([top_count, two_count]) # cludgy, should be up with "inputs"
            right = np.asarray([top, two]) == label
            right = right*2 - 1
            right[counts == 0] = 0

            # get correct values
            features = np.concatenate([x, exists, counts, right])
            X_mat.append(np.asarray(features))

        return {"labels": possible_labels,
                "matrix" : np.asmatrix(X_mat)}

    def doc_to_guess(self, doc):
        if not hasattr(doc, "ents"):
            doc = nlp(doc)
        proced = self.process_text(doc, require_maj=False)

        feat_list = []
        for loc in proced:
            feat = self.entry_for_prediction(loc)
            feat_list.append(feat)

            for n, i in enumerate(feat_list):
                labels = i['labels']
                prediction = self.model.predict(i['matrix']).transpose()[0]
                ranks = prediction.argsort()[::-1]
                labels = np.asarray(labels)[ranks]
                prediction = prediction[ranks]
            loc['label'] = labels[0]
            loc['confidence'] = prediction[0]
            loc['all_countries'] = labels
            loc['all_confidence'] = prediction

        return proced

    def geoparse(self, doc):
        if not hasattr(doc, "ents"):
            doc = nlp(doc)
        proced = self.doc_to_guess(doc)
        for loc in proced:
            place_id = loc['word'] + "_" + loc['label']
            # need to handle lack of key
            if loc['confidence'] >= 0.8: # shrug
                try:
                    res = self.cache[place_id]
                    if res:
                        self.cache[place_id] = res
                except KeyError:
                    res = self.query_geonames_country(loc['word'], loc['label'])
                    if res:
                        self.cache[place_id] = res
            elif loc['confidence'] < 0.8:
                # if the confidence is too low, don't use the country info
                try:
                    res = self.cache[loc['word']]
                except KeyError:
                    res = self.query_geonames(i['word'])
                    self.cache[loc['word']] = res

            loc['geonames'] = res
        return proced


    def format_geonames(self, top_result):
        # pull out just what we want from the top geonames entry, do the admin1 formatting
        pass

    def clean_dict(self, proced):
        # optionally clean up the main dictionary before returning it. Most people
        # won't want the sentence, all the features, etc. to come back.
        pass
