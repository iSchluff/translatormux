#!/usr/bin/env python3

import argparse
from lib import run, config
import logging

logging.basicConfig()
log = logging.getLogger("translatormux")


def main():
    argp = argparse.ArgumentParser(allow_abbrev=False)

    argp.add_argument("--debug", help="Print debug log", action="store_true")

    args = argp.parse_args()
    if args.debug:
        log.setLevel(logging.DEBUG)

    run.start(["voc-lounge"], config.Config)


if __name__ == "__main__":
    main()
