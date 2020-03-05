import os, sys
import mido
import random
import pandas as pd
import numpy as np
from collections import defaultdict
import math
import csv
import Levenshtein

static_dir = "../static/"

DEBUG = True
percentages = [0, 5, 10, 20, 30, 40, 50]

def generateRandNumInRange(low, high, percentage):
	def containsSameNumber(samples):
		sample_set = set(samples)
		if len(sample_set) == len(samples):
			return False
		return True

	size = high - low
	count = int(size*percentage/100)

	samples = random.sample(list(range(low, high)), count)

	while (0 in samples) or (containsSameNumber(samples)):
		samples = random.sample(list(range(low, high)), count)

	return samples


def pickRandNumInRange(low, high):
	return random.randint(low, high)


# returns the first message that sets the time signature of the file
# and return the default time signature message if none exists in the original file
def getTimeSignature(f):
	# get time signature message
	meta_msg = mido.MetaMessage("time_signature", numerator=4, denominator=4) #default meta message
	merged_tracks = mido.merge_tracks(f.tracks)
	for i,msg in enumerate(merged_tracks):
		if msg.type == "time_signature":
			meta_msg = msg
			break
	return meta_msg


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

# index calculation out of dated!! split inds should start from 0 now
def getRandomSplitInds(f, num_split=10):
	notes = getNotesWithDeltaTick(f)
	num_notes = len(notes)
	# generate population without indices of meta tracks 
	avail_inds = list(range(num_notes))

	# randomly sample split points from the generated population
	split_inds = random.sample(avail_inds, num_split)
	split_inds = [-1] + split_inds
	split_inds.sort()

	return split_inds


def getFixedIntervalSplitInds(f, len_split=5):
	if (len_split <= 0):
		raise Exception("Split interval too small!")

	# generate population without indices of meta tracks 
	# split interval determined by len
	notes = getNotesWithDeltaTick(f)
	num_notes = len(notes)
	split_inds = list(range(0, num_notes, len_split))

	return split_inds


# randomly slice merged_tracks and save as a new midi file 
# for testing purpose
# if num_split is provided -> random split
# if len_split is provided -> fixed interval split
def createAndSaveMidiSlices(f, save_path, num_split=None, len_split=None):
	# get time signature message
	meta_msg = getTimeSignature(f)

	notes = getNotesWithDeltaTick(f)

	assert((num_split != None) or (len_split != None))

	if (num_split):
		split_inds = getRandomSplitInds(f, num_split)
	else:
		split_inds = getFixedIntervalSplitInds(f, len_split)

	mid = mido.MidiFile()
	track = mido.MidiTrack()
	mid.tracks.append(track)
	track.append(meta_msg)
	for i, (msg_type, msg_note, msg_velocity, msg_time) in enumerate(notes):
		if (i != 0) and (i in split_inds):
			cur_ind = split_inds.index(i)
			prev_split = split_inds[cur_ind-1]
			
			# create a new file using the messages
			mid_save_path = os.path.join(save_path, "{}_{}.mid".\
				format(prev_split,i-1))
			mid.save(mid_save_path)
			print(".........saved file at {} ...............".format(mid_save_path))

			# reset new midi file
			mid = mido.MidiFile()
			track = mido.MidiTrack()
			mid.tracks.append(track)
			track.append(meta_msg)

		track.append(mido.Message(msg_type, note=msg_note, velocity=msg_velocity, time=msg_time))


def replaceRandomNotes(f_dir, save_path, percentage=10):
	for filename in os.listdir(f_dir):
		if not (filename.endswith(".mid") or filename.endswith(".midi")):
			continue

		f_path = os.path.join(f_dir, filename)
		f = mido.MidiFile(f_path)

		# get time signature message
		meta_msg = getTimeSignature(f)

		notes = getNotesWithDeltaTick(f)
		num_notes = len(notes)
		avail_inds = list(range(num_notes))
		del_indices = generateRandNumInRange(0, num_notes, percentage)
		del_indices.sort()

		if DEBUG: meta_str = "Replaced Indices: {}\n\n".format(del_indices);

		# create new midi file to save the generated slice
		mid = mido.MidiFile()
		track = mido.MidiTrack()
		mid.tracks.append(track)
		track.append(meta_msg)

		for i, (msg_type, msg_note, msg_velocity, msg_time) in enumerate(notes):
			if i in del_indices:
				note_rep = pickRandNumInRange(msg_note-10, msg_note+10)
				track.append(mido.Message(msg_type, note=note_rep, velocity=msg_velocity, time=msg_time))
				if DEBUG: 
					meta_str += "{} <{}, note={}, tick={}>(original)\n".format(i, msg_type, msg_note, msg_time)
					meta_str += "{} <{}, note={}, tick={}>(replaced)\n".format(i, msg_type, note_rep, msg_time);
				continue

			
			track.append(mido.Message(msg_type, note=msg_note, velocity=msg_velocity, time=msg_time))
			if DEBUG: 
				meta_str += "{} <{}, note={}, tick={}>\n".format(i, msg_type, msg_note, msg_time)

		mid_save_path = os.path.join(save_path, str(percentage))
		if not os.path.exists(mid_save_path):
			os.makedirs(mid_save_path)
		mid.save(os.path.join(mid_save_path, filename)) # Chopin, 0-154.txt
		print(".........saved file at {} ...............".format(os.path.join(mid_save_path, filename)))

		if DEBUG:
			file_range = filename[:filename.index(".")]
			meta_save_path = os.path.join(mid_save_path, "{}_replace_meta.txt".format(file_range))
			meta_f = open(meta_save_path, "w")
			meta_f.write(meta_str)
			meta_f.close()



