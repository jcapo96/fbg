import os
import ROOT, array
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm

class SpectrumConverter():
    def __init__(self, spectrumFileName, outputRootFileName):
        self.spectrumFileName = spectrumFileName #has to contain the full path
        self.outputRootFileName      = outputRootFileName #has to contain the full path
        self.treeNames = ["spectrumP", "spectrumS"]
        self.header = ["packetSize", "epochTime", "validityFlag", "channelN", "fibreN", "startWL", "endWL", "nPoints", "amplitude"]
        self.channels = [0,1]

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
            outputTreeP = ROOT.TTree(self.treeNames[0], "P-Spectrums from I4G")
            outputTreeS = ROOT.TTree(self.treeNames[1], "S-Spectrums from I4G")

            packetSize = np.array([0.0], dtype=np.int32)
            timeStamp = np.array([0.0], dtype=np.double)
            validityFlag = np.array([0.0], dtype=np.int32)
            channelN = np.array([0.0], dtype=np.int32)
            fibreN = np.array([0.0], dtype=np.int32)
            startWL = np.array([0.0], dtype=np.float32)
            finalWL = np.array([0.0], dtype=np.float32)
            nPoints = np.array([0.0], dtype=np.int32)
            data = {}
            for ch in self.channels:
                data[ch] = np.array([0.0 for i in range(0, 39200)], dtype=np.float32)

            outputTreeP.Branch("packetSize", packetSize, f"packetSize/I")
            outputTreeP.Branch("epochTime", timeStamp, f"timeStamp/D")
            outputTreeP.Branch("validityFlag", validityFlag, f"validityFlag/I")
            outputTreeP.Branch("channelN", channelN, f"channelN/I")
            outputTreeP.Branch("fibreN", fibreN, f"fibreN/I")
            outputTreeP.Branch("startWL", startWL, f"startWL/F")
            outputTreeP.Branch("finalWL", finalWL, f"finalWL/F")
            outputTreeP.Branch("nPoints", nPoints, f"nPoints/I")
            for ch in self.channels:
                outputTreeP.Branch(f"Wav{ch}", data[ch], f"data[39200]/F")

            outputTreeS.Branch("packetSize", packetSize, f"packetSize/I")
            outputTreeS.Branch("epochTime", timeStamp, f"timeStamp/D")
            outputTreeS.Branch("validityFlag", validityFlag, f"validityFlag/I")
            outputTreeS.Branch("channelN", channelN, f"channelN/I")
            outputTreeS.Branch("fibreN", fibreN, f"fibreN/I")
            outputTreeS.Branch("startWL", startWL, f"startWL/F")
            outputTreeS.Branch("finalWL", finalWL, f"finalWL/F")
            outputTreeS.Branch("nPoints", nPoints, f"nPoints/I")
            for ch in self.channels:
                outputTreeS.Branch(f"Wav{ch}", data[ch], f"data[39200]/F")

            outputFile.cd()
            outputTreeP.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
            outputTreeS.Write(self.treeNames[1], ROOT.TObject.kWriteDelete)
            outputFile.Close()

        print(f"Start filling: '{self.outputRootFileName}' from file: '{self.spectrumFileName}' \n")
        outputFile = ROOT.TFile(f"{self.outputRootFileName}", "UPDATE")
        outputTreeP = outputFile.Get(self.treeNames[0])
        outputTreeS = outputFile.Get(self.treeNames[1])
        packetSize = np.array([0.0], dtype=np.int32)
        timeStamp = np.array([0.0], dtype=np.double)
        validityFlag = np.array([0.0], dtype=np.int32)
        channelN = np.array([0.0], dtype=np.int32)
        fibreN = np.array([0.0], dtype=np.int32)
        startWL = np.array([0.0], dtype=np.float32)
        finalWL = np.array([0.0], dtype=np.float32)
        nPoints = np.array([0.0], dtype=np.int32)
        data = {}
        for ch in self.channels:
            data[ch] = np.array([0.0 for i in range(0, 39200)], dtype=np.float32)

        outputTreeP.SetBranchAddress("packetSize", packetSize)
        outputTreeP.SetBranchAddress("epochTime", timeStamp)
        outputTreeP.SetBranchAddress("validityFlag", validityFlag)
        outputTreeP.SetBranchAddress("channelN", channelN)
        outputTreeP.SetBranchAddress("fibreN", fibreN)
        outputTreeP.SetBranchAddress("startWL", startWL)
        outputTreeP.SetBranchAddress("finalWL", finalWL)
        outputTreeP.SetBranchAddress("nPoints", nPoints)
        for ch in self.channels:
            outputTreeP.SetBranchAddress(f"Wav{ch}", data[ch])

        outputTreeS.SetBranchAddress("packetSize", packetSize)
        outputTreeS.SetBranchAddress("epochTime", timeStamp)
        outputTreeS.SetBranchAddress("validityFlag", validityFlag)
        outputTreeS.SetBranchAddress("channelN", channelN)
        outputTreeS.SetBranchAddress("fibreN", fibreN)
        outputTreeS.SetBranchAddress("startWL", startWL)
        outputTreeS.SetBranchAddress("finalWL", finalWL)
        outputTreeS.SetBranchAddress("nPoints", nPoints)
        for ch in self.channels:
            outputTreeS.SetBranchAddress(f"Wav{ch}", data[ch])

        persistentRead = True
        file_size = os.path.getsize(self.spectrumFileName)
        nEvent = 0
        fileId=open(self.spectrumFileName,'rb')
        channelsRead = []
        with tqdm(total=file_size, unit='bytes', unit_scale=True) as pbar:
            while persistentRead == True:
                # if nEvent > 100:
                #     persistentRead = False
                try:
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
                    if channelN[0] not in self.channels:
                        continue
                    for index, element in enumerate(dataIni):
                        data[channelN[0]][index] = element
                    channelsRead.append(channelN[0])
                    if np.sum(self.channels) == np.sum(channelsRead):
                        channelsRead = []
                        nEvent += 1
                    if nEvent%2 == True:
                        outputTreeP.Fill()
                    elif nEvent%2 == False:
                        outputTreeS.Fill()
                    pbar.update(fileId.tell() - pbar.n)
                except:
                    persistentRead = False
        outputFile.cd()
        outputTreeP.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
        outputTreeS.Write(self.treeNames[1], ROOT.TObject.kWriteDelete)
        outputFile.Close()