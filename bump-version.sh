#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: ./bump-version.sh <version>"
  echo "Example: ./bump-version.sh 1.0.0"
  exit 1
fi

VERSION=$1

echo "Bumping version to $VERSION..."

# Update README.md
sed -i "s/badge\/Version-.*-blue/badge\/Version-$VERSION-blue/g" README.md

# Update cascabel-covers.py
sed -i "s/APP_VERSION = \".*\"/APP_VERSION = \"$VERSION\"/g" cascabel-covers.py

echo "Done!"
