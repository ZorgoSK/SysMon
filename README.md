![alt text](https://github.com/ZorgoSK/SysMon/blob/main/zorgoSysMon_2.png?raw=true)

Hey guys!

I was looking for some cpu temperature graph in linux, which will allow me to see the history of temperatures.
More or less i find out only 'psensors', which is showing some history with ability to select different sensors.

At the end of the day, i started to play with ChatGPT and Python (honestly, i'm newbie in Python at all), ended up
with this SysMon, which is actually showing CPU temperature, CPU load, TOP process with highest load in actual moment,
battery level, battery status (charge/discharge).

(probably can cause a problem with computers without battery, but maybe python3-psutils is returning something else, when
battery is not installed)

App is loaded in system tray under icon, click on this tray icon will show/hide the graph window.
Right click on tray icon will show the menu with:
  -  selection "Show duration" - select how much to show from last update
  -  selection "Refresh rate" - how often load actual values and refresh the graph
  -  Quit ...

All values are stored in arrays.
To lower the CPU load on long usage (when you keep the app running nonstop) after 10,000 array values app will start 
to remove the oldest values by 1, so array lenght should remain fullfilled by last 10,000 readings only.


Surely, code will contain lot of programming errors, non-actual functions, etc. I will invite any comments, how to improve it.

Hope it will help someone, enjoy.

![alt text](https://github.com/ZorgoSK/SysMon/blob/main/zorgoSysMon.png?raw=true)