# loop through all slices in f_dir
# create midi slices with randomly notes being deleted from the original slice
def deleteRandomNotes(f_dir, save_path, percentage=10):
	for filename in os.listdir(f_dir):
		if not (filename.endswith(".mid") or filename.endswith(".midi")):
			continue

		f_path = os.path.join(f_dir, filename)
		f = mido.MidiFile(f_path)

		# get time signature message
		meta_msg = getTimeSignature(f)

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
			meta_save_path = os.path.join(mid_save_path, "{}_delete_meta.txt".format(file_range))
			meta_f = open(meta_save_path, "w")
			meta_f.write(meta_str)
			meta_f.close()


# save the panda dataframe of notes as a csv at notes.csv
# save path only specifies the directory to save
def createCSVFromDF(df, save_path, name):
	csv_path = os.path.join(save_path, name)
	df.to_csv(csv_path)


# get vector of sequential notes from a input midi sequence
def getSeqVec(notes, window=15):
	seq_vec = []
	for (_, note, _, _) in notes:
		seq_vec.append(int(note))

	seq_vec.extend([0]*(window-len(seq_vec)))
	# print("seq_vec:{}, length:{}".format(seq_vec, len(seq_vec)))
	return seq_vec


# get freq vector from an input midi sequence
# stores the number of times a note occurs in the input sequence
def getFreqVec(notes):
	# a total number of 128 pitch values on a keyboard
	# normalization: divide by the total number of notes
	freq_vec = [0]*128
	total_num = len(notes)
	for (_, note, _, _) in notes:
		freq_vec[int(note)] += (1/total_num)

	return freq_vec
	

# used to process the midi file
# df defined in delta ticks
# takes in size of sliding window as a parameter defined in number of midi notes
# define SeqVec or FreqVec here!!!
def getVecWithSlidingWindowFromDf(df, offset=0, window=15):
	notes = df.values.tolist()

	info = dict()
	for start in range(len(notes)):
		if (start+window) > len(notes):
			part = notes[start:]
		else:
			part = notes[start:start+window]
		vec = getSeqVec(part, window=window)
		info[start+offset] = vec

	return info


def getEuclideanDist(test_freq_vec, orig_freq_vec):
	return np.linalg.norm(np.array(test_freq_vec)-np.array(orig_freq_vec), ord=2)


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

			orig_freq_info = getVecWithSlidingWindowFromDf(orig_notes_df, window=test_df_size)
			test_freq_info = getVecWithSlidingWindowFromDf(test_notes_df, \
				offset=test_start, window=test_df_size)
			test_start, minDistStart, minDist = matchDFs(test_freq_info, orig_freq_info, test_df_size)

			orig_dist = getEuclideanDist(test_freq_info[test_start], orig_freq_info[test_start])

			is_matched = True if (test_start in minDistStart) else False

			row["is_matched"] = is_matched
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
	midi_file_name = "Mariage_dAmour"
	midi_file_path = os.path.join(static_dir, midi_file_name + ".midi")
	sample_save_path = os.path.join(static_dir, midi_file_name)
	if not os.path.exists(sample_save_path):
		os.makedirs(sample_save_path)

	print("........master midi file loaded at path {}............".format(midi_file_path))

	f = mido.MidiFile(midi_file_path)
	orig_notes_df = getNotesDFWithDeltaTick(f)
	# time saved means "tick" here
	createCSVFromDF(orig_notes_df, sample_save_path, "notes_delta_tick.csv")

	orig_sample_save_path = os.path.join(sample_save_path, "0")
	if not os.path.exists(orig_sample_save_path):
		os.makedirs(orig_sample_save_path)

	# split the master midi file accordingly and then save them in different folders
	createAndSaveMidiSlices(f, orig_sample_save_path, len_split=30)

	# version 2 midi matching
	for p in percentages[1:]:
		# arguments: (1) dir of original sample files (2) path to save generated midi files
		replaceRandomNotes(orig_sample_save_path, sample_save_path, percentage=p)

	
	for p in percentages:
		result = testFileMatching(os.path.join(sample_save_path, str(p)), orig_notes_df)
		f_result_name = "match_results_{}_normalized.csv".format(p)
		with open(os.path.join(sample_save_path, str(p), f_result_name), "w") as f_result:
			writer = csv.DictWriter(f_result, fieldnames=list(result[0].keys()))
			writer.writeheader()
			for row in result:
				writer.writerow(row)

if __name__ == "__main__":
	main()
