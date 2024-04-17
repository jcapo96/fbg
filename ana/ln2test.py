import ROOT
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from tqdm import tqdm
from scipy.optimize import curve_fit

def epoch_to_yyyymmdd(epoch_time):
    return datetime.utcfromtimestamp(epoch_time).strftime('%Y/%m/%d %H:%M:%S')

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

fileName = "/eos/user/j/jcapotor/FBGdata/ROOTFiles/Climatic_Chamber/2024_March/20240312.root "
outputFile = ROOT.TFile(fileName, "READ")

peakP     = outputFile.Get("peakP")
peakS     = outputFile.Get("peakS")
temp      = outputFile.Get("temp")

nEntriesT = temp.GetEntries()
timesT, dataT = [], []
plt.figure()
with tqdm(total=nEntriesT) as pbar:
    for i, entry in enumerate(temp):
        # if i > 1:
        #     break
        time = getattr(entry, "epochTime")
        # print(epoch_to_yyyymmdd(time))
        t = getattr(entry, "s1")
        timesT.append(time)
        dataT.append(t)
        pbar.update(1)

nEntries = temp.GetEntries()
for i, entry in enumerate(temp):
    if i == 0:
        t0 = getattr(entry, "epochTime")
tlast = getattr(entry, "epochTime")

plateaus = findPlateaus(temp, "s1", tolerance = 0.2, min_plateau_length=1000)

indexes = list(plateaus.keys())
t0 = plateaus[6480][0][1]
tlast = plateaus[16397][0][0]
del plateaus[9393]

nPoints = 20
midTime = np.linspace(t0, tlast, nPoints)
for index, i in enumerate(midTime):
    if index == nPoints-1:
        break
    plateaus[index] = [[midTime[index], midTime[index+1]]]

for index, plateau in plateaus.items():
    plt.axvline(plateau[0][0])
    plt.axvline(plateau[0][1])

plt.plot(timesT, dataT)
plt.savefig("ana/test.png")

data, temperature = {}, {}
for key in plateaus.keys():
    data[key] = []
    temperature[key] = []

nEntries = peakP.GetEntries()
timesP, dataP = [], []
with tqdm(total=nEntries) as pbar:
    for i, entry in enumerate(peakP):
        # if i > 1:
        #     break
        time = getattr(entry, "pepochTime") + 2*60*60
        # print(epoch_to_yyyymmdd(time))
        wav = getattr(entry, "pWav1_1")*1e12
        if wav*1e9 < 1529:
            pbar.update(1)
            continue
        for key, ptimes in plateaus.items():
            if time > (ptimes[0][0]) and time < (ptimes[0][1]):
                data[key].append(wav)
        timesP.append(time)
        dataP.append(wav)
        pbar.update(1)

nEntriesT = temp.GetEntries()
timesT, dataT = [], []
with tqdm(total=nEntriesT) as pbar:
    for i, entry in enumerate(temp):
        # if i > 1:
        #     break
        time = getattr(entry, "epochTime")
        # print(epoch_to_yyyymmdd(time))
        t = getattr(entry, "s1")
        for key, ptimes in plateaus.items():
            if time > (ptimes[0][0]) and time < (ptimes[0][1]):
                temperature[key].append(t)
        timesT.append(time)
        dataT.append(t)
        pbar.update(1)

plt.figure()
results_wav, results_temp = [], []
results_wav_err, results_temp_err = [], []

for key, value in data.items():
    # if key in [6480, 0, 1, 3]:
    #     continue
    if np.mean(temperature[key]) > 150:
        continue
    if len(data[key]) <= 1:
        continue
    results_wav.append(np.mean(data[key]))
    results_temp.append(np.mean(temperature[key]))
    results_wav_err.append(np.std(data[key]))
    results_temp_err.append(np.std(temperature[key]))

print(results_wav, results_temp)
results_temp = np.array(results_temp)
results_wav = np.array(results_wav)
results_wav_err = np.array(results_wav_err)
results_temp_err = np.array(results_temp_err)
plt.errorbar(results_temp, results_wav,
                xerr=results_temp_err, yerr=results_wav_err, fmt=".", color="blue")
def order5(x, A, B, C, D, E, F):
    return A + B*x + C*x**2 + D*x**3 + E*x**4 + F*x**5

def order4(x, A, B, C, D, E):
    return A + B*x + C*x**2 + D*x**3 + E*x**4

def order3(x, A, B, C, D):
    return A + B*x + C*x**2 + D*x**3

def parabola(x, A, B, C):
    return A + B*x + C*x**2

def line(x, A, B):
    return A + B*x

popt, _ = curve_fit(order5, results_temp, results_wav, sigma=results_wav_err, absolute_sigma=True)
print(popt)
tempOfInterest = 87
sensitivity = order4(tempOfInterest, popt[1], 2*popt[2], 3*popt[3], 4*popt[4], 5*popt[5])
xAxis = np.linspace(77, 125, 1000)
plt.plot(xAxis, order5(xAxis, *popt), label=f"Sensitivity @{tempOfInterest} K = {sensitivity:.1f} pm/K")
plt.legend()
plt.xlabel("Temperature (K)")
plt.ylabel("Wavelength (pm)")
plt.title("PEEK sample sensitivity")
plt.grid("on")
plt.savefig("ana/sens.png")

plt.figure()
sensitivity = order4(xAxis, popt[1], 2*popt[2], 3*popt[3], 4*popt[4], 5*popt[5])
plt.plot(xAxis, sensitivity, label="Sensitivity")
plt.legend()
plt.xlabel("Temperature (K)")
plt.ylabel("Sensitivity (pm/K)")
plt.title("Sensitivity for PEEK sample @ cryogenics")
plt.grid("on")
plt.savefig("ana/sensitivity.png")

plt.figure(figsize=(10,10))
# plt.subplot(1,2,1)
for index, plateau in plateaus.items():
    print(plateau)
    plt.axvline(plateau[0][0])
    plt.axvline(plateau[0][1])
plt.plot(timesT, dataT)
plt.xlabel("Epoch Time")
plt.ylabel("Temperature (K)")
# plt.subplot(1,2,2)
# plt.plot(timesP, dataP)
# plt.xlabel("Epoch Time")
# plt.ylabel("Wavelength (pm)")
plt.savefig("ana/test.png")
outputFile.Close()