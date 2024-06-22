import PySimpleGUI as sg           
import sys 
import time
import csv
import serial # import Serial Library
import serial.tools.list_ports
import numpy as np # Import numpy
import matplotlib
import matplotlib.pyplot as plt #import matplotlib library
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation
 
#define the CNC data Arrays
Pump1_T = []
Pump2_T = []
PCB_T = []
Pump1_I = []
Pump2_I = []
Battery_V = []
Pump1_BEMF = []
Pump1_PWM = []
Pump2_BEMF = []
Pump2_PWM = []
LOPC_time = [0]
sum300 = []
sum500 = []
sum1000 = []
sum2000 = []

HG_Sizes = []
LG_Sizes = []

Frame = 0

hg_m = 7.524e-4
hg_b = -2.543e-2
lg_m = 5.979e-3
lg_b = -0.1895
c4 = -71.05
c3 = 282.74
c2 = 329.18
c1 = 1132.3
c0 = 297.09
flow = 20.0

Instrument_name = 'Default'

#flow_input = input("Enter the intrument flow rate in VLPM:")
#flow = float(flow_input)


plt.ion() #Tell matplotlib you want interactive mode to plot live data
cnt=0
secs = 0

def pick_a_port():
    
    cal_array = np.loadtxt('LOPC_Calibration_Record.txt', delimiter = ',')
    instruments = ["%d" % sn for sn in cal_array[0:,0]]
    instruments = ['Default'] + instruments

    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        print(p)

    instrument_layout = [[sg.InputCombo(values=instruments, key = '_inst_',  font = ('any', 16))]]
    port_layout = [[sg.InputCombo(values=ports, key = '_port_',  font = ('any', 16))]]
    layout_pick_port = [[sg.Frame('Select Instrument: ', instrument_layout, font = 'any 16')],
                        [sg.Frame('Select Serial Port: ', port_layout, font = 'any 16')],
                        [sg.Submit( font = ('any', 16)), sg.Cancel( font = ('any', 16))]]

    serial_window = sg.Window('Select LOPC Instrument and Port', layout_pick_port)
    event, values = serial_window.Read()
    serial_window.Close()

    if event is None or event == 'Cancel':
        return None
    if event == 'Submit':
        print(values['_port_'])
        print(values['_inst_'])

        if values['_inst_'] == 'Default':
            cal_val = np.array([999,hg_m,hg_b,lg_m, lg_b, c4, c3, c2, c1, c0, flow])
        else:
            inst = instruments.index(values['_inst_']) - 1
            print('Calibration constants: ')
            print(cal_array[inst,0:])
            cal_val = cal_array[inst,0:]
            global Instrument_name
            Instrument_name = 'LOPC ' + values['_inst_']
            
        s = serial.Serial(str(values['_port_']).split(' ', 1)[0])
        #s.reset_input_buffer()
        return s, cal_val

 
