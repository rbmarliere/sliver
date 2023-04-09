import re
import unicodedata

import nltk
import pandas as pd
from nltk.corpus import stopwords

from sliver.strategies.hypnox import HypnoxTweet
from sliver.utils import standardize

# https://towardsdatascience.com/from-dataframe-to-n-grams-e34e29df3460
ADDITIONAL_STOPWORDS = ["covfefe"]

nltk.download("stopwords")
nltk.download("wordnet")


def basic_clean(text):
    """
    A simple function to clean up the data. All the words that
    are not designated as a stop word is then lemmatized after
    encoding and basic regex parsing are performed.
    """
    wnl = nltk.stem.WordNetLemmatizer()
    stopwords = nltk.corpus.stopwords.words("english") + ADDITIONAL_STOPWORDS
    text = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("utf-8", "ignore")
        .lower()
    )
    words = re.sub(r"[^\w\s]", "", text).split()
    # return [wnl.lemmatize(word) for word in words if word not in stopwords]
    return [wnl.lemmatize(word) for word in words]


def main():
    filter = "btc|bitcoin".encode("unicode_escape")
    q = HypnoxTweet.select().where(HypnoxTweet.text.iregexp(filter))

    df = pd.DataFrame(q.dicts())
    df = df.dropna()

    df["text"] = df["text"].apply(standardize)
    df["text"] = df["text"].apply(basic_clean)

    print(df["text"])

    words = basic_clean("".join(str(df["text"].tolist())))

    uniq_words = pd.Series(words).unique()
    with open("words.txt", "w") as f:
        for word in uniq_words:
            f.write(f"{word}\n")

    # bigrams = pd.Series(nltk.ngrams(words, 2)).value_counts()
    # ch = [bigrams[i : i + 100000] for i in range(0, len(bigrams.values), 100000)]
    # i = 0
    # for chunk in ch:
    #     chunk.to_csv(f"{i}.csv", index=False)
    #     i = i + 1

    print("done")


if __name__ == "__main__":
    main()
