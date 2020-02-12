import os, sys
from mido import MidiFile

static_dir = "../static/"

def main():
	#clip the velocity of all notes to 127 if they are higher than that
	path = os.path.join(static_dir, "test.mid")
	f = MidiFile(path, clip=True)

	print("midi file loaded at path {}: {}".format(path, f))

	for track in f.tracks:
	    print(track)
	    for msg in track:
	    	print(msg)

if __name__ == "__main__":
	main()
