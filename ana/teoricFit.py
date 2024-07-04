import ROOT
import numpy as np
import matplotlib.pyplot as plt
import cmath
import json
from scipy.signal import find_peaks
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
# from iminuit import Minuit
# from iminuit.cost import UnbinnedNLL
from scipy.stats import norm
# from iminuit.cost import LeastSquares


def custom_spectrum_3(l, n, delta_n, lammbda_bragg, L):
    j = 1j  # Unidad imaginaria
    lammbda = lammbda_bragg / (2 * n)
    beta = 2 * np.pi * n / l
    delta_beta = 2 * beta - 2 * np.pi / lammbda
    k = np.pi * delta_n / (n * lammbda_bragg)
    B = np.array([cmath.sqrt(k**2 - (db / 2) ** 2) for db in delta_beta])
    max_val = 700  # Valor límite para evitar overflow
    B = np.clip(B, -max_val, max_val)
    exponent_A1 = j * (delta_beta / 2) * 0
    numerator_A1 = B * np.cosh(B * (0 - L)) - j * (delta_beta / 2) * np.sinh(B * (0 - L))
    denominator_A1 = B * np.cosh(B * L) + j * (delta_beta / 2) * np.sinh(B * L)
    A1 = np.exp(exponent_A1) * (numerator_A1 / denominator_A1)
    exponent_A2 = -j * (delta_beta / 2) * 0
    numerator_A2 = np.sinh(B * (0 - L))
    denominator_A2 = B * np.cosh(B * L) + j * (delta_beta / 2) * np.sinh(B * L)
    A2 = k * np.exp(exponent_A2) * (numerator_A2 / denominator_A2)
    reflex_spectrum = np.abs(A2 / A1) ** 2
    return reflex_spectrum / max(reflex_spectrum)

