/*
 * Pump_Test
 *  Initial Version Mark Turner
 *  Created: May 2024
 *  Last Edit: 6.21.24
 
 *  Purpose: run pumps for 3 minutes on, 3 minutes off; measure pump opperation
                -volumetric flow rate
                -current draw
                -temperature
                
    Outputs data to csv file (on instrument SD card) and to Serial Monitor
 */
#include "src/LOPCLibrary_revF.h"
String Version = "V5_0";
#define DEBUG_SERIAL Serial
#define FLOW_METER 1
#define sensor 0x49 //Define airflow sensor

#define T_PUMP_SHUTDOWN 80.0 // Max operating temperature for rotary vane pump
#define T_PCB_SHUTDOWN 65.0  // Max operating temperature for DC-DC converter
#define FLOW 0.667 //flow rate in liters per sample
#define MIN_FLIGHT_TIME 90*60*1000 // Minimum on time before we will shutdown for end of flight -  in milliseconds.

//EEPROM Addresses
#define EEPROM_FLAG  30 //value to say there is valid pump data in eeprom
#define EEPROM_PUMP1 40 //pump 1 BEMF (float)
#define EEPROM_PUMP2 50 //pump 2 BEMF (float)

boolean usingInterrupt = false;
boolean verbose = true;



/*Global Variables */
/*HK Temperatures*/
float TempPump1;
float TempPump2;
float TempPCB;
float TempCase;

/*HK Voltages */
float VBat;
float VTeensy;

/*Back EMF Control Variables */
int backEMF1 = 0;
int backEMF2 = 0;
float BEMF1_V = 0;
float BEMF2_V = 0;
float BEMF1_SP = 7.8; //Set point for large pumps
float BEMF2_SP = 7.8; //Set point for large pumps
float error1 = 0.0;
float error2 = 0.0;
float Kp = 30.0;
int BEMF1_pwm = 512;
int BEMF2_pwm = 512;

float Flow;

/*HK Currents */
float IPump1;
float IPump2;
float IHeater1;
float IHeater2;

float Pressure;

char OPCArray[1024];
String OPCString;
String OutputString = "";
String file;
int Frame = 1;
int TimeStamp = 0;
unsigned long ElapsedTime = 0;
String header;

float flow, avg_flow=0; //Define flow variable
byte aa,bb; //Define bytes used when requesting data from sensor
int digital_output; //Define integer to convert bytes to

bool ConverterOverTemp = false;
bool DCDCShutdown = false;
bool TimeON = 0;
int CheckTime = 180000; //3 Minute on time, in [ms]
int CheckTime2 = 360000;  //3 minute off time (6 minutes total)
int k=1;
int PumpAdjustTime = 5000;
int i=1;
String hrMinSec;
int PumpCycleCount = 1;
//int MFS_POWER = 4;

String DEBUG_Buff;

LOPCLibrary OPC(13);  //Creates an instance of the OPC

