import os, csv
import pandas as pd
import ROOT, array
import datetime, xlrd
from tqdm import tqdm

class climaticChamberConverter():
    def __init__(self, climaticChamberFileName, outputRootFileName):
        self.climaticChamberFilename = climaticChamberFileName #has to contain the full path
        self.outputRootFileName      = outputRootFileName #has to contain the full path
        self.header                  = ["t", "objtemp", "objhum", "hum", "temp"]
        self.dataTypes               = ["d", "d", "d", "d", "d"]
        self.treeNames               = ["cc"]

    def prepareData(self):
        self.df = pd.read_csv(self.climaticChamberFilename, sep=";",
                              header=0, names=self.header, on_bad_lines="warn",
                              dtype=float, decimal=",")
        self.df['t'] = pd.to_numeric(self.df['t'], errors='coerce')
        self.df["t"] = (pd.to_datetime(self.df["t"], unit='d', origin='1899-12-30')).astype(int) // 10**9
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

    def fillRootFile(self):
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
            outputTree = ROOT.TTree(self.treeNames[0], "Objective and measured temperature/humidity by climatic chamber")
            valuesToFill = {}
            for index, element in enumerate(self.header):
                valuesToFill[f"{element}"] = array.array(self.dataTypes[index], [0.0])
                outputTree.Branch(f"{element}", valuesToFill[f"{element}"], f"{element}/D")
            outputFile.cd()
            outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
            outputFile.Close()
        print(f"Start filling: '{self.outputRootFileName}' from file: '{self.climaticChamberFilename}'")
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
                pbar.update(1)
                outputTree.Fill()
        outputFile.cd()
        outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
        outputFile.Close()