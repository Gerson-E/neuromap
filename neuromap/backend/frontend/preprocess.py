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

def format_time(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"

start = time.time()

DATA_DIR = "/data"

subject_id = '001'

cmd = [
    "docker", "compose", "run", "--rm",
    "freesurfer",
    "recon-all",
    "-i", f"/input/{subject_id}.nii",  # or .mgz if your input is already MGZ
    "-s", subject_id,
    "-all", # runs autorecon1,2,3 and produces brain.mgz
]

subprocess.run(cmd, check=True)

end = time.time()
elapsed = end - start

print("Time elapsed:", format_time(elapsed))