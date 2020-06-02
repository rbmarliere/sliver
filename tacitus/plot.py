from gensim.models import word2vec
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import sys

# define the function to compute the dimensionality reduction
# and then produce the biplot
def tsne_plot(model):
	"Creates a TSNE model and plots it"
	labels = []
	tokens = []
	for word in model.wv.vocab:
		tokens.append(model[word])
		labels.append(word)
	tsne_model = TSNE(perplexity=40, n_components=2, init='pca', n_iter=2500)
	new_values = tsne_model.fit_transform(tokens)
	x = []
	y = []
	for value in new_values:
		x.append(value[0])
		y.append(value[1])
	plt.figure(figsize=(8, 8))
	for i in range(len(x)):
		plt.scatter(x[i],y[i])
		plt.annotate(labels[i],
		xy=(x[i], y[i]),
	xytext=(5, 2),
	textcoords='offset points',
	ha='right',
	va='bottom')
	plt.show()

model = word2vec.Word2Vec.load(sys.argv[1])

# call the function on our dataset
tsne_plot(model)