void setup() {
   pinMode(PULSE_LED, OUTPUT);  //Initialize heart beat LED
   digitalWrite(PULSE_LED, HIGH);
   
   DEBUG_SERIAL.begin(115200); //Setup the USB/serial debug port
   delay(100);

   /*Set up PWM for Motor Drive*/
   analogWriteResolution(10); //PWM duty cycle 0 - 1023
   analogWriteFrequency(PUMP1_PWR, 10000); //PWM Frequency
   analogWriteFrequency(PUMP2_PWR, 10000);
   
   DEBUG_SERIAL.println("OPC Mainboard");
   DEBUG_SERIAL.println(Version);
   
   OPC.SetUp();  //Setup the main board
   OPC.configure_memory_table(); //Setup the custom thermistor specs
   OPC.ConfigureChannels(); //Setup the LTC2983 Temperature Channels

  DEBUG_SERIAL.print("SD card initilization...");  
  if(!SD.begin(BUILTIN_SDCARD)){
   Serial.println("Warning,SD card not inserted");
  }
  DEBUG_SERIAL.println(" complete");

  pinMode(PHA_POWER,OUTPUT);
  digitalWrite(PHA_POWER,HIGH);
   
  //Configure UBlox to only send the NMEA strings we want
   byte settingsArray[] = {0x06, 0xE8, 0x03, 0x80, 0x25, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01}; 

   /* Mass Flow Meter Setup*/
   if(FLOW_METER)
   {
    pinMode(MFS_POWER, OUTPUT);  // Turn on Mass Flow Sensor
    digitalWrite(MFS_POWER, HIGH);
    Wire.begin();//Activate  Bus I2C 
   }

   /*OPC Serial port setup */
   OPCSERIAL.begin(500000);  //PHA serial speed = 0.5Mb  
   delay(500);
   OPCSERIAL.setTimeout(2000); //Set the serial timout to 2s
   
    /* Read parameters from EEPROM */
  int type = OPC.InstrumentType();
  int serial = OPC.SerialNumber();
  int filenum = OPC.FileNumber();
  
  /*Debug to console */
  DEBUG_SERIAL.println("Startup");
  DEBUG_SERIAL.print("Type: ");
  DEBUG_SERIAL.println(type);
  DEBUG_SERIAL.print("Serial: ");
  DEBUG_SERIAL.println(serial);
  DEBUG_SERIAL.print("File Number: ");
  DEBUG_SERIAL.println(filenum);

  
  DEBUG_SERIAL.println("Check for battery power before continuing");
  ReadHK();
  while (VBat < 12.0)
  {
    DEBUG_SERIAL.print("Battery Voltage: ");    
    DEBUG_SERIAL.println(VBat);
    DEBUG_SERIAL.println("Cannot start - Battery voltage too low, battery not connected, or power switch is off");
    delay(1000);
    ReadHK();
  }

  
  DEBUG_SERIAL.println("Turning on RS41 Power");
  
  digitalWrite(RS41_PWR, HIGH);  // Turn on the RS41 power supply
  delay(500);

  
    //This creates a file name that can be stored on the SD card
  file = OPC.CreateFileName();
  DEBUG_SERIAL.print("Filename: ");
  DEBUG_SERIAL.println(file);   

  //This checks to see if the file name has been used.
  if (OPC.FileExists(file) == true)
    file = OPC.GetNewFileName();
  memset(OPCArray, 0, sizeof(OPCArray));
  OPCString.reserve(1024);

  /* Write a header to the data file */
  //String header = "; MainBoard Firmware Version: " + Version + ", Main Board Revision: G, Flow Rate 20vLPM";
  //OPC.WriteData(file, header+"\n");
  String header = "Time, PumpCycle, T_Pump1 [C], T_Pump2 [C], T_PCB [C], T_Case [C], I_Pump1 [A], I_Pump2 [A], V_Bat, Flow [SLM], BEMF_1, Pump1_PWM, BEMF_2, Pump2_PWM";
  OPC.WriteData(file, header+"\n"); 
  ReadHK();
  DEBUG_SERIAL.println("Zero Currents: ");  //Read the current monitor zeros before starting pumps
  DEBUG_SERIAL.println( IPump1);
  DEBUG_SERIAL.println( IPump2);
  TempPCB = OPC.MeasureLTC2983(BOARD_THERM);  
  DEBUG_SERIAL.print("TempPCB: ");
  DEBUG_SERIAL.println(TempPCB);
  printHK();
  delay(100);

  /*Check to see if we have valid pump set points in EEPROM and read if we do */
  if (EEPROM.read(EEPROM_FLAG) == 0x01)
  {
    EEPROM.get(EEPROM_PUMP1, BEMF1_SP);
    DEBUG_SERIAL.print("Saved Pump 1 Setting loaded: ");
    DEBUG_SERIAL.println(BEMF1_SP);
    EEPROM.get(EEPROM_PUMP2, BEMF2_SP);
    DEBUG_SERIAL.print("Saved Pump 2 Setting loaded: ");
    DEBUG_SERIAL.println(BEMF2_SP);
  }
  else
  {
    DEBUG_SERIAL.println("Using default pump settings");
  }
  
  /* Turn on the pumps and read the initial current */
  DEBUG_SERIAL.print("Starting Pump 1, Initial Current (mA): ");
  analogWrite(PUMP1_PWR, BEMF1_pwm);
  delay(100);
  ReadHK();
  DEBUG_SERIAL.println(IPump1);

  delay(1000);
  DEBUG_SERIAL.print("Starting Pump 2, Initial Current (mA): ");
  analogWrite(PUMP2_PWR, BEMF1_pwm);
  delay(100);
  ReadHK();
  DEBUG_SERIAL.println(IPump2);
  digitalWrite(PULSE_LED, LOW);

}


