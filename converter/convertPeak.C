#include <iostream>
#include <fstream>
#include <vector>
#include <TFile.h>
#include <TTree.h>

void ReadCSVAndSaveToROOT(const char* csvFileName, const char* rootFileName) {
    // Open the CSV file for reading
    std::ifstream csvFile(csvFileName);

    if (!csvFile.is_open()) {
        std::cerr << "Failed to open the CSV file." << std::endl;
        return;
    }

    // Create a ROOT TFile to store the TTree
    TFile* outputFile = new TFile(rootFileName, "RECREATE");

    // Create a TTree to hold the data
    TTree* tree = new TTree("CableLengthData", "Cable Length Data");

    // Define variables to hold the data
    int index;
    double col3_value;
    double col4_value;

    // Create branches in the TTree
    tree->Branch("INDEX", &index, "INDEX/I");
    tree->Branch("Column3", &col3_value, "Column3/D");
    tree->Branch("Column4", &col4_value, "Column4/D");

    // Read and process the CSV data
    std::string line;
    while (std::getline(csvFile, line)) {
        // Assuming CSV format: INDEX,Column3,Column4
        std::istringstream iss(line);
        iss >> index >> col3_value >> col4_value;
        tree->Fill();
    }

    // Write the TTree to the ROOT file
    tree->Write();
    outputFile->Close();

    std::cout << "Data has been successfully written to ROOT file: " << rootFileName << std::endl;
}

int main() {
    const char* csvFileName = "your_input.csv";
    const char* rootFileName = "output.root";
    ReadCSVAndSaveToROOT(csvFileName, rootFileName);
    return 0;
}
