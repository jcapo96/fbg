#include <TFile.h>
#include <TTree.h>
#include <TBranch.h>
#include <TKey.h>
#include <TObjArray.h>
#include <iostream>
#include <vector>
#include <map>

void makeFLATfile(const char* input_filename, const char* output_filename) {
    // Open the ROOT input file
    TFile *file = TFile::Open(input_filename);
    if (!file || file->IsZombie()) {
        std::cerr << "Error: Cannot open file " << input_filename << std::endl;
        return;
    }

    std::cout << "Processing input file: " << input_filename << std::endl;

    // Create a new ROOT output file where the resampled trees will be saved
    TFile *output_file = new TFile(output_filename, "RECREATE");
    if (!output_file || output_file->IsZombie()) {
        std::cerr << "Error: Cannot create output file " << output_filename << std::endl;
        file->Close();
        return;
    }

    // Loop over all trees in the input ROOT file
    TIter next(file->GetListOfKeys());
    TKey *key;
    double global_max_sampling_time = 0;  // Variable to store the global maximum sampling time

    // First, find the maximum sampling time
    while ((key = (TKey*)next())) {
        if (std::string(key->GetClassName()) == "TTree") {
            TTree *tree = (TTree*)key->ReadObj();
            std::cout << "Processing tree: " << tree->GetName() << std::endl;

            // Access the "t" branch and other branches
            TBranch *branch_t = tree->GetBranch("t");
            if (!branch_t) {
                std::cerr << "Error: Branch 't' not found in tree " << tree->GetName() << std::endl;
                continue;
            }

            // Define a variable to hold the value of "t"
            double t;
            branch_t->SetAddress(&t);

            // Calculate the sampling time for this tree
            double prev_t = 0;
            double sampling_time = 0;
            double max_sampling_time = 0;

            // Get the number of entries
            Long64_t nEntries = tree->GetEntries();

            // Loop over the entries in the tree to find the maximum sampling time
            for (Long64_t i = 0; i < nEntries; i++) {
                branch_t->GetEntry(i);  // Get the value of "t" for this entry

                if (i > 0) {
                    sampling_time = t - prev_t;  // Calculate the time difference (sampling time)
                    if (sampling_time > max_sampling_time) {
                        max_sampling_time = sampling_time;  // Update the maximum sampling time for the current tree
                    }
                }

                prev_t = t;  // Update prev_t for the next iteration
            }

            // Update the global maximum sampling time
            if (max_sampling_time > global_max_sampling_time) {
                global_max_sampling_time = max_sampling_time;
            }
        }
    }

    // Resample each tree at the maximum sampling time
    next.Reset();  // Reset iterator to start over
    TTree* resampled_tree = nullptr;
    std::map<std::string, std::vector<double>> branch_data;  // Map to store branch data for resampling

    while ((key = (TKey*)next())) {
        if (std::string(key->GetClassName()) == "TTree") {
            TTree* tree = (TTree*)key->ReadObj();
            std::cout << "Resampling tree: " << tree->GetName() << std::endl;

            // Access the "t" branch and other branches
            TBranch *branch_t = tree->GetBranch("t");
            if (!branch_t) {
                std::cerr << "Error: Branch 't' not found in tree " << tree->GetName() << std::endl;
                continue;
            }

            // Define a variable to hold the value of "t"
            double t;
            branch_t->SetAddress(&t);

            // Loop over all branches in the tree and collect the branch data
            for (int i = 0; i < tree->GetNbranches(); i++) {
                TBranch *branch = tree->GetBranch(i);
                if (branch->GetName() != "t") {  // Don't add "t" again
                    std::vector<double> branch_values;
                    double value;
                    branch->SetAddress(&value);  // Use a temporary variable to store the branch value
                    branch_data[branch->GetName()].push_back(value);
                }
            }

            // Create a new tree to store resampled values
            if (!resampled_tree) {
                resampled_tree = new TTree("resampled_tree", "Resampled Tree");
                resampled_tree->Branch("t", &t, "t/D");  // Add "t" branch

                // Create branches for the other variables in the map
                for (const auto& entry : branch_data) {
                    const std::string& branch_name = entry.first;
                    resampled_tree->Branch(branch_name.c_str(), &entry.second);
                }
            }

            // Variables to store the values of branches
            double prev_t = 0;
            double sampling_time = 0;

            // Loop over the entries and resample them at the maximum sampling time
            Long64_t nEntries = tree->GetEntries();
            for (Long64_t i = 0; i < nEntries; i++) {
                branch_t->GetEntry(i);
                sampling_time = t - prev_t;

                // If the sampling time exceeds the global maximum sampling time, resample
                if (sampling_time >= global_max_sampling_time) {
                    resampled_tree->Fill();  // Add this entry to the resampled tree
                    prev_t = t;  // Update prev_t for the next entry
                }
            }
        }
    }

    // Write the resampled tree to the output file
    output_file->cd();
    if (resampled_tree) {
        resampled_tree->Write();
    }

    // Close the files
    output_file->Close();
    file->Close();
    delete file;
    delete output_file;

    std::cout << "Resampling complete. Resampled tree saved to: " << output_filename << std::endl;
}
