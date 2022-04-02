"""Handle mapping of grip addresses to coordinates."""

import os

import pandas as pd  # To read data
from sklearn.linear_model import LinearRegression

HERE = os.path.abspath(os.path.dirname(__file__))


class Grid:
    """Load in the grid info, build a regression model, and use it to calculate location based on address."""

    def __init__(self):
        """Read in average grid locations and build model."""
        data = pd.read_csv(HERE + "/data/grid_locations.csv")  # load data set
        self.predictors = dict()
        for d in ("N", "W", "E", "S"):
            direction = data[data["direction"] == d]
            x = direction["grid"].values.reshape(
                -1, 1
            )  # values converts it into a numpy array
            y = direction["value"].values.reshape(
                -1, 1
            )  # -1 means that calculate the dimension of rows, but have 1 column
            linear_regressor = LinearRegression()  # create object for the class
            linear_regressor.fit(x, y)  # perform linear regression
            self.predictors[d] = linear_regressor

    def predict(self, direction, address):
        """Given a street address, determine relevant coordinate."""
        return self.predictors[direction].predict([[address]])[0][0]


if __name__ == "__main__":
    g = Grid()
    print(g.predict("N", 5300))
