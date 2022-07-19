import logging
import os
import psycopg2
import src.config
import src.standardize
import tensorflow

def init():
	config = src.config.Config()
	db = psycopg2.connect(host=config.config["DB_HOST"], database=config.config["DB_DATABASE"], user=config.config["DB_USER"], password=config.config["DB_PASSWORD"])
	cursor = db.cursor()
	return db, cursor

def close(db, c):
	db.commit()
	c.close()
	db.close()

def replay(argp, args):
	if args.model == None:
		logging.error("provide a model name with --model")
		return 1
	modelpath = "models/" + args.model
	if not os.path.exists(modelpath):
		logging.warning(modelpath + " not found")
		return 1
	if args.polarity:
		modelcol = "model_p"
		target = "polarity"
	else:
		modelcol = "model_i"
		target = "intensity"
	if args.table:
		table = args.table
	else:
		table = "stream_user"

	model = tensorflow.keras.models.load_model(modelpath, custom_objects={"standardize": src.standardize.standardize})
	db, c = init()

	c.execute("SELECT * FROM \"%s\" WHERE %s IS NULL OR %s <> '%s' ORDER BY id ASC" % (table, modelcol, modelcol, args.model))
	while True:
		rows = c.fetchmany(100000)
		if not rows:
			break
		ids = [ row[0] for row in rows ]
		tweets = [ row[2] for row in rows ]
		scores = [ "{:.8f}".format(x[0]) for x in model.predict(tweets, verbose=1, use_multiprocessing=True, workers=os.cpu_count) ]
		for tweet_id, tweet_score in zip(ids, scores):
			db.cursor().execute("UPDATE \"%s\" SET %s = %s, %s = '%s' WHERE id = %s" % (table, target, tweet_score, modelcol, args.model, tweet_id))

	close(db, c)

def insert(tweet):
	db, c = init()
	sql = "INSERT INTO stream_user(time,tweet) VALUES(%s, %s)"
	c.execute(sql, (tweet["time"], tweet["tweet"]))
	close(db, c)
