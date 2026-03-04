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
        Detect which channels (0-15) have real fiber data by:
        1. Navigating with nPoints (robust, same as fillRootFile) to avoid
           corrupt packetSize jumps.
        2. Sampling amplitude per channel - channels without a fiber connected
           show max(|data|) < ~10 counts (noise floor), while real fibers
           show thousands of counts.
        """
        channel_max_amplitude = {}
        MIN_NPOINTS = 100
        MAX_NPOINTS = 50000
        MAX_SYNC_RETRIES = 10000
        AMPLITUDE_THRESHOLD = 50  # counts; noise floor is ~2-8, real signal is >1000

        try:
            file_size = os.path.getsize(self.spectrumFileName)
            sync_retries = 0
            with open(self.spectrumFileName, 'rb') as f:
                while f.tell() < file_size - 44:
                    pos_before = f.tell()
                    try:
                        packetSize   = np.fromfile(f, dtype='<i4', count=1)
                        timeStamp    = np.fromfile(f, dtype='<u8', count=1)
                        validityFlag = np.fromfile(f, dtype='<i4', count=1)
                        channelN     = np.fromfile(f, dtype='<i4', count=1)
                        fibreN       = np.fromfile(f, dtype='<i4', count=1)
                        startWL      = np.fromfile(f, dtype='<d',  count=1)
                        finalWL      = np.fromfile(f, dtype='<d',  count=1)
                        nPoints      = np.fromfile(f, dtype='<i4', count=1)

                        if any(len(x) == 0 for x in [packetSize, timeStamp, validityFlag,
                                                      channelN, fibreN, startWL, finalWL, nPoints]):
                            break

                        nPoints_val    = nPoints[0]
                        packetSize_val = packetSize[0]
                        ch             = channelN[0]
                        expected_packetSize = nPoints_val * 2 + 40

                        valid = (MIN_NPOINTS <= nPoints_val <= MAX_NPOINTS and
                                 0 <= ch <= 15 and
                                 abs(packetSize_val - expected_packetSize) < 100)

                        if not valid:
                            f.seek(pos_before + 1)
                            sync_retries += 1
                            if sync_retries > MAX_SYNC_RETRIES:
                                break
                            continue

                        sync_retries = 0

                        # Read data and track max amplitude per channel
                        data = np.fromfile(f, dtype='<i2', count=nPoints_val)
                        amp = int(np.max(np.abs(data)))
                        if ch not in channel_max_amplitude:
                            channel_max_amplitude[ch] = amp
                        else:
                            channel_max_amplitude[ch] = max(channel_max_amplitude[ch], amp)

                    except:
                        break

        except Exception as e:
            print(f"Warning during channel detection: {e}")
            if not channel_max_amplitude:
                print("No channels detected, defaulting to [0,1,2]")
                channel_max_amplitude = {0: 9999, 1: 9999, 2: 9999}

        # Keep only channels with real fiber signal above noise floor
        channels_found = {ch for ch, amp in channel_max_amplitude.items()
                          if amp >= AMPLITUDE_THRESHOLD}

        if channel_max_amplitude:
            print(f"Channel detection summary (noise floor ≈ 2-8 counts, threshold = {AMPLITUDE_THRESHOLD}):")
            for ch in sorted(channel_max_amplitude.keys()):
                amp = channel_max_amplitude[ch]
                status = "✓ FIBER DETECTED" if ch in channels_found else "✗ NO FIBER (noise only)"
                print(f"  Channel {ch:2d}: max amplitude = {amp:6d}  {status}")

        self.channels = sorted(list(channels_found))
        self.channel_to_index = {ch: idx for idx, ch in enumerate(self.channels)}
        print(f"✅ Final channel list: {self.channels} ({len(self.channels)} channels)")
        return self

    def getExistingTreeChannelCount(self):
        """
        Get the number of channels in existing tree, or None if tree doesn't exist.
        """
        if not self.checkFileExists():
            return None
        
        try:
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "READ")
            tree = outputFile.Get(self.treeNames[0])
            
            if not tree:
                outputFile.Close()
                return None
            
            # Get the wav branch to check dimensions
            wav_branch = tree.GetBranch("wav")
            if wav_branch:
                # Get leaf title which contains dimensions like "wav[2][N][39200]"
                leaf = wav_branch.GetLeaf("wav")
                leaf_title = leaf.GetTitle()
                
                # Extract channel count from leaf title
                import re
                match = re.search(r'\[(\d+)\]\[(\d+)\]\[(\d+)\]', leaf_title)
                if match:
                    existing_nChannels = int(match.group(2))
                    outputFile.Close()
                    return existing_nChannels
            
            outputFile.Close()
            return None
            
        except Exception as e:
            print(f"Warning: Could not check existing channel count: {e}")
            return None
    
    def mergeChannelLists(self, existing_nChannels):
        """
        When tree has more channels than current file, we need to preserve the original
        channel list. We assume channels are stored sequentially starting from 0.
        Current file channels will fill their positions, rest stay at zero.
        
        Returns: (all_channels_list, max_channel_count)
        """
        if existing_nChannels is None:
            # No existing tree, use detected channels
            return self.channels, len(self.channels)
        
        if existing_nChannels <= len(self.channels):
            # Current file has same or more channels
            return self.channels, len(self.channels)
        
        # Tree has MORE channels - need to accommodate all of them
        # Assume tree was created with channels [0, 1, 2, ..., existing_nChannels-1]
        # (This is a safe assumption since channels are stored by index)
        all_channels = list(range(existing_nChannels))
        
        print(f"   Tree expects channels: {all_channels}")
        print(f"   File contains channels: {self.channels}")
        print(f"   Missing channels will be filled with zeros")
        
        return all_channels, existing_nChannels
    
    def checkTreeCompatibility(self):
        """
        Check if current file can be added to existing tree.
        Strategy: Use max(existing, current) channels and pad with zeros.
        Returns: (is_compatible, all_channels_list, max_channel_count, needs_recreation)
        """
        existing_nChannels = self.getExistingTreeChannelCount()
        
        if existing_nChannels is None:
            # No existing tree, use current file's channel count
            return (True, self.channels, len(self.channels), False)
        
        if existing_nChannels == len(self.channels):
            # Perfect match, no issues
            return (True, self.channels, len(self.channels), False)
        
        # Mismatch detected
        if existing_nChannels > len(self.channels):
            # Tree has MORE channels than current file (e.g., tree=5, file=4)
            # Solution: Pad current file with zeros for missing channels
            print(f"\n⚠️  Channel count mismatch:")
            print(f"   Existing tree: {existing_nChannels} channels")
            print(f"   Current file:  {len(self.channels)} channels {self.channels}")
            print(f"   → Will pad file data with ZEROS for missing channels")
            all_channels, max_count = self.mergeChannelLists(existing_nChannels)
            return (True, all_channels, max_count, False)
        else:
            # Tree has FEWER channels than current file (e.g., tree=4, file=5)
            # Solution: Recreate tree with more channels
            print(f"\n❌ Channel count mismatch - tree needs expansion:")
            print(f"   Existing tree: {existing_nChannels} channels")
            print(f"   Current file:  {len(self.channels)} channels {self.channels}")
            print(f"   → Tree will be RECREATED with {len(self.channels)} channels")
            print(f"   ⚠️  Note: Old data will be lost. Process files in order from largest to smallest channel count.")
            return (False, self.channels, len(self.channels), True)

    def fillRootFile(self):
        # Detect channels dynamically from the spectrum file
        self.detectChannels()
        
        if self.checkFileExists() is False:
            #If the file does not exists, it creates it and closes it
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "RECREATE")
            outputFile.Close()
            print(f"Creating new file at: {self.outputRootFileName} \n")
        
        # ✅ NEW: Check compatibility and determine channel count to use
        is_compatible, all_channels, tree_nChannels, _ = self.checkTreeCompatibility()
        
        if not is_compatible:
            print(f"\n{'='*70}")
            print(f"Tree needs recreation. Proceeding with {tree_nChannels} channels.")
            print(f"{'='*70}\n")
        
        # Use tree_nChannels (max of existing and current) for array dimensions
        # This allows padding with zeros for files with fewer channels
        use_nChannels = tree_nChannels
        
        # Update channel_to_index mapping to work with the full channel list
        # Map physical channel numbers to their index in the tree array
        self.channel_to_index = {ch: idx for idx, ch in enumerate(all_channels)}
        
        if self.checkTreeExists() is False or not is_compatible:
            #If the trees are not in the rootfile, it creates them
            print(f"Trees: {self.treeNames} not existing in the rootfile. \n")
            print(f"Creating tree with {use_nChannels} channel slots for channels: {all_channels}\n")
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
            data = np.array([[[0.0 for _ in range(0, 39200)] for _ in range(use_nChannels)] for _ in range(self.nPols)])

            outputTree.Branch("t", timeStamp, f"t[{self.nPols}]/D")
            outputTree.Branch("wav", data, f"wav[{self.nPols}][{use_nChannels}][39200]/D")

            outputFile.cd()
            outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
            outputFile.Close()

        print(f"Start filling: '{self.outputRootFileName}' from file: '{self.spectrumFileName}'")
        print(f"File has {len(self.channels)} channels {self.channels}, tree accommodates {use_nChannels} channels {all_channels}")
        if len(self.channels) < use_nChannels:
            missing_channels = [ch for ch in all_channels if ch not in self.channels]
            print(f"→ Channels {missing_channels} will be filled with ZEROS (not present in file)\n")
        else:
            print()
        
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
        data = np.array([[[0.0 for _ in range(0, 39200)] for _ in range(use_nChannels)] for _ in range(self.nPols)])

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