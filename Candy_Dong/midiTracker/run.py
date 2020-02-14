import os, sys
import mido
import random
import pandas as pd
import numpy as np
from collections import defaultdict

static_dir = "../static/"

# stores note_on/note values in a list of timestamps from a midiFile object
def getNotesWithGlobalTime(f):
	notes = [] # each entry: (time, note) if a note_on event occurs
	global_time = 0 # global time starts at time 0
	for msg in f:
		global_time += msg.time
		if msg.type == "note_on":
			notes.append((global_time, msg.note))
	return notes


# return a pandas dataframe saving note along with time in seconds
def getNotesDFWithGlobalTime(f):
	#clip the velocity of all notes to 127 if they are higher than that
	notes = getNotesWithGlobalTime(f)
	df = pd.DataFrame(np.array(notes), columns=['Time', 'Note'])
	return df


# stores midi note info in a list
def getNotesWithDeltaTick(f):
	notes = []
	merged_tracks = mido.merge_tracks(f.tracks)
	for i,msg in enumerate(merged_tracks):
		if msg.is_meta:
			continue
		if msg.type == "note_on":
			notes.append((msg.type, msg.note, msg.velocity, msg.time))
	return notes


def getNotesDFWithDeltaTick(f):
	notes = getNotesWithDeltaTick(f)
	df = pd.DataFrame(np.array(notes), columns=['Type', 'Note', 'Velocity', 'Time'])
	return df


# create midi file from messages
# the midi file only has one track which contains all the messages
def createNewMidiFile(msgs, save_path):
	print("...................creating new midi file at {}...............".format(save_path))
	mid = mido.MidiFile()
	track = mido.MidiTrack()
	mid.tracks.append(track)
	for msg in msgs:
		track.append(msg)
	mid.save(save_path)


# randomly slice merged_tracks and save as a new midi file 
# for testing purpose
def createAndSaveRandomMidiSlices(f, save_path, num_split=10):
	# get time signature message
	meta_msg = mido.MetaMessage("time_signature", numerator=4, denominator=4) #default meta message
	merged_tracks = mido.merge_tracks(f.tracks)
	for i,msg in enumerate(merged_tracks):
		if msg.type == "time_signature":
			meta_msg = msg


	notes = getNotesWithDeltaTick(f)
	num_notes = len(notes)
	# generate population without indices of meta tracks 
	avail_inds = list(range(num_notes))

	random.seed(0)
	# randomly sample split points from the generated population
	split_inds = random.sample(avail_inds, num_split)

	mid = mido.MidiFile()
	track = mido.MidiTrack()
	mid.tracks.append(track)
	track.append(meta_msg)
	for i, (msg_type, msg_note, msg_velocity, msg_time) in enumerate(notes):
		if i in split_inds:
			# create a new file using the messages
			mid_save_path = os.path.join(save_path, "{}.mid".format(i))
			mid.save(mid_save_path)

			# reset new midi file
			mid = mido.MidiFile()
			track = mido.MidiTrack()
			mid.tracks.append(track)
			track.append(meta_msg)
			continue

		track.append(mido.Message(msg_type, note=msg_note, velocity=msg_velocity, time=msg_time))


# save the panda dataframe of notes as a csv at notes.csv
# save path only specifies the directory to save
def createCSVFromDF(df, save_path, name):
	csv_path = os.path.join(save_path, name)
	df.to_csv(csv_path)


# get freq vector from an input midi sequence
# stores the number of times a note occurs in the input sequence
def getFreqVec(midi_vec):
	# key = note, value = frequency
	freqVec = defaultdict(int)
	for (ind, note) in midi_vec:
		if note in freqVec:
			freqVec[note] += 1
	return freqVec
		

# locate given midi slice in the original midi file
# returns the index of the note in the original midi file's notes list
def locateMidi(cur_notes, ori_note_path):
	ori_note_df = pd.read_csv(ori_note_path)

	pass

def main():
	#Chopin_-_Nocturne_Op_9_No_2_E_Flat_Major.midi
	midi_file_name = "Chopin_-_Nocturne_Op_9_No_2_E_Flat_Major"
	midi_file_path = os.path.join(static_dir, midi_file_name+".midi")
	f = mido.MidiFile(midi_file_path)
	
	sample_save_path = os.path.join(static_dir, midi_file_name)
	if not os.path.exists(sample_save_path):
		os.makedirs(sample_save_path)

	notes_tick_df = getNotesDFWithDeltaTick(f)
	createCSVFromDF(notes_tick_df, sample_save_path, "notes_delta_tick.csv")

	createAndSaveRandomMidiSlices(f, sample_save_path)
	
	

if __name__ == "__main__":
	main()