def make_LOPC_fig(cal_val, log_lin):  #Plot the CN Counts
    diams, counts, sum300, sum500, sum1000, sum2000 = scale_bins(cal_val)
    try:

        plt.subplot2grid((4,1), (3, 0))
        plt.ylim(0, 1000)
        plt.title('Currents', fontsize = 'x-small')      #Plot the title
        plt.grid(True)                                  #Turn the grid on
        plt.ylabel('mA')                            #Set ylabels
        plt.plot(LOPC_time[1:], Pump1_I, 'k-', label='Pump1 I')       #plot the channels
        plt.plot(LOPC_time[1:], Pump2_I, 'r-', label='Pump2 I')
        plt.legend(loc='upper left', fontsize = 'x-small')
        plt.xlabel('Elapsed Time [s]', fontsize = 'x-small')
        plt.tight_layout()
        
        plt2=plt.twinx()
        plt2.plot(LOPC_time[1:], Pump1_T, 'b-', label='Pump1 T')
        plt2.plot(LOPC_time[1:], Pump2_T, 'g-', label='Pump2 T')
        plt2.legend(loc='upper right', fontsize = 'x-small')
        
        plt.subplot2grid((4,1), (0,0), colspan = 1, rowspan = 2)
        plt.fontsize = 'small'
        plt.title(Instrument_name, fontsize = 'x-small')      #Plot the title
        plt.ylabel('dN/dD')                            #Set ylabels
        plt.xlabel('Diameter [nm]', fontsize = 'small')
        plt.plot(diams, smooth(counts,5), 'k-', label='High Gain')       #plot the channels
        plt.xlim(300,10000)
        plt.xscale('log')
        xticks = [300,400, 500, 700, 1000, 2000, 5000]
        plt.grid(True)
        plt.xticks(xticks, ['%d'  % i for i in xticks] )
        #plt.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        if log_lin == True:
            plt.yscale('log')
        plt.tight_layout()
        
        plt.subplot2grid((4,1), (2, 0))
        plt.title('Cumulative', fontsize = 'x-small')      #Plot the title
        plt.grid(True)                                  #Turn the grid on
        plt.ylabel('#/cc')                            
        plt.plot(LOPC_time[1:], sum300, 'k-', label='300nm')
        plt.plot(LOPC_time[1:], sum500, 'r-', label='500nm')
        plt.plot(LOPC_time[1:], sum1000, 'b-', label='1000nm')
        plt.plot(LOPC_time[1:], sum2000, 'g-', label='2000nm')
        if log_lin == True:
            plt.yscale('log')
        plt.legend(loc='upper left', fontsize = 'x-small')
        plt.tight_layout()
    except:
        print('Plotting Exception')
 
 
 
