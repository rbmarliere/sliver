import nltk
import pandas as pd

from sliver.strategies.hypnox import HypnoxTweet
from sliver.strategies.hypnoxv2 import Hypnoxv2Gram
from sliver.utils import clean_text

# https://towardsdatascience.com/from-dataframe-to-n-grams-e34e29df3460


def main():
    known_bi = Hypnoxv2Gram.get_by_rank(2)
    known_un = Hypnoxv2Gram.get_by_rank(1)

    filter = "btc|bitcoin".encode("unicode_escape")
    q = (
        HypnoxTweet.select()
        .where(HypnoxTweet.text.iregexp(filter))
        .where(HypnoxTweet.time < "2020-01-01")
    )

    df = pd.DataFrame(q.dicts())
    df = df.dropna()

    df["text"] = df["text"].apply(clean_text)

    print(df["text"])

    words = clean_text("".join(str(df["text"].tolist())))

    uniq_words = pd.Series(words).unique()
    un = pd.DataFrame(uniq_words)
    un.reset_index(inplace=True)
    un["str"] = un[0].astype(str)
    un = un.loc[~un.str.isin(known_un.index)]
    un["label"] = 0
    un.rename(columns={"str": "gram"}, inplace=True)

    un[["label", "gram"]].to_csv("unigrams.tsv", sep="\t", index=False)

    bigrams = pd.Series(nltk.ngrams(words, 2)).value_counts()

    bi = pd.DataFrame(bigrams)
    bi.reset_index(inplace=True)
    bi["str"] = bi["index"].astype(str)
    bi = bi.loc[~bi.str.isin(known_bi.index)]
    bi["label"] = 0
    bi.rename(columns={"str": "gram"}, inplace=True)

    ch = [bi[i : i + 100000] for i in range(0, len(bi), 100000)]
    i = 0
    for chunk in ch:
        chunk[["label", "gram"]].to_csv(f"{i}.tsv", sep="\t", index=False)
        i = i + 1

    print("done")


if __name__ == "__main__":
    main()
