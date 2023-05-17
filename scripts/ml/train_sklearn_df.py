import argparse

import pandas
import sklearn.model_selection
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV

# https://bibliotecadigital.fgv.br/dspace/handle/10438/33113


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument("input", type=str)
    args = argp.parse_args()

    df = pandas.read_csv(args.input)

    train_df, test_df = sklearn.model_selection.train_test_split(
        df,
        test_size=0.1,
        random_state=93,
    )
    train_size = int(len(df) * (1 - 0.1))
    train_df = df[:train_size]
    test_df = df[train_size:]

    model = RandomForestRegressor(random_state=109, verbose=1)

    X_train = train_df.drop("operation", axis=1)
    y_train = train_df["operation"]
    X_test = test_df.drop("operation", axis=1)
    y_test = test_df["operation"]

    params = {
        "n_estimators": [100, 200, 600, 1000],
        "max_features": [2, 4, 6, 8],
    }
    grid = GridSearchCV(
        model,
        param_grid=params,
        verbose=1,
        cv=5,
        return_train_score=True,
        n_jobs=-1,
    )
    grid.fit(X_train, y_train)

    model = grid.best_estimator_
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    results = X_test.copy()
    results["PREVISAO"] = predictions
    print("Score: ", round(model.score(X_test, y_test), 3))


if __name__ == "__main__":
    main()
