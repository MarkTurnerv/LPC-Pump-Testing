# -*- coding: utf-8 -*-
"""
Graphing LPC Thermal Chamber Results
Mark Turner
Created 6/7/24

NOTE: The labels for Current 1 and Current 2 are still switched in the LOPC code
"""
#reset
from IPython import get_ipython
get_ipython().magic('clear')
get_ipython().magic('reset -f')

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

plt.close('all')

filename = 'LPC0008_ThermalTest1B'
pump1 = 5;
pump2 = 6;
filename2 = filename + '.txt'

script_dir = os.path.dirname(__file__)
results_dir = os.path.join(script_dir, 'Graphs/')

os.makedirs(results_dir, exist_ok=True)

pump_data = pd.read_table(filename2, sep=",", header=[0])
pump_data.rename(columns=lambda x: x.strip(), inplace=True)
maxTime = len(pump_data) * 5
time = range(0,maxTime,5)
temp_hrs = 0;
temp_min = 0;
temp_sec = 0;
time2 = []
'''
for x in time:
    time_string = x
    split_time = time_string.split(":")
    stripped_time = [s.strip() for s in split_time]
    for i in range(0, len(stripped_time)):
        stripped_time[i] = int(stripped_time[i])
    if stripped_time[0] < temp_hrs:
        stripped_time[2] += temp_sec
        if stripped_time[2] > 60:
            temp_min += 1
            stripped_time[2] -= 60;
        stripped_time[1] += temp_min
        if stripped_time[1] > 60:
            temp_hrs += 1
            stripped_time[1] -= 60;
        stripped_time[0] += temp_hrs
    time_string = str(stripped_time[0]) + ":" + str(stripped_time[1]) + ":" + str(stripped_time[2])
    time2.append(time_string)
    


'''
plt.plot(time, pump_data['T_Pump1 [C]'],time, pump_data['T_Pump2 [C]'],time, pump_data['T_PCB [C]'])
#plt.plot(time,pump_data['T_Pump1 [C]'],'s')
plt.ylabel("Temperature")
plt.grid()
plt.ylim([-15, 0])
plt.title(filename.replace("_",' ')+" Pump Temperature vs Time")
plt.legend(['Pump 1','Pump 2','PCB'])
plt.savefig(os.path.join(results_dir,filename+"PumpTemps.png"))

plt.figure()
plt.plot(time, pump_data['Flow [SLM]'])
#plt.xticks(rotation=90)
#plt.locator_params(axis='x', nbins=10)
plt.ylim((8, 12))
plt.grid()
plt.title(filename.replace("_",' ')+" Flow Rate vs Time")
plt.savefig(os.path.join(results_dir,filename+"PumpFlow.png"))

plt.figure()
plt.plot(time, pump_data['I_Pump1 [A]'],time, pump_data['I_Pump2 [A]'])
plt.ylabel("Current [A]")
plt.grid()
#plt.ylim((200, 700))
plt.title(filename.replace("_",' ')+" Pump Current vs Time")
plt.legend(['Pump 1','Pump 2'])
plt.savefig(os.path.join(results_dir,filename+"PumpCurrent.png"))


def smooth(y, box_pts):
    box = np.ones(box_pts)/box_pts
    y_smooth = np.convolve(y, box, mode='same')
    return y_smooth

BEMF1_smooth = smooth(pump_data['BEMF_1'],50)
BEMF2_smooth = smooth(pump_data['BEMF_2'],50)

#fig = plt.figure
plt.figure()
plt.plot(time, BEMF1_smooth)
plt.plot(time, BEMF2_smooth)
plt.ylabel("Pump Back EMF [V]")
plt.grid('major',linewidth = 0.5)
plt.ylim((2, 8))
plt.xticks(rotation=270)
plt.title(filename.replace("_",' ')+" Pump Back EMF vs Time")
plt.legend(['Pump 1','Pump 2'])
plt.savefig(os.path.join(results_dir,filename+"PumpBEMF.png"))

plt.figure()
plt.plot(time, pump_data['Pump1_PWM'],time, pump_data['Pump2_PWM'])
plt.ylabel("Pump PWM Count")
plt.grid()
#plt.ylim((400, 1000))
plt.title(filename.replace("_",' ')+" Pump PWM vs Time")
plt.legend(['Pump 1','Pump 2'])
plt.savefig(os.path.join(results_dir,filename+"PumpPWM.png"))

plt.figure()
plt.plot(time, pump_data['I_Det [mA]'])
plt.ylabel("I_Det [mA]")
plt.grid()
#plt.ylim((400, 1000))
plt.title(filename.replace("_",' ')+" I_Det [mA] vs Time")
plt.savefig(os.path.join(results_dir,filename+"I_Det [mA].png"))
'''
plt.figure()
pump_data.plot(x="Time", y = ['PumpCycle'], marker='o',linewidth=0,markersize=0.1)
plt.ylabel("Pump Cycle Count")
plt.grid()
plt.title(filename.replace("_",' ')+" Pump Cycle Count vs Time")
plt.savefig(os.path.join(results_dir,filename+"PumpCycle.png"))


def smooth(y, box_pts):
    box = np.ones(box_pts)/box_pts
    y_smooth = np.convolve(y, box, mode='same')
    return y_smooth

BEMF1_smooth = smooth(pump_data['BEMF_1'],50)
BEMF2_smooth = smooth(pump_data['BEMF_2'],50)

plt.figure(figsize=(19.2,14.4))
axs = plt.subplot(6,1,1)
#pump_data.plot(x="Time", y = ['T_Pump1 [C]','T_Pump2 [C]', 'T_PCB [C]'])
plt.plot(time,pump_data['I_Pump2 [A]'])
plt.ylabel("Current [A]")
#plt.title("Pump " + str(pump1) +" Current vs Time")
plt.grid()

plt.subplot(6,1,2)
plt.plot(time, pump_data['Flow [SLM]'])
plt.ylabel("FLow Rate")
#plt.ylim(())
#plt.title(" Flow Rate vs Time")
plt.grid()

plt.subplot(6,1,3)
plt.plot(time, BEMF1_smooth)
plt.ylabel("BEMF (AVG)")
#plt.ylim(())
#plt.title(" BEMF vs Time")
plt.grid()

plt.subplot(6,1,4)
plt.plot(time, pump_data['T_Pump1 [C]'])
plt.ylabel("Temperature")
#plt.ylim(())
#plt.title(" Temperature vs Time")
plt.grid()

plt.subplot(6,1,5)
plt.plot(time, pump_data['Pump1_PWM'])
plt.ylabel("PWM")
#plt.ylim(())
#plt.title(" PWM vs Time")
plt.grid()

plt.subplot(6,1,6)
plt.plot(time, pump_data['PumpCycle'], marker='o',linewidth=0,markersize=0.1)
plt.ylabel("Pump Cycle")
#plt.ylim(())
#plt.title(" Pump Cycle vs Time")
plt.grid()
plt.suptitle("Pump "  + str(pump1))


#plt.show

'''