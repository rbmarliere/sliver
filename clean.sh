#!/bin/bash

rm data/{filter,parse,predict,split,tally,vader}/*
./hypnox filter --input data/raw
./hypnox split --input data/filter --timeframe 4h
./hypnox vader --input data/split
./hypnox parse --input data/vader
#./hypnox predict --input data/split
#./hypnox tally --input data/predict

