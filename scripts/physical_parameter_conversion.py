#!/usr/bin/env python3
# ____________________________________________________________________ #
#                                                                      #
# SDC2-SoFiA: Physical Parameter Conversion v0.2                       #
# Copyright (C) 2021 SDC2 Team SoFiA                                   #
# ____________________________________________________________________ #
#                                                                      #
# Address:  Tobias Westmeier                                           #
#           ICRAR M468                                                 #
#           The University of Western Australia                        #
#           35 Stirling Highway                                        #
#           Crawley WA 6009                                            #
#           Australia                                                  #
#                                                                      #
# E-mail:   tobias.westmeier [at] uwa.edu.au                           #
# ____________________________________________________________________ #
#                                                                      #
# This program is free software: you can redistribute it and/or modify #
# it under the terms of the GNU General Public License as published by #
# the Free Software Foundation, either version 3 of the License, or    #
# (at your option) any later version.                                  #
#                                                                      #
# This program is distributed in the hope that it will be useful, but  #
# WITHOUT ANY WARRANTY without even the implied warranty of MERCHANT- #
# ABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General     #
# Public License for more details.                                     #
#                                                                      #
# You should have received a copy of the GNU General Public License    #
# along with this program. If not, see http://www.gnu.org/licenses/.   #
# ____________________________________________________________________ #
#                                                                      #
# Usage: physical_parameter_conversion.py <VOTable> [<rel_thresh>      #
#        [<snr_thresh> [<n_pix_thresh>]]]                              #
#                                                                      #
# <VOTable> is the SoFiA 2 catalogue in VOTable (XML) format. The      #
#   catalogue must have been obtained with both physical parameter     #
#   conversion and WCS conversion enabled (SoFiA 2 settings 'parameter #
#   .physical = true' and 'parameter.wcs = true').                     #
#                                                                      #
# <rel_thresh> is an optional reliability threshold. If set, then      #
#   only detections with a reliability >= <rel_thresh> will be added   #
#   to the output catalogue.                                           #
#                                                                      #
# <snr_thresh> is an optional threshold in integrated signal-to-noise  #
#   (SNR) ratio, where SNR is calculated as f_sum / err_f_sum. Only    #
#   detections with SNR >= <snr_thresh> will be added to the output    #
#   catalogue.                                                         #
#                                                                      #
# <n_pix_thresh> is an optional threshold in the total number of       #
#   pixels contained within the source mask (SoFiA parameter n_pix).   #
#   Only detections with n_pix >= <n_pix_thresh> will be added to the  #
#   output catalogue.                                                  #
#                                                                      #
# The purpose of this script is to convert the raw source parameters   #
# from the SoFiA 2 catalogue into the required physical parameters to  #
# be submitted to the SKA Science Data Challenge 2. The catalogue from #
# SoFiA 2 must be in XML format (VOTable), and the output will be      #
# written to standard output in the correct format required by the     #
# SDC2 scoring service.                                                #
# A typical example call might look like this:                         #
#                                                                      #
#   ./physical_parameter_conversion.py sofia_cat.xml > sdc2_cat.dat    #
#                                                                      #
# which would read the SoFiA 2 source catalogue named "sofia_cat.xml"  #
# and direct the output to a file named "sdc2_cat.dat" which can then  #
# be submitted directly to the SDC2 scoring service.                   #
#                                                                      #
# Note that several settings and assumptions, e.g. on the cosmology    #
# used, are hard-coded at the beginning of the main routine below.     #
# Users are advised to review and revise those as needed.              #
# ____________________________________________________________________ #
#                                                                      #

import sys
import math
from astropy.cosmology import FlatLambdaCDM
from astropy.io.votable import parse_single_table


# ----------------------
# Gaussian deconvolution
# ----------------------
#
# This function deconvolves the major axis, minor axis and position angle of
# one Gaussian with those of another Gaussian. The deconvolved parameters are
# returned. The algorithm is the same as the one used by the ATNF Miriad data
# reduction package.
#
# Arguments:
#
#  a1, b1    Major and minor axis of the Gaussian to be deconvolved. These
#            must be standard deviations (sigma) in radians (rad).
#  pa1       Position angle in radians of the Gaussian to be deconvolved.
#  a2, b2    Same as a1, b1, but for the Gaussian to deconvolve with
#            (e.g. beam size).
#  pa2       Same as pa1. but for the Gaussian to deconvolve with
#            (e.g. beam PA).
#
# Return value:
#
#  (a, b, pa)   Tuple containing the major axis, minor axis and position angle
#               of the deconvolved Gaussian. a and b are standard deviations
#               in radians, while pa is the position angle in radians.

