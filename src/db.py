import concurrent
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

def predict(model, tweets):
	intensities = [ "{:.8f}".format(x[0]) for x in model.predict(tweets) ]
	return intensities

def replay(argp, args):
	if args.model == None:
		logging.error("provide a model name with --model")
		return 1
	modelpath = "models/" + args.model
	if not os.path.exists(modelpath):
		logging.warning(modelpath + " not found")
		return 1

	cpu_count = os.cpu_count()
	sector_size = 1024
	page_size = sector_size * cpu_count
	model = tensorflow.keras.models.load_model(modelpath, custom_objects={"standardize": src.standardize.standardize})
	db, c = init()

	c.execute("SELECT * FROM stream_user WHERE model IS NULL OR model <> '" + args.model + "'")
	while True:
		rows = c.fetchmany(page_size)
		if not rows:
			break
		#model.predict([ row[2] for row in rows ], verbose=1, use_multiprocessing=True, workers=cpu_count)

		with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count) as executor:
			ids = [ row[0] for row in rows ]
			tweets = [ row[2] for row in rows ]
			futures = {}
			for i in range(0, len(rows), sector_size):
				futures[i] = { executor.submit(predict, model, tweets[i:i+sector_size]) }
			for i, f in futures.items():
				for future in concurrent.futures.as_completed(f):
					intensities = future.result()
					for tweet_id, tweet_intensity in zip(ids[i:i+sector_size], intensities):
						db.cursor().execute("UPDATE stream_user SET intensity = %s, model = %s WHERE id = %s", (tweet_intensity, args.model, tweet_id))

	db.commit()
	c.close()
	db.close()

def store(argp, args):
	if args.input == None:
		logging.error("provide a data .tsv file name with --input")
		return 1
	if not os.path.exists(args.input):
		logging.warning(args.input + " not found")
		return 1

	db, c = init()
	sql = "COPY stream_user(created_at,text,model,intensity,polarity) FROM STDOUT WITH CSV HEADER ENCODING 'UTF8' DELIMITER AS '\t'"
	with open(args.input, "r", encoding="utf-8") as f:
		c.copy_expert(sql, f)

	db.commit()
	c.close()
	db.close()

def insert(tweet):
	db, c = init()
	sql = "INSERT INTO stream_user(created_at,text) VALUES(%s, %s)"
	c.execute(sql, (tweet["created_at"], tweet["text"]))
	db.commit()
	c.close()
	db.close()
