#!/usr/bin/env python

import sys


def main():
    from pganonymizer.cli import main
    try:
        exit_status = main()
    except KeyboardInterrupt:
        exit_status = 1
    sys.exit(exit_status)


if __name__ == '__main__':
    main()
