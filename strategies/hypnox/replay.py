import numpy
import pandas

import core
import strategies


def predict(model, tweets, verbose=0):
    inputs = model.tokenizer(tweets,
                             truncation=True,
                             padding="max_length",
                             max_length=model.config["max_length"],
                             return_tensors="tf")

    prob = model.predict(
        {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"]
        },
        batch_size=model.config["batch_size"],
        verbose=verbose)

    if model.config["class"] == "polarity":
        indexes = prob.argmax(axis=1)
        values = numpy.take_along_axis(prob,
                                       numpy.expand_dims(indexes, axis=1),
                                       axis=1).squeeze(axis=1)
        labels = [-1 if x == 2 else x for x in indexes]

        scores = labels * values

    elif model.config["class"] == "intensity":
        scores = prob.flatten()

    return scores


def replay(model, update_only=True, verbose=0):
    query = strategies.hypnox \
        .HypnoxTweet.get_tweets_by_model(model.config["name"])

    if update_only:
        query = query.where(strategies.hypnox.HypnoxScore.model.is_null())

    count = query.count()
    if count == 0:
        core.watchdog.info("{m}: no tweets to replay"
                           .format(m=model.config["name"]))
        return
    core.watchdog.info("{m}: replaying {c} tweets"
                       .format(c=count,
                               m=model.config["name"]))

    with core.db.connection.atomic():
        # page = 0
        # while True:
        # page_q = query.paginate(page, 1024)
        # page += 1
        # if page_q.count() == 0:
        #     break

        tweets = pandas.DataFrame(query.dicts())
        tweets.text = tweets.text.apply(core.utils.standardize)
        tweets.text = tweets.text.str.slice(0, model.config["max_length"])
        tweets = tweets.rename(columns={"id": "tweet_id"})
        tweets["model"] = model.config["name"]
        tweets["score"] = predict(model,
                                  tweets["text"].to_list(),
                                  verbose=verbose)

        scores = tweets[["tweet_id", "model", "score"]]

        try:
            strategies.hypnox \
                .HypnoxScore.insert_many(scores.to_dict("records")).execute()

        except Exception:
            # drop to a python interpreter shell
            import code
            code.interact(local=locals())
