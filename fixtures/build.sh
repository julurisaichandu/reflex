#!/bin/sh
# Builds every sandbox fixture image as reflex-fixture/<dir name>.
set -e
cd "$(dirname "$0")"
for dir in */; do
  docker build -t "reflex-fixture/${dir%/}" "$dir"
done
