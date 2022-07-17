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

def replay(argp, args):
	if args.model == None:
		logging.error("provide a model name with --model")
		return 1
	modelpath = "models/" + args.model
	if not os.path.exists(modelpath):
		logging.warning(modelpath + " not found")
		return 1

	model = tensorflow.keras.models.load_model(modelpath, custom_objects={"standardize": src.standardize.standardize})
	db, c = init()

	c.execute("SELECT * FROM stream_user")
	while True:
		rows = c.fetchmany(1024)
		for row in rows:
			intensity = "{:.8f}".format(model.predict([row[2]])[0][0])
			db.cursor().execute("UPDATE stream_user SET intensity = %s, model = %s WHERE id = %s", (intensity, args.model, row[0]))
		if not rows:
			break

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
