"""Handle mapping of grip addresses to coordinates."""


class Grid:
    """Using regression model, calculate location based on address."""

    lines = {
        "N": (6.56106944, 1900205.24500993),
        "W": (-6.80865418, 1176786.98556475),
        "E": (6.79533698, 1177450.57112369),
        "S": (-6.42085299, 1902839.08039695),
    }

    def predict(self, direction, address):
        """Given a street address, determine relevant coordinate."""
        slope, intercept = self.lines[direction]
        return slope * address + intercept


if __name__ == "__main__":
    g = Grid()
    print(g.predict("N", 5300))
