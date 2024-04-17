import os, csv, json
import pandas as pd
import ROOT, array

class topologyConverter():
    def __init__(self, topologyFileName, outputRootFileName):
        self.topologyFileName   = topologyFileName
        self.outputRootFileName = outputRootFileName
        self.treeNames          = ["runInfo"]

    def readFile(self):
        with open(self.topologyFileName) as f:
            topology = json.load(f)
            print(topology.keys())
            for key in list(topology.keys()):
                try:
                    print(key, topology[key].keys())
                except:
                    print(key, topology[key])

    def checkFileExists(self):
        return os.path.isfile(self.outputRootFileName)

    def checkTreeExists(self):
        outputFile = ROOT.TFile(f"{self.outputRootFileName}", "READ")
        treeList = outputFile.GetListOfKeys()
        if len(treeList) == 0:
            return False
        else:
            boolTreeExists = []
            for index, treeName in enumerate(treeList):
                treeName = treeName.ReadObj()
                if isinstance(treeName, ROOT.TTree):
                    if treeName.GetName() in self.treeNames:
                        boolTreeExists.append(True)
                    else:
                        boolTreeExists.append(False)
            outputFile.Close()
            return all(boolTreeExists)

    def fillRootFile(self):
        if self.checkFileExists() is False:
            #If the file does not exists, it creates it and closes it
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "RECREATE")
            outputFile.Close()
            print(f"Creating new file at: {self.outputRootFileName}")
        if self.checkTreeExists() is False:
            #If the trees are not in the rootfile, it creates them
            print(f"Trees: {self.treeNames} not existing in the rootfile.")
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "UPDATE")
            outputTree = ROOT.TTree(self.treeNames[0], "Metadata - Run information")
            valuesToFill = {}
            for index, element in enumerate(self.header):
                valuesToFill[f"{element}"] = array.array(self.dataTypes[index], [0.0])
                outputTree.Branch(f"{element}", valuesToFill[f"{element}"], f"{element}/D")
            outputFile.cd()
            outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
            outputFile.Close()

topology = topologyConverter("/eos/user/j/jcapotor/FBGdata/Data/camara_climatica/2024MarchRuns/20240307/topology.json", "")
data = topology.readFile()