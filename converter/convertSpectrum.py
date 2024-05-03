import os
import ROOT, array
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm

class SpectrumConverter():
    def __init__(self, spectrumFileName, outputRootFileName):
        self.spectrumFileName = spectrumFileName #has to contain the full path
        self.outputRootFileName      = outputRootFileName #has to contain the full path
        self.treeNames = ["spectrum"]
        self.header = ["packetSize", "epochTime", "validityFlag", "channelN", "fibreN", "startWL", "endWL", "nPoints", "amplitude"]
        self.channels = [0,1]
        self.nPols = 2

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
        if self.checkFileExists() is False:
            #If the file does not exists, it creates it and closes it
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "RECREATE")
            outputFile.Close()
            print(f"Creating new file at: {self.outputRootFileName} \n")
        if self.checkTreeExists() is False:
            #If the trees are not in the rootfile, it creates them
            print(f"Trees: {self.treeNames} not existing in the rootfile. \n")
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "UPDATE")
            outputTree = ROOT.TTree(self.treeNames[0], "Spectrums from I4G")

            packetSize = np.array([0.0], dtype=np.int32)
            timeStamp = np.array([0.0], dtype=np.double)
            validityFlag = np.array([0.0], dtype=np.int32)
            channelN = np.array([0.0], dtype=np.int32)
            fibreN = np.array([0.0], dtype=np.int32)
            startWL = np.array([0.0], dtype=np.float32)
            finalWL = np.array([0.0], dtype=np.float32)
            nPoints = np.array([0.0], dtype=np.int32)
            data = np.array([[[0.0 for _ in range(0, 39200)] for _ in range(len(self.channels))] for _ in range(self.nPols)])

            outputTree.Branch("t", timeStamp, f"t[{self.nPols}]/D")
            outputTree.Branch("wav", data, f"wav[{self.nPols}][{len(self.channels)}][39200]/D")

            outputFile.cd()
            outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
            outputFile.Close()

        print(f"Start filling: '{self.outputRootFileName}' from file: '{self.spectrumFileName}' \n")
        outputFile = ROOT.TFile(f"{self.outputRootFileName}", "UPDATE")
        outputTree = outputFile.Get(self.treeNames[0])
        packetSize = np.array([0.0], dtype=np.int32)
        timeStamp = np.array([0.0 for _ in range(self.nPols)], dtype=np.double)
        t = np.array([0.0 for _ in range(self.nPols)], dtype=np.double)
        validityFlag = np.array([0.0], dtype=np.int32)
        channelN = np.array([0.0], dtype=np.int32)
        fibreN = np.array([0.0], dtype=np.int32)
        startWL = np.array([0.0], dtype=np.float32)
        finalWL = np.array([0.0], dtype=np.float32)
        nPoints = np.array([0.0], dtype=np.int32)
        data = np.array([[[0.0 for _ in range(0, 39200)] for _ in range(len(self.channels))] for _ in range(self.nPols)])

        outputTree.SetBranchAddress("t", t)
        outputTree.SetBranchAddress("wav", data)

        persistentRead = True
        file_size = os.path.getsize(self.spectrumFileName)
        nEvent = 0
        fileId=open(self.spectrumFileName,'rb')
        channelsRead = []
        with tqdm(total=file_size, unit='bytes', unit_scale=True) as pbar:
            while persistentRead == True:
                # if nEvent > 10:
                #     persistentRead = False
                try:
                    if int(np.sum(channelsRead)) == int(np.sum([0, 9, 2, 11, 4, 13, 6, 15, 8, 1, 10, 3, 12, 5, 14, 7])):
                        channelsRead = []
                        if nEvent%2 == True:
                            outputTree.Fill()
                        nEvent += 1

                    if nEvent%2 == True:
                        packetSize[0] = np.fromfile(fileId, dtype='<i4', count=1)[0]
                        timeStamp[1] = int((np.fromfile(fileId, dtype='<u8', count=1))[0]) * 10**-9
                        validityFlag[0] = np.fromfile(fileId, dtype='<i4', count=1)[0]
                        channelN[0] = np.fromfile(fileId, dtype='<i4', count=1)[0]
                        fibreN[0] = np.fromfile(fileId, dtype='<i4', count=1)[0]
                        startWL[0] = np.fromfile(fileId, dtype='<d', count=1)[0]
                        finalWL[0] = np.fromfile(fileId, dtype='<d', count=1)[0]
                        nPoints[0] = np.fromfile(fileId, dtype='<i4', count=1)[0]
                        dataIni = np.fromfile(fileId, dtype='<i2', count=nPoints[0])
                        timeStamp[1] = (datetime.utcfromtimestamp(timeStamp[1]) - timedelta(days=70*365+17)).timestamp()
                        channelsRead.append(channelN[0])
                        if channelN[0] not in self.channels:
                            continue
                        t[1] = timeStamp[1]
                        for index, element in enumerate(dataIni):
                            data[1][channelN[0]][index] = float(element)

                        pbar.update(fileId.tell() - pbar.n)
                    elif nEvent%2 == False:
                        packetSize[0] = np.fromfile(fileId, dtype='<i4', count=1)[0]
                        timeStamp[0] = int((np.fromfile(fileId, dtype='<u8', count=1))[0]) * 10**-9
                        validityFlag[0] = np.fromfile(fileId, dtype='<i4', count=1)[0]
                        channelN[0] = np.fromfile(fileId, dtype='<i4', count=1)[0]
                        fibreN[0] = np.fromfile(fileId, dtype='<i4', count=1)[0]
                        startWL[0] = np.fromfile(fileId, dtype='<d', count=1)[0]
                        finalWL[0] = np.fromfile(fileId, dtype='<d', count=1)[0]
                        nPoints[0] = np.fromfile(fileId, dtype='<i4', count=1)[0]
                        dataIni = np.fromfile(fileId, dtype='<i2', count=nPoints[0])
                        timeStamp[0] = (datetime.utcfromtimestamp(timeStamp[0]) - timedelta(days=70*365+17)).timestamp()
                        channelsRead.append(channelN[0])
                        if channelN[0] not in self.channels:
                            continue
                        t[0] = timeStamp[0]
                        for index, element in enumerate(dataIni):
                            data[0][channelN[0]][index] = float(element)
                        pbar.update(fileId.tell() - pbar.n)

                except:
                    persistentRead = False
        outputFile.cd()
        outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
        outputFile.Close()