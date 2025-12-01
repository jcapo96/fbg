# Bug Fix: Catastrophic Data Loss in Peak Converter

> **⚠️ CRITICAL FIX**: This patch prevents **complete data loss** when processing multiple peak files with variable sensor counts. If you have existing ROOT files, **they may be incomplete** and need reprocessing.

## 📋 Executive Summary

**Problem:** `convertPeak.py` was using `ROOT.TObject.kWriteDelete` to recreate trees when sensor counts changed. This **deleted ALL previous data** from the ROOT file, keeping only the last processed file's data.

**Impact:** Hours or days of measurements reduced to minutes. Example: 6.5 hours of data → 1 hour remaining.

**Solution:** Zero-padding strategy—use maximum sensor count across all files, pad missing sensors with zeros, refuse tree expansion with clear instructions.

**Action Required:** 
1. Delete existing ROOT files
2. Process peak files in descending sensor order (most sensors first)
3. Verify all time ranges are present in output

---

## 🐛 Problem Description

When processing multiple peak files with **different numbers of sensors**, the ROOT tree handling had **CRITICAL BUGS** that caused data loss and corruption.

### Critical Issues Found:

#### **Issue #1: Data Loss with `kWriteDelete`** (MOST SEVERE)
**Example Scenario:**
1. Process `peaks_1.txt` (11:00-12:00, **4 sensors**) → Creates tree with `wav[2][4]` ✅
2. Process `peaks_2.txt` (16:00-17:00, **5 sensors**) → Detects mismatch
3. **RECREATES tree with `kWriteDelete`** → ❌ **DELETES ALL peaks_1 data!**
4. **Result**: Only peaks_2 data remains (1 hour instead of 6+ hours)

This caused **silent data loss** where users would see only the last file's data in the ROOT file.

#### **Issue #2: Array Dimension Mismatch**
When sensor counts changed, data would be written to wrong memory locations, causing sensor mixing and polarization shifts.

## 🔍 Bugs Identified (Technical Details)

### 1. **Data Loss via Tree Overwriting** (CRITICAL)
- **Location**: `fillRootFile()` line ~170
- **Issue**: Used `ROOT.TObject.kWriteDelete` which **deletes existing tree**
- **Code**:
  ```python
  # ❌ DANGEROUS: Deletes all existing data!
  outputTree.Write(self.treeNames[0], ROOT.TObject.kWriteDelete)
  ```
- **Effect**: When sensor count changed, ALL previous peak data was erased

### 2. **Missing Tree Compatibility Check**
- **Location**: `fillRootFile()` method (line ~143)
- **Issue**: Code only checked if tree exists, not if it's compatible with current file
- **Effect**: Would attempt to write incompatible data structures

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

## ✅ Solution Implemented (Version 3 - Current)

### **Strategy: Zero-Padding with Maximum Sensor Count**

ROOT trees cannot be resized after creation. Our solution:
- **Always use maximum sensor count** across all peak files
- **Pad missing sensors with zeros** for files with fewer sensors
- **Protect existing data** by refusing tree expansion

### 1. Added `getExistingTreeSensorCount()` Method
```python
def getExistingTreeSensorCount(self):
    """
    Get the number of sensors in existing tree, or None if tree doesn't exist.
    """
    # Reads existing tree dimensions from ROOT file
    # Returns sensor count or None
```

### 2. Enhanced `checkTreeCompatibility()` Method
```python
def checkTreeCompatibility(self):
    """
    Check if current file can be added to existing tree.
    Strategy: Use max(existing, current) sensors and pad with zeros.
    Returns: (is_compatible, max_sensors, needs_expansion)
    """
```

**Returns tuple with 3 values:**
- `is_compatible`: Can file be processed?
- `max_sensors`: Number of sensor slots to use (max of existing and current)
- `needs_expansion`: Does tree need expansion? (not supported)

**Scenarios:**

| Case | Existing | Current | Action | Result |
|------|----------|---------|--------|---------|
| **First file** | None | 4 | Create tree[4] | ✅ Tree with 4 slots |
| **Same count** | 4 | 4 | Use existing | ✅ Perfect match |
| **Fewer sensors** | 5 | 4 | Pad with zeros | ✅ Slots 5 = 0 |
| **More sensors** | 4 | 5 | ❌ REJECT | ⚠️ Need expansion |

### 3. Automatic Zero-Padding
```python
use_nSensors = tree_nSensors  # Max of existing and current

# Create arrays with max size
wav = np.zeros((self.nPols, use_nSensors), dtype=np.float64)

# File data fills first self.nSensors slots
# Remaining slots stay as zeros (padding)
```

**Example with 3 files:**

```
peaks_1.txt: 4 sensors (11:00-12:00)
  → Creates tree[4]
  → Data: [S1, S2, S3, S4]

peaks_2.txt: 4 sensors (13:00-14:00)
  → Uses tree[4]
  → Data: [S1, S2, S3, S4]

peaks_3.txt: 5 sensors (16:00-17:00)
  → ❌ REJECTED! Tree cannot expand from [4] to [5]
  → Message: "Delete ROOT file and reprocess with largest sensor count first"
```

