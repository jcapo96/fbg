import ROOT
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from tqdm import tqdm

class Waveform():
    def __init__(self, entry):
        self.entry = entry
        self.ampThreshold = 0.1
        self.getWaveformData()
        self.findPeaks()

    def getWaveformData(self):
        self.packetSize = getattr(entry, "packetSize")
        self.timeStamp = getattr(self.entry, "timeStamp")
        self.validityFlags = getattr(self.entry, "validityFlag")
        self.channelN = getattr(entry, "channelN")
        self.fibreN = getattr(self.entry, "fibreN")
        self.startWL = getattr(self.entry, "startWL")
        self.finalWL = getattr(self.entry, "finalWL")
        self.nPoints = getattr(self.entry, "nPoints")
        self.waveform = np.array(getattr(self.entry, "data"))
        self.wavelength = np.linspace(self.startWL, self.finalWL, self.nPoints)
        return self

    def findPeaks(self):
        self.indexes, self.heights = find_peaks(self.waveform,
                                                height=np.max(self.waveform)*self.ampThreshold,
                                                distance=1000/((self.finalWL - self.startWL)/self.nPoints))
        self.heights = self.heights["peak_heights"]

        self.peakInd = {f"Ind{nSensor+1}":index for nSensor, index in enumerate(self.indexes)}
        self.peakPos = {f"Wav{nSensor+1}":self.wavelength[index] for nSensor, index in enumerate(self.indexes)}
        self.peakAmp = {f"Amp{nSensor+1}":height for nSensor, height in enumerate(self.heights)}
        return self

    def gaus(self, x,a,x0,sigma):
        return a*np.exp(-(x-x0)**2/(2*sigma**2))

    def fitPeaks(self, fitPoints=300):
        self.wav, amp, sigma = {}, {}, {}
        plt.figure()
        for indexName, index in self.peakInd.items():
            ampToFit = self.waveform[int(index-fitPoints/2):int(index+fitPoints/2)]
            wavToFit = self.wavelength[int(index-fitPoints/2):int(index+fitPoints/2)]
            plt.plot(wavToFit, ampToFit)
            # print([np.max(ampToFit), wavToFit[int(fitPoints/2)], wavToFit[-1]-wavToFit[0]])
            popt, pcov = curve_fit(self.gaus, wavToFit, ampToFit, p0=[np.max(ampToFit), wavToFit[int(fitPoints/2)], wavToFit[-1]-wavToFit[0]])
            name = indexName.split("Ind")[1]
            self.wav[f"Wav{name}"] = popt[1]
            plt.plot(wavToFit, self.gaus(wavToFit, popt[0], popt[1], popt[2]))
            plt.savefig("test.png")
        return self


    def plot(self):
        self.findPeaks()
        print(self.peakPos)
        plt.plot(self.wavelength, self.waveform)
        for pos in self.peakPos:
            plt.axvline(pos)
        plt.savefig("test.png")


inputFilename = "/Users/jcapo/cernbox/FBGdata/ROOTFiles/Climatic_Chamber/2024_March/20240306.root"
inputFile = ROOT.TFile(inputFilename, "READ")

tree = inputFile.Get("spectrumS")
nEntries = tree.GetEntries()
pbar = tqdm(total=nEntries)
wav, time, peakPos = [], [], []
for i, entry in enumerate(tree):
    waveform = Waveform(entry)
    # if waveform.channelN != 1:
    #     pbar.update(1)
    #     continue
    # if i > 1:
    #     break
    waveform.fitPeaks()
    peakPos.append(waveform.peakPos["Wav1"])
    wav.append(waveform.wav["Wav1"])
    time.append(waveform.timeStamp)
    pbar.update(1)
pbar.close()

# plt.plot(time, wav, label="Gaussian fits")
# plt.plot(time, peakPos, label="Peak Finder Algorithm")
plt.plot(time, np.array(wav)-np.array(peakPos))
plt.legend()
plt.savefig("test.png")
inputFile.Close()