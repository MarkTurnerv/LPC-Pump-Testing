# LPC-Pump-Testing

Stress testing pumps to ensure they provide the expected outputs (airflow, current draw, temperature, back EMF, and driving PWM) over an extended run-time and number of cycles.

## Pump_Test.ino

### Functionality and Operation
Located in 'Pump_Test' folder. Arduino file to run two pumps connected to the LOPC mainboard (rev G) with airflow meter. Outputs data to the onboard SD card and the Serial Monitor. Pumps run 3 minutes on, 3 minutes off. Uses OPC_V5_0 as a basis for flowmeter communications using I2C with Honeywell Zephyr 20 SLPM Digital Airflow Sensor, writing to the SD card on the LOPC mainboard, controlling the pump motors. The motor speed is determined by stalling the motor and measuring the BEMF. A proportional control law uses the BEMF to determine the driving PWM.

### Installation
Pump_Test.ino uses the following libraries:
* Linduino
* LT_SPI
* TinyGPSPlus

TinyGPSPlus must be downloaded through Arduino/ArduinoIDE. Linduino and LT_SPI are included in the src folder but can also be used under the Arduino 'libraries' folder.

## PumpGraphing-SeparateGraphs.py

### Functionality
Takes txt files (manually transferred from LOPC mainboard SD card) and plots the pump and PCB temperatures, flow rate, motor currents, smoothed pump back electromotive forces, and driving pump PWM. Automatically saves plots to the 'Graphs' folder.

### User Input
The filename must be manually changed on line 21 of the code.

## Data folder
Holds data from pump tests.

## Checkout
Holds documentation from LPC checkout and results from running known particle sizes through the Optical Partical Counter (OPC)

## Graphs
Holds Pump Test and Thermal Chamber graphs
