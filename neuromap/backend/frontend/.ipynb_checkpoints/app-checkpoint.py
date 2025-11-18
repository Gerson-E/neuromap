import os
import subprocess

DATA_DIR = "/data"

cmd = [
    "docker", "compose", "run", "--rm",
    "freesurfer",
    "recon-all",
    "-i", "/input/sample.nii",   # path *inside* the container
    "-s", subject_id,
    "-all"
]

subprocess.run(cmd, check=True)

    # # Run brain age model
    # cmd2 = [
    #     "docker", "compose", "run", "--rm",
    #     "brainage",
    #     "python", "predict.py",
    #     "--subjdir", f"/data/subjects/{subject_id}"
    # ]

    # result = subprocess.run(cmd2, capture_output=True, text=True, check=True)
    # age = result.stdout.strip()

    # return {"brain_age": age}
