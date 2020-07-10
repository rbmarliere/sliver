#!/bin/bash

rm data/{filter,parse,predict,split,tally}/*
./hypnox filter --input data/raw
./hypnox split --input data/filter --timeframe 4h
./hypnox parse --input data/split
./hypnox predict --input data/split
./hypnox tally --input data/predict

