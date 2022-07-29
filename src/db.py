import logging
import numpy
import os
import pandas
import psycopg2
import src
import sys
import tensorflow
import transformers

def init():
    # get config object
    config = src.config.Config()

    # connect to database
    try:
        db = psycopg2.connect(host=config.config["DB_HOST"], database=config.config["DB_DATABASE"], user=config.config["DB_USER"], password=config.config["DB_PASSWORD"])
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
    # check if model exists
    modelpath = "models/" + args.model
    if not os.path.exists(modelpath):
        logging.error(modelpath + " not found")
        return 1

    db, c = init()

    # check if target table exists
    try:
        query = "SELECT * FROM \"%s\" LIMIT 1" % args.table
        c.execute(query)
    except psycopg2.errors.UndefinedTable:
        logging.error("table \"%s\" doesn't exist" % args.table)
        sys.exit(1)

    # check which column to use
    if args.polarity:
        modelcol = "model_p"
        target = "polarity"
    else:
        modelcol = "model_i"
        target = "intensity"

    # check which rows to update
    if args.update_only:
        update_only = "WHERE %s IS NULL OR %s <> '%s'" % (modelcol, modelcol, args.model)
    else:
        update_only = ""

    # fetch rows to update
    query = "SELECT * FROM \"%s\" %s" % (args.table, update_only)
    c.execute(query)
    rows = c.fetchall()
    if not rows:
        logging.error("no rows to update")
        sys.exit(1)

    # process data
    ids = [ row[0] for row in rows ]
    df = pandas.DataFrame(ids, columns=["id"])
    df["tweet"] = [ row[2] for row in rows ]

    # check which model to use
    if args.polarity:
        # load BERT model
        model = transformers.TFBertForSequenceClassification.from_pretrained(modelpath)
        tokenizer = transformers.BertTokenizer.from_pretrained(modelpath + "/tokenizer")
        labels = {0: 0, 2: -1, 1: 1}

        # preprocess model input
        df["clean_tweet"] = df["tweet"].apply(src.standardize.clean)
        df = df.dropna()

        # compute predictions
        inputs = tokenizer(df["clean_tweet"].values.tolist(), truncation=True, padding='max_length', max_length=280, return_tensors="tf")
        outputs = model.predict([inputs["input_ids"], inputs["attention_mask"], inputs["token_type_ids"]], verbose=1)
        prob = tensorflow.nn.softmax( outputs.logits )
        df["polarity"] = [ labels[numpy.argmax(x)] for x in prob.numpy() ]

    else:
        # load model
        model = tensorflow.keras.models.load_model(modelpath, custom_objects={"standardize": src.standardize.standardize})

        # compute predictions
        df["intensity"] = [ x[0] for x in model.predict(df["tweet"].values.tolist(), verbose=1) ]

    # update database
    try:
        tuples = str(list(zip( df["id"].values, df[target].values, [args.model] * len(df) )))[1:-1]
        c.execute("UPDATE \"%s\" AS t SET %s = t2.%s, %s = t2.%s from (values %s) as t2(id,%s,%s) where t2.id = t.id" % (args.table, target, target, modelcol, modelcol, tuples, target, modelcol) )
    except psycopg2.errors.OperationalError:
        logging.error("could not complete database update")
        sys.exit(1)

    # close connection
    close(db, c)