/* Main operating loop, runs for ever. 
 * Timing is defined by incoming serial data strings from Pulse Height Analyzer
 */

void loop() {

  TimeON = 1;
  while (TimeON) {
  checkForSerial();
    int indx = 0;   


      /* Get Temperatures from LTC2983, and reset if there is a glitch */
      TempPump1 = OPC.MeasureLTC2983(PUMP1_THERM);
      checkForSerial();
      TempPump2 = OPC.MeasureLTC2983(PUMP2_THERM);
      checkForSerial();
      TempPCB = OPC.MeasureLTC2983(BOARD_THERM);
      checkForSerial();
    
      checkForSerial();
      if(PumpAdjustTime * i <= millis()){
        ReadHK();  //read the Teensy analog channels
        AdjustPumps();
        StringTemps(); //Add HK data to string  
        if(FLOW_METER){
          flow = getFlow();  //get flow from MFS
        }
        DEBUG_SERIAL.print(OutputString); //print the output string to the USB terminal
        OutputString.replace(" ", "");  //remove any leftover spaces in output string

        OutputString += "\n";
      
        OPC.WriteData(file, OutputString);  // Write a data line to SD card

      
        OPCString = "";    // Clear strings
        OutputString = "";
        
        ElapsedTime = millis();  //Time since instrument start in milliseconds

        Frame++;
        i++;
      }

      checkForSerial();

       if(VBat < 14.0)
        {
          DEBUG_SERIAL.print("Low Battery Voltage: ");
          DEBUG_SERIAL.println(VBat);
         OPC.WriteData(file, "Low Battery Voltage - Entering Ground Mode\n");  // Write a data line to SD card
          //GroundMode();
        } 
        if(CheckTime + (CheckTime2*(k-1)) <= millis()) {
          TimeON = 0;
          checkForSerial();
        }
  }
  analogWrite(PUMP1_PWR, 0);
  analogWrite(PUMP2_PWR, 0);
  checkForSerial(); 
  while(!TimeON) {
    
    if(PumpAdjustTime * i <= millis()){
        DEBUG_SERIAL.println("Time Off");
        i++;
    }
    if(CheckTime2*k <= millis()){
      TimeON = 1;
      k++;
      PumpCycleCount++;
      analogWrite(PUMP1_PWR, BEMF1_pwm);
      analogWrite(PUMP2_PWR, BEMF2_pwm);
      DEBUG_SERIAL.println("Time On");
    }
  }  
}


/*
 * Debug routine for housekeeping - dumps to console
 */

