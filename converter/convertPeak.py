import os, csv
import pandas as pd
import ROOT, array
from datetime import datetime, timedelta
from tqdm import tqdm

def reshapeEpochTime(timestamp):
    return (datetime.utcfromtimestamp(timestamp*10**-9) - timedelta(days=70*365+17)).timestamp()

class PeakConverter():
    def __init__(self, peakFileName, outputRootFileName):
        self.peakFileName       = peakFileName #has to contain the full path
        self.outputRootFileName = outputRootFileName #has to contain the full path
        self.header             = None
        self.nSensors           = None
        self.treeNames          = ["peakP", "peakS"]

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

    def fillRootFile(self, chunksize=None):
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
            outputTreeP = ROOT.TTree(self.treeNames[0], "P-Peaks fitted by I4G")
            outputTreeS = ROOT.TTree(self.treeNames[1], "S-Peaks fitted by I4G")
            valuesToFill = {}
            for index, element in enumerate(self.header):
                if "Wav" in element or "Ptime" in element or "epoch" in element:
                    valuesToFill[f"p{element}"] = array.array(self.dataTypes[index], [0.0])
                    outputTreeP.Branch(f"{element}", valuesToFill[f"p{element}"], f"p{element}/D")
                    valuesToFill[f"s{element}"] = array.array(self.dataTypes[index], [0.0])
                    outputTreeS.Branch(f"{element}", valuesToFill[f"s{element}"], f"s{element}/D")
                else:
                    continue
            outputFile.cd()
            outputTreeP.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
            outputTreeS.Write(self.treeNames[1], ROOT.TObject.kWriteDelete)
            outputFile.Close()

        print(f"Start filling: '{self.outputRootFileName}' from file: '{self.peakFileName}'")
        outputFile = ROOT.TFile(f"{self.outputRootFileName}", "UPDATE")
        outputTreeP = outputFile.Get(self.treeNames[0])
        outputTreeS = outputFile.Get(self.treeNames[1])
        valuesToFill = {}
        for index, element in enumerate(self.header):
            if "Wav" in element or "Ptime" in element or "epoch" in element:
                valuesToFill[f"p{element}"] = array.array(self.dataTypes[index], [0.0])
                valuesToFill[f"s{element}"] = array.array(self.dataTypes[index], [0.0])
                outputTreeP.SetBranchAddress(f"{element}", valuesToFill[f"p{element}"])
                outputTreeS.SetBranchAddress(f"{element}", valuesToFill[f"s{element}"])
            else:
                continue
        peakData = pd.read_csv(self.peakFileName, sep="\t", header=None, names=self.header,
                               chunksize=chunksize, on_bad_lines="warn")
        peakData["epochTime"] = peakData["epochTime"].apply(reshapeEpochTime)
        if chunksize is not None:
            for nChunk, chunk in enumerate(peakData):
                for index, row in chunk.iterrows():
                    for element in chunk.columns:
                        if (index%2 == True) and ("Wav" in element or "Ptime" in element or "epoch" in element):
                            valuesToFill[f"p{element}"][0] = (row[element])
                        elif (index%2 == False) and ("Wav" in element or "Ptime" in element or "epoch" in element):
                            valuesToFill[f"s{element}"][0] = (row[element])
                    if index%2 == True:
                        outputTreeP.Fill()
                    elif index%2 == False:
                        outputTreeS.Fill()
        elif chunksize is None:
            chunk = peakData
            print(f"{len(chunk)} entries in total:")
            with tqdm(total=len(chunk)) as pbar:
                for index, row in chunk.iterrows():
                    # if index > 10000:
                    #     break
                    pbar.update(1)
                    for element in chunk.columns:
                        if (index%2 == True) and ("Wav" in element or "Ptime" in element or "epoch" in element):
                            valuesToFill[f"p{element}"][0] = (row[element])
                        elif (index%2 == False) and ("Wav" in element or "Ptime" in element or "epoch" in element):
                            valuesToFill[f"s{element}"][0] = (row[element])
                    if index%2 == True:
                        outputTreeP.Fill()
                    elif index%2 == False:
                        outputTreeS.Fill()
        outputFile.cd()
        outputTreeP.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
        outputTreeS.Write(self.treeNames[1], ROOT.TObject.kWriteDelete)
        outputFile.Close()