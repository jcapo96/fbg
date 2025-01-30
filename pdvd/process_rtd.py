import h5py, os, lmfit, cmath, pickle
from datetime import datetime
import numpy as np
from tqdm import tqdm
from datetime import datetime
import pandas as pd
from scipy.interpolate import UnivariateSpline
import scipy as sc

path = "/eos/user/j/jcapotor/PDVDdata/rtd_data/"

container = pd.DataFrame()
for nfile, filename in enumerate(tqdm(os.listdir(path), desc="Processing files", unit="file")):
    # if nfile > 2:
    #     break
    filename = fr"{path}{filename}"
    try:
        data = pd.read_csv(filename, header=0)
        container = pd.concat([container, data], ignore_index=True)
    except:
        continue

container["Unnamed: 0"] = pd.to_datetime(container["Unnamed: 0"])
container = container.set_index("Unnamed: 0")
print(container.resample("10min").mean())