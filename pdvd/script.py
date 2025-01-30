import h5py, os, lmfit, cmath, pickle
from datetime import datetime
import numpy as np
from tqdm import tqdm
import pandas as pd
from scipy.interpolate import UnivariateSpline
import scipy as sc
import sys

def custom_spectrum_3(l, amp, lammbda_bragg, lammbda, delta_n, L):
    j = 1j
    #lammbda_bragg = 2 * neff * lammbda
    neff = lammbda_bragg/(2*lammbda)
    beta = 2 * np.pi * neff / l
    #L = lammbda * num_periods
    delta_beta = 2 * beta - 2 * np.pi / lammbda
    #delta_n = delta_n_0 * np.abs(np.cos(2*np.pi*L/lammbda))
    k = np.pi * delta_n / (neff * lammbda_bragg)
    #k = np.pi * delta_n / (neff * l)
    B = np.array([cmath.sqrt(k**2 - (db / 2) ** 2) for db in delta_beta])
    #max_val = 700
    #B = np.clip(B, -max_val, max_val)
    exponent_A1 = j * (delta_beta / 2) * 0
    numerator_A1 = B * np.cosh(B * (0 - L)) - j * (delta_beta / 2) * np.sinh(B * (0 - L))
    denominator_A1 = B * np.cosh(B * L) + j * (delta_beta / 2) * np.sinh(B * L)
    A1 = np.exp(exponent_A1) * (numerator_A1 / denominator_A1)
    exponent_A2 = -j * (delta_beta / 2) * 0
    numerator_A2 = np.sinh(B * (0 - L))
    denominator_A2 = B * np.cosh(B * L) + j * (delta_beta / 2) * np.sinh(B * L)
    A2 = k * np.exp(exponent_A2) * (numerator_A2 / denominator_A2)
    reflex_spectrum = np.abs(A2 / A1) ** 2
    return reflex_spectrum*amp

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        path_to_data = f"/eos/user/j/jcapotor/FBGdata/Data/NP02/{filename}"
        filename_split = filename.split(".")[0].split("_")
        new_filename = f"{filename_split[3]}_{filename_split[2]}_{filename_split[1]}_{filename_split[4]}_{filename_split[5]}_{filename_split[6]}.csv"
        datafile = h5py.File(path_to_data, 'r')
        spectrums = datafile['SPECTRAL_CHANNEL_DATA']
        fit_results = {}
        for nchan, channel in enumerate(spectrums.keys()):
            if channel not in fit_results.keys():
                fit_results[channel] = {}
            channel_data = spectrums[channel]
            for nEvent, key in enumerate(channel_data.keys()):
                data = np.array(channel_data[key][:])
                peaks, amps = sc.signal.find_peaks(data, height=0.1, distance=100)
                if len(fit_results[channel]) == 0:
                    for nSensor in range(len(peaks)):
                        fit_results[channel][nSensor+1] = {}
                xAxis = np.linspace(1529, 1568.2, 39200)
                timestamp = channel_data[key].attrs["timestamp"]
                evt_unixtime = int(datetime.strptime(timestamp, "%d/%m/%Y %H:%M:%S").timestamp())
                for nSensor, index in enumerate(peaks):
                    cmodel = lmfit.Model(custom_spectrum_3, nan_policy="omit")
                    gmodel = lmfit.models.GaussianModel()
                    gpars = gmodel.make_params(center=xAxis[index],
                                        sigma=0.1,
                                        amplitude=30)
                    gout = gmodel.fit(data[index-60:index+60], gpars, x=xAxis[index-60:index+60])
                    cparams = cmodel.make_params()
                    cparams['amp'].set(value=30, min=0, max=1e3)
                    cparams['lammbda_bragg'].set(value=xAxis[index], min=1529, max=1568.2)
                    cparams['lammbda'].set(value=xAxis[index]/(2*1.447), min=530, max=534)
                    cparams['delta_n'].set(value=1.1997e-05, min=1e-6, max=1e-4, vary=False)
                    cparams['L'].set(value=0.5e7, min=0.1e-7, max=2e7, vary=True)
                    cout = cmodel.fit(data[index-150:index+150], cparams, l=xAxis[index-150:index+150])
                    fit_results[channel][nSensor+1][nEvent] = {}
                    fit_results[channel][nSensor+1][nEvent]["cbragg"] = cout.params["lammbda_bragg"].value
                    fit_results[channel][nSensor+1][nEvent]["cbragg_err"] = cout.params["lammbda_bragg"].stderr
                    fit_results[channel][nSensor+1][nEvent]["credchi"] = cout.redchi
                    fit_results[channel][nSensor+1][nEvent]["gbragg"] = gout.params["center"].value
                    fit_results[channel][nSensor+1][nEvent]["gbragg_err"] = gout.params["center"].stderr
                    fit_results[channel][nSensor+1][nEvent]["gsigma"] = gout.params["sigma"].value
                    fit_results[channel][nSensor+1][nEvent]["gsigma_err"] = gout.params["sigma"].stderr
                    fit_results[channel][nSensor+1][nEvent]["gredchi"] = gout.redchi
                    fit_results[channel][nSensor+1][nEvent]["camp"] = cout.params["amp"].value
                    fit_results[channel][nSensor+1][nEvent]["clammbda"] = cout.params["lammbda"].value
                    fit_results[channel][nSensor+1][nEvent]["cdelta_n"] = cout.params["delta_n"].value
                    fit_results[channel][nSensor+1][nEvent]["cL"] = cout.params["L"].value
                    fit_results[channel][nSensor+1][nEvent]["timestamp"] = evt_unixtime

        for channel in fit_results.keys():
            for nSensor in fit_results[channel].keys():
                fit_results[channel][nSensor] = pd.DataFrame(fit_results[channel][nSensor]).T
                print(fr"{channel}_{nSensor}")
                print(fit_results[channel][nSensor])
        with open(f"/eos/user/j/jcapotor/PDVDdata/fit_spectrums/{new_filename}", "wb") as file:
            pickle.dump(fit_results, file)
    except Exception as e:
        print(f"Error processing {filename}: {e}")
