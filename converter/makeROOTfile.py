import os, sys

current_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(current_directory)
if current_directory not in sys.path:
    sys.path.insert(0, current_directory)
import pandas as pd

from convertSpectrum import SpectrumConverter
from convertPeak import PeakConverter
from convertClimaticChamber import climaticChamberConverter
from convertRTD import RTDConverter
from convertHumidity import HumConverter

import os, sys

class makeROOTfile():
    def __init__(self, rawDirectory):
        self.rawDirectory = rawDirectory
        self.makeConvertedDirectory()
        self.fileNames = [file for file in os.listdir(self.rawDirectory) if not file.startswith('.')]

    def makeConvertedDirectory(self):
        first, second = self.rawDirectory.split('Data')
        self.convertedDirectory = f"{first}"
        self.convertedDirectory += "ROOTFiles"
        split = second[1:].split("/")
        second = split[0:-1]
        third = split[-1]
        for item in second:
            self.convertedDirectory += f"/{item}"
        self.outputRootFileName = f"{self.convertedDirectory}/{third}.root"
        return self

    def make(self):
        if os.path.exists(self.outputRootFileName):
            os.remove(self.outputRootFileName)
            print(f"File '{self.outputRootFileName}' has been deleted.")
            print("****************************************************")
        else:
            if os.path.exists(self.convertedDirectory):
                print(f"Directory '{self.convertedDirectory}' already exists.")
            else:
                os.makedirs(self.convertedDirectory)
                print(f"File '{self.outputRootFileName}' does not exist.")
            print("****************************************************")

        for fileName in self.fileNames:
            print(fileName)
            if "LOG" in fileName.upper():
                continue
            if "spectrum" in fileName:
                # try:
                print(f"\n ******* Using Spectrum Converter ******* \n")
                spectrum = SpectrumConverter(f"{self.rawDirectory}/{fileName}", self.outputRootFileName)
                spectrum.fillRootFile()
                # except:
                #     print(f"\n Not able to process file: {self.rawDirectory}/{fileName} \n")
            if "peak" in fileName:
                # try:
                print("\n ******* Using Peak Converter *******")
                peak = PeakConverter(f"{self.rawDirectory}/{fileName}", self.outputRootFileName)
                peak.fillRootFile()
                # except:
                #     print(f"\n Not able to process file: {self.rawDirectory}/{fileName} \n")
            if "temperature" in fileName:
                # try:
                print("\n ******* Using RTD Converter *******")
                peak = RTDConverter(f"{self.rawDirectory}/{fileName}", self.outputRootFileName)
                peak.fillRootFile()
                # except:
                #     print(f"\n Not able to process file: {self.rawDirectory}/{fileName} \n")
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


path = "/eos/user/j/jcapotor/FBGdata/MAPPING/LogFile.xlsx"
logFile = pd.read_excel(path, sheet_name="all")

for index, row in logFile.iterrows():
    if row["PROCESSED"] == "YES":
        continue
    try:
        m = makeROOTfile(
            rawDirectory=row["RAW-FOLDER"],
        )
        m.make()
    except Exception as e:
        print(f"Error on file {row['RAW-FOLDER']}")
        continue