void printHK()
{
  
  DEBUG_SERIAL.print("Frame Number: ");
  DEBUG_SERIAL.println(Frame);
  DEBUG_SERIAL.print("Pump1 [C]: ");
  DEBUG_SERIAL.println(TempPump1);
  DEBUG_SERIAL.print("Pump2 [C]: ");
  DEBUG_SERIAL.println(TempPump2);
  DEBUG_SERIAL.print("DC-DC Converter [C]: ");
  DEBUG_SERIAL.println(TempPCB);
  DEBUG_SERIAL.print("Case [C]: ");
  DEBUG_SERIAL.println(TempCase);
  DEBUG_SERIAL.print("I Pump1 [mA]: ");
  DEBUG_SERIAL.println(IPump1);
  DEBUG_SERIAL.print("I Pump2 [mA]: ");
  DEBUG_SERIAL.println(IPump2);
  DEBUG_SERIAL.print("V Battery [V]: ");
  DEBUG_SERIAL.println(VBat);
  DEBUG_SERIAL.print("V Teensy [V]: ");
  DEBUG_SERIAL.println(VTeensy);
  DEBUG_SERIAL.print("Flow [SLM]: ");
  DEBUG_SERIAL.println(flow);
}

void checkForSerial(void)
{
     if (DEBUG_SERIAL.available()) {
   char DEBUG_Char = DEBUG_SERIAL.read();
   
   if((DEBUG_Char == '\n') || (DEBUG_Char == '\r'))
   {
    //DEBUG_SERIAL.print("FLASH String: ");
    //DEBUG_SERIAL.println(FLASH_Buff);
    parseCommand(DEBUG_Buff);
    DEBUG_Buff = "";
   } else
   {
    DEBUG_Buff += DEBUG_Char;
   }   
  }
}

/*
 * Creates a formated string with temperature data
 */

void StringTemps()
{
  //Starts At index 5 (value 6) for array processing 
  float tme = millis()/1000;
  int hr = tme/3600;                                                        //Number of seconds in an hour
  int mins = (tme-hr*3600)/60;                                              //Remove the number of hours and calculate the minutes.
  int sec = tme-hr*3600-mins*60;                                            //Remove the number of hours and minutes, leaving only seconds.
  if(hr < 10){
    if(mins < 10){
      if(sec < 10){
        hrMinSec = ("0" + String(hr) + ":" + "0" + String(mins) + ":" + "0" + String(sec));  //Converts to HH:MM:SS string
      }
      else{
        hrMinSec = ("0" + String(hr) + ":" + "0" + String(mins) + ":" + String(sec));  //Converts to HH:MM:SS string
      }
    }
    else{
      if(sec < 10){
        hrMinSec = ("0" + String(hr) + ":" + String(mins) + ":" + "0" + String(sec));  //Converts to HH:MM:SS string
      }
      else{
        hrMinSec = ("0" + String(hr) + ":" + String(mins) + ":" + String(sec));  //Converts to HH:MM:SS string
      }
    }
  }
  else{
    if(mins < 10){
      if(sec < 10){
        hrMinSec = (String(hr) + ":" + "0" + String(mins) + ":" + "0" + String(sec));  //Converts to HH:MM:SS string
      }
      else{
        hrMinSec = (String(hr) + ":" + "0" + String(mins) + ":" + String(sec));  //Converts to HH:MM:SS string
      }
    }
    else{
      if(sec < 10){
        hrMinSec = (String(hr) + ":" + String(mins) + ":" + "0" + String(sec));  //Converts to HH:MM:SS string
      }
      else{
        hrMinSec = (String(hr) + ":" + String(mins) + ":" + String(sec));  //Converts to HH:MM:SS string
      }
    }
  }
  OutputString += hrMinSec;
  OutputString += ", ";
  OutputString += PumpCycleCount;
  OutputString += ", ";
  OutputString += TempPump1; //8
  OutputString += ", "; 
  OutputString += TempPump2; //9
  OutputString += ", ";
  OutputString += TempPCB; //11
  OutputString += ", "; 
  OutputString += TempCase; //12
  OutputString += ", "; 
  OutputString += IPump1; //13
  OutputString += ", "; 
  OutputString += IPump2;  //14
  OutputString += ", "; 
  OutputString += VBat;  //18
  OutputString += ", "; 
  OutputString += flow;
  OutputString += ",";
  OutputString += BEMF1_V;  //19
  OutputString += ", "; 
  OutputString += BEMF1_pwm;  //20
  OutputString += ", "; 
  OutputString += BEMF2_V;  //21
  OutputString += ", "; 
  OutputString += BEMF2_pwm;  //22
  OutputString += "\n";

}

