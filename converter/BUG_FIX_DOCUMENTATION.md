# Bug Fix: Sensor Mismatch in Peak Converter

## 🐛 Problem Description

When processing multiple peak files with **different numbers of sensors**, the ROOT tree structure was not being updated, causing data corruption and sensor mixing.

### Example Scenario:
1. Process `peaks_1.txt` with **4 sensors** → Creates tree with `wav[2][4]`
2. Process `peaks_2.txt` with **5 sensors** → Tries to fill 5 sensors into 4-sensor structure
3. **Result**: Sensor 5 data gets mixed with Sensor 4, polarizations shift incorrectly

## 🔍 Bugs Identified

### 1. **Missing Tree Compatibility Check**
- **Location**: `fillRootFile()` method (line ~143)
- **Issue**: Code only checked if tree exists, not if it's compatible with current file
- **Effect**: New files with different sensor counts would corrupt existing data

### 2. **Incorrect Array Dimensions for `ch` and `pos`**
- **Location**: Lines 158-159 and 186-187
- **Issue**: Arrays declared as 2D `(nPols, nSensors)` but branches defined as 1D `[nSensors]`
- **Code**:
  ```python
  # ❌ BEFORE (WRONG)
  ch = np.zeros((self.nPols, self.nSensors), dtype=np.float64)
  pos = np.zeros((self.nPols, self.nSensors), dtype=np.float64)
  outputTree.Branch("ch", ch, f"ch[{self.nSensors}]/D")  # 1D branch!
  ```
- **Effect**: Memory layout mismatch, incorrect indexing like `ch[1][nSens]`

### 3. **Wrong Polarization Index in Sweep**
- **Location**: Line 270 (chunksize=None branch)
- **Issue**: Using `sweep[0][nSens]` instead of `sweep[1][nSens]` for second polarization
- **Effect**: Second polarization sweep times written to first polarization array

## ✅ Solution Implemented

### 1. Added `checkTreeCompatibility()` Method
```python
def checkTreeCompatibility(self):
    """
    Check if existing peak tree structure is compatible with current file's sensor count.
    Returns True if compatible or if tree doesn't exist yet.
    Returns False if sensor count mismatch detected.
    """
    # Reads existing tree dimensions from ROOT file
    # Compares with current file's sensor count
    # Returns False if mismatch detected
```

**What it does**:
- Reads the `wav` branch leaf description (e.g., `"wav[2][4]"`)
- Extracts existing sensor count using regex
- Compares with current file's `self.nSensors`
- Prints clear warning if mismatch detected

### 2. Tree Recreation on Incompatibility
```python
# ✅ NEW LOGIC
tree_compatible = self.checkTreeCompatibility()

if self.checkTreeExists() is False or not tree_compatible:
    # Recreate tree with correct dimensions
```

**What it does**:
- If sensor count changed → Recreates tree with new dimensions
- Prevents data corruption from dimension mismatch
- Logs warning message for user awareness

### 3. Fixed Array Dimensions
```python
# ✅ AFTER (CORRECT)
ch = np.zeros(self.nSensors, dtype=np.float64)      # 1D array
pos = np.zeros(self.nSensors, dtype=np.float64)     # 1D array

# And access as 1D:
ch[nSens] = int(element.split("Wav")[1].split("_")[0])
pos[nSens] = float(element.split("Wav")[1].split("_")[1]) * 50
```

### 4. Fixed Sweep Index
```python
# ✅ FIXED
elif "Ptime" in element:
    sweep[1][nSens] = row[element]  # Correct polarization index
    nSens += 1
```

## 🧪 Testing Recommendations

### Test Case 1: Variable Sensor Count
```bash
# Process files with different sensor counts
python makeROOTfile.py /path/to/data/with/peaks_4sensors/
python makeROOTfile.py /path/to/data/with/peaks_5sensors/

# Expected: Warning message + tree recreation
# ⚠️  WARNING: Sensor count mismatch detected!
#    Existing tree has 4 sensors
#    Current file has 5 sensors
#    → Tree will be RECREATED to avoid data corruption
```

### Test Case 2: Verify Data Integrity
```python
import uproot
import numpy as np

# Open ROOT file
file = uproot.open("output.root")
tree = file["peak"]
data = tree.arrays(library="np")

# Check dimensions
print(f"wav shape: {data['wav'].shape}")      # Should be (n_entries, 2, n_sensors)
print(f"ch shape: {data['ch'].shape}")        # Should be (n_entries, n_sensors)
print(f"pos shape: {data['pos'].shape}")      # Should be (n_entries, n_sensors)

# Verify no mixing: check that ch values are consistent
print(f"Channel values: {np.unique(data['ch'])}")
```

## 📊 Impact

### Before Fix:
- ❌ Sensor 5 data mixed with Sensor 4
- ❌ Polarization 2 data shifted to next sensor
- ❌ Silent data corruption
- ❌ Difficult to debug during analysis

### After Fix:
- ✅ Each sensor's data properly isolated
- ✅ Polarizations correctly assigned
- ✅ Clear warnings when sensor count changes
- ✅ Automatic tree recreation when needed

## 🚀 Usage

No changes needed in user code. The converter now automatically:
1. Detects sensor count changes
2. Warns the user
3. Recreates the tree structure with correct dimensions
4. Continues processing without data corruption

## � Future Work: Similar Fixes for Other Converters

### **convertSpectrum.py** - If you need to change the number of fiber channels

**Current Status**: Hardcoded to 3 channels (line 14):
```python
self.channels = [0,1,2]  # Fixed: 3 fiber channels
```

**When to apply fix**: If you need to add/remove fiber channels between measurements

**Steps to implement**:

