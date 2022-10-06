import setuptools

deps = [
    "PyYAML==6.0",
    "ccxt==1.92.21",
    "nltk==3.7",
    "pandas==1.4.3",
    "peewee==3.15.1",
    "psycopg2==2.9.3",
    "python-telegram-bot==13.14",
    "scikit-learn==1.1.2",
    "tensorflow==2.9.1",
    "torch==1.12.1",
    "transformers==4.21.1",
    "tweepy==4.10.0"
]

setuptools.setup(name="hypnox",
                 version="0.1",
                 packages=["src"],
                 install_requires=deps)
