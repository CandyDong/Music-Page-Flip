import os, sys
import mido
import random

static_dir = "../static/"

# stores note_on/note values in a list of timestamps from a midiFile object
def getNotes(f):
	notes = [] # each entry: (time, note) if a note_on event occurs
	global_time = 0 # global time starts at time 0
	for msg in f:
		global_time += msg.time
		if msg.type == "note_on":
			notes.append((global_time, msg.note))
	return notes

# check if all messages are meta messages
def isAllMeta(track):
	for msg in track:
		if not msg.is_meta:
			return False
	return True

# create midi file from messages
# the midi file only has one track which contains all the messages
def createNewFile(msgs, save_path):
	print("creating new midi file at {}".format(save_path))
	mid = mido.MidiFile()
	track = mido.MidiTrack()
	mid.tracks.append(track)
	for msg in msgs:
		print(msg)
		track.append(msg)
	mid.save(save_path)

# randomly slice merged_tracks and save as a new midi file 
# for testing purpose
def saveRandomMidiSlices(f, save_path, num_split=10):
	global_time = 0
	merged_tracks = mido.merge_tracks(f.tracks)
	meta_track_inds = []
	for i,msg in enumerate(merged_tracks):
		if msg.is_meta:
			meta_track_inds.append(i)

	num_msg = len(merged_tracks)
	# generate population without indices of meta tracks 
	avail_inds = list(filter(lambda i: i not in meta_track_inds, list(range(num_msg))))
	avail_inds.sort() 

	# randomly sample split points from the generated population
	split_inds = random.sample(avail_inds, num_split)

	with open(os.path.join(save_path, "split_inds.txt"), "w") as f:
		f.write(str(split_inds))

	new_msgs = []
	for i, msg in enumerate(merged_tracks):
		if i in split_inds:
			if not isAllMeta(new_msgs):
				# create a new file using the messages
				createNewFile(new_msgs, os.path.join(save_path, "{}.mid".format(i)))
				new_msgs = [] # reset new msgs
				continue
		new_msgs.append(msg)


def main():
	#clip the velocity of all notes to 127 if they are higher than that
	#Chopin_-_Nocturne_Op_9_No_2_E_Flat_Major.midi
	midi_file_name = "Chopin_-_Nocturne_Op_9_No_2_E_Flat_Major"
	path = os.path.join(static_dir, midi_file_name+".midi")
	f = mido.MidiFile(path, clip=True)
	print("midi file loaded at {}: {}\n".format(path, f))

	'''
	type 0 (single track): all messages are saved in one track
	type 1 (synchronous): all tracks start at the same time
	type 2 (asynchronous): each track is independent of the others
	delta time: how many ticks have passed since the last message
	'''
	sample_save_path = os.path.join(static_dir, midi_file_name)
	if not os.path.exists(sample_save_path):
		os.makedirs(sample_save_path)

	saveRandomMidiSlices(f, sample_save_path)

	# notes = getNotes(f)
	# note_save_path = os.path.join(sample_save_path, "notes.txt")
	# with open(note_save_path, "w") as f:
	# 	f.write(str(notes))


if __name__ == "__main__":
	main()
