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
	split_inds = [-1] + split_inds
	split_inds.sort()

	mid = mido.MidiFile()
	track = mido.MidiTrack()
	mid.tracks.append(track)
	track.append(meta_msg)
	for i, (msg_type, msg_note, msg_velocity, msg_time) in enumerate(notes):
		if (i != -1) and (i in split_inds):
			# create a new file using the messages
			mid_save_path = os.path.join(save_path, "{}_{}.mid".\
				format(split_inds[split_inds.index(i)-1]+1,i))
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
def getFreqVec(notes):
	# a total number of 128 digital keys on a keyboard
	freq_vec = [0]*128
	for (_, note, _, _) in notes:
		freq_vec[int(note)] += 1
	return freq_vec
	
# used to process the midi file
# df defined in delta ticks
# takes in size of sliding window as a parameter defined in number of midi notes
def getFreqVecWithSlidingWindowFromDf(df, offset=0, size=15):
	notes = df.values.tolist()

	freq_info = dict()
	for start in range(len(notes)):
		if (start+size) > len(notes):
			part = notes[start:]
		else:
			part = notes[start:start+size]
		freq_vec = getFreqVec(part)
		freq_info[start+offset] = freq_vec

	return freq_info

def getEuclideanDist(test_freq_vec, orig_freq_vec):
	return np.linalg.norm(np.array(test_freq_vec)-np.array(orig_freq_vec), ord=2)

# locate given midi slice in the original midi file
# returns the index of the note in the original midi file's notes list
def locateMidi(cur_notes, ori_note_path):
	ori_note_df = pd.read_csv(ori_note_path)
	pass

def testFileMatching(test_dir, orig_notes_df):
	for (dirpath, dirnames, filenames) in os.walk(test_dir):
		for filename in filenames:
			if filename.endswith('.mid'): 
				test_midi_file_name = filename[:-4]
				test_midi_file_path = os.path.join(test_dir, filename)
				test_f = mido.MidiFile(test_midi_file_path)

				# print("........test midi file loaded at path {}............".\
				# 	format(test_midi_file_path))

				hypen = filename.find("_")
				test_start = int(filename[:hypen])
				test_end = int(filename[hypen+1:-4])

				test_notes_df = getNotesDFWithDeltaTick(test_f)
				test_df_size = len(test_notes_df.index)

				orig_freq_info = getFreqVecWithSlidingWindowFromDf(orig_notes_df, size=test_df_size)
				test_freq_info = getFreqVecWithSlidingWindowFromDf(test_notes_df, \
					offset=test_start, size=test_df_size)
				matchDFs(test_freq_info, orig_freq_info, test_df_size)

def matchDFs(test_freq_info, orig_freq_info, test_df_size):
	for test_start, test_freq_vec in test_freq_info.items():
		minDist = None
		minDistStart = None
		for orig_start, orig_freq_vec in orig_freq_info.items():
			dist = getEuclideanDist(test_freq_vec, orig_freq_vec)
			# print(".........test: {}, original: {}, distance: {}...........".\
			# 	format(test_start, orig_start, dist))
			if ((minDist == None) or (dist <= minDist)):
				if dist == minDist:
					minDistStart.append(orig_start)
					continue
				minDist = dist
				minDistStart = [orig_start] 
		print("......testing midi sequence with size {} starting at {} matched at {} \
			with distance {}.......".\
			format(test_df_size, test_start, minDistStart, minDist))
		break


def main():
	#Chopin_-_Nocturne_Op_9_No_2_E_Flat_Major.midi
	midi_file_name = "Chopin_-_Nocturne_Op_9_No_2_E_Flat_Major"
	midi_file_path = os.path.join(static_dir, midi_file_name + ".midi")
	f = mido.MidiFile(midi_file_path)
	orig_notes_df = getNotesDFWithDeltaTick(f)

	print("........original midi file loaded at path {}............".format(midi_file_path))
	
	
	sample_save_path = os.path.join(static_dir, midi_file_name)
	if not os.path.exists(sample_save_path):
		os.makedirs(sample_save_path)

	# createCSVFromDF(notes_tick_df, sample_save_path, "notes_delta_tick.csv")

	# createAndSaveRandomMidiSlices(f, sample_save_path)

	testFileMatching(sample_save_path, orig_notes_df)


if __name__ == "__main__":
	main()
