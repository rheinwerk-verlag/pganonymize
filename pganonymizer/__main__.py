#!/usr/bin/env python
from __future__ import absolute_import

import sys


def main():
    from pganonymizer.cli import main
    try:
        main()
        exit_status = 0
    except KeyboardInterrupt:
        exit_status = 1
    sys.exit(exit_status)


if __name__ == '__main__':
    main()
