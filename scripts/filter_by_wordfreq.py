import sys

import pandas

sys.path.insert(0, ".")

import src as hypnox  # noqa: E402

last_training_file = "data/training/20220811.tsv"
output_file = "training.tsv"

query = hypnox.db.Tweet.select().order_by(
    hypnox.db.Tweet.intensity.desc()).limit(10000)
tweets = pandas.DataFrame(query.dicts())
tweets["clean"] = tweets["text"].apply(hypnox.text_utils.standardize)

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
dup_filter = pandas.merge(filtered["clean"],
                          last_training["clean"],
                          indicator=True,
                          how="outer").query('_merge=="left_only"')

# format output data
dup_filtered = filtered.loc[dup_filter.index]["text"]
output = pandas.DataFrame({
    "intensity": 0,
    "polarity": 0,
    "tweet": dup_filtered
})

# save to file
output.to_csv(output_file,
              sep="\t",
              line_terminator="\n",
              encoding="utf-8",
              index=False)