def deconvolve(a1, b1, pa1, a2, b2, pa2):
    alpha = (a1 * math.cos(pa1)) ** 2.0 + (b1 * math.sin(pa1)) ** 2.0 - \
        (a2 * math.cos(pa2)) ** 2.0 - (b2 * math.sin(pa2)) ** 2.0
    beta = (a1 * math.sin(pa1)) ** 2.0 + (b1 * math.cos(pa1)) ** 2.0 - \
        (a2 * math.sin(pa2)) ** 2.0 - (b2 * math.cos(pa2)) ** 2.0
    gamma = 2.0 * (b1 * b1 - a1 * a1) * math.sin(pa1) * math.cos(pa1) - \
        2.0 * (b2 * b2 - a2 * a2) * math.sin(pa2) * math.cos(pa2)

    if(alpha < 0 or beta < 0):
        return (0.0, 0.0, 0.0)

    s = alpha + beta
    t = math.sqrt((alpha - beta) * (alpha - beta) + gamma * gamma)

    if(s < t):
        return (0.0, 0.0, 0.0)

    a = math.sqrt(0.5 * (s + t))
    b = math.sqrt(0.5 * (s - t))
    if (abs(alpha - beta) + abs(gamma) > 0.0):
        pa = 0.5 * math.atan2(-gamma, alpha - beta)
    else:
        pa = 0.0

    return (a, b, pa)


# --------------------
# Conversion functions
# --------------------
#
# Several convenience functions for converting between frequently required
# properties. These should all be self-explanatory.

def deg_to_rad(x):
    return x * math.pi / 180.0


def rad_to_deg(x):
    return x * 180.0 / math.pi


def sigma_to_fwhm(x):
    return x * 2.0 * math.sqrt(2.0 * math.log(2.0))


def fwhm_to_sigma(x):
    return x / (2.0 * math.sqrt(2.0 * math.log(2.0)))


def deg_to_arcsec(x):
    return x * 3600.0


def arcsec_to_deg(x):
    return x / 3600.0


# --------------------------
# Parameter bias corrections
# --------------------------
#
# Noise bias correction for certain parameters as a function of flux.
# The flux is expected to be supplied in units of Jy Hz.
# The corrections were derived by comparing the parameters measured by
# SoFiA with those from the truth catalogue during a test run on the
# 40 GB development data cube.

def corr_flux(flux):
    x = math.log10(flux)
    return -1.95944 * math.pow(x, 6) + 25.0718 * math.pow(x, 5) - \
        130.981 * math.pow(x, 4) + 357.67 * math.pow(x, 2) - \
        538.804 * math.pow(x, 2) + 424.973 * x - 136.178


def corr_w20(flux):
    x = math.log10(flux)
    return 0.109584 * math.pow(x, 3) - 1.092518 * math.pow(x, 2) + \
        3.013832 * x - 1.309686


def corr_size(flux):
    x = math.log10(flux)
    return 0.384714 * math.pow(x, 3) - 2.448307 * math.pow(x, 2) + \
        4.967467 * x - 2.287058


# ------------
# Main routine
# ------------

