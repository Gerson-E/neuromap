# RUN DOCKER

import os, sys
import subprocess
import time

import numpy as np
sys.path.insert(0, r"../model/")
from utils import dataLoader, saliency, visualize
from model import NativeSpacemodel
import pandas as pd
import tensorflow as tf

## filePaths - replace with your file paths - should point to brain.mgz
filePaths = ["../subjects/002/mri/brain.mgz"] 
csvLocation = ""

csvName = "BAtest.csv"

# limit TF memory usage
physical_devices = tf.config.list_physical_devices('GPU')
try:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)
except:
    print("Could not limit memory usage")

BAPredictor = NativeSpacemodel.get_model()
modelWeights = "../model/model/NativeSpaceWeight.h5"
BAPredictor.load_weights(modelWeights)

brains = dataLoader.dataLoader(filePaths)

[n, h, w, d] = np.shape(brains)
print("Loaded ", n, " brains")

# make sure the prepocessed brains have 128^3 volumes  
assert h==w==d == 128

predictions = BAPredictor.predict(brains)
dfBA = pd.DataFrame(predictions)
dfBA.columns = ["BA"]
dfBA.to_csv(csvLocation+csvName)

print('Estimated Biological Brain Age:', dfBA['BA'][0], 'yrs')