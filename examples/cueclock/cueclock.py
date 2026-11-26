#!/usr/bin/env python3
"""Shift an SRT subtitle timestamp by a signed millisecond offset."""
import re
import sys


def shift(stamp, offset):
    match = re.fullmatch(r"(\d{2,}):(\d{2}):(\d{2}),(\d{3})", stamp)
    if match is None:
        raise ValueError("Expected HH:MM:SS,mmm")
    hours, minutes, seconds, millis = map(int, match.groups())
    seconds, millis = divmod(seconds * 1000 + millis + offset, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: cueclock TIMESTAMP MILLISECONDS")
    print(shift(sys.argv[1], int(sys.argv[2])))
