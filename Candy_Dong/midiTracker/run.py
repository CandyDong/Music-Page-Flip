import os, sys
from mido import MidiFile

static_dir = "../static/"

def main():
	#clip the velocity of all notes to 127 if they are higher than that
	path = os.path.join(static_dir, "VampireKillerCV1.mid")
	f = MidiFile(path, clip=True)
	print("midi file loaded at {}: {}\n".format(path, f))

	'''
	type 0 (single track): all messages are saved in one track
	type 1 (synchronous): all tracks start at the same time
	type 2 (asynchronous): each track is independent of the others
	'''
	for track in f.tracks:
	    print(track)
	    for msg in track:
	    	print(" ", msg)

	# remove the duplicate tracks (tracks with same number of messages)
	mes_num = set()
	duplicates = []

	for track in f.tracks:
	    if len(track) in mes_num:
	        duplicates.append(track)
	    else:
	        mes_num.add(len(track))

	for track in duplicates:
	    f.tracks.remove(track)

	f.save(os.path.join(static_dir, 'VampireKillerCV1_no_dup.mid'))


if __name__ == "__main__":
	main()
