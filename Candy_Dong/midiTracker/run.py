import os, sys
import mido
import random
import pandas as pd
import numpy as np
from collections import defaultdict
import math
import csv

static_dir = "../static/"

DEBUG = True

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
			break

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
			print(".........saved file at {} ...............".format(mid_save_path))

			# reset new midi file
			mid = mido.MidiFile()
			track = mido.MidiTrack()
			mid.tracks.append(track)
			track.append(meta_msg)
			continue

		track.append(mido.Message(msg_type, note=msg_note, velocity=msg_velocity, time=msg_time))


def generateRandNumInRange(low, high, percentage):
	size = high - low
	count = int(size*percentage/100)
	random.seed(0)
	return random.sample(list(range(low, high)), count)


# loop through all slices in f_dir
# create midi slices with randomly notes being deleted from the original slice
def deleteRandomNotes(f_dir, save_path, percentage=10):
	# get time signature message
	for filename in os.listdir(f_dir):
		if not (filename.endswith(".mid") or filename.endswith(".midi")):
			continue

		f_path = os.path.join(f_dir, filename)
		f = mido.MidiFile(f_path)
		merged_tracks = mido.merge_tracks(f.tracks)

		meta_msg = mido.MetaMessage("time_signature", numerator=4, denominator=4) #default meta message
		for i,msg in enumerate(merged_tracks):
			if msg.type == "time_signature":
				meta_msg = msg
				break

		notes = getNotesWithDeltaTick(f)
		num_notes = len(notes)
		avail_inds = list(range(num_notes))
		del_indices = generateRandNumInRange(0, num_notes, percentage)
		del_indices.sort()

		if DEBUG: meta_str = "Deleted Indices: {}\n\n".format(del_indices);

		# create new midi file to save the generated slice
		mid = mido.MidiFile()
		track = mido.MidiTrack()
		mid.tracks.append(track)
		track.append(meta_msg)
		tick = None

		for i, (msg_type, msg_note, msg_velocity, msg_time) in enumerate(notes):
			if i in del_indices:
				if (tick != None):
					tick += msg_time
				else:
					tick = msg_time
				if DEBUG: meta_str += "{} <{}, note={}, tick={}>(deleted)\n".format(i, msg_type, msg_note, msg_time);
				continue

			if tick != None:
				track.append(mido.Message(msg_type, note=msg_note, velocity=msg_velocity, time=msg_time+tick))
				if DEBUG: 
					meta_str += "{} <{}, note={}, tick={}>(original)\n".format(i, msg_type, msg_note, msg_time);
					meta_str += "{} <{}, note={}, tick={}>(merged)\n".format(i, msg_type, msg_note, msg_time+tick);
			else:
				track.append(mido.Message(msg_type, note=msg_note, velocity=msg_velocity, time=msg_time))
				if DEBUG: meta_str += "{} <{}, note={}, tick={}>\n".format(i, msg_type, msg_note, msg_time);
			tick = None

		mid_save_path = os.path.join(save_path, str(percentage))
		if not os.path.exists(mid_save_path):
			os.makedirs(mid_save_path)
		mid.save(os.path.join(mid_save_path, filename)) # Chopin, 0-154.txt
		print(".........saved file at {} ...............".format(os.path.join(mid_save_path, filename)))

		if DEBUG:
			file_range = filename[:filename.index(".")]
			meta_save_path = os.path.join(mid_save_path, "{}_meta.txt".format(file_range))
			meta_f = open(meta_save_path, "w")
			meta_f.write(meta_str)
			meta_f.close()


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
		result = []
		for filename in filenames:
			if not (filename.endswith(".mid") or filename.endswith(".midi")):
				continue
			row = {}
			test_midi_file_name = filename[:-4]
			test_midi_file_path = os.path.join(test_dir, filename)
			test_f = mido.MidiFile(test_midi_file_path)

			print("........test midi file loaded at path {}............".\
				format(test_midi_file_path))

			row["filename"] = test_midi_file_path
			row["accuracy"] = "{}%".format(test_dir[-test_dir[::-1].find("/"):])

			hypen = filename.find("_")
			test_start = int(filename[:hypen])
			test_end = int(filename[hypen+1:-4])

			test_notes_df = getNotesDFWithDeltaTick(test_f)
			test_df_size = len(test_notes_df.index)

			row["size"] = test_df_size

			orig_freq_info = getFreqVecWithSlidingWindowFromDf(orig_notes_df, size=test_df_size)
			test_freq_info = getFreqVecWithSlidingWindowFromDf(test_notes_df, \
				offset=test_start, size=test_df_size)
			test_start, minDistStart, minDist = matchDFs(test_freq_info, orig_freq_info, test_df_size)

			orig_dist = getEuclideanDist(test_freq_info[test_start], orig_freq_info[test_start])
			row["start"] = test_start
			row["matched_start"] = minDistStart
			row["distance"] = minDist
			row["answer_distance"] = orig_dist

			result.append(row)
	return result


def matchDFs(test_freq_info, orig_freq_info, test_df_size):
	for test_start, test_freq_vec in test_freq_info.items():
		minDist = None
		minDistStart = None
		for orig_start, orig_freq_vec in orig_freq_info.items():
			dist = getEuclideanDist(test_freq_vec, orig_freq_vec)
			# print(".........test: {}, original: {}, distance: {}...........".\
			# 	format(test_start, orig_start, dist))
			if ((minDist == None) or (dist <= minDist)):
				if (minDist != None) and (math.isclose(dist, minDist, rel_tol=1e-5)):
					minDistStart.append(orig_start)
					continue
				minDist = dist
				minDistStart = [orig_start] 
		break
	return test_start, minDistStart, minDist


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
	orig_sample_save_path = os.path.join(sample_save_path, "0")
	if not os.path.exists(orig_sample_save_path):
		os.makedirs(orig_sample_save_path)
	# createAndSaveRandomMidiSlices(f, orig_sample_save_path)

	# version 2 midi matching
	
	percentages = [0, 5, 10, 15, 20, 25, 30, 25, 40, 45, 50, 55, 60]
	# for p in percentages[1:]:
	# 	# arguments: (1) dir of original sample files (2) path to save generated midi files
	# 	deleteRandomNotes(orig_sample_save_path, sample_save_path, percentage=p)

	
	for p in percentages:
		result = testFileMatching(os.path.join(sample_save_path, str(p)), orig_notes_df)
		f_result_name = "match_results_{}.csv".format(p)
		with open(os.path.join(sample_save_path, str(p), f_result_name), "w") as f_result:
			writer = csv.DictWriter(f_result, fieldnames=list(result[0].keys()))
			writer.writeheader()
			for row in result:
				writer.writerow(row)

if __name__ == "__main__":
	main()