def main():
    # Mathematical and physical constants
    const_c = 299792.458       # km/s
    const_f0 = 1.420405752e+9  # Hz
    micro = 1e-6
    milli = 1e-3
    kilo = 1e+3
    mega = 1e+6

    # Global settings
    H0 = 67.00                  # Hubble constant in km/s/Mpc
    Om0 = 0.32                  # cosmic matter density
    beam_size = 7.00            # beam FWHM in arcsec
    px_size = 2.80              # pixel size in arcsec
    ch_size = 3e+4              # channel size in Hz
    beam_area = math.pi * (beam_size / px_size) * (beam_size / px_size) / (4.0 * math.log(2.0))
    cosmo = FlatLambdaCDM(H0=H0, Om0=Om0)  # set up cosmology

    # Default thresholds
    thresh_rel = 0.0
    thresh_npix = 0.0
    thresh_snr = 0.0

    # Default values for unresolved sources
    def_size = 8.5      # mean HI size assumed for point sources (arcsec)
    def_incl = 57.3     # mean disk inclination assumed for point sources (deg)

    # Check command-line arguments
    if len(sys.argv) < 2 or len(sys.argv) > 5:
        sys.stderr.write(
            "Usage: ./physical_parameter_conversion.py <VOTable> [<rel_thresh> [<snr_thresh> [<n_pix_thresh>]]]\n"  # noqa
        )
        sys.exit(1)

    if len(sys.argv) > 2:
        thresh_rel = float(sys.argv[2])

    if len(sys.argv) > 3:
        thresh_snr = float(sys.argv[3])

    if len(sys.argv) > 4:
        thresh_npix = float(sys.argv[4])

    # Read SoFiA catalogue (VOTable only)
    table = parse_single_table(sys.argv[1])

    # Extract relevant columns
    freq = table.array["freq"].data                 # Hz
    flux = table.array["f_sum"].data                # Jy Hz
    flux_err = table.array["err_f_sum"].data        # Jy Hz
    ell_maj = table.array["ell_maj"].data           # px (2 sigma)
    ell_min = table.array["ell_min"].data           # px (2 sigma)
    ell_pa = table.array["ell_pa"].data             # deg
    w20 = table.array["w20"].data                   # Hz
    kin_pa = table.array["kin_pa"].data + 180.0     # deg
    ra = table.array["ra"].data                     # deg
    dec = table.array["dec"].data                   # deg
    rel = table.array["rel"].data
    n_pix = table.array["n_pix"].data
    rms = table.array["rms"].data
    skew = table.array["skew"].data
    fill = table.array["fill"].data
    std = table.array["std"].data
    snr = flux / flux_err

    for i in range(len(kin_pa)):
        if kin_pa[i] < 0.0 or math.isnan(kin_pa[i]):
            kin_pa[i] = 0.0
        while kin_pa[i] >= 360.0:
            kin_pa[i] -= 360.0

    # Print header row
    sys.stdout.write(
        "id ra dec hi_size line_flux_integral central_freq pa i w20\n"
    )
    source_id_counter = 0

    # Loop over all detections
    for i in range(len(freq)):
        # Check user-defined thresholds
        if snr[i] < thresh_snr or n_pix[i] < thresh_npix or rel[i] < thresh_rel:  # noqa
            continue

        # Hard-coded cuts in skew-n_pix space and fill-snr space
        # These are the primary cuts used to discard false positives
        # due to noise
        if skew[i] < -0.00135 * (n_pix[i] - 942) or fill[i] > 0.18 * snr[i] + 0.17:  # noqa
            continue

        # --------------------------------------------
        # (1) Convert ellipse size to physical HI size
        #     and calculate disc inclination angle
        # --------------------------------------------
        hi_size = def_size
        incl = def_incl

        # Obtain redshift and distances
        z = const_f0 / freq[i] - 1
        dl = cosmo.luminosity_distance(z).value                         # Mpc
        da = cosmo.angular_diameter_distance(z).value                   # Mpc

        # Deconvolve major and minor axis of source
        a1 = deg_to_rad(0.5 * ell_maj[i] * arcsec_to_deg(px_size))      # rad (sigma)
        b1 = deg_to_rad(0.5 * ell_min[i] * arcsec_to_deg(px_size))      # rad (sigma)
        pa1 = deg_to_rad(ell_pa[i])                                     # rad
        a2 = fwhm_to_sigma(deg_to_rad(arcsec_to_deg(beam_size)))        # rad (sigma)
        (a, b, pa) = deconvolve(a1, b1, pa1, a2, a2, 0.0)               # note: beam is symmetric

        if a != 0.0 and b != 0.0:
            # Convert deconvolved major axis to physical size
            sigma_phys = a * da * mega                                  # pc (sigma)

            # Derive HI mass and central mass surface density
            M_HI = 49.7 * dl * dl * flux[i]                             # M_sun
            S0 = M_HI / (2.0 * math.pi * sigma_phys * sigma_phys)       # M_sun / pc^2

            if S0 > 1.0:
                # Source diameter at 1 M_sun/pc^2
                hi_size = math.sqrt(-2.0 * math.log(1.0 / S0)) * sigma_phys      # pc
                hi_size = 2.0 * deg_to_arcsec(rad_to_deg(hi_size * micro / da))  # arcsec
                hi_size /= corr_size(flux[i])

                # Disc inclination
                incl = rad_to_deg(math.acos(b / a))

        # --------------------------------------------
        # (2) Convert line width to km/s in source RF
        # --------------------------------------------
        w20[i] *= const_c * (1.0 + z) / (const_f0 * corr_w20(flux[i]))  # km/s

        # --------------------------------------------
        # (3) Print output row increment counter
        # --------------------------------------------
        if w20[i] > 0.0 and corr_flux(flux[i]) > 0.0 and hi_size > 0.0:
            sys.stdout.write(
                "{:d} {:.14f} {:.14f} {:.14f} {:.14f} {:.1f} {:.14f} {:.14f} {:.14f}\n".format(source_id_counter, ra[i], dec[i], hi_size, flux[i] / corr_flux(flux[i]), freq[i], kin_pa[i], incl, w20[i])  # noqa
            )
            source_id_counter += 1


# ------------
# Run main
# ------------

if __name__ == "__main__":
    main()
