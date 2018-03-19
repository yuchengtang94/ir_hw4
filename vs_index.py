# -*- coding: utf-8 -*-
import shelve
import nltk
import json
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import time
import math
import heapq

# stopwords list from nltk
stemmer = PorterStemmer()
tokenizer = RegexpTokenizer(r'\w+')

data_path = 'test_corpus.json'


############   Building Posting List ####################
# load_data
def loadJson(data_path):
    database = shelve.open('database', writeback=False)
    film_data = open(data_path).read()
    data = json.loads(film_data)
    database['corpus'] = data
    database.close()
    return data


# indexAll
def indexAllData(data):
    database = shelve.open('database', writeback=False)
    posting_list = {}
    for i in range(0, len(data)) :

        words_list = tokenize_stemming(data[str(i)]['text'])
        for word in words_list :

            if word not in posting_list:
                posting_list[word] = {}
            if i not in posting_list[word]:
                posting_list[word][i] = 0

            posting_list[word][i] = posting_list[word][i] + 1
        if i % 500 == 0:
            print('index finish  ' + str(i))
            # posting_list[word].append(i)
        if i > 2049:
            print(i)
    print("posting list finished")
    database['posting_list'] = posting_list
    database.close()
    print("store posting list finished")
    calculate_doc_length()
    return


def get_tf_doc(term, docId):

    posting_list = shelve.open('database', writeback=False)['posting_list']

    return 1 + math.log(posting_list[term][docId], 10)

# caculate term frequency for a term in search query
def get_tf_query(term, query):

    raw_tf = 0

    for word in query:
        if word == term:
            raw_tf = raw_tf + 1

    return 1 + math.log(raw_tf, 10)

# get idf for a term
def get_idf(term):
    database = shelve.open('database', writeback=False)
    posting_list = database['posting_list']
    data = database['corpus']

    df = len(posting_list[term])
    N = len(data)

    res = math.log(float(N)/ float(df), 10)
    return res


# return doc_length for a docId
def get_doc_length(docId):
    database = shelve.open('database', writeback=False)
    doc_lenth = database['doc_length']
    return doc_lenth[docId]

# calculate weight lenth of all document
def calculate_doc_length():
    database = shelve.open('database', writeback=False)
    print('calculate length begin')
    doc_length = {}
    data = database['corpus']

    for i in range(0, len(data)) :
        words_list = tokenize_stemming(data[str(i)]['text'])
        doc_len = 0
        for word in set(words_list) :
            tf = get_tf_doc(word, i)
            idf = get_idf(word)
            score = tf * idf
            doc_len = doc_len + score * score

        doc_length[i] = math.sqrt(doc_len)
        if i % 500 == 0:
            print('calculate doc_length finish  ' + str(i))

    database['doc_length'] = doc_length
    return


# get cosin score for a query, docId pair
def cosin_score(query, docId):

    score = 0.0

    for term in set(query):

        score = score + get_tf_doc(term, docId) * get_idf(term) * get_tf_query(term, query) * get_idf(term) / get_doc_length(docId)

    return score

# rank all result based on cosi score
def rank_result(query, movieId):

    score = {}
    ranked = []
    res_scores = []
    res_movieId = []
    for i in movieId:
        score[i] = cosin_score(query, i)
        heapq.heappush(ranked, (score[i], i))

    res = heapq.nlargest(len(movieId), ranked)

    for i in range(0, len(res)):
        res_movieId.append(res[i][1])
        res_scores.append(res[i][0])

    return res_movieId, res_scores

# tokenize() to generate all possible words


def tokenize_stemming(raw_text):

    words = tokenizer.tokenize(raw_text)
    stem_word = []
    for word in words :
        stem_word.append(stemmer.stem(word))
    return set(stem_word)


def storeStopWords():
    database = shelve.open('database', writeback=False)
    database['stopWords'] = set(stopwords.words('english'))
    database.close()


##################  Process Input query And Search #########################

class SearchEngine:

    def search(self, query) :
        pre_result = self.preprocess(query)
        pre_result['movie_ids'] = []
        if pre_result['unKnown']:
            return pre_result
        new_query = pre_result['realQuery']
        pre_result['movie_ids'], pre_result['scores'] = self.findMovieId(new_query)

        return pre_result


    def preprocess(self, query):
        database = shelve.open('database', writeback=False)
        res = {}
        res['stopWords'] = []
        res['unKnown'] = []
        res['realQuery'] = []
        posting_list = database['posting_list']
        stopWords = database['stopWords']

        words = tokenizer.tokenize(query)
        for word in words:
            if word in stopWords:
                res['stopWords'].append(word.encode('ascii', 'ignore'))
            else :
                wd = stemmer.stem(word).encode('ascii', 'ignore')
                if wd not in posting_list:
                    res['unKnown'].append(wd)
                else :
                    res['realQuery'].append(wd)
        database.close()
        return res


    def findMovieId(self, query):
        database = shelve.open('database', writeback=False)
        movieId = []
        if len(query) == 0 :
            return movieId, []

        posting_list = database['posting_list']
        new_query = sorted(query, key = lambda word : len(posting_list[word]))
        movieId = sorted(posting_list[new_query[0]].keys())
        if len(query) == 1 :
            movieId, rank_score = rank_result(query, movieId)
            return movieId, rank_score
        print(len(movieId))
        for word in new_query[1:]:
            movieId = self.intersect(movieId, sorted(posting_list[word].keys()))

        movieId, rank_score = rank_result(query, movieId)

        return movieId, rank_score

    def intersect(self, idList1, idList2):
        print(len(idList2))
        i = 0
        j = 0
        res = []
        while (i < len(idList1) and j < len(idList2)) :
            if idList1[i] < idList2[j]:
                i = i + 1
            elif idList1[i] > idList2[j]:
                j = j + 1
            else:
                res.append(idList1[i])
                i = i + 1
                j = j + 1
        return res


    def get_movie_data(self, doc_id):
        database = shelve.open('database', writeback=False)
        corpus = database['corpus']

        return corpus[doc_id]


    def get_movie_snippet(self, doc_id):

        database = shelve.open('database', writeback=False)
        data = database['corpus']

        try:
            title = data[str(doc_id)]['title']
        except:
            title = ''

        try:
            text = data[str(doc_id)]['text']
        except:
            text = ''

        return (doc_id, title, text)


if __name__ == '__main__':

    start_time = time.clock()
    print('Build Start!')
    data = loadJson(data_path)
    indexAllData(data)
    storeStopWords()
    end_time = time.clock()
    print('Build End!')
    print('Build Time Use ' + str(end_time - start_time) + ' seconds')