path = '/eos/user/j/jcapotor/FBGdata/ROOTFiles/camara_climatica/202404AprilRuns/20240422.root'
outputFile = ROOT.TFile(path, "READ") #leo el archivo en ese path
tree = outputFile.Get("spectrum") #cojo los espectros de ese archivo y los guardo en spectrum
#startPoint = 1529.0 #min nm
#endPoint = 1568.2 #max nm
nPoints = 39200 #cada muestra separada 1pm
#lamb = np.linspace(startPoint, endPoint, nPoints) # array de números espaciados de manera uniforme en el intervalo
pos, drindex, rindex, length = [], [], [], []
for index, entry in enumerate(tree):
    if index > 500:
        break
    tree.GetEntry(index)
    time = np.array(getattr(tree, "t")) #así lees los tiempos, en time[0] tienes los tiempos para las polarizaciones P y en time[1] para las S
    wav = np.array(getattr(tree, "wav")) # este array nos junta todos los datos en un único array de dimensión 4*39200 -> los primeros 39200 corresponden a la primera polarización del primer canal,
                                            # los segundos a la segunda polarización del segundo canal, etc.
    wav = [[wav[0:nPoints], wav[nPoints:nPoints*2]],[wav[nPoints*2:nPoints*3], wav[nPoints*3:nPoints*4]]]
    amplitudes = wav[0][0]
    # Datos para ajuste
    l = np.linspace(1529e-9, 1568.2e-9, 39200)
    # plt.plot(l, amplitudes)
    # plt.xlabel('Wavelength (m)')
    # plt.ylabel('Amplitude')
    # plt.title('Measured Spectrum')
    # plt.savefig('data.png')
    # Encontrar picos
    peaks, properties = find_peaks(amplitudes, height=400, distance = 800)  # height=0 significa que encontrará todos los picos, tambien tengo argumentos en esta funcion para indicar separacion minima entre picos etc distance son las muestras de separacion entre picos
    peak_wavelengths = l[peaks]
    peak_amplitudes = amplitudes[peaks]
    delta_n_range = np.linspace(5e-5, 10e-5, 50)
    lammbda_bragg_range = np.linspace(1544.6e-9, 1545.8e-9, 50)
    n_range = np.linspace(1.4552, 1.4558, 50)
    L_range = np.linspace(0.007, 0.01, 50)
    #reflex_spectrum_example = custom_spectrum_3(l, n, 0.0001, 1550e-9, L)
    i=0
    p = peaks[i]
    npoints = 700
    l = np.linspace(1529e-9, 1568.2e-9, 39200)
    #y1 = reflex_spectrum_example[p - npoints:p + npoints] / max(reflex_spectrum_example[p - npoints:p + npoints]) espectro teorico en swan
    x1 = l[p - npoints:p + npoints]
    y1 = amplitudes[p - npoints:p+npoints]/max(amplitudes[p - npoints:p+npoints])
    # Función de error (tb se puede definir con una sigma y definir un error constante del interrogador)
    def chi_squared(y_observed, y_expected):
        return np.sum((y_observed - y_expected) ** 2 / y_expected)
    # Parámetros iniciales y rangos
    n_initial = 1.456
    delta_n_initial = 9e-5
    lammbda_bragg_initial = peak_wavelengths[i]
    L_initial = 0.008
    chi2_values_n = []
    chi2_values_delta_n = []
    chi2_values_lammbda_bragg = []
    chi2_values_L = []
    num = 0.008e-9
    # Límites para los parámetros
    bounds = (
        [1.4552, 1e-5, peak_wavelengths[i]-num, 0.0075],  # Límites inferiores
        [1.456, 9e-5, peak_wavelengths[i]+num, 0.0105]   # Límites superiores
    )
    # bounds = (
    #     [1.4555, 8.5e-5, peak_wavelengths[i]-num, 0.0075],  # Límites inferiores
    #     [1.456, 10.5e-5, peak_wavelengths[i]+num, 0.0105]   # Límites superiores
    # )
    # Ajuste de la curva utilizando curve_fit con valores iniciales y límites
    popt, pcov = curve_fit(custom_spectrum_3, x1, y1, p0=[n_initial, delta_n_initial, lammbda_bragg_initial, L_initial], bounds=bounds, maxfev=2000)
    #print(np.sum((np.array(y1)-custom_spectrum_3(x1, *popt))**2))
    rindex.append(popt[0])
    pos.append(popt[2]*1e12)
    length.append(popt[3]*1e6)
    drindex.append(popt[1])
    # print((peak_wavelengths[i] - popt[2])*1e12)
    # print("Parámetros ajustados:")
    # print("n:", popt[0])
    # print("delta_n:", popt[1])
    # print("lammbda_bragg:", popt[2])
    # print("L:", popt[3])
    # plt.figure()
    # plt.plot(x1, y1)
    # plt.plot(x1, custom_spectrum_3(x1, *popt), label="fit")
    # plt.savefig(f"/afs/cern.ch/user/j/jcapotor/software/fbg/ana/plots/fit{index}")

plt.figure()
plt.plot(pos-pos[0])
plt.title("bragg wlg")
plt.ylabel("Wavelength Diff (pm)")
plt.savefig("bevo.png")

plt.figure()
plt.plot(rindex - rindex[0])
plt.title("n")
plt.ylabel("Index of refraction")
plt.savefig("nevo.png")

plt.figure()
plt.plot(length - length[0])
plt.ylabel("Length (um)")
plt.title("length")
plt.savefig("levo.png")

plt.figure()
plt.plot(drindex - drindex[0])
plt.title("Delta n")
plt.savefig("rnevo.png")

plt.figure()
plt.plot(pos-pos[0], length-length[0])
plt.title("Correlation")
plt.savefig("posvslength.png")

plt.figure()
plt.plot(pos-pos[0], drindex-drindex[0])
plt.title("Correlation")
plt.savefig("posvsdn.png")
    # # Visualización del ajuste
    # plt.figure()
    # plt.plot(x1, y1, 'o', label='Data')
    # plt.plot(x1, custom_spectrum_3(x1, *popt), '-', label='Theoretical fit')
    # plt.xlabel('Wavelength (m)')
    # #plt.ylim(0.998, 1.002)
    # #plt.xlim(peak_wavelengths[i]-0.05*1e-9, peak_wavelengths[i]+0.05*1e-9)
    # plt.ylabel('Amplitudes')
    # plt.legend(fontsize='small')
    # plt.title('Reflection spectrum fitting. FBGS-1. Sensor 1. "p" polarization.')
    # plt.savefig('fit.png')
