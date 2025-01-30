import h5py, os, lmfit, cmath, pickle
from datetime import datetime
import numpy as np
from tqdm import tqdm
from datetime import datetime
import pandas as pd
from scipy.interpolate import UnivariateSpline
import scipy as sc

path = "/eos/user/j/jcapotor/PDVDdata/fit_spectrums/"

container = {}
for nfile, filename in enumerate(tqdm(os.listdir(path), desc="Processing files", unit="file")):
    # if nfile > 2:
    #     break
    filename = fr"{path}{filename}"
    try:
        with open(filename, "rb") as file:
            data = pickle.load(file)
            for channel in data.keys():
                for sensor in data[channel].keys():
                    if fr"{channel}_{sensor}" not in container.keys():
                        container[fr"{channel}_{sensor}"] = pd.DataFrame()
                    container[fr"{channel}_{sensor}"] = pd.concat([container[fr"{channel}_{sensor}"], data[channel][sensor]], ignore_index=True)
    except:
        continue

for key in container.keys():
    container[key].to_csv(fr"/eos/user/j/jcapotor/PDVDdata/fits/{key}.csv")