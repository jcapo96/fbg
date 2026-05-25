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
        dt -= timedelta(days=70*365+17, minutes=1)
    return dt.timestamp()

class PeakConverter():
    def __init__(self, peakFileName, outputRootFileName):
        self.peakFileName       = peakFileName #has to contain the full path
        self.outputRootFileName = outputRootFileName #has to contain the full path
        self.header             = None
        self.nSensors           = None
        self.treeNames          = ["peak"]
        self.nPols              = 2

    @staticmethod
    def getSensorCount(peakFileName):
        """
        Quickly detect the number of sensors in a peak file by reading only the first line.
        Used for sorting peak files by sensor count before processing.
        
        Args:
            peakFileName: Full path to the peak file
            
        Returns:
            int: Number of sensors in the file
        """
        try:
            with open(peakFileName, "r") as csvFile:
                csvReader = csv.reader(csvFile)
                firstLine = next(csvReader)[0].split("\t")
            nSensors = int((len(firstLine) - 4) / 6)
            return nSensors
        except Exception as e:
            print(f"⚠️  Warning: Could not detect sensor count for {peakFileName}")
            print(f"   Error: {e}")
            return 0  # Return 0 so file is processed last

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
            print(f"File {self.outputRootFileName} exists. VICKY.")
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

    def getExistingTreeSensorCount(self):
        """
        Get the number of sensors in existing tree, or None if tree doesn't exist.
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
                # Get leaf title which contains dimensions like "wav[2][4]"
                leaf = wav_branch.GetLeaf("wav")
                leaf_title = leaf.GetTitle()
                
                # Extract sensor count from leaf title
                import re
                match = re.search(r'\[(\d+)\]\[(\d+)\]', leaf_title)
                if match:
                    existing_nSensors = int(match.group(2))
                    outputFile.Close()
                    return existing_nSensors
            
            outputFile.Close()
            return None
            
        except Exception as e:
            print(f"Warning: Could not check existing sensor count: {e}")
            return None
    
    def checkTreeCompatibility(self):
        """
        Check if current file can be added to existing tree.
        Strategy: Use max(existing, current) sensors and pad with zeros.
        Returns: (is_compatible, max_sensors, needs_expansion)
        """
        existing_nSensors = self.getExistingTreeSensorCount()
        
        if existing_nSensors is None:
            # No existing tree, use current file's sensor count
            return (True, self.nSensors, False)
        
        if existing_nSensors == self.nSensors:
            # Perfect match, no issues
            return (True, self.nSensors, False)
        
        # Mismatch detected
        if existing_nSensors > self.nSensors:
            # Tree has MORE sensors than current file (e.g., tree=5, file=4)
            # Solution: Pad current file with zeros for missing sensors
            print(f"\n⚠️  Sensor count mismatch:")
            print(f"   Existing tree: {existing_nSensors} sensors")
            print(f"   Current file:  {self.nSensors} sensors")
            print(f"   → Will pad file data with ZEROS for sensors {self.nSensors+1}-{existing_nSensors}")
            return (True, existing_nSensors, False)
        else:
            # Tree has FEWER sensors than current file (e.g., tree=4, file=5)
            # Solution: Need to recreate tree with more sensors and copy old data
            print(f"\n❌ INCOMPATIBLE: Tree expansion needed but NOT SUPPORTED!")
            print(f"   Existing tree: {existing_nSensors} sensors")
            print(f"   Current file:  {self.nSensors} sensors")
            print(f"\n💡 ROOT trees cannot be expanded after creation.")
            print(f"   SOLUTION: Delete the ROOT file and reprocess ALL files in order:")
            print(f"   1. rm {self.outputRootFileName}")
            print(f"   2. Process peak files from LARGEST sensor count first")
            print(f"   3. Files with fewer sensors will be padded with zeros automatically")
            return (False, None, True)

    def fillRootFile(self, chunksize=1e6):
        if self.header is None:
            #Checks if the header is already created in the class, if not, it creates the header
            self.createHeader()
        if self.checkFileExists() is False:
            #If the file does not exists, it creates it and closes it
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "RECREATE")
            outputFile.Close()
            print(f"Creating new file at: {self.outputRootFileName} \n")
        
        # ✅ Check compatibility and determine sensor count to use
        is_compatible, tree_nSensors, needs_expansion = self.checkTreeCompatibility()
        
        if not is_compatible:
            print(f"\n{'='*70}")
            print(f"Processing SKIPPED to protect existing data.")
            print(f"{'='*70}\n")
            return  # Exit without processing
        
        # Use tree_nSensors (max of existing and current) for array dimensions
        use_nSensors = tree_nSensors
        
        if self.checkTreeExists() is False:
            #If the trees are not in the rootfile, it creates them
            print(f"Trees: {self.treeNames} not existing in the rootfile. \n")
            print(f"Creating tree with {use_nSensors} sensor slots\n")
            outputFile = ROOT.TFile(f"{self.outputRootFileName}", "UPDATE")
            outputTree = ROOT.TTree(self.treeNames[0], "Peaks fitted by I4G")

            t = np.zeros(self.nPols, dtype=np.float64)
            wav = np.zeros((self.nPols, use_nSensors), dtype=np.float64)
            sweep = np.zeros((self.nPols, use_nSensors), dtype=np.float64)
            ch = np.zeros(use_nSensors, dtype=np.float64)
            pos = np.zeros(use_nSensors, dtype=np.float64)

            outputTree.Branch("t", t, f"t[{self.nPols}]/D")
            outputTree.Branch("wav", wav, f"wav[{self.nPols}][{use_nSensors}]/D")
            outputTree.Branch("sweep", sweep, f"sweep[{self.nPols}][{use_nSensors}]/D")
            outputTree.Branch("ch", ch, f"ch[{use_nSensors}]/D")
            outputTree.Branch("pos", pos, f"pos[{use_nSensors}]/D")

            outputFile.cd()
            outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
            outputFile.Close()

        print(f"Start filling: '{self.outputRootFileName}' from file: '{self.peakFileName}'")
        print(f"File has {self.nSensors} sensors, tree accommodates {use_nSensors} sensors")
        if self.nSensors < use_nSensors:
            print(f"→ Sensors {self.nSensors+1}-{use_nSensors} will be filled with ZEROS (not present in file)\n")
        
        outputFile = ROOT.TFile(f"{self.outputRootFileName}", "UPDATE")
        outputTree = outputFile.Get(self.treeNames[0])

        t = np.zeros(self.nPols, dtype=np.float64)
        wav = np.zeros((self.nPols, use_nSensors), dtype=np.float64)
        sweep = np.zeros((self.nPols, use_nSensors), dtype=np.float64)
        ch = np.zeros(use_nSensors, dtype=np.float64)
        pos = np.zeros(use_nSensors, dtype=np.float64)

        outputTree.SetBranchAddress("t", t)
        outputTree.SetBranchAddress("wav", wav)
        outputTree.SetBranchAddress("sweep", sweep)
        outputTree.SetBranchAddress("ch", ch)
        outputTree.SetBranchAddress("pos", pos)

        peakData = pd.read_csv(self.peakFileName, sep="\t", header=None, names=self.header,
                               chunksize=chunksize, on_bad_lines="warn")

        result = subprocess.run(['wc', '-l', self.peakFileName], capture_output=True, text=True)
        line_count = int(result.stdout.split()[0])

        if chunksize is not None:
            line_in_pair = 0
            with tqdm(total=line_count) as pbar:
                for nChunk, chunk in enumerate(peakData):
                    chunk["epochTime"] = chunk["epochTime"].apply(reshapeEpochTime)
                    for index, row in chunk.iterrows():
                        nSens = 0
                        is_second_pol = (line_in_pair == 1)
                        pol_idx = 1 if is_second_pol else 0

                        for element in chunk.columns:
                            if "epoch" in element:
                                t[pol_idx] = row[element]
                            elif "Wav" in element:
                                wav[pol_idx][nSens] = row[element]
                                ch[nSens] = int(element.split("Wav")[1].split("_")[0])
                                pos[nSens] = float(element.split("Wav")[1].split("_")[1])*50
                            elif "Ptime" in element:
                                sweep[pol_idx][nSens] = row[element]
                                nSens += 1

                        if is_second_pol:
                            outputTree.Fill()
                            line_in_pair = 0
                        else:
                            line_in_pair = 1
                        pbar.update(1)

        elif chunksize is None:
            chunk = peakData
            chunk["epochTime"] = chunk["epochTime"].apply(reshapeEpochTime)
            print(f"{len(chunk)} entries in total:")
            line_in_pair = 0
            with tqdm(total=len(chunk)) as pbar:
                for index, row in chunk.iterrows():
                    nSens = 0
                    is_second_pol = (line_in_pair == 1)
                    pol_idx = 1 if is_second_pol else 0

                    for element in chunk.columns:
                        if "epoch" in element:
                            t[pol_idx] = row[element]
                        elif "Wav" in element:
                            wav[pol_idx][nSens] = row[element]
                            ch[nSens] = int(element.split("Wav")[1].split("_")[0])
                            pos[nSens] = float(element.split("Wav")[1].split("_")[1])*50
                        elif "Ptime" in element:
                            sweep[pol_idx][nSens] = row[element]
                            nSens += 1

                    if is_second_pol:
                        outputTree.Fill()
                        line_in_pair = 0
                    else:
                        line_in_pair = 1
                    pbar.update(1)

        outputFile.cd()
        outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
        outputFile.Close()