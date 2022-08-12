import pandas
import src as hypnox

tweets_file = "i20220810_top.tsv"
last_training_file = "data/training/20220810.tsv"
output_file = "training.tsv"

# SELECT * FROM tweets ORDER BY intensity DESC LIMIT 10000
tweets = pandas.read_csv(tweets_file,
                         lineterminator="\n",
                         delimiter="\t",
                         encoding="utf-8")
tweets["clean"] = tweets["tweet"].apply(hypnox.text_utils.standardize)

# grab 200 most frequent words in the set
words = tweets.clean.str.split(
    expand=True).stack().value_counts().reset_index()
list_words = words["index"].head(200).values.tolist()

# filter tweets that uses at least 3 most frequent words
match = pandas.concat(
    [tweets.clean.str.contains(word, regex=False) for word in list_words],
    axis=1).sum(1) > 3
filtered = tweets.loc[match].reset_index(drop=True)

# load last labeled data
last_training = pandas.read_csv(last_training_file,
                                lineterminator="\n",
                                delimiter="\t",
                                encoding="utf-8")
last_training["clean"] = last_training["tweet"].apply(
    hypnox.text_utils.standardize)

# check if new tweets aren't labeled already
dup_filtered = pandas.merge(filtered,
                            last_training,
                            indicator=True,
                            how="outer").query('_merge=="left_only"').drop(
                                '_merge',
                                axis=1).reset_index(drop=True).drop('clean',
                                                                    axis=1)

# save to file
dup_filtered.to_csv(output_file,
                    sep="\t",
                    line_terminator="\n",
                    encoding="utf-8",
                    index=False)
