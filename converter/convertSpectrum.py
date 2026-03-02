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
        self.channels = []  # Will be detected dynamically from file (up to 16 channels)
        self.channel_to_index = {}  # Mapping from physical channel number to array index
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

    def detectChannels(self):
        """
        Detect which channels (0-15) contain valid data by sampling the spectrum file.
        Only channels with actual data will be included in self.channels.
        Creates a mapping from physical channel number to array index.
        """
        channels_found = set()
        try:
            with open(self.spectrumFileName, 'rb') as f:
                # Read first 200 packets to detect all channels present
                for _ in range(200):
                    try:
                        packetSize = np.fromfile(f, dtype='<i4', count=1)
                        if len(packetSize) == 0:
                            break
                        packetSize = packetSize[0]
                        
                        timeStamp = np.fromfile(f, dtype='<u8', count=1)
                        if len(timeStamp) == 0:
                            break
                        
                        validityFlag = np.fromfile(f, dtype='<i4', count=1)
                        if len(validityFlag) == 0:
                            break
                        
                        channelN = np.fromfile(f, dtype='<i4', count=1)
                        if len(channelN) == 0:
                            break
                        channelN = channelN[0]
                        
                        # Only accept valid channel numbers (0-15)
                        if 0 <= channelN <= 15:
                            channels_found.add(channelN)
                        
                        # Skip rest of packet to next one
                        remaining = packetSize - 20  # 20 bytes already read
                        f.seek(remaining, 1)
                    except:
                        break
        except Exception as e:
            print(f"Warning during channel detection: {e}")
            if not channels_found:
                print("No channels detected, defaulting to [0,1,2]")
                channels_found = {0, 1, 2}
        
        self.channels = sorted(list(channels_found))
        # Create mapping from physical channel number to array index
        # e.g., if channels = [0, 3, 7], mapping = {0: 0, 3: 1, 7: 2}
        self.channel_to_index = {ch: idx for idx, ch in enumerate(self.channels)}
        print(f"Detected {len(self.channels)} active channels: {self.channels}")
        return self

    def checkTreeCompatibility(self):
        """
        Check if existing spectrum tree structure matches current file's channel count.
        Returns True if compatible, False if channel count mismatch detected.
        """
        if not self.checkFileExists():
            return True
        
        try:
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "READ")
            tree = outputFile.Get(self.treeNames[0])
            
            if not tree:
                outputFile.Close()
                return True
            
            wav_branch = tree.GetBranch("wav")
            if wav_branch:
                leaf = wav_branch.GetLeaf("wav")
                leaf_title = leaf.GetTitle()
                
                # Extract channel count from "wav[2][N][39200]" format
                import re
                match = re.search(r'\[(\d+)\]\[(\d+)\]\[(\d+)\]', leaf_title)
                if match:
                    existing_nChannels = int(match.group(2))
                    is_compatible = (existing_nChannels == len(self.channels))
                    
                    if not is_compatible:
                        print(f"\n⚠️  WARNING: Channel count mismatch detected!")
                        print(f"   Existing tree has {existing_nChannels} channels")
                        print(f"   Current file has {len(self.channels)} channels: {self.channels}")
                        print(f"   → Tree will be RECREATED to avoid data corruption\n")
                    
                    outputFile.Close()
                    return is_compatible
            
            outputFile.Close()
            return True
            
        except Exception as e:
            print(f"Warning: Could not check tree compatibility: {e}")
            return True

    def fillRootFile(self):
        # Detect channels dynamically from the spectrum file
        self.detectChannels()
        
        if self.checkFileExists() is False:
            #If the file does not exists, it creates it and closes it
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "RECREATE")
            outputFile.Close()
            print(f"Creating new file at: {self.outputRootFileName} \n")
        
        # Check tree compatibility
        tree_compatible = self.checkTreeCompatibility()
        
        if self.checkTreeExists() is False or not tree_compatible:
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
                        if datetime.utcfromtimestamp(timeStamp[1]) > datetime.utcnow():
                            timeStamp[1] = (datetime.utcfromtimestamp(timeStamp[1]) - timedelta(days=70*365+17)).timestamp()
                        channelsRead.append(channelN[0])
                        if channelN[0] not in self.channels:
                            continue
                        t[1] = timeStamp[1]
                        # Use mapping to get correct array index
                        channel_idx = self.channel_to_index[channelN[0]]
                        for index, element in enumerate(dataIni):
                            data[1][channel_idx][index] = float(element)

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
                        if datetime.utcfromtimestamp(timeStamp[0]) > datetime.utcnow():
                            timeStamp[0] = (datetime.utcfromtimestamp(timeStamp[0]) - timedelta(days=70*365+17)).timestamp()
                        channelsRead.append(channelN[0])
                        if channelN[0] not in self.channels:
                            continue
                        t[0] = timeStamp[0]
                        # Use mapping to get correct array index
                        channel_idx = self.channel_to_index[channelN[0]]
                        for index, element in enumerate(dataIni):
                            data[0][channel_idx][index] = float(element)
                        pbar.update(fileId.tell() - pbar.n)

                except:
                    persistentRead = False
        outputFile.cd()
        outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
        outputFile.Close()