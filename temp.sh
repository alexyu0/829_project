#!/bin/bash

pipenv run python scripts/run_analysis.py \
    -P test_analysis \
    -T test_dumps \
    -G graphs \
    -Y \
    -c csvs \
    -S \
    -l starbucks \
    -t 120 \
    -C
echo " "
pipenv run python scripts/run_analysis.py \
    -P test_analysis \
    -T test_dumps \
    -G graphs \
    -Y \
    -c csvs \
    -S \
    -l starbucks \
    -t 120 \
    -L
echo " "
