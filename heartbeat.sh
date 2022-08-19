#!/bin/bash

dir=$(dirname $0)
source $dir/.venv/bin/activate

#./hypnox download --since last_beat
#./hypnox replay 

date -u
$dir/hypnox refresh
echo ""
