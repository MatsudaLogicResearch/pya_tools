#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#===================================================================
# This file is associated with the pya_toos project.
# Copyright (C) 2025 LogicResearch K.K (Author: MATSUDA Masahiro)
# 
# This script file is licensed under the MIT License.
#===================================================================
import pya
import os, sys

# argument is given from klayout -rd <name>=<value> options.
#  ex) klayout -b -r pya_flatspice.py -rd ifile=xxx -rd ofile=yyyy -rd top=top_cell
#ifile="top.spice"
#ofile="top_flat.spice"
#top="top"

print(f"[INFO] ifile={ifile}, ofile={ofile}, top={top}")

# check
if not os.path.isfile(ifile):
    print(f"[ERROR]: Input file '{ifile}' does not exist.", file=sys.stderr)
    sys.exit(1)

# flatten
netlist=pya.Netlist()
reader=pya.NetlistSpiceReader()
writer=pya.NetlistSpiceWriter()
writer.use_net_names=True

netlist.read(ifile, reader)

top_name=top

#-- search target cell
if top_name in list(netlist.each_circuit()):
    print(f"[ERROR]: top cell '{top_name}' does not exist.", file=sys.stderr)
    sys.exit(1)
    
#-- flatten cell except top-cell
for circuit in list(netlist.each_circuit()):
    if circuit.name != top_name:
        print(f"  [INFO] flatten cell{circuit.name}")
        netlist.flatten_circuit(circuit.name)

#---#-- remove AS/AD/PS/PD
#---remove_params = {"AS", "AD", "PS", "PD"}
#---for circuit in netlist.each_circuit():
#---  for device in circuit.each_device():
#---
#---    #-- read parameter list (L,W,AS,AD,PS,PD)
#---    for param_def in device.device_class().parameter_definitions():
#---      print(param_def.name)
#---      print(device.parameter("AD"))

#--- write out
netlist.write(ofile, writer)

#EOF
