from gensim.models import word2vec
import logging
import sys

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

data = open(sys.argv[1], 'r')

# build a corpus for the word2vec model
def build_corpus(data):
	"Creates a list of lists containing words from each sentence"
	corpus = []
	for sentence in data:
		word_list = sentence.split(" ")
		if word_list != ['']:
			corpus.append(word_list)
	return corpus

corpus = build_corpus(data)

model = word2vec.Word2Vec(corpus, size=300, window=10, min_count=40, workers=16, sg=1) #sg=1 is skipgram, default is 0 = cbow
model.save('tacitus.model')

