#!/bin/sh
set -eu
/opt/cross-toolchain/bin/cc -std=c11 -O2 hoststamp.c -o hoststamp
