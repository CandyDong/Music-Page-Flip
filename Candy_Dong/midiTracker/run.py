import os, sys
import mido
import random
import pandas as pd
import numpy as np
from collections import defaultdict
import math
import csv
import Levenshtein
from fractions import Fraction

static_dir = "../static/"

DEBUG = True
percentages = [0, 5, 10, 20, 30, 40, 50]

def numberToNote(num):
	notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
	return notes[num%12]


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


def find_nth(s, substring, n):
    start = s.find(substring)
    while start >= 0 and n > 1:
        start = s.find(substring, start+len(substring))
        n -= 1
    return start


# returns the first message that sets the time signature of the file
# and return the default time signature message if none exists in the original file
def getTimeSignature(f):
	# get time signature message
	meta_msg = mido.MetaMessage("time_signature", numerator=4, denominator=4) #default meta message
	for i,msg in enumerate(f.tracks[0]):
		if msg.type == "time_signature":
			meta_msg = msg
			break

	return meta_msg


def getGlobalTickFromInd(notes, ind):
	if (ind >= 0) and (ind < len(notes)):
		return notes[ind][-1]
	return None


# get measure information 
# use global tick instead of delta tick
# returns a dictionary that stores (tick, measure) as key pairs
# save in a csv file
def getTickMeasureDict(f):
	ticks_per_beat = f.ticks_per_beat #TODO:!!!!
	beats_per_bar, beats_per_whole_note = None, None
	
	num_notes = 0
	for i, msg in enumerate(f.tracks[0]):
		if msg.type == "time_signature":
			beats_per_bar = msg.numerator
			beats_per_whole_note = msg.denominator
		if msg.type == "note_on":
			num_notes += 1

	# defined in unit of tick
	num_ticks_per_measure = ticks_per_beat * beats_per_bar

	print("ticks_per_beat: {}\nbeats_per_bar: {}\nbeats_per_whole_note: {}\n".\
		format(ticks_per_beat, beats_per_bar, beats_per_whole_note))

	notes = getNotesWithDeltaTick(f)
	tick_measure_list = []
	for (msg_type, msg_note_number, msg_note, _, msg_delta_tick, global_tick) in notes:
		num_measure_passed = (global_tick // num_ticks_per_measure)
		fraction = Fraction((global_tick - num_ticks_per_measure * num_measure_passed), num_ticks_per_measure)
		entry = {"global_tick": global_tick, "delta_tick": msg_delta_tick, \
				 "note_number": msg_note_number, "note": msg_note,\
				 "num_measure_passed": num_measure_passed, \
				 "pos_in_measure": fraction.numerator, "measure_resolution": fraction.denominator}
		tick_measure_list.append(entry)

	return tick_measure_list


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
# merge delta time on deleted events 
# keep only note_on events (remove note_off and note_on with velocity = 0)
def getNotesWithDeltaTick(f):
	notes = []
	global_tick = 0
	delta_tick = 0
	for i,msg in enumerate(f.tracks[0]):
		global_tick += msg.time
		if msg.is_meta:
			delta_tick += msg.time
			continue
		if (msg.type == "note_on") and (msg.velocity != 0):
			notes.append((msg.type, msg.note, numberToNote(msg.note), msg.velocity, \
				msg.time + delta_tick, global_tick))
			delta_tick = 0
			continue
		delta_tick += msg.time
	return notes


def getNotesDFWithDeltaTick(f):
	notes = getNotesWithDeltaTick(f)
	df = pd.DataFrame(np.array(notes), columns=["Type", 'Number', 'Note', "Velocity", 'Delta_Tick', 'Global_Tick'])
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


def getFixedIntervalSplitInds(f, window=5):
	if (window <= 0):
		raise Exception("Split interval too small!")

	# generate population without indices of meta tracks 
	# split interval determined by len
	notes = getNotesWithDeltaTick(f)
	num_notes = len(notes)
	split_inds = list(range(0, num_notes, window))

	return split_inds


# randomly slice merged_tracks and save as a new midi file 
# for testing purpose
# if num_split is provided -> random split
# if len_split is provided -> fixed interval split
def createAndSaveMidiSlices(f, save_path, num_split=None, window=None):
	# get time signature message
	meta_msg = getTimeSignature(f)
	notes = getNotesWithDeltaTick(f)

	assert((num_split != None) or (window != None))

	if (num_split):
		split_inds = getRandomSplitInds(f, num_split)
	else:
		split_inds = getFixedIntervalSplitInds(f, window)

	mid = mido.MidiFile()
	track = mido.MidiTrack()
	mid.tracks.append(track)
	track.append(meta_msg)
	for i, (msg_type, msg_note_number, _, msg_velocity, msg_delta_tick, msg_global_tick) in enumerate(notes):

		track.append(mido.Message(type=msg_type, note=msg_note_number, velocity=msg_velocity, time=msg_delta_tick))

		if ((i+1) in split_inds):
			cur_ind = split_inds.index(i+1)
			prev_split = split_inds[cur_ind-1]
			prev_tick = getGlobalTickFromInd(notes, prev_split-1)
			if prev_tick == None:
				prev_tick = 0
			
			# create a new file using the messages
			mid_save_path = os.path.join(save_path, "{}_{}_{}.mid".\
				format(prev_split,i, prev_tick))
			mid.save(mid_save_path)
			print(".........saved file at {} ...............".format(mid_save_path))

			# reset new midi file
			mid = mido.MidiFile()
			track = mido.MidiTrack()
			mid.tracks.append(track)
			track.append(meta_msg)



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
		rep_indices = generateRandNumInRange(0, num_notes, percentage)
		rep_indices.sort()

		if DEBUG: meta_str = "Replaced Indices: {}\n\n".format(rep_indices);

		# create new midi file to save the generated slice
		mid = mido.MidiFile()
		track = mido.MidiTrack()
		mid.tracks.append(track)
		track.append(meta_msg)

		for i, (msg_type, msg_note_number, _, msg_velocity, msg_delta_tick, msg_global_tick) in enumerate(notes):
			if i in rep_indices:
				note_rep = pickRandNumInRange(msg_note_number-10, msg_note_number+10)
				track.append(mido.Message(msg_type, note=note_rep, velocity=msg_velocity, time=msg_delta_tick))
				if DEBUG: 
					meta_str += "{} <{}, note={}, tick={}>(original)\n".format(i, msg_type, msg_note_number, msg_delta_tick)
					meta_str += "{} <{}, note={}, tick={}>(replaced)\n".format(i, msg_type, note_rep, msg_delta_tick);
				continue
			
			track.append(mido.Message(msg_type, note=msg_note_number, velocity=msg_velocity, time=msg_delta_tick))
			if DEBUG: 
				meta_str += "{} <{}, note={}, tick={}>\n".format(i, msg_type, msg_note_number, msg_delta_tick)

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

		for i, (msg_type, msg_note_number, _, msg_velocity, msg_delta_tick, _) in enumerate(notes):
			if i in del_indices:
				if (tick != None):
					tick += msg_delta_tick
				else:
					tick = msg_delta_tick
				if DEBUG: meta_str += "{} <{}, note={}, tick={}>(deleted)\n".format(i, msg_type, msg_note_number, msg_delta_tick);
				continue

			if tick != None:
				track.append(mido.Message(msg_type, note=msg_note_number, velocity=msg_velocity, time=msg_delta_tick+tick))
				if DEBUG: 
					meta_str += "{} <{}, note={}, tick={}>(original)\n".format(i, msg_type, msg_note_number, msg_delta_tick);
					meta_str += "{} <{}, note={}, tick={}>(merged)\n".format(i, msg_type, msg_note_number, msg_delta_tick+tick);
			else:
				track.append(mido.Message(msg_type, note=msg_note_number, velocity=msg_velocity, time=msg_delta_tick))
				if DEBUG: meta_str += "{} <{}, note={}, tick={}>\n".format(i, msg_type, msg_note_number, msg_delta_tick);
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


def createCSVFromListOfDict(l, csv_path):
	with open(csv_path, "w") as f_result:
			writer = csv.DictWriter(f_result, fieldnames=["index"] + list(l[0].keys()))   
			writer.writeheader()
			for i, row in enumerate(l):
				row["index"] = i
				writer.writerow(row)


# get vector of sequential notes from a input midi sequence
def getSeqVec(notes, window=15):
	seq_vec = []
	for (_, note_number, _, _, _, _) in notes:
		seq_vec.append(int(note_number))

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
	for (_, note_number, _, _, _, _) in notes:
		freq_vec[int(note_number)] += (1/total_num)

	return freq_vec
	

# used to process the midi file
# takes in size of sliding window as a parameter defined in number of midi notes
# define SeqVec or FreqVec here!!!
def getVecWithSlidingWindowFromDf(notes, offset_start=0, offset_global_tick=0, window=15):
	info = dict()
	for start, (_, _, _, _, delta_tick, global_tick) in enumerate(notes):
		if (start+window) > len(notes):
			part = notes[start:]
		else:
			part = notes[start:start+window]
		vec = getSeqVec(part, window=window)
		info[start+offset_start] = {"global_tick": offset_global_tick+global_tick, "feature": vec}

	return info


def getEuclideanDist(test_freq_vec, orig_freq_vec):
	return np.linalg.norm(np.array(test_freq_vec)-np.array(orig_freq_vec), ord=2)


def findEntryInTickMeasureList(tick_measure_list, global_tick):
	# entry = {"global_tick": global_tick, "delta_tick": msg_delta_tick, \
	# 			 "note_number": msg_note_number, "note": msg_note,\
	# 			 "num_measure_passed": num_measure_passed, \
	# 			 "pos_in_measure": fraction.numerator, "measure_resolution": fraction.denominator}
	for entry in tick_measure_list:
		entry_global_tick = entry["global_tick"]
		
		if (entry_global_tick == global_tick):
			return entry["num_measure_passed"], entry["pos_in_measure"], entry["measure_resolution"]
	return None, None, None


def testFileMatching(test_dir, orig_notes, tick_measure_list):
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

			hypen_1 = find_nth(filename, "_", 1)
			hypen_2 = find_nth(filename, "_", 2)
			test_start = int(filename[:hypen_1])
			test_end = int(filename[hypen_1+1:hypen_2])
			test_tick = int(filename[hypen_2+1:-4])

			test_notes = getNotesWithDeltaTick(test_f)
			test_size = len(test_notes)

			row["size"] = test_size

			orig_freq_info = getVecWithSlidingWindowFromDf(orig_notes, window=test_size)
			test_freq_info = getVecWithSlidingWindowFromDf(test_notes, \
				offset_start=test_start, offset_global_tick=test_tick, window=test_size)

			minDistTick, minDist = matchDFs(test_freq_info, orig_freq_info)

			orig_dist = getEuclideanDist(test_freq_info[test_start]["feature"], \
				orig_freq_info[test_start]["feature"])

			row["matched_ticks"] = minDistTick
			row["answer_tick"] = orig_freq_info[test_start]["global_tick"]
			row["is_matched"] = True if (test_freq_info[test_start]["global_tick"] in minDistTick) else False

			num_measure_passed, pos_in_measure, measure_resolution = \
			findEntryInTickMeasureList(tick_measure_list, orig_freq_info[test_start]["global_tick"])

			row["matched_measure"] = num_measure_passed
			row["matched_position"] = pos_in_measure
			row["measure_resolution"] = measure_resolution
			row["distance"] = minDist
			row["answer_distance"] = orig_dist

			result.append(row)
	return result


def matchDFs(test_freq_info, orig_freq_info):
	for test_start, test_freq_dict in test_freq_info.items():
		minDist = None
		minDistTick = None

		test_freq_vec = test_freq_dict["feature"]
		for orig_start, orig_freq_dict in orig_freq_info.items():
			orig_freq_tick = orig_freq_dict["global_tick"]
			orig_freq_vec = orig_freq_dict["feature"]
			dist = getEuclideanDist(test_freq_vec, orig_freq_vec)
			# print(".........test: {}, original: {}, distance: {}...........".\
			# 	format(test_start, orig_start, dist))
			if ((minDist == None) or (dist <= minDist)):
				if (minDist != None) and (math.isclose(dist, minDist, rel_tol=1e-5)):
					minDistTick.add(orig_freq_tick)
					continue
				minDist = dist
				minDistTick = set([orig_freq_tick])
		break
	return minDistTick, minDist


# remove unkown meta messages
# merge tracks
def preprocess(filename):
	# remove unknown meta messages
	f = mido.MidiFile(os.path.join(static_dir, filename + ".mid"))
	new_file = mido.MidiFile()

	tracks = []
	for i, track in enumerate(f.tracks):
		tmp_track = mido.MidiTrack()
		# print(track)
		for msg in track:
			# print(msg)
			if msg.type:
				if msg.type == "unknown_meta":
					continue
				tmp_track.append(msg)
		tracks.append(tmp_track)

	merged_track = mido.merge_tracks(tracks)
	# print("merged_track:{}".format(merged_track))
	# for msg in merged_track:
	# 	print(msg)
	new_file.tracks.append(merged_track)
	new_file.save(os.path.join(static_dir, filename+"_edited.mid"))


def main():
	#Chopin_-_Nocturne_Op_9_No_2_E_Flat_Major.midi
	midi_file_name = "Piano_Man_Easy.mscz"
	preprocess(midi_file_name)

	################################# prepare file paths to be used #######################
	midi_file_path = os.path.join(static_dir, midi_file_name + "_edited.mid")
	sample_save_path = os.path.join(static_dir, midi_file_name)
	if not os.path.exists(sample_save_path):
		os.makedirs(sample_save_path)
	orig_sample_save_path = os.path.join(sample_save_path, "0")
	if not os.path.exists(orig_sample_save_path):
		os.makedirs(orig_sample_save_path)
	################################# prepare file paths to be used #######################

	f = mido.MidiFile(midi_file_path)
	print("........master midi file loaded at path {}............".format(midi_file_path))

	###################### make data structures to store meta info ########################
	orig_notes = getNotesWithDeltaTick(f)
	tick_measure_list = getTickMeasureDict(f)
	# createCSVFromListOfDict(tick_measure_list, os.path.join(sample_save_path, "tick_measure.csv"))
	###################### make data structures to store meta info ########################


	# split the master midi file accordingly and then save them in different folders
	# createAndSaveMidiSlices(f, orig_sample_save_path, window=30)

	# version 2 midi matching
	# for p in percentages[1:]:
	# 	# arguments: (1) dir of original sample files (2) path to save generated midi files
	# 	replaceRandomNotes(orig_sample_save_path, sample_save_path, percentage=p)
	
	for p in percentages:
		result = testFileMatching(os.path.join(sample_save_path, str(p)), orig_notes, tick_measure_list)
		f_result_name = "match_results_{}_normalized.csv".format(p)
		createCSVFromListOfDict(result, os.path.join(sample_save_path, str(p), f_result_name))

if __name__ == "__main__":
	main()
