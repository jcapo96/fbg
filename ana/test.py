import ROOT
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from tqdm import tqdm
from scipy.optimize import curve_fit

fileName = "/eos/user/j/jcapotor/FBGdata/ROOTFiles/LN2_Tests/2023_September/20230925.root"
outputFile = ROOT.TFile(fileName, "READ")

# Access the spectrumP tree
spectrumP = outputFile.Get("spectrumP")
spectrumS = outputFile.Get("spectrumS")
peakP     = outputFile.Get("peakP")
peakS     = outputFile.Get("peakS")
cc        = outputFile.Get("cc")
temp      = outputFile.Get("temp")
hum       = outputFile.Get("hum")

def findPlateaus(tree, branch="objtemp", tolerance=5e-4, min_plateau_length=100):
    nEntries = tree.GetEntries()
    PLATEAU_TIMES = {}  # Dictionary to store start and end timestamps for each plateau

    # Get the value and timestamp of the first entry
    tree.GetEntry(0)
    VALUE0, T0 = getattr(tree, branch), getattr(tree, "epochTime")

    # Initialize variables to track plateau
    plateau_start = T0
    plateau_length = 0

    # Iterate over entries
    for i in range(1, nEntries):
        tree.GetEntry(i)
        VALUE, T = getattr(tree, branch), getattr(tree, "epochTime")

        # Check if the current value is close to the previous value
        if abs(VALUE - VALUE0) < tolerance:
            # If not already in a plateau, mark the start of the plateau
            if plateau_length == 0:
                plateau_start = T0
            plateau_length += 1
        else:
            # If we were in a plateau and its length is greater than min_plateau_length, mark the end and record it
            if plateau_length >= min_plateau_length:
                if i - min_plateau_length not in PLATEAU_TIMES:
                    PLATEAU_TIMES[i - min_plateau_length] = []
                PLATEAU_TIMES[i - min_plateau_length].append((plateau_start, T0))
            # Reset plateau variables
            plateau_length = 0

        # Update previous value and timestamp
        VALUE0 = VALUE
        T0 = T

    # If still in a plateau at the end and its length is greater than min_plateau_length, mark its end and record it
    if plateau_length >= min_plateau_length:
        if nEntries - min_plateau_length not in PLATEAU_TIMES:
            PLATEAU_TIMES[nEntries - min_plateau_length] = []
        PLATEAU_TIMES[nEntries - min_plateau_length].append((plateau_start, T))

    return PLATEAU_TIMES


def epoch_to_yyyymmdd(epoch_time):
    return datetime.utcfromtimestamp(epoch_time).strftime('%Y/%m/%d %H:%M:%S')


times = findPlateaus(cc, branch="objtemp")

data, temperature = {}, {}
plt.figure()
cnt = 0
colors = ["red", "blue", "green", "orange", "red", "blue", "green", "orange", "red", "blue", "green", "orange", "red"]
for key in times.keys():
    plt.axvline(times[key][0][0], color=colors[cnt])
    plt.axvline(times[key][0][1], color=colors[cnt])
    data[key] = []
    temperature[key] = []
    cnt += 1

peakdata, peaktime = [], []
nEntries = peakS.GetEntries()
with tqdm(total=nEntries) as pbar:
    for i in range(nEntries):
        peakS.GetEntry(i)
        time, value = getattr(peakS, "sepochTime") + 2*60*60, getattr(peakS, "sWav1_1")*1e12
        peaktime.append(time)
        peakdata.append(value)
        for key, ptimes in times.items():
            if time > (ptimes[0][0] + 10*60) and time < (ptimes[0][1]):
                data[key].append(value)
        pbar.update(1)

tempdata, temptime = [], []
nEntries = temp.GetEntries()
with tqdm(total=nEntries) as pbar:
    for i in range(nEntries):
        temp.GetEntry(i)
        time, value = getattr(temp, "epochTime"), getattr(temp, "s1")
        tempdata.append(value)
        temptime.append(time)
        for key, ptimes in times.items():
            if time > (ptimes[0][0] + 10*60) and time < (ptimes[0][1]):
                temperature[key].append(value)
        pbar.update(1)

plt.plot(peaktime, peakdata)
plt.savefig("converter/plateaus_peak.png")
plt.figure()
cnt = 0
for key in times.keys():
    plt.axvline(times[key][0][0], color=colors[cnt])
    plt.axvline(times[key][0][1], color=colors[cnt])
    cnt += 1
plt.plot(temptime, tempdata)
plt.savefig("converter/plateaus_temp.png")
plt.figure()
results_wav, results_temp = [], []
for key, value in data.items():
    if len(data[key]) <= 1:
        continue
    results_wav.append(np.mean(data[key]))
    results_temp.append(np.mean(temperature[key]))
    plt.errorbar(np.mean(temperature[key]), np.mean(data[key]),
                 xerr=np.std(temperature[key]), yerr=np.std(data[key]), fmt=".", color="blue")

results_temp = np.array(results_temp)
results_wav = np.array(results_wav)
def line(x, A, B):
    return A + B*x

popt, _ = curve_fit(line, results_temp, results_wav)
print(popt)
plt.plot(results_temp, line(results_temp, popt[0], popt[1]), label=f"Sensitivity = {popt[1]:.1f} pm/K")
plt.legend()
plt.xlabel("Temperature (K)")
plt.ylabel("Wavelength (pm)")
plt.title("PEEK sample sensitivity")
plt.grid("on")
plt.savefig("converter/test.png")
outputFile.Close()