# # Cálculo de Chi^2 para cada valor de delta_n, fijando los demás parámetros
# for delta_n in delta_n_range:
#     try:
#         popt, _ = curve_fit(lambda l, n, lammbda_bragg, L: custom_spectrum_3(l, n, delta_n, lammbda_bragg, L), x1, y1, p0=[n_initial, lammbda_bragg_initial, L_initial])
#         y_fit = custom_spectrum_3(x1, *popt, delta_n)
#         chi2 = chi_squared(y1, y_fit)
#         chi2_values_delta_n.append(chi2)
#     except RuntimeError:
#         chi2_values_delta_n.append(np.inf)
# for n in n_range:
#     try:
#         popt, _ = curve_fit(lambda l, delta_n, lammbda_bragg, L: custom_spectrum_3(l, n, delta_n, lammbda_bragg, L), x1, y1, p0=[delta_n_initial, lammbda_bragg_initial, L_initial])
#         y_fit = custom_spectrum_3(x1, n, *popt)
#         chi2 = chi_squared(y1, y_fit)
#         chi2_values_n.append(chi2)
#     except RuntimeError:
#         chi2_values_n.append(np.inf)
# # Cálculo de Chi^2 para cada valor de L, fijando los demás parámetros
# for L in L_range:
#     try:
#         popt, _ = curve_fit(lambda l, n, delta_n, lammbda_bragg: custom_spectrum_3(l, n, delta_n, lammbda_bragg, L), x1, y1, p0=[n_initial, delta_n_initial, lammbda_bragg_initial])
#         y_fit = custom_spectrum_3(x1, *popt, L)
#         chi2 = chi_squared(y1, y_fit)
#         chi2_values_L.append(chi2)
#     except RuntimeError:
#         chi2_values_L.append(np.inf)
# # Cálculo de Chi^2 para cada valor de lammbda_bragg, fijando los demás parámetros
# for lammbda_bragg in lammbda_bragg_range:
#     try:
#         popt, _ = curve_fit(lambda l, n, delta_n, L: custom_spectrum_3(l, n, delta_n, lammbda_bragg, L), x1, y1, p0=[n_initial, delta_n_initial, L_initial])
#         y_fit = custom_spectrum_3(x1, *popt, lammbda_bragg)
#         chi2 = chi_squared(y1, y_fit)
#         chi2_values_lammbda_bragg.append(chi2)
#     except RuntimeError:
#         chi2_values_lammbda_bragg.append(np.inf)
# # Generación de gráficos
# plt.figure(figsize=(12, 12))
# # Gráfico de Chi^2 vs n
# plt.subplot(2, 2, 1)
# plt.plot(n_range, chi2_values_n, '-o')
# plt.xlabel(r'$n$')
# plt.xlim(1.44, 1.46)
# plt.ylabel(r'$\chi^2$')
# plt.title(r'$\chi^2$ vs $n$')
# # Gráfico de Chi^2 vs delta_n
# plt.subplot(2, 2, 2)
# plt.plot(delta_n_range, chi2_values_delta_n, '-o')
# plt.xlabel(r'$\Delta n$')
# plt.xlim(1e-5, 10e-5)
# plt.ylabel(r'$\chi^2$')
# plt.title(r'$\chi^2$ vs $\Delta n$')
# # Gráfico de Chi^2 vs lammbda_bragg
# plt.subplot(2, 2, 3)
# plt.plot(lammbda_bragg_range, chi2_values_lammbda_bragg, '-o')
# plt.xlabel(r'$\lambda_{bragg}$ (m)')
# plt.xlim(1539.09e-9, 1539.31e-9)
# plt.ylabel(r'$\chi^2$')
# plt.title(r'$\chi^2$ vs $\lambda_{bragg}$')
# # Gráfico de Chi^2 vs L
# plt.subplot(2, 2, 4)
# plt.plot(L_range, chi2_values_L, '-o')
# plt.xlabel(r'$L$')
# plt.xlim(0.009, 0.011)
# plt.ylabel(r'$\chi^2$')
# plt.title(r'$\chi^2$ vs $L$')
# plt.tight_layout()
# plt.savefig('chis.png')