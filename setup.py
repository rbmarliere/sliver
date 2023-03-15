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
    "ccxt==2.0.73",
    "pandas==1.5.1",
    "peewee==3.15.3",
    "psycopg2-binary==2.9.5",
    "python-dotenv==0.21.0",
    "python-telegram-bot==13.14",
    "telethon==1.27.0",
]

hypnox_deps = [
    "emoji==2.1.0",  # used in vinai/bertweet-base
    "scikit-learn==1.1.3",
    "tensorflow==2.10.0",
    "torch==1.12.1",
    "transformers==4.23.1",
    "tweepy==4.13.0"
]

dev_deps = [
    "debugpy"
]

entry_points = {
    "console_scripts": [
        "serve = api.__main__:main",
        "stream = strategies.hypnox.twitter:stream",
        "watch = core.__main__:main"
    ]
}

setuptools.setup(name="sliver",
                 version="0.5",
                 packages=["api", "models", "strategies", "core"],
                 entry_points=entry_points,
                 install_requires=api_deps + core_deps + hypnox_deps)
