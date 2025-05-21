#!/bin/bash

workdir=$(pwd)
script_path=$(realpath "$0")
script_dir=$(dirname "$script_path")
cd $script_dir
uv run lacia -C $workdir

