import nltk
import pandas as pd

from sliver.strategies.hypnox import HypnoxTweet
from sliver.utils import clean_text

# https://towardsdatascience.com/from-dataframe-to-n-grams-e34e29df3460


def main():
    filter = "btc|bitcoin".encode("unicode_escape")
    q = HypnoxTweet.select().where(HypnoxTweet.text.iregexp(filter))

    df = pd.DataFrame(q.dicts())
    df = df.dropna()

    df["text"] = df["text"].apply(clean_text)

    print(df["text"])

    words = clean_text("".join(str(df["text"].tolist())))

    uniq_words = pd.Series(words).unique()
    with open("words.txt", "w") as f:
        for word in uniq_words:
            f.write(f"{word}\n")

    bigrams = pd.Series(nltk.ngrams(words, 2)).value_counts()
    ch = [bigrams[i : i + 100000] for i in range(0, len(bigrams.values), 100000)]
    i = 0
    for chunk in ch:
        chunk.to_csv(f"{i}.csv", index=False)
        i = i + 1

    print("done")


if __name__ == "__main__":
    main()