/*
 * Read the analog data from Teensy channels and convert to real units. 
 */

void ReadHK(void)
{
 long I1_Bits = 0;
 long I2_Bits = 0;
 long i = 0;  
 int StartTime = millis();
 
 while (millis() - StartTime < 10) //Average pump current for 10ms to make sure we get a full pwm cycle
 {
    I1_Bits += analogRead(I_PUMP1);
    I2_Bits += analogRead(I_PUMP2);
    i++;
 }
 
  IPump1 = (I1_Bits/i)/4095.0 * 30000;
  IPump2 = (I2_Bits/i)/4095.0 * 30000;
  
  IHeater1 = analogRead(HEATER1_I)/1.058;
  IHeater2 = analogRead(HEATER2_I)/1.058; 
  VBat = analogRead(BATTERY_V)*3.3/4095.0 *6.772;
  VTeensy = analogRead(TEENSY_3V3)*3.3/4095.0*2.0; 
}

void AdjustPumps()
{
  int i = 0;
  analogWrite(PUMP1_PWR, 0); //Turn off Pump1
  delayMicroseconds(500); //Hold off for spike to collapse
  
  for(i = 0; i < 32 ; i++)
    backEMF1 += analogRead(PUMP1_BEMF); 

  BEMF1_V = VBat - backEMF1/(4095.0*32.0)*18.0;
  error1 = BEMF1_V - BEMF1_SP;
  BEMF1_pwm = int(BEMF1_pwm - error1*Kp);
  analogWrite(PUMP1_PWR, BEMF1_pwm);
  delay(10);
  
  analogWrite(PUMP2_PWR, 0); //Turn off Pump1
  delayMicroseconds(500); //Hold off for spike to collapse
  
  for(i = 0; i < 32 ; i++)
    backEMF2 += analogRead(PUMP2_BEMF); 

  BEMF2_V = VBat - backEMF2/(4095.0*32.0)*18.0;
  error2 = BEMF2_V - BEMF2_SP;
  BEMF2_pwm = int(BEMF2_pwm - error2*Kp);
  analogWrite(PUMP2_PWR, BEMF2_pwm);

  backEMF1 = 0;
  backEMF2 = 0;
  
}


/*
 * Sometimes the LTC2983 glitches and hangs, reset it if necessary
 */

void ResetLTC2983(void)
{
  int Done = 0;
  digitalWrite(RESET, LOW);
  delay(100);
  digitalWrite(RESET, HIGH);
  while(!Done)
  {
    Done = digitalRead(INTERUPT);
  }
  //DEBUG_SERIAL.println("LTC2983 has been reset");
  OPC.ConfigureChannels();
  //DEBUG_SERIAL.println("Part has been configured");
  
}



/*
 * Read the Mass flow meter and return calibrated values (standard liters per minute) if installed
 */
float getFlow()
{
  //DEBUG_SERIAL.println("Starting request from MFM");
  Wire.requestFrom(sensor,2); //Request data from sensor, 2 bytes at a time 
  aa = Wire.read(); //Get first byte
  bb = Wire.read(); //Get second byte
  digital_output=aa<<8;
  digital_output=digital_output+bb; //Combine bytes into an integer
  flow = 20.0*((digital_output/16383.0)-0.1)/0.8; //Convert digital output into correct air flow
  
  //Return correct value
  return flow;
}


void GroundMode(void)
{

  DEBUG_SERIAL.println("Going into deep low power mode");
  analogWrite(PUMP1_PWR, 0); //turn off pump 1
  analogWrite(PUMP2_PWR, 0); // turn off pump 2
  digitalWrite(MFS_POWER, LOW); // turn off Mass Flow Meter
  /*Put LTC2983 to sleep */
  OPC.SleepLTC2983();
  delay(1000);
  while(1);
}