def decode_string(strng, saveFile, filename):
    d = strng.split(',')   #Split it into an array called dataArray
    #print(len(d))
    
    if len(d) == 534 or len(d) == 537:
        Pump1_T.append(float(d[8]))
        Pump2_T.append(float(d[9]))
        PCB_T.append(float(d[11]))
        Pump1_I.append(float(d[13]))
        Pump2_I.append(float(d[14]))
        Battery_V.append(float(d[18]))
        Pump1_BEMF.append(float(d[19]))
        Pump1_PWM.append(float(d[20]))
        Pump2_BEMF.append(float(d[21]))
        Pump2_PWM.append(float(d[22]))
        LOPC_time.append(LOPC_time[-1]+2)

        global HG_Array
        global LG_Array
        HG_Array = np.array(list(map(float,d[23:278])),dtype = float)
        LG_Array = np.array(list(map(float,d[279:533])),dtype = float)
        
        d.insert(0,time.strftime("%H%M%S"))
        
        if saveFile == True:                
            with open(filename, mode='a') as output_file:
                output_writer = csv.writer(output_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                output_writer.writerow(d)
        return True
    return False

def smooth(y, box_pts):
    box = np.ones(box_pts)/box_pts
    y_smooth = np.convolve(y, box, mode='same')
    return y_smooth

def scale_bins(cal_val):

    indexer = 4.0*np.array(range(len(HG_Array),0, -1), dtype=float)

    #calculate voltage arrays for HG and LG
    HG_volts = cal_val[1]*indexer + cal_val[2]
    LG_volts = cal_val[3]*indexer + cal_val[4]
    
    #Stitch the too arrays together using 0.7V as the stitch point
    HG_stitch = np.argmin(abs(HG_volts - 0.7))
    LG_stitch = np.argmin(abs(LG_volts - 0.7))
    volts = np.concatenate((LG_volts[0:LG_stitch],HG_volts[HG_stitch:]))
    #calculate the correspodning diameters based on the calibration constants    
    diams = cal_val[5]*volts**4 + cal_val[6]*volts**3 + cal_val[7]*volts**2 + cal_val[8]*volts + cal_val[9]

    #stitch the two arrays of counts togther and divide by the flow rate
    counts = np.concatenate((LG_Array[0:LG_stitch],HG_Array[HG_stitch:]))
    counts = counts / (cal_val[10]*1000.0/30.0)
    #reverse the arrays so that the small particles are first
    counts = np.flip(counts)
    diams = np.flip(diams)

    #cut off the arrays at 10,000nm as the fit inverts at that point.
    ten_microns = np.argmax(diams)
    diams = diams[0:ten_microns]
    counts = counts[0:ten_microns]

    #calculate the bin widths and then repeat the last one to make the diffs 
    dr = np.diff(diams)
    dr = np.append(dr, dr[-1])

    #create dn/dr
    dndr = counts/dr

    indx300nm = np.argmin(abs(diams - 300.0))
    indx500nm = np.argmin(abs(diams - 500.0))
    indx1000nm = np.argmin(abs(diams - 1000.0))
    indx2000nm = np.argmin(abs(diams - 2000.0))
    
    sum300.append(sum(counts[indx300nm:])) 
    sum500.append(sum(counts[indx500nm:]))
    sum1000.append(sum(counts[indx1000nm:]))
    sum2000.append(sum(counts[indx2000nm:]))

    return diams, dndr, sum300, sum500, sum1000, sum2000

def main():
    cnt = 0
    flow = 20.0
    s, cal_val = pick_a_port()
    log_plot = True
    filename = time.strftime("%Y%m%d-%H%M%S") + "_LOPC.csv"
    saveFile = False

    plot_frame_layout = [[sg.Text('Plot Axis Type: ', font = ('any', 16))],
                         [sg.Button('Log', font = ('any', 16), border_width = 3), sg.Button('Linear', font = ('any', 16),border_width = 3)]]
    
    config_frame_layout = [[sg.Text('Flow Rate [VLPM]: ',  font = ('any', 16)), sg.Input(do_not_clear=True, key='_Flow_')],
                           [sg.Text('Pump Set Point: ',  font = ('any', 16)), sg.Input(do_not_clear=True, key='_BEMF_')],
                           [sg.Button('Upload', font = ('any', 16), border_width = 3, button_color = ('black', 'green')), sg.Button('Save Settings to EEPROM', font = ('any', 16),border_width = 3, button_color = ('black', 'green'))]]
    save_frame_layout = [[sg.Text('File Name: ',  font = ('any', 16)), sg.Input(do_not_clear=True, key='_FileName_', font = ('any', 16))],
                        [sg.Button('Save', font = ('any', 16), border_width = 3, button_color = ('black', 'green')), sg.Button('Stop', font = ('any', 16),border_width = 3, button_color = ('black', 'red'))], [sg.Checkbox('Saving File', default = False, key = '_SaveLED_')]]

    layout_cmnd = [[sg.Text('LOPC Instrument Configuration', font = ('any', 16, 'underline'))],
                   [sg.Frame('Instrument Configuration', config_frame_layout, title_color = 'blue', font = 'Any 16')],
                   [sg.Frame('Plot Configuration', plot_frame_layout, title_color = 'blue', font = 'Any 16')],
                   [sg.Frame('Log File', save_frame_layout, title_color = 'blue', font = 'Any 16')],                   
                   [sg.Button('Exit',  font = ('any', 16),border_width = 3, button_color = ('black', 'red'))]]

    window1 = sg.Window('LOPC Command', layout_cmnd, keep_on_top=True)

    #window1.Element('_FileName_').Update(filename)

    layout_hk =[[sg.Text('LOPC House Keeping', font = ('any', 16, 'underline'))],
                [sg.Text('')],
                [sg.Text('OPC Time: ',  font = ('any', 16)), sg.Text('', key='_OPC_Time_',  font = ('any', 16))],
                [sg.Text('LOPC Raw Counts: ',  font = ('any', 16)), sg.Text('', key='_CN_Counts_',  font = ('any', 16))],
                [sg.Text('Pump 1 Temp: ',  font = ('any', 16)), sg.Text('', key='_Pump1_T_',  font = ('any', 16))],
                [sg.Text('Pump 1 I: ',  font = ('any', 16)), sg.Text('', key='_Pump1_I_',  font = ('any', 16))],
                [sg.Text('Pump 1 Drive: ',  font = ('any', 16)), sg.Text('', key='_Pump1_PWM_',  font = ('any', 16))],
                [sg.Text('')],
                [sg.Text('Pump 2 Temp: ',  font = ('any', 16)), sg.Text('', key='_Pump2_T_',  font = ('any', 16))],
                [sg.Text('Pump 2 I: ',  font = ('any', 16)), sg.Text('', key='_Pump2_I_',  font = ('any', 16))],
                [sg.Text('Pump 2 Drive: ',  font = ('any', 16)), sg.Text('', key='_Pump2_PWM_',  font = ('any', 16))],
                [sg.Text('')],
                [sg.Text('Internal Temp: ',  font = ('any', 16)), sg.Text('', key='_PCB_T_',  font = ('any', 16))],
                [sg.Text('Battery Voltage: ',  font = ('any', 16)), sg.Text('', key='_Batt_V_',  font = ('any', 16))]]

    window2 = sg.Window('LOPC House Keeping', layout_hk, keep_on_top=True)
    
    while True: # While loop that loops forever
        #print('Waiting for data')
        LOPCString = ''
        while (len(LOPCString) == 0): #Wait here until there is data
            LOPCString = s.readline().decode('ascii').strip() #read the line of text from the serial port
            event, values = window1.Read(timeout=0)
            event2, values2 = window2.Read(timeout=0) 
            if event is None or event == 'Exit':  
                s.close()
                sys.exit()
                break
            if event == 'Save':
                if values['_FileName_'] != '':
                    filename = values['_FileName_']
                saveFile = True
                window1.Element('_SaveLED_').Update(value=True)
                print('Saving to: '+filename)
            if event == 'Stop':
                saveFile = False
                window1.Element('_SaveLED_').Update(value=False)
                print('Stop Saving')
            if event == 'Save Settings to EEPROM':
                print("Saving Settings")
                out = '#save\n'
                s.write(out.encode())
            if event == 'Upload':
              if values['_BEMF_'] != '':
                  out = '#BEMF,' + values['_BEMF_'] + '\n'
                  print(out)
                  s.write(out.encode())
                  values['_BEMF_'] = ''
              if values['_Flow_'] != '':
                  flow = float(values['_Flow_']) 
                  print("Updating Flow Rate")
            if event == 'Log':
                  log_plot = True
                  print('Switching to Log')
            if event == 'Linear':
                  log_plot = False
                  print('Switching to Linear')
                
            time.sleep(0.01)

       
        if decode_string(LOPCString,saveFile,filename) == True:
 
            plt.clf()
            make_LOPC_fig(cal_val, log_plot)
            time.sleep(0.01) 
            plt.draw()
            time.sleep(0.01)                #Pause Briefly. Important to keep drawnow from crashing

            window2.Element('_OPC_Time_').Update(LOPC_time[-1])
            window2.Element('_CN_Counts_').Update(int(sum300[-1]*(flow*1000.0/30.0)))
            window2.Element('_PCB_T_').Update(PCB_T[-1])
            window2.Element('_Pump1_T_').Update(Pump1_T[-1])
            window2.Element('_Pump2_T_').Update(Pump2_T[-1])
            window2.Element('_Pump1_I_').Update(Pump1_I[-1])
            window2.Element('_Pump2_I_').Update(Pump2_I[-1])
            window2.Element('_Pump1_PWM_').Update(Pump1_PWM[-1])
            window2.Element('_Pump2_PWM_').Update(Pump2_PWM[-1])
            window2.Element('_Batt_V_').Update(Battery_V[-1])
            
            cnt=cnt+1    
        if(cnt>150):                            #If you have 150 or more points (5 minutes), delete the first one from the array
            Pump1_T.pop(0)
            Pump2_T.pop(0)
            PCB_T.pop(0)
            Pump1_I.pop(0)
            Pump2_I.pop(0)
            Battery_V.pop(0)
            Pump1_BEMF.pop(0)
            Pump1_PWM.pop(0)
            Pump2_BEMF.pop(0)
            Pump2_PWM.pop(0)
            LOPC_time.pop(0)
            sum300.pop(0)
            sum500.pop(0)
            sum1000.pop(0)
            LOPC_time.pop(0)
            
if (__name__ == '__main__'): 
    main()          
