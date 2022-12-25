import setuptools


api_deps = [
    "Flask==2.2.2",
    "Flask-Bcrypt==1.0.1",
    "Flask-Cors==3.0.10",
    "Flask-JWT-Extended==4.4.4",
    "Flask-RESTful==0.3.9",
    "waitress==2.1.2"
]

core_deps = [
    "PyYAML==6.0",
    "ccxt==2.0.73",
    "emoji==2.1.0",  # used in vinai/bertweet-base
    "pandas==1.5.1",
    "peewee==3.15.3",
    "psycopg2-binary==2.9.5",
    "python-dotenv==0.21.0",
    "python-telegram-bot==13.14",
    "scikit-learn==1.1.3",
    "tensorflow==2.10.0",
    "torch==1.12.1",
    "transformers==4.23.1",
    "tweepy==4.11.0"
]

dev_deps = [
    "debugpy==1.6.3",
    "pudb==2022.1.2"
]

entry_points = {
    "console_scripts": [
        "serve = api:serve",
        "stream = strategies.hypnox.twitter:stream",
        "watch = core.watchdog:watch"
    ]
}

setuptools.setup(name="sliver",
                 version="1.0",
                 packages=["api", "models", "strategies", "core"],
                 entry_points=entry_points,
                 install_requires=api_deps + core_deps)
