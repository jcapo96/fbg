from .convertSpectrum import SpectrumConverter
from .convertPeak import PeakConverter
from .convertClimaticChamber import climaticChamberConverter
from .convertRTD import RTDConverter
from .convertHumidity import HumConverter

import os, sys

class makeROOTfile():
    def __init__(self, rawDirectory, outputRootFileName):
        self.rawDirectory = rawDirectory
        self.outputRootFileName = outputRootFileName
        self.fileNames = os.listdir(self.rawDirectory)

    def make(self):
        if os.path.exists(self.outputRootFileName):
            os.remove(self.outputRootFileName)
            print(f"File '{self.outputRootFileName}' has been deleted.")
            print("****************************************************")
        else:
            print(f"File '{self.outputRootFileName}' does not exist.")
            print("****************************************************")

        for fileName in self.fileNames:
            print(fileName)
            if "LOG" in fileName.upper():
                continue
            if "specstrum" in fileName:
                try:
                    print(f"\n ******* Using Spectrum Converter ******* \n")
                    spectrum = SpectrumConverter(f"{self.rawDirectory}/{fileName}", self.outputRootFileName)
                    spectrum.fillRootFile()
                except:
                    print(f"\n Not able to process file: {self.rawDirectory}/{fileName} \n")
            if "peak" in fileName:
                try:
                    print("\n ******* Using Peak Converter *******")
                    peak = PeakConverter(f"{self.rawDirectory}/{fileName}", self.outputRootFileName)
                    peak.fillRootFile()
                except:
                    print(f"\n Not able to process file: {self.rawDirectory}/{fileName} \n")
            if "temperature" in fileName:
                try:
                    print("\n ******* Using RTD Converter *******")
                    peak = RTDConverter(f"{self.rawDirectory}/{fileName}", self.outputRootFileName)
                    peak.fillRootFile()
                except:
                    print(f"\n Not able to process file: {self.rawDirectory}/{fileName} \n")
            if "humidity" in fileName:
                try:
                    print("\n ******* Using Humidity Converter *******")
                    peak = HumConverter(f"{self.rawDirectory}/{fileName}", self.outputRootFileName)
                    peak.fillRootFile()
                except:
                    print(f"\n Not able to process file: {self.rawDirectory}/{fileName} \n")
            if "CLIMATIC" in fileName.upper():
                try:
                    print("\n ******* Using Climatic Chamber Converter *******")
                    peak = climaticChamberConverter(f"{self.rawDirectory}/{fileName}", self.outputRootFileName)
                    peak.fillRootFile()
                except:
                    print(f"\n Not able to process file: {self.rawDirectory}/{fileName} \n")

M = makeROOTfile(
    rawDirectory="/eos/user/j/jcapotor/FBGdata/Data/LN2_tests/September2023/20230925",
    outputRootFileName="/eos/user/j/jcapotor/FBGdata/ROOTFiles/Climatic_Chamber/2023_September/20230925.root",
    )

M.make()