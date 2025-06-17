#!/bin/bash

set -ex

WORKSPACE=$(pwd)

rm -rf dist
rm -rf build

mkdir -p build/runtime
cd build/runtime
# curl --output python-3.12.10-embed-amd64.zip https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip
cp $WORKSPACE/python-3.12.10-embed-amd64.zip .
unzip python-3.12.10-embed-amd64.zip

cd $WORKSPACE

uv sync
uv build
uv export > requirements-vendor.txt
uv pip install -r requirements-vendor.txt --target build/vendor
uv pip install dist/*.whl --target build/vendor
cp __main__.py build
cp lacia.* build