int nearest(float x, float myArray[], int elements)
{
  /* Helper function to find the value in 'myArray' that is closest to the x
   *  and return the index of that element.  Used to look up the index for real
   *  diameters for bin boundaries
   */
  int idx = 0; // by default near first element

  int distance = abs(myArray[idx] - x);
  for (int i = 1; i < elements; i++)
  {
    int d = abs(myArray[i] - x);
    if (d < distance)
    {
      idx = i;
      distance = d;
    }
  }
  return idx;
}

void parseCommand(String commandToParse)
{
  /* This is where all the commands are interpreted and is the meat of the control system
   * so far
   * #stop  - switches to ground mode
   * #header - print a header to the terminal
   * #verbose - toggles to full 256 bin differential display
   * #terse - toggles to cummulative defined bins
   * #BEMF, float - set a new pump speed
   * #save - save pump setpoints to EEPROM
   * #clear - clear saved pump settings
   */
  
  char * strtokIndx; // this is used by strtok() as an index
  char CommandArray[64];

  float flt1 = 0;

  if(commandToParse.startsWith("#stop"))
  {
    DEBUG_SERIAL.println("Switching to Ground Mode");
    DEBUG_Buff = "";
    GroundMode(); //go to idle mode for almost ever
  }
  else if(commandToParse.startsWith("#header"))
  {
     DEBUG_SERIAL.println(header);
     
  }
  else if(commandToParse.startsWith("#verbose"))
  {
     DEBUG_SERIAL.println("Verbose Mode");
     verbose = true;
  }
  else if(commandToParse.startsWith("#terse"))
  {
     DEBUG_SERIAL.println("Terse Mode");
     verbose = false;
  }
  else if(commandToParse.startsWith("#BEM"))
  {
     commandToParse.toCharArray(CommandArray, 64); //copy the String() to a string
     strtokIndx = strtok(CommandArray,",");      // get the first part - the string we don't care about this
  
     strtokIndx = strtok(NULL, ","); // this continues where the previous call left off
     flt1 = atof(strtokIndx);     // convert this part to a float for the temperature set point

     DEBUG_SERIAL.print("Setting Back EMF to: ");
     DEBUG_SERIAL.print(flt1); DEBUG_SERIAL.println("[V]");

     BEMF1_SP = flt1; //Set point for pump 1
     BEMF2_SP = flt1; //Set point for pump 2
     
     commandToParse = "";
  }
  
  else if(commandToParse.startsWith("#save"))
  {
     DEBUG_SERIAL.println("Writing Pump Settings to EEPROM");
     EEPROM.put(EEPROM_PUMP1, BEMF1_SP); //save pump1 as float
     EEPROM.put(EEPROM_PUMP2, BEMF2_SP); //save pump2 as float
     EEPROM.write(EEPROM_FLAG, 0x01);    //update flag to show valid data in eeprom
     return; 
  }
  
  else if(commandToParse.startsWith("#cle"))
  {
     DEBUG_SERIAL.println("Clearing Pump settings from EEPROM");
     EEPROM.put(EEPROM_PUMP1, 0.0); //save pump1 as float
     EEPROM.put(EEPROM_PUMP2, 0.0); //save pump2 as float
     EEPROM.write(EEPROM_FLAG, 0x00);    //update flag to show no valid data in eeprom
  }
  
}

void calcChecksum(byte *checksumPayload, byte payloadSize) {
  byte CK_A = 0, CK_B = 0;
  for (int i = 0; i < payloadSize ;i++) {
    CK_A = CK_A + *checksumPayload;
    CK_B = CK_B + CK_A;
    checksumPayload++;
  }
  *checksumPayload = CK_A;
  checksumPayload++;
  *checksumPayload = CK_B;
}
