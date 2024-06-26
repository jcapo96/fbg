import ROOT
import numpy as np
import matplotlib.pyplot as plt
path = '/eos/user/j/jcapotor/FBGdata/ROOTFiles/LN2_tests/202404MarchRuns/20240313.root'
outputFile = ROOT.TFile(path, "READ")
spectrum = outputFile.Get("spectrum")

startPoint = 1529.0 #nm
endPoint = 1568.2 #nm
nPoints = 39200

lamb = np.linspace(startPoint, endPoint, nPoints) # esto son los

spectrum.GetEntry(0)
t0 = np.array(spectrum.t)

nEvent = 1
print(nEvent, nEvent%2 == True)
print(spectrum.GetEntries())

for i, entry in enumerate(spectrum):
    if i > 10: break
    print(i)
    time = np.array(getattr(entry, "t")) #así lees los tiempos, en time[0] tienes los tiempos para las polarizaciones P y en time[1] para las S
    print("Ppol", time[0] - t0[0])
    print("Spol", time[1] - t0[1])
    wav = np.array(getattr(entry, "wav")) # este array nos junta todos los datos en un único array de dimensión 4*39200 -> los primeros 39200 corresponden a la primera polarización del primer canal,
                                          # los segundos a la ssegunda polarización del segundo canal, etc.
    wav = [[wav[0:nPoints], wav[nPoints:nPoints*2]],[wav[nPoints*2:nPoints*3], wav[nPoints*3:nPoints*4]]] #esta es la forma en la que leer los espectros si hay 2 polarizaciones (P y S) por cada uno de los dos canales
    plt.plot(lamb, wav[0][0], color="blue") # así ploteamos la primera polarización del primer canal para un instante de tiempo t[0]
    plt.plot(lamb, wav[1][0], color="orange") # así la segunda polarización del primer canal para un instante de tiempo t[1]

plt.savefig("test2.png") #esto te guarda una imagen del plot en el directory desde el que estés corriendo el archivo