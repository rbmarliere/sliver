import setuptools

api_deps = [
    "flask",
    "flask-bcrypt",
    "flask-jwt-extended",
    "flask-restful",
    "waitress"
]

core_deps = [
    "PyYAML",
    "ccxt",
    "emoji",
    "nltk",
    "pandas",
    "peewee",
    "plotly",
    "psycopg2-binary",
    "python-dotenv",
    "python-telegram-bot",
    "scikit-learn",
    "tensorflow",
    "torch",
    "transformers",
    "tweepy"
]

entry_points = {
    "console_scripts": [
        "serve = api:serve",
        "stream = core.twitter:stream",
        "watch = core.watchdog:watch"
    ]
}

setuptools.setup(name="hypnox",
                 version="0.02",
                 packages=["api", "core"],
                 entry_points=entry_points,
                 install_requires=api_deps + core_deps)
