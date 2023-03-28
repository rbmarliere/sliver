#!/usr/bin/env python3

from sliver.alert import get_client


if __name__ == "__main__":
    client = get_client("user")
    client.start()