**Correct order:**

```
rm output.root  # Start fresh

peaks_3.txt: 5 sensors (16:00-17:00)
  → Creates tree[5]
  → Data: [S1, S2, S3, S4, S5]

peaks_1.txt: 4 sensors (11:00-12:00)
  → Uses tree[5]
  → Data: [S1, S2, S3, S4, 0]  ← S5 padded with zeros

peaks_2.txt: 4 sensors (13:00-14:00)
  → Uses tree[5]
  → Data: [S1, S2, S3, S4, 0]  ← S5 padded with zeros
```

**Result:** All data preserved! Sensor 5 has valid data only during 16:00-17:00.

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

### ⚠️ CRITICAL: Process Files in Descending Sensor Order

**Always process files with MOST sensors first:**

```bash
# ❌ BAD ORDER (will fail)
peaks_1.txt: 4 sensors → creates tree[4]
peaks_2.txt: 5 sensors → ❌ ERROR! Cannot expand tree[4] → tree[5]

# ✅ CORRECT ORDER
peaks_2.txt: 5 sensors → creates tree[5]
peaks_1.txt: 4 sensors → pads S5 with zeros ✅
```

### Test Case 1: Variable Sensor Count (Correct Order)
```bash
# Create 3 peak files with different sensor counts
peaks_1.txt: 4 sensors (11:00-12:00)
peaks_2.txt: 5 sensors (13:00-14:00)
peaks_3.txt: 4 sensors (15:00-16:00)

# Delete existing ROOT file (if any)
rm output.root

# Process LARGEST file first
python3 makeROOTfile.py peaks_2.txt  # Creates tree[5]
python3 makeROOTfile.py peaks_1.txt  # Pads to [5]
python3 makeROOTfile.py peaks_3.txt  # Pads to [5]

# Expected result: ✅ All data preserved, S5 has zeros for peaks_1 and peaks_3
```

### Test Case 2: Verify Data Integrity
```python
import uproot
import pandas as pd

# Open ROOT file
f = uproot.open("output.root")
tree = f["peak"]

# Check structure
print(tree["wav"].typename)  # Should show float[2][5] (2 pols, 5 sensors)

# Verify data
data = tree.arrays(library="pd")

# Check all time ranges present
print("Time coverage per date:")
print(data.groupby("Date")["Time"].agg(['min', 'max', 'count']))
# Should show ALL time ranges from all 3 files

# Verify sensor 5 padding
print("\nSensor 5 check:")
print("Non-zero entries:", (data["wav"][:, 1, 4] != 0).sum())  # Only peaks_2 data
print("Zero entries:", (data["wav"][:, 1, 4] == 0).sum())      # peaks_1 + peaks_3 data
```

### Test Case 3: Wrong Order Detection
```bash
# Delete existing ROOT file
rm output.root

# Process SMALLEST file first (will cause error later)
python3 makeROOTfile.py peaks_1.txt  # Creates tree[4]
python3 makeROOTfile.py peaks_2.txt  # ❌ ERROR! 
# Expected error message:
# "⚠️  INCOMPATIBLE: Tree has 4 sensors but file has 5 sensors."
# "Tree cannot be expanded after creation."
# "Delete output.root and reprocess with largest sensor count first."
```

## 📊 Impact

### Before Fix (CATASTROPHIC):
- ❌ **DATA LOSS**: Only last file's data kept (6 hours reduced to 1 hour!)
- ❌ `TObject.kWriteDelete` silently erased all previous entries
- ❌ Sensor 5 data mixed with Sensor 4 (dimension mismatch)
- ❌ Polarization 2 data shifted to next sensor (indexing bug)
- ❌ Silent corruption—impossible to detect during conversion

**Real Example from ROOT_DEWAR_28_11.ipynb:**
```python
# Expected: 11:00 - 17:30 (6.5 hours of data)
# Actual:   16:27 - 17:32 (1 hour of data)
# Lost:     5.5 hours of measurements!
```

### After Fix (SAFE):
- ✅ **ALL DATA PRESERVED**: Zero-padding maintains complete time coverage
- ✅ Each sensor's data properly isolated in correct dimension
- ✅ Polarizations correctly assigned (sweep[1] for pol2)
- ✅ Clear error messages when tree expansion needed
- ✅ Processing order guidance (largest sensor count first)

## 🚀 Usage

### Critical Workflow Change

**YOU MUST process files in descending sensor order:**

```bash
# Step 1: Check sensor counts in your data
grep "^[0-9]" peaks_*.txt | head -1 | awk '{print NF-2}' 

# Step 2: Delete existing ROOT file
rm output.root

# Step 3: Process files with MOST sensors FIRST
python3 makeROOTfile.py peaks_5sensors.txt  # Creates tree[5]
python3 makeROOTfile.py peaks_4sensors.txt  # Pads to tree[5]
```

### What the Converter Does Automatically:
1. Detects existing tree sensor count
2. Compares with current file sensor count
3. If current ≥ existing: Pads with zeros ✅
4. If current < existing: **REJECTS FILE** with clear instructions ❌

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
