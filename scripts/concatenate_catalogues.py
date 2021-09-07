#!/usr/bin/env python3
# ____________________________________________________________________ #
#                                                                      #
# SDC2-SoFiA: SoFiA catalogue concatenation script v0.1                #
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
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANT- #
# ABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General     #
# Public License for more details.                                     #
#                                                                      #
# You should have received a copy of the GNU General Public License    #
# along with this program. If not, see http://www.gnu.org/licenses/.   #
# ____________________________________________________________________ #
#                                                                      #
# The purpose of this script is to concatenate the individual source   #
# catalogues produced by SoFiA 2 from the 80 parameter files used to   #
# run the pipeline in parallel on the full SKA SDC2 data cube. It is   #
# assumed that the input catalogues are named 'sofia_sdc2_001_cat.xml' #
# to 'sofia_sdc2_080_cat.xml'. The script will write the concatenated  #
# output catalogue, named 'merged_catalogue.xml', to disc.             #
# ____________________________________________________________________ #

from astropy.io.votable import parse_single_table, from_table, writeto
from astropy.table import vstack


print("Loading catalogue 1")
table = parse_single_table("sofia_sdc2_001_cat.xml").to_table()

for i in range(2, 81):
    print("Loading catalogue {:d}".format(i))
    table2 = parse_single_table(
        "sofia_sdc2_{:03d}_cat.xml".format(i)
    ).to_table()
    table = vstack([table, table2])

print("Writing merged catalogue")
votable = from_table(table)
writeto(votable, "merged_catalogue.xml")
