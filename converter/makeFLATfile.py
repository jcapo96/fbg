import ROOT
import numpy as np

def resample_root_file(input_filename, output_filename, sampling_interval=5, default_value=-99999):
    """
    Resamples the trees ('peak', 'temp', 'press') in a ROOT file.
    Creates a single tree containing time, wav, temp, and press arrays.
    """
    file = ROOT.TFile.Open(input_filename, "READ")
    if not file or file.IsZombie():
        print(f"Error: Cannot open file {input_filename}")
        return

    output_file = ROOT.TFile(output_filename, "RECREATE")
    trees_to_resample = ['peak', 'temp', 'press']
    
    # Step 1: Find the global initial time t0
    t0 = float('inf')
    max_t = float('-inf')
    num_sensors = None
    num_polarizations = 2  # Always defined as 2
    
    processed_trees = []
    
    for tree_name in trees_to_resample:
        tree = file.Get(tree_name)
        if tree and tree.GetEntries() > 0:
            processed_trees.append(tree_name)
            tree.GetEntry(0)
            min_time = min(tree.t[0], tree.t[1]) if tree_name == 'peak' else tree.t
            t0 = min(t0, min_time)
            print(f"{tree_name} initial time: {min_time}")
            
            tree.GetEntry(tree.GetEntries() - 1)
            max_time = max(tree.t[0], tree.t[1]) if tree_name == 'peak' else tree.t
            max_t = max(max_t, max_time)
            print(f"{tree_name} final time: {max_time}")
            
            if tree_name == 'peak':
                if hasattr(tree, 'wav'):
                    num_sensors = len(tree.wav[0]) if len(tree.wav) > 0 else 1
                    print(f"Structure of wav: {num_polarizations} polarizations, {num_sensors} sensors")
                else:
                    print("Warning: 'peak' tree does not contain 'wav' attribute.")
    
    print(f"Trees being processed: {processed_trees}")
    
    if num_sensors is None:
        print("Error: Could not determine wav dimensions.")
        return

    print(f"Global initial time t0: {t0}")
    print(f"Global final time max_t: {max_t}")
    bins = np.arange(t0, max_t + sampling_interval, sampling_interval)
    print(f"Number of intervals: {len(bins) - 1}")
    
    # Step 2: Prepare data storage
    resampled_data = {b: {"wav": [], "temp": [], "press": []} for b in bins[:-1]}
    count_temp = {b: 0 for b in bins[:-1]}
    count_press = {b: 0 for b in bins[:-1]}
    count_wav = {b: 0 for b in bins[:-1]}
    
    for tree_name in trees_to_resample:
        tree = file.Get(tree_name)
        if not tree:
            continue
        
        for entry in range(tree.GetEntries()):
            tree.GetEntry(entry)
            time_value = min(tree.t[0], tree.t[1]) if tree_name == 'peak' else tree.t
            
            idx = np.searchsorted(bins, time_value, side='right') - 1
            if 0 <= idx < len(bins) - 1:
                if tree_name == 'peak' and hasattr(tree, 'wav'):
                    resampled_data[bins[idx]]["wav"].append(np.array(tree.wav))
                    count_wav[bins[idx]] += 1
                elif tree_name == 'temp' and hasattr(tree, 'temp'):
                    resampled_data[bins[idx]]["temp"].append(np.array(tree.temp))
                    count_temp[bins[idx]] += 1
                elif tree_name == 'press' and hasattr(tree, 'press'):
                    resampled_data[bins[idx]]["press"].append(tree.press)
                    count_press[bins[idx]] += 1
    
    # Step 3: Compute mean values ignoring default values
    for b in bins[:-1]:
        if count_wav[b] > 0:
            wav_values = np.array(resampled_data[b]["wav"])
            wav_values = np.where(wav_values == default_value, np.nan, wav_values)
            if np.all(np.isnan(wav_values)):
                resampled_data[b]["wav"] = np.full((num_polarizations, num_sensors), default_value)
            else:
                resampled_data[b]["wav"] = np.nanmean(wav_values, axis=0)
        else:
            resampled_data[b]["wav"] = np.full((num_polarizations, num_sensors), default_value)
        
        if count_temp[b] > 0:
            temp_values = np.array(resampled_data[b]["temp"])
            temp_values = np.where(temp_values == default_value, np.nan, temp_values)
            if np.all(np.isnan(temp_values)):
                resampled_data[b]["temp"] = np.full(8, default_value)
            else:
                resampled_data[b]["temp"] = np.nanmean(temp_values, axis=0)
        else:
            resampled_data[b]["temp"] = np.full(8, default_value)
        
        if count_press[b] > 0:
            press_values = np.array(resampled_data[b]["press"])
            press_values = np.where(press_values == default_value, np.nan, press_values)
            if np.all(np.isnan(press_values)):
                resampled_data[b]["press"] = default_value
            else:
                resampled_data[b]["press"] = np.nanmean(press_values)
        else:
            resampled_data[b]["press"] = default_value
    
    # Step 4: Create a single resampled tree
    resampled_tree = ROOT.TTree("resampled_data", "Resampled Data")
    resampled_t = np.zeros(1, dtype=np.float64)
    resampled_wav = np.zeros((num_polarizations, num_sensors), dtype=np.float64)
    resampled_temp = np.zeros(8, dtype=np.float64)
    resampled_press = np.zeros(1, dtype=np.float64)
    
    resampled_tree.Branch("t", resampled_t, "t/D")
    resampled_tree.Branch("wav", resampled_wav, f"wav[{num_polarizations}][{num_sensors}]/D")
    resampled_tree.Branch("temp", resampled_temp, "temp[8]/D")
    resampled_tree.Branch("press", resampled_press, "press/D")
    
    for i, b in enumerate(bins[:-1]):
        resampled_t[0] = b
        resampled_wav[:] = resampled_data[b]["wav"]
        resampled_temp[:] = resampled_data[b]["temp"]
        resampled_press[0] = resampled_data[b]["press"]
        resampled_tree.Fill()
    
    resampled_tree.Write()
    output_file.Close()
    file.Close()
    print(f"Resampling completed. Output file: {output_filename}")

resample_root_file("/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/20241001.root", "/eos/user/j/jcapotor/FBGdata/ROOTFiles/pressure_setup/resampled20241001.root", sampling_interval=5, default_value=-99999)