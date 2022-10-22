import setuptools

deps = [
    "PyYAML",
    "ccxt",
    "emoji",
    "nltk",
    "pandas",
    "peewee",
    "plotly",
    "psycopg2-binary",
    "python-telegram-bot",
    "scikit-learn",
    "tensorflow",
    "torch",
    "transformers",
    "tweepy"
]

setuptools.setup(name="hypnox",
                 version="0.01",
                 packages=["hypnox"],
                 install_requires=deps)
