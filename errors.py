class Error(Exception):
    def __init__(self, message):
        self.message = message


class ConnectionError(Error):
    def __str__(self):
        return f"Connection error: {self.message}"

# ADD MORE ERRORS....
