#!/bin/bash

# Activate the virtual environment
source /afs/cern.ch/work/j/jcapotor/software/fbg/pdvd/np02_data_processing/bin/activate

# Run the Python script with the provided argument
python3 script.py "$1"