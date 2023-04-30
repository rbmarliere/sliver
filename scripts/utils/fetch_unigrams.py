import argparse
import pandas

from sliver.utils import clean_text


def main(args):
    df = pandas.read_csv(args.bigrams_file, sep="\t")
    words = clean_text("".join(str(df["bigram"].tolist())))
    uniq_words = pandas.Series(words).unique()

    unigrams = pandas.read_csv(args.unigrams_file, sep="\t")

    out_df = pandas.DataFrame(columns=["label", "unigram"])
    out_df["unigram"] = uniq_words
    out_df.loc[~out_df["unigram"].isin(unigrams["unigram"]), "label"] = 2

    unigrams = pandas.concat(
        [unigrams, out_df.loc[out_df["label"] == 2]], ignore_index=True
    )
    unigrams.to_csv("new_unigrams.tsv", index=False, sep="\t")


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("-b", "--bigrams-file", required=True)
    argp.add_argument("-u", "--unigrams-file", required=True)
    args = argp.parse_args()

    main(args)
