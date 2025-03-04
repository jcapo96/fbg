import os, csv
import pandas as pd
import ROOT
from datetime import datetime, timedelta
from tqdm import tqdm
import numpy as np
import subprocess

def reshapeEpochTime(timestamp):
    dt = datetime.utcfromtimestamp(timestamp * 10**-9)
    today = datetime.utcnow()
    if dt > today:
        dt -= timedelta(days=66*365 + 30*9 + 11, hours=6)
    return dt.timestamp()

class PeakConverter():
    def __init__(self, peakFileName, outputRootFileName):
        self.peakFileName       = peakFileName #has to contain the full path
        self.outputRootFileName = outputRootFileName #has to contain the full path
        self.header             = None
        self.nSensors           = None
        self.treeNames          = ["peak"]
        self.nPols              = 2

    def createHeader(self):
        self.header = ["timeStamp", "epochTime", "errorFlag0", "sweepNumber"]
        self.dataTypes = ["u", "d", "d", "d"]
        with open(self.peakFileName, "r") as csvFile:
            csvReader = csv.reader(csvFile)
            firstLine = next(csvReader)[0].split("\t")
        self.nSensors = int((len(firstLine)-4)/6)
        nItems = 6
        for i in range(self.nSensors):
            try:
                channel = str(int(firstLine[4 + i*nItems].split("Channel")[1]))
            except:
                channel = str(int(firstLine[4 + i*nItems].split("Ch")[1]))
            sensor = f"{i+1}"
            self.header.append(f"channelS{i+1}")
            self.header.append(f"fibreS{i+1}")
            self.header.append(f"sensor{i+1}")
            self.header.append(f"errorFlagS{i+1}")
            self.header.append(f"Wav{channel}_{sensor}")
            self.header.append(f"Ptime{channel}_{sensor}")

            self.dataTypes.append("u")
            self.dataTypes.append("u")
            self.dataTypes.append("u")
            self.dataTypes.append("d")
            self.dataTypes.append("d")
            self.dataTypes.append("d")
        return self

    def checkFileExists(self):
        if os.path.isfile(self.outputRootFileName):
            print(f"File {self.outputRootFileName} exists.")
        return os.path.isfile(self.outputRootFileName)

    def checkTreeExists(self):
        outputFile = ROOT.TFile(f"{self.outputRootFileName}", "READ")
        treeList = outputFile.GetListOfKeys()
        names = []
        if len(treeList) == 0:
            return False
        else:
            boolTreeExists = []
            boolTreeNotExists = []
            for index, treeName in enumerate(treeList):
                treeName = treeName.ReadObj()
                names.append(treeName.GetName())
                if isinstance(treeName, ROOT.TTree):
                    if treeName.GetName() in self.treeNames:
                        boolTreeExists.append(True)
                    else:
                        boolTreeNotExists.append(False)
            print(f"Already existing trees: {names}")
            outputFile.Close()
            if (len(boolTreeExists) == len(self.treeNames)):
                return True
            else:
                return False

    def fillRootFile(self, chunksize=1e6):
        if self.header is None:
            #Checks if the header is already created in the class, if not, it creates the header
            self.createHeader()
        if self.checkFileExists() is False:
            #If the file does not exists, it creates it and closes it
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "RECREATE")
            outputFile.Close()
            print(f"Creating new file at: {self.outputRootFileName} \n")
        if self.checkTreeExists() is False:
            #If the trees are not in the rootfile, it creates them
            print(f"Trees: {self.treeNames} not existing in the rootfile. \n")
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "UPDATE")
            outputTree = ROOT.TTree(self.treeNames[0], "Peaks fitted by I4G")

            # t = np.array([0.0 for _ in range(self.nPols)])
            # wav = np.array([0.0 for _ in range(self.nSensors)] for _ in range(self.nPols))
            # sweep = np.array([0.0 for _ in range(self.nSensors)] for _ in range(self.nPols)) #this is the time the signal takes to come back to the I4G (SWEEP TIME)
            # ch = np.array([0.0 for _ in range(self.nSensors)])
            # pos = np.array([0.0 for _ in range(self.nSensors)])

            t = np.zeros(self.nPols, dtype=np.float64)
            wav = np.zeros((self.nPols, self.nSensors), dtype=np.float64)
            sweep = np.zeros((self.nPols, self.nSensors), dtype=np.float64)
            ch = np.zeros((self.nPols, self.nSensors), dtype=np.float64)
            pos = np.zeros((self.nPols, self.nSensors), dtype=np.float64)


            outputTree.Branch("t", t, f"t[{self.nPols}]/D")
            outputTree.Branch("wav", wav, f"wav[{self.nPols}][{self.nSensors}]/D")
            outputTree.Branch("sweep", sweep, f"sweep[{self.nPols}][{self.nSensors}]/D")
            outputTree.Branch("ch", ch, f"ch[{self.nSensors}]/D")
            outputTree.Branch("pos", pos, f"pos[{self.nSensors}]/D")

            outputFile.cd()
            outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
            outputFile.Close()

        print(f"Start filling: '{self.outputRootFileName}' from file: '{self.peakFileName}'")
        outputFile = ROOT.TFile(f"{self.outputRootFileName}", "UPDATE")
        outputTree = outputFile.Get(self.treeNames[0])

        # t = np.array([0.0 for _ in range(self.nPols)])
        # wav = np.array([[0.0 for _ in range(self.nSensors)] for _ in range(self.nPols)])
        # sweep = np.array([[0.0 for _ in range(self.nSensors)] for _ in range(self.nPols)])
        # ch = np.array([[0.0 for _ in range(self.nSensors)] for _ in range(self.nPols)])
        # pos = np.array([[0.0 for _ in range(self.nSensors)] for _ in range(self.nPols)])

        t = np.zeros(self.nPols, dtype=np.float64)
        wav = np.zeros((self.nPols, self.nSensors), dtype=np.float64)
        sweep = np.zeros((self.nPols, self.nSensors), dtype=np.float64)
        ch = np.zeros((self.nPols, self.nSensors), dtype=np.float64)
        pos = np.zeros((self.nPols, self.nSensors), dtype=np.float64)


        outputTree.SetBranchAddress("t", t)
        outputTree.SetBranchAddress("wav", wav)
        outputTree.SetBranchAddress("sweep", sweep)
        outputTree.SetBranchAddress("ch", ch)
        outputTree.SetBranchAddress("pos", pos)

        # outputTree.Branch("t", t, f"t[{self.nPols}]/D")
        # outputTree.Branch("wav", wav, f"wav[{self.nPols}][{self.nSensors}]/D")
        # outputTree.Branch("sweep", sweep, f"sweep[{self.nPols}][{self.nSensors}]/D")
        # outputTree.Branch("ch", ch, f"ch[{self.nSensors}]/D")
        # outputTree.Branch("pos", pos, f"pos[{self.nSensors}]/D")


        peakData = pd.read_csv(self.peakFileName, sep="\t", header=None, names=self.header,
                               chunksize=chunksize, on_bad_lines="warn")

        result = subprocess.run(['wc', '-l', self.peakFileName], capture_output=True, text=True)
        line_count = int(result.stdout.split()[0])

        if chunksize is not None:
            with tqdm(total=line_count) as pbar:
                for nChunk, chunk in enumerate(peakData):
                    chunk["epochTime"] = chunk["epochTime"].apply(reshapeEpochTime)
                    for index, row in chunk.iterrows():
                        nSens = 0
                        for element in chunk.columns:
                            if (index%2 == True):
                                if "epoch" in element:
                                    t[1] = row[element]
                                elif "Wav" in element:
                                    wav[1][nSens] = row[element]
                                    ch[1][nSens] = int(element.split("Wav")[1].split("_")[0])
                                    pos[1][nSens] = float(element.split("Wav")[1].split("_")[1])*50
                                elif "Ptime" in element:
                                    sweep[1][nSens] = row[element]
                                    nSens += 1
                            elif (index%2 == False):
                                if "epoch" in element:
                                    t[0] = row[element]
                                elif "Wav" in element:
                                    wav[0][nSens] = row[element]
                                    ch[0][nSens] = int(element.split("Wav")[1].split("_")[0])
                                    pos[0][nSens] = float(element.split("Wav")[1].split("_")[1])*50
                                elif "Ptime" in element:
                                    sweep[0][nSens] = row[element]
                                    nSens += 1
                        if index%2 == True:
                            outputTree.Fill()
                        pbar.update(1)
        elif chunksize is None:
            chunk = peakData
            chunk["epochTime"] = chunk["epochTime"].apply(reshapeEpochTime)
            print(f"{len(chunk)} entries in total:")
            with tqdm(total=len(chunk)) as pbar:
                for index, row in chunk.iterrows():
                    nSens = 0
                    for element in chunk.columns:
                        if (index%2 == True):
                            if "epoch" in element:
                                t[0] = row[element]
                            elif "Wav" in element:
                                wav[0][nSens] = row[element]
                                ch[0][nSens] = int(element.split("Wav")[1].split("_")[0])
                                pos[0][nSens] = float(element.split("Wav")[1].split("_")[1])*50
                            elif "Ptime" in element:
                                sweep[0][nSens] = row[element]
                                nSens += 1
                        elif (index%2 == False):
                            if "epoch" in element:
                                t[1] = row[element]
                            elif "Wav" in element:
                                wav[1][nSens] = row[element]
                                ch[1][nSens] = int(element.split("Wav")[1].split("_")[0])
                                pos[1][nSens] = float(element.split("Wav")[1].split("_")[1])*50
                            elif "Ptime" in element:
                                sweep[0][nSens] = row[element]
                                nSens += 1
                    if index%2 == True:
                        outputTree.Fill()
                    pbar.update(1)
        outputFile.cd()
        outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
        outputFile.Close()