1. **Add dynamic channel detection**:
```python
def detectChannels(self):
    """
    Detect channels from spectrum file instead of hardcoding.
    Read first few packets to determine which channels are present.
    """
    channels_found = set()
    with open(self.spectrumFileName, 'rb') as f:
        # Read first N packets to detect channels
        for _ in range(100):  # Sample first 100 packets
            try:
                packetSize = np.fromfile(f, dtype='<i4', count=1)[0]
                timeStamp = np.fromfile(f, dtype='<u8', count=1)[0]
                validityFlag = np.fromfile(f, dtype='<i4', count=1)[0]
                channelN = np.fromfile(f, dtype='<i4', count=1)[0]
                channels_found.add(channelN)
                # Skip rest of packet
                f.seek(packetSize - 20, 1)
            except:
                break
        f.seek(0)  # Reset to beginning
    self.channels = sorted(list(channels_found))
    return self
```

2. **Add checkTreeCompatibility() method** (similar to Peak converter):
```python
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
                    print(f"   Current file has {len(self.channels)} channels")
                    print(f"   → Tree will be RECREATED to avoid data corruption\n")
                
                outputFile.Close()
                return is_compatible
        
        outputFile.Close()
        return True
        
    except Exception as e:
        print(f"Warning: Could not check tree compatibility: {e}")
        return True
```

3. **Modify fillRootFile()** to use compatibility check:
```python
def fillRootFile(self):
    # Add dynamic channel detection
    self.detectChannels()
    
    if self.checkFileExists() is False:
        outputFile = ROOT.TFile(f"{self.outputRootFileName}", "RECREATE")
        outputFile.Close()
        print(f"Creating new file at: {self.outputRootFileName} \n")
    
    # ✅ NEW: Check tree compatibility
    tree_compatible = self.checkTreeCompatibility()
    
    if self.checkTreeExists() is False or not tree_compatible:
        # Recreate tree with correct dimensions
        ...
```

**Expected output when channel count changes**:
```
⚠️  WARNING: Channel count mismatch detected!
   Existing tree has 3 channels
   Current file has 4 channels
   → Tree will be RECREATED to avoid data corruption
```

---

### **convertRTD.py** - If you need to change the number of RTD sensors

**Current Status**: Already detects `nSensors` dynamically (line 22):
```python
self.nSensors = len(firstLine) - 2  # ✅ Dynamic detection
```

**When to apply fix**: If you add/remove RTD sensors between measurements

**Steps to implement** (very similar to Peak fix):

1. **Add checkTreeCompatibility() method**:
```python
def checkTreeCompatibility(self):
    """
    Check if existing temp tree structure matches current file's sensor count.
    Returns True if compatible, False if sensor count mismatch detected.
    """
    if not self.checkFileExists():
        return True
    
    try:
        outputFile = ROOT.TFile(f"{self.outputRootFileName}", "READ")
        tree = outputFile.Get(self.treeNames[0])
        
        if not tree:
            outputFile.Close()
            return True
        
        temp_branch = tree.GetBranch("temp")
        if temp_branch:
            leaf = temp_branch.GetLeaf("temp")
            leaf_title = leaf.GetTitle()
            
            # Extract sensor count from "temp[N]" format
            import re
            match = re.search(r'\[(\d+)\]', leaf_title)
            if match:
                existing_nSensors = int(match.group(1))
                is_compatible = (existing_nSensors == self.nSensors)
                
                if not is_compatible:
                    print(f"\n⚠️  WARNING: RTD sensor count mismatch detected!")
                    print(f"   Existing tree has {existing_nSensors} sensors")
                    print(f"   Current file has {self.nSensors} sensors")
                    print(f"   → Tree will be RECREATED to avoid data corruption\n")
                
                outputFile.Close()
                return is_compatible
        
        outputFile.Close()
        return True
        
    except Exception as e:
        print(f"Warning: Could not check tree compatibility: {e}")
        return True
```

2. **Modify fillRootFile()** in line ~78:
```python
def fillRootFile(self, chunksize=None):
    if self.header is None:
        self.prepareData()
    
    if self.checkFileExists() is False:
        outputFile = ROOT.TFile(f"{self.outputRootFileName}", "RECREATE")
        outputFile.Close()
        print(f"Creating new file at: {self.outputRootFileName}")
    
    # ✅ NEW: Check tree compatibility
    tree_compatible = self.checkTreeCompatibility()
    
    if self.checkTreeExists() is False or not tree_compatible:
        # Recreate tree with correct dimensions
        ...
```

---

### **convertPressure.py** - No changes expected

**Status**: Single sensor (`self.nSensors = 1`), unlikely to change.

**If needed**: Follow same pattern as RTD converter above.

---

### **convertHumidity.py** & **convertClimaticChamber.py** - No changes expected

**Status**: Fixed sensor layouts, unlikely to change.

---

## 🎯 Summary Table

| Converter | Dynamic Detection | Needs Fix If... | Priority |
|-----------|-------------------|-----------------|----------|
| **Peak** | ✅ Implemented | Add/remove FBG sensors | ✅ DONE |
| **Spectrum** | ❌ Hardcoded (3 channels) | Add/remove fiber channels | 🔵 Future |
| **RTD** | ✅ Already dynamic | Add/remove RTD sensors | 🟡 Future |
| **Pressure** | N/A (single sensor) | N/A | - |
| **Humidity** | N/A (fixed layout) | N/A | - |
| **Climatic** | N/A (fixed layout) | N/A | - |

---

## �📝 Git Branch

Branch: `fix/peak-sensor-mismatch`
Commit: 048656cb

## 👤 Author

Victor Garcia (vgarciap)
Date: December 1, 2025
