import os, csv
import pandas as pd
import ROOT, array
from tqdm import tqdm

class RTDConverter():
    def __init__(self, rtdFilename, outputRootFileName):
        self.rtdFilename        = rtdFilename #has to contain the full path
        self.outputRootFileName = outputRootFileName #has to contain the full path
        self.header             = None
        self.nSensors           = None
        self.treeNames          = ["temp"]

    def prepareData(self):
        self.header = ["Date", "Time"]
        self.dataTypes = []
        with open(self.rtdFilename, "r") as csvFile:
            csvReader = csv.reader(csvFile)
            firstLine = next(csvReader)[0].split("\t")
        self.nSensors = len(firstLine) - 2
        for n in range(self.nSensors):
            self.header.append(f"s{n+1}")
            self.dataTypes.append("d")
        self.df = pd.read_csv(self.rtdFilename, sep="\t", header=None, names=self.header)
        # Combine "Date" and "Time" columns into a single datetime column
        self.df["Datetime"] = pd.to_datetime(self.df["Date"] + " " + self.df["Time"], format='%d/%m/%Y %H:%M:%S')
        # Convert datetime to epoch time
        self.df["epochTime"] = self.df["Datetime"].astype(int) * 10**-9  # Convert nanoseconds to seconds
        # Drop the original "Date", "Time", and "Datetime" columns
        self.df.drop(["Date", "Time", "Datetime"], axis=1, inplace=True)
        print(len(self.df))
        self.dataTypes.append("d") #add the u-long for the timestamp
        self.header = self.df.columns
        return self

    def checkFileExists(self):
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
            self.prepareData()
        if self.checkFileExists() is False:
            #If the file does not exists, it creates it and closes it
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "RECREATE")
            outputFile.Close()
            print(f"Creating new file at: {self.outputRootFileName}")
        if self.checkTreeExists() is False:
            #If the trees are not in the rootfile, it creates them
            print(f"Trees: {self.treeNames} not existing in the rootfile.")
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "UPDATE")
            outputTree = ROOT.TTree(self.treeNames[0], "Temperature measured by RTDs")
            valuesToFill = {}
            for index, element in enumerate(self.header):
                valuesToFill[f"{element}"] = array.array(self.dataTypes[index], [0.0])
                outputTree.Branch(f"{element}", valuesToFill[f"{element}"], f"{element}/D")
            outputFile.cd()
            outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
            outputFile.Close()
        print(f"Start filling: '{self.outputRootFileName}' from file: '{self.rtdFilename}'")
        outputFile = ROOT.TFile(f"{self.outputRootFileName}", "UPDATE")
        outputTree = outputFile.Get(self.treeNames[0])
        valuesToFill = {}
        for index, element in enumerate(self.header):
            valuesToFill[f"{element}"] = array.array(self.dataTypes[index], [0.0])
            outputTree.SetBranchAddress(f"{element}", valuesToFill[f"{element}"])
        print(f"{len(self.df)} entries in total.")
        with tqdm(total=len(self.df)) as pbar:
            for index, row in self.df.iterrows():
                for element in self.df.columns:
                    valuesToFill[f"{element}"][0] = (row[element])
                outputTree.Fill()
                pbar.update(1)

        outputFile.cd()
        outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
        outputFile.Close()
