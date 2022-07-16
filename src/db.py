from src.standardize import standardize
import os
import psycopg2
import tensorflow

def replay(argp, args):
	if args.model == None:
		logging.error("provide a model name with --model")
		return 1
	modelpath = "models/" + args.model
	if not os.path.exists(modelpath):
		logging.warning(modelpath + " not found")
		return 1

	model = tensorflow.keras.models.load_model(modelpath, custom_objects={"standardize": standardize})
	db = psycopg2.connect(host=args.config["DB_HOST"], database=args.config["DB_DATABASE"], user=args.config["DB_USER"], password=args.config["DB_PASSWORD"])
	cursor = db.cursor()

	cursor.execute("SELECT * FROM stream_user")
	while True:
		rows = cursor.fetchmany(1024)
		for row in rows:
			intensity = "{:.8f}".format(model.predict([row[2]])[0][0])
			db.cursor().execute("UPDATE stream_user SET intensity = %s, model = %s WHERE id = %s", (intensity, args.model, row[0]))
		if not rows:
			break

	db.commit()
	cursor.close()
	db.close()

def store(argp, args):
	if args.input == None:
		logging.error("provide a data .tsv file name with --input")
		return 1
	if not os.path.exists(args.input):
		logging.warning(args.input + " not found")
		return 1

	db = psycopg2.connect(host=args.config["DB_HOST"], database=args.config["DB_DATABASE"], user=args.config["DB_USER"], password=args.config["DB_PASSWORD"])
	cursor = db.cursor()

	query = "COPY stream_user(created_at,text,model,intensity,polarity) FROM STDOUT WITH CSV HEADER ENCODING 'UTF8' DELIMITER AS '\t'"
	with open(args.input, "r", encoding="utf-8") as f:
		cursor.copy_expert(query, f)

	db.commit()
	cursor.close()
	db.close()

