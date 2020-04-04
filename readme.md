# pageFlipper

## How to Run the Web Application Along with the MIDI Tracker Program

### Prepopulating database with RPI data

Open up commandline in Lily_Du/develop/Web, and write RPI data in pageFlipper/fixtures/rpis.json to be loaded to database

```bash
python3 manage.py loaddata rpis.json
```

### Run the Web Application

```bash
python3 manage.py runserver
```

### Run the MIDI tracker program

Open up another commandline in Candy_Dong/midiTracker and type

```bash
python3 readLiveMidi.py
```

The program will wait until the web application gets user input and sends the title of the sheet music back.
Once received, the program starts running, reads in live midi input from the midi keyboard, and sends a flip page signal back to the webserver once the user reaches the end of page. The web application updates the page to show the next page of the sheet music through ajax calls.

