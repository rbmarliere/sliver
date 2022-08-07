import logging
import numpy
import pandas
import psycopg2
import src as hypnox
import sys
import tensorflow
import transformers


def init():
    # get config object
    config = hypnox.config.Config()

    # connect to database
    try:
        db = psycopg2.connect(host=config.config["DB_HOST"],
                              database=config.config["DB_DATABASE"],
                              user=config.config["DB_USER"],
                              password=config.config["DB_PASSWORD"])
        cursor = db.cursor()

        return db, cursor

    except psycopg2.errors.OperationalError:
        logging.error("could not complete database connection")
        sys.exit(1)


def close(db, c):
    db.commit()
    c.close()
    db.close()


def insert(tweet):
    db, c = init()
    sql = "INSERT INTO stream_user(time,tweet) VALUES(%s, %s)"
    c.execute(sql, (tweet["time"], tweet["tweet"]))
    close(db, c)


def replay(args):
    # load model config
    model_config = hypnox.config.ModelConfig(args.model)
    model_config.check_model()

    # load transformer
    bert = transformers.TFAutoModel.from_pretrained(
        model_config.yaml["bert"],
        num_labels=model_config.yaml["num_labels"],
        from_pt=True)
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        model_config.yaml["bert"])
    labels = {0: 0, 2: -1, 1: 1}

    # load model
    model = tensorflow.keras.models.load_model(
        model_config.model_path, custom_objects={"TFBertModel": bert})

    # start database connection
    db, c = init()

    # check if target table exists
    try:
        query = "SELECT * FROM \"%s\" LIMIT 1" % args.table
        c.execute(query)
    except psycopg2.errors.UndefinedTable:
        logging.error("table \"%s\" doesn't exist" % args.table)
        sys.exit(1)

    # check which column to use
    if model_config.yaml["class"] == "polarity":
        modelcol = "model_p"
        target = "polarity"
    elif model_config.yaml["class"] == "intensity":
        modelcol = "model_i"
        target = "intensity"
    else:
        logging.error(
            "could not parse model config file (model class is missing)")
        sys.exit(1)

    # check which rows to update
    if args.update_only:
        update_only = "WHERE %s IS NULL OR %s <> '%s'" % (modelcol, modelcol,
                                                          args.model)
    else:
        update_only = ""

    # fetch rows to update
    query = "SELECT * FROM \"%s\" %s" % (args.table, update_only)
    c.execute(query)
    rows = c.fetchall()
    if not rows:
        logging.error("no rows to update")
        sys.exit(1)

    # load data
    ids = [row[0] for row in rows]
    df = pandas.DataFrame(ids, columns=["id"])
    df["tweet"] = [row[2] for row in rows]

    # preprocess model input
    df["clean_tweet"] = df["tweet"].apply(hypnox.text_utils.standardize)
    df = df.dropna()

    # compute predictions
    inputs = tokenizer(df["clean_tweet"].values.tolist(),
                       truncation=True,
                       padding='max_length',
                       max_length=model_config.yaml["max_length"],
                       return_tensors="tf")
    prob = model.predict(
        {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"]
        },
        verbose=1)

    # check model class
    if model_config.yaml["class"] == "polarity":
        df["polarity"] = [
            labels[numpy.argmax(x)] * x[numpy.argmax(x)] for x in prob
        ]
        df["polarity"] = df["polarity"].apply("{:.8f}".format).apply(
            pandas.to_numeric)
    else:
        df["intensity"] = [x[1] for x in prob]
        df["intensity"] = df["intensity"].apply("{:.8f}".format).apply(
            pandas.to_numeric)

    # update database
    try:
        tuples = str(
            list(
                zip(df["id"].values, df[target].values,
                    [args.model] * len(df))))[1:-1]
        update = "UPDATE \"%s\" AS t SET %s = t2.%s, %s = t2.%s" \
            % args.table, target, target, modelcol, modelcol
        update += "FROM (values %s) AS t2(id,%s,%s) WHERE t2.id = t.id" \
            % tuples, target, modelcol
        c.execute(update)
    except psycopg2.errors.OperationalError:
        logging.error("could not complete database update")
        sys.exit(1)

    # close database connection
    close(db, c)
