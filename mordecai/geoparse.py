import keras
import pandas as pd
from elasticsearch_dsl.query import MultiMatch
from elasticsearch_dsl import Search, Q
import numpy as np
from collections import Counter
from functools import lru_cache
import editdistance
import pkg_resources

from . import utilities

import spacy

try:
    nlp
except NameError:
    nlp = spacy.load('en_core_web_lg')

class Geoparser:
    def __init__(self, es_ip="localhost", es_port="9200", verbose = False,
                country_threshold = 0.8):
        DATA_PATH = pkg_resources.resource_filename('mordecai', 'data/')
        MODELS_PATH = pkg_resources.resource_filename('mordecai', 'models/')
        self._cts = utilities.country_list_maker()
        self._just_cts = utilities.country_list_maker()
        self._inv_cts = utilities.make_inv_cts(self._cts)
        country_state_city = utilities.other_vectors()
        self._cts.update(country_state_city)
        self._ct_nlp = utilities.country_list_nlp(self._cts)
        self._prebuilt_vec = [w.vector for w in self._ct_nlp]
        self._both_codes = utilities.make_country_nationality_list(self._cts, DATA_PATH + "nat_df.csv")
        self._admin1_dict = utilities.read_in_admin1(DATA_PATH + "admin1CodesASCII.json")
        self.conn = utilities.setup_es(es_ip, es_port)
        #self.country_exact = False # flag if it detects a country UPDATE: not currently holding per-query state like this
        #self.fuzzy = False # did it have to use fuzziness? UPDATE: not currently holding per-query state like this
        self.country_model = keras.models.load_model(MODELS_PATH + "country_model.h5")
        self.rank_model = keras.models.load_model(MODELS_PATH + "rank_model.h5")
        #countries = pd.read_csv("nat_df.csv")
        #nationality = dict(zip(countries.nationality, countries.alpha_3_code))
        #self._both_codes = {**nationality, **self._cts}
        self._skip_list = utilities.make_skip_list(self._cts)
        self.training_setting = False # make this true if you want training formatted
        self.country_threshold = country_threshold # if the best guess is below this, don't return
                                                   # anything at all
        feature_codes = pd.read_csv(DATA_PATH + "feature_codes.txt", sep="\t", header = None)
        self._code_to_text = dict(zip(feature_codes[1], feature_codes[3])) # human readable geonames IDs
        self.verbose = verbose # return the full dictionary or just the good parts?

    def _feature_country_mentions(self, doc):
        """
        Given a document, count how many times different country names and adjectives are mentioned.
        These are features used in the country picking phase.

        Parameters
        ---------
        doc: a spaCy nlp'ed piece of text

        Returns
        -------
        countries: dict
            the top two countries (ISO code) and their frequency of mentions.
        """

        c_list = []
        for i in doc.ents:
            try:
                country = self._both_codes[i.text]
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

    def _feature_most_common(self, results):
        """
        Find the most common country name in ES/Geonames results

        Paramaters
        ----------
        results: dict
            output of `query_geonames`

        Returns
        -------
        most_common: str
            ISO code of most common country, or empty string if none
        """
        try:
            country_count = Counter([i['country_code3'] for i in results['hits']['hits']])
            most_common = country_count.most_common()[0][0]
            return most_common
        except IndexError:
            return ""
        except TypeError:
            return ""


    def _feature_most_alternative(self, results, full_results = False):
        """
        Find the placename with the most alternative names and return its country.
        More alternative names are a rough measure of importance.

        Paramaters
        ----------
        results: dict
            output of `query_geonames`

        Returns
        -------
        most_alt: str
            ISO code of country of place with most alternative names,
            or empty string if none
        """
        try:
            alt_names = [len(i['alternativenames']) for i in results['hits']['hits']]
            most_alt = results['hits']['hits'][np.array(alt_names).argmax()]
            if full_results == True:
                return most_alt
            else:
                return most_alt['country_code3']
        except (IndexError, ValueError, TypeError):
            return ""


    def _feature_most_population(self, results):
        """
        Find the placename with the largest population and return its country.
        More population is a rough measure of importance.

        Paramaters
        ----------
        results: dict
            output of `query_geonames`

        Returns
        -------
        most_pop: str
            ISO code of country of place with largest population,
            or empty string if none
        """

        try:
            populations = [i['population'] for i in results['hits']['hits']]
            most_pop = results['hits']['hits'][np.array(populations).astype("int").argmax()]
            return most_pop['country_code3']
        except Exception as e:
            return ""


    def _feature_word_embedding(self, text):
        """
        Given a word, guess the appropriate country by word vector.

        Parameters
        ---------
        text: str
            the text to extract locations from.

        Returns
        -------
        country_picking: dict
            The top two countries (ISO codes) and two measures
            confidence for the first choice.
        """
        try:
            simils = np.dot(self._prebuilt_vec, text.vector)
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
        if confid == 0 or confid2 == 0:
            return ""
        country_code = self._cts[str(self._ct_nlp[ranks[0]])]
        country_picking = {"country_1" : country_code,
                "confid_a" : confid,
                "confid_b" : confid2,
                "country_2" : self._cts[str(self._ct_nlp[ranks[1]])]}
        return country_picking

    def _feature_first_back(self, results):
        """
        Get the country of the first two results back from geonames.

        Parameters
        -----------
        results: dict
            elasticsearch results

        Returns
        -------
        top: tuple
            first and second results' country name (ISO)
        """
        try:
            first_back = results['hits']['hits'][0]['country_code3']
        except (TypeError, IndexError):
            # usually occurs if no Geonames result
            first_back = ""
        try:
            second_back = results['hits']['hits'][1]['country_code3']
        except (TypeError, IndexError):
            second_back = ""

        top = (first_back, second_back)
        return top

    def is_country(self, text):
        """Check if a piece of text is in the list of countries"""
        ct_list = self._just_cts.keys()
        if text in ct_list:
            return True
        else:
            return False

    @lru_cache(maxsize=200)
    def query_geonames(self, placename):
        """
        Wrap search parameters into an elasticsearch query to the geonames index
        and return results.

        Parameters
        ---------
        conn: an elasticsearch Search conn, like the one returned by `setup_es()`

        placename: str
            the placename text extracted by NER system

        Returns
        -------
        out: The raw results of the elasticsearch query
        """
        # first first, try for country name
        if self.is_country(placename):
            q = {"multi_match": {"query": placename,
                                 "fields": ['name', 'asciiname', 'alternativenames'],
                                "type" : "phrase"}}
            r = Q("match", feature_code='PCLI')
            res = self.conn.query(q).query(r)[0:5].execute()
            #self.country_exact = True

        else:
            # second, try for an exact phrase match
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
                #self.fuzzy = True  # idea was to preserve this info as a feature, but not using state like this
                res = self.conn.query(q)[0:50].execute()


        es_result = utilities.structure_results(res)
        return es_result

    @lru_cache(maxsize=200)
    def query_geonames_country(self, placename, country):
        """
        Like query_geonames, but this time limited to a specified country.
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

    def _feature_location_type_mention(self, ent):
        """
        Count forward 1 word from each entity, looking for defined terms that indicate
        geographic feature types (e.g. "village" = "P").

        Parameters
        -----------
        ent : spacy entity span
            It has to be an entity to handle indexing in the document

        Returns
        --------
        tuple (length 2)
            (feature_code, feature_class) derived from explicit word usage

        """

        P_list = ["city", "cities", "town", "towns", "villages", "village", "settlement",
                  "capital", "town", "towns", "neighborhood", "neighborhoods",
                 "municipality"]
        ADM1_list = ["province", "governorate", "state", "department", "oblast",
                     "changwat"]
        ADM2_list = ["district", "rayon", "amphoe", "county"]
        A_other = ["region"]
        AIRPORT_list = ["airport"]
        TERRAIN_list = ["mountain", "mountains", "stream", "river"]
        FOREST_list = ["forest"]

        feature_positions = []
        feature_class = feature_code = ""

        interest_words = ent.doc[ent.end-1 : ent.end + 1] # last word or next word following

        for word in interest_words: #ent.sent:
            if ent.text in self._just_cts.keys():
                feature_class = "A"
                feature_code = "PCLI"
            elif word.text.lower() in P_list:
                feature_class = "P"
                feature_code = ""
            elif word.text.lower() in ADM1_list:
                feature_class = "A"
                feature_code = "ADM1"
            elif word.text.lower() in ADM2_list:
                feature_class = "A"
                feature_code = "ADM2"
            elif word.text.lower() in TERRAIN_list:
                feature_class = "T"
                feature_code = ""
            elif word.text.lower() in AIRPORT_list:
                feature_class = "S"
                feature_code = "AIRP"
            elif word.text.lower() in A_other:
                feature_class = "A"
                feature_code = ""

        return (feature_class, feature_code)



    def make_country_features(self, doc, require_maj = False):
        """
        Create features for the country picking model. Function where all the individual
        feature maker functions are called and aggregated. (Formerly "process_text")

        Parameters
        -----------
        doc : str or spaCy doc

        Returns
        -------
        task_list : list of dicts
            Each entry has the word, surrounding text, span, and the country picking features.
            This output can be put into Prodigy for labeling almost as-is (the "features" key needs
            to be renamed "meta" or be deleted.)
        """
        if not hasattr(doc, "ents"):
            text = nlp(doc)
        # initialize the place to store finalized tasks
        task_list = []

        # get document vector
        #doc_vec = self._feature_word_embedding(text)['country_1']

        # get explicit counts of country names
        ct_mention, ctm_count1, ct_mention2, ctm_count2 = self._feature_country_mentions(doc)

        # now iterate through the entities, skipping irrelevant ones and countries
        for ent in doc.ents:
            if not ent.text.strip():
                continue
            if ent.label_ not in ["GPE","LOC","FAC"]:
                continue
            # don't include country names (make a parameter)
            if ent.text.strip() in self._skip_list:
                continue

            ## just for training purposes
            #if ent.text.strip() in self._just_cts.keys():
            #    continue

            #skip_list.add(ent.text.strip())
            ent_label = ent.label_ # destroyed by trimming
            ent = self.clean_entity(ent)

            # vector for just the solo word
            vp = self._feature_word_embedding(ent)
            try:
                word_vec = vp['country_1']
                wv_confid = float(vp['confid_a'])
            except TypeError:
                # no idea why this comes up
                word_vec = ""
                wv_confid = "0"

            # look for explicit mentions of feature names
            class_mention, code_mention = self._feature_location_type_mention(ent)

            ##### ES-based features
            try:
                result = self.query_geonames(ent.text)
            except ConnectionTimeout:
                result = ""

            # build results-based features
            most_alt = self._feature_most_alternative(result)
            most_common = self._feature_most_common(result)
            most_pop = self._feature_most_population(result)
            first_back, second_back = self._feature_first_back(result)

            try:
                maj_vote = Counter([word_vec, most_alt,
                                    first_back, most_pop,
                                    ct_mention
                                    #doc_vec_sent, doc_vec
                                    ]).most_common()[0][0]
            except Exception as e:
                print("Problem taking majority vote: ", ent, e)
                maj_vote = ""


            if not maj_vote:
                maj_vote = ""

            # We only want all this junk for the labeling task. We just want to straight to features
            # and the model when in production.


            try:
                start = ent.start_char - ent.sent.start_char
                end = ent.end_char - ent.sent.start_char
                iso_label = maj_vote
                try:
                    text_label = self._inv_cts[iso_label]
                except KeyError:
                    text_label = ""

                task = {"text" : ent.sent.text,
                        "label" : text_label, # human-readable country name
                        "word" : ent.text,
                        "spans" : [{
                            "start" : start,
                            "end" : end,
                            } # make sure to rename for Prodigy
                                ],
                        "features" : {
                                "maj_vote" : iso_label,
                                "word_vec" : word_vec,
                                "first_back" : first_back,
                                #"doc_vec" : doc_vec,
                                "most_alt" : most_alt,
                                "most_pop" : most_pop,
                                "ct_mention" : ct_mention,
                                "ctm_count1" : ctm_count1,
                                "ct_mention2" : ct_mention2,
                                "ctm_count2" : ctm_count2,
                                "wv_confid" : wv_confid,
                                "class_mention" : class_mention, # inferred geonames class from mentions
                                "code_mention" : code_mention,
                                #"places_vec" : places_vec,
                                #"doc_vec_sent" : doc_vec_sent
                                } }
                task_list.append(task)
            except Exception as e:
                print(ent.text,)
                print(e)
        return task_list # rename this var

    # Two modules that call `make_country_features`:
    #  1. write out with majority vote for training
    #  2. turn into features, run model, return countries
    #  A third, standalone function will convert the labeled JSON from Prodigy into
    #    features for updating the model.

    def make_country_matrix(self, loc):
        """
        Create features for all possible country labels, return as matrix for keras.

        Parameters
        ----------
        loc: dict
            one entry from the list of locations and features that come out of make_country_features

        Returns
        --------
        keras_inputs: dict with two keys, "label" and "matrix"
        """

        top = loc['features']['ct_mention']
        top_count = loc['features']['ctm_count1']
        two =  loc['features']['ct_mention2']
        two_count = loc['features']['ctm_count2']
        word_vec = loc['features']['word_vec']
        first_back = loc['features']['first_back']
        most_alt = loc['features']['most_alt']
        most_pop = loc['features']['most_pop']

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

        keras_inputs = {"labels": possible_labels,
                        "matrix" : np.asmatrix(X_mat)}
        return keras_inputs



    def infer_country(self, doc):
        """NLP a doc, find its entities, get their features, and return the model's country guess for each.
        Maybe use a better name.

        Parameters
        -----------
        doc: str or spaCy
            the document to country-resolve the entities in

        Returns
        -------
        proced: list of dict
            the feature output of "make_country_features" updated with the model's
            estimated country for each entity.
            E.g.:
                {'all_confidence': array([ 0.95783567,  0.03769876,  0.00454875], dtype=float32),
                  'all_countries': array(['SYR', 'USA', 'JAM'], dtype='<U3'),
                  'country_conf': 0.95783567,
                  'country_predicted': 'SYR',
                  'features': {'ct_mention': '',
                       'ct_mention2': '',
                       'ctm_count1': 0,
                       'ctm_count2': 0,
                       'first_back': 'JAM',
                       'maj_vote': 'SYR',
                       'most_alt': 'USA',
                       'most_pop': 'SYR',
                       'word_vec': 'SYR',
                       'wv_confid': '29.3188'},
                  'label': 'Syria',
                  'spans': [{'end': 26, 'start': 20}],
                  'text': "There's fighting in Aleppo and Homs.",
                  'word': 'Aleppo'}

        """
        if not hasattr(doc, "ents"):
            doc = nlp(doc)
        proced = self.make_country_features(doc, require_maj=False)
        if not proced:
            pass
            # logging!
            #print("Nothing came back from make_country_features")
        feat_list = []
        #proced = self.ent_list_to_matrix(proced)

        for loc in proced:
            feat = self.make_country_matrix(loc)
            #labels = loc['labels']
            feat_list.append(feat)
            #try:
            # for each potential country...
            for n, i in enumerate(feat_list):
                labels = i['labels']
                try:
                    prediction = self.country_model.predict(i['matrix']).transpose()[0]
                    ranks = prediction.argsort()[::-1]
                    labels = np.asarray(labels)[ranks]
                    prediction = prediction[ranks]
                except ValueError:
                    prediction = np.array([0])
                    labels = np.array([""])

            loc['country_predicted'] = labels[0]
            loc['country_conf'] = prediction[0]
            loc['all_countries'] = labels
            loc['all_confidence'] = prediction

        return proced

    def get_admin1(self, country_code2, admin1_code):
        """
        Convert a geonames admin1 code to the associated place name.

        Parameters
        ---------
        country_code2: string
                       The two character country code
        admin1_code: string
                     The admin1 code to be converted. (Admin1 is the highest
                     subnational political unit, state/region/provice/etc.
        admin1_dict: dictionary
                     The dictionary containing the country code + admin1 code
                     as keys and the admin1 names as values.

        Returns
        ------
        admin1_name: string
                     The admin1 name. If none is found, return "NA".
        """
        lookup_key = ".".join([country_code2, admin1_code])
        try:
            admin1_name = self._admin1_dict[lookup_key]
            return admin1_name
        except KeyError:
            #print("No admin code found for country {} and code {}".format(country_code2, admin1_code))
            return "NA"

    def features_for_rank(self, proc, results):
        """Compute features for ranking results from ES/geonames


        Parameters
        ----------
        proc : dict
            One dictionary from the list that comes back from geoparse or from make_country_features (doesn't matter)
        results : dict
            the response from a geonames query

        Returns
        --------
        X : numpy matrix
            holding the computed features

        meta: list of dicts
            including feature information
        """
        feature_list = []
        meta = []
        results = results['hits']['hits']
        search_name = proc['word']
        code_mention = proc['features']['code_mention']
        class_mention = proc['features']['class_mention']

        for rank, entry in enumerate(results):
            # go through the results and calculate some features
            # get population number and exists
            try:
                pop = int(entry['population'])
                has_pop = 1
            except Exception as e:
                pop = 0
                has_pop = 0
            if pop > 0:
                logp = np.log(pop)
            else:
                logp = 0
            ### order the results came back
            adj_rank = 1 / np.log(rank + 2)
            # alternative names
            len_alt = len(entry['alternativenames'])
            adj_alt = np.log(len_alt)
            ### feature class (just boost the good ones)
            if entry['feature_class'] == "A" or entry['feature_class'] == "P":
                good_type = 1
            else:
                good_type = 0
                #fc_score = 3
            ### feature class/code matching
            if entry['feature_class'] == class_mention:
                good_class_mention = 1
            else:
                good_class_mention = 0
            if entry['feature_code'] == code_mention:
                good_code_mention = 1
            else:
                good_code_mention = 0
            ### edit distance
            ed = editdistance.eval(search_name, entry['name'])
            ed = ed # shrug
            # maybe also get min edit distance to alternative names...

            features = [has_pop, pop, logp, adj_rank, len_alt, adj_alt,
                        good_type, good_class_mention, good_code_mention, ed]
            m = self.format_geonames(entry)

            feature_list.append(features)
            meta.append(m)

        #meta = geo.format_geonames(results)
        X = np.asmatrix(feature_list)
        return (X, meta)

    def ranker(self, X, meta):
        """
        Sort the place features list by the score of its relevance.
        """
        # total score is just a sum of each row
        total_score = X.sum(axis=1).transpose()
        total_score = np.squeeze(np.asarray(total_score)) # matrix to array
        ranks = total_score.argsort()
        ranks = ranks[::-1]
        # sort the list of dicts according to ranks
        sorted_meta = [meta[r] for r in ranks]
        sorted_X = X[ranks]
        return (sorted_X, sorted_meta)

    def format_for_prodigy(self, X, meta, placename, return_feature_subset = False):
        """
        Given a feature matrix, geonames data, and the original query,
        construct a prodigy task.

        Make meta nicely readable: "A town in Germany"

        Parameters
        ----------

        X: matrix
            vector of features for ranking. Output of features_for_rank()
        meta: list of dictionaries
            other place information. Output of features_for_rank(). Used to provide
            information like "city in Germany" to the coding task.
        placename: str
            The extracted place name from text


        Returns
        --------
        task_list: list of dicts
            Tasks ready to be written to JSONL and use in Prodigy. Each potential match includes
            a text description to the annotator can pick the right one.
        """

        all_tasks = []

        sorted_X, sorted_meta = self.ranker(X, meta)
        sorted_meta = sorted_meta[:4]
        sorted_X = sorted_X[:4]
        for n, i in enumerate(sorted_meta):
            fc = self._code_to_text[i['feature_code']]
            text = ''.join(['"', i['place_name'], '"',
                            ", a ", fc,
                            " in ", i['country_code3'],
                            ", id: ", i['geonameid']])
            d = {"id" : n + 1, "text" : text}
            all_tasks.append(d)

        if return_feature_subset:
            return (all_tasks, sorted_meta, sorted_X)
        else:
            return all_tasks



    def format_geonames(self, entry, searchterm = None):
        """Pull out just the fields we want from a geonames entry

        To do:
        - switch to model picking

        Parameters
        -----------
        res : dict
            ES/geonames result

        searchterm : str
            (not implemented). Needed for better results picking

        Returns
        --------
        new_res : dict
            containing selected fields from selected geonames entry
        """
        try:
            lat, lon = entry['coordinates'].split(",")
            new_res = {"admin1" : self.get_admin1(entry['country_code2'], entry['admin1_code']),
                  "lat" : lat,
                  "lon" : lon,
                  "country_code3" : entry["country_code3"],
                  "geonameid" : entry["geonameid"],
                  "place_name" : entry["name"],
                  "feature_class" : entry["feature_class"],
                   "feature_code" : entry["feature_code"]}
            return new_res
        except (IndexError, TypeError):
            # two conditions for these errors:
            # 1. there are no results for some reason (Index)
            # 2. res is set to "" because the country model was below the thresh
            new_res = {"admin1" : "",
                  "lat" : "",
                  "lon" : "",
                  "country_code3" : "",
                  "geonameid" : "",
                  "place_name" : "",
                  "feature_class" : "",
                   "feature_code" : ""}
            return new_res



    def clean_proced(self, proced):
        """Small helper function to delete the features from the final dictionary.
        These features are mostly interesting for debugging but won't be relevant for most users.
        """
        for loc in proced:
            try:
                del loc['all_countries']
            except KeyError:
                pass
            try:
                del loc['matrix']
            except KeyError:
                pass
            try:
                del loc['all_confidence']
            except KeyError:
                pass
            try:
                del loc['place_confidence']
            except KeyError:
                pass
            try:
                del loc['text']
            except KeyError:
                pass
            try:
                del loc['label']
            except KeyError:
                pass
            try:
                del loc['features']
            except KeyError:
                pass
        return proced

    def geoparse(self, doc, verbose = False):
        """Main geoparsing function. Text to extracted, resolved entities.

        Parameters
        ----------
        doc : str or spaCy
            The document to be geoparsed. Can be either raw text or already spacy processed.
            In some cases, it makes sense to bulk parse using spacy's .pipe() before sending
            through to Mordecai

        Returns
        -------
        proced : list of dicts
            Each entity gets an entry in the list, with the dictionary including geo info, spans,
            and optionally, the input features.
        """
        if not hasattr(doc, "ents"):
            doc = nlp(doc)
        proced = self.infer_country(doc)
        if not proced:
            pass
            # logging!
            #print("Nothing came back from infer_country...")
        for loc in proced:
            if loc['country_conf'] >= self.country_threshold: # shrug
                res = self.query_geonames_country(loc['word'], loc['country_predicted'])
            elif loc['country_conf'] < self.country_threshold:
                res = ""
                # if the confidence is too low, don't use the country info

            try:
                _ = res['hits']['hits']
                # If there's no geonames result, what to do?
                # For now, just continue.
                # In the future, delete? Or add an empty "loc" field?
            except TypeError:
                continue
            # Pick the best place
            X, meta = self.features_for_rank(loc, res)
            all_tasks, sorted_meta, sorted_X = self.format_for_prodigy(X, meta, loc['word'], return_feature_subset=True)
            fl_pad = np.pad(sorted_X, ((0, 4 - sorted_X.shape[0]), (0, 0)), 'constant')
            fl_unwrap = fl_pad.flatten()
            prediction = self.rank_model.predict(np.asmatrix(fl_unwrap))
            place_confidence = prediction.max()
            loc['geo'] = sorted_meta[prediction.argmax()]
            loc['place_confidence'] = place_confidence


        if not verbose:
            proced = self.clean_proced(proced)

        return proced


