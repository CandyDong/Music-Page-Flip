import pygame
import pygame.midi
from pygame.locals import *

import os
import numpy as np
import math

import mido

from fractions import Fraction
from itertools import permutations 

static_dir = "../static/"
WINDOW = 10

###############Matching Utils####################
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

	notes = getNotes(f)
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


def getPositionFromTick(tick_measure_list, tick):
	for entry in tick_measure_list:
		if entry["global_tick"] == tick:
			return entry["num_measure_passed"], \
			Fraction(entry["pos_in_measure"], entry["measure_resolution"])


def getEuclideanDist(test_vec, orig_vecs):
	# print("test_vec: {}, orig_vec: {}".format(test_vec, orig_vec))
	smallest = None
	for orig_vec in orig_vecs:
		dist = np.linalg.norm(np.array(test_vec)-np.array(orig_vec), ord=2)
		if (smallest == None) or (smallest > dist):
			smallest = dist
		if smallest == 0:
			break
	return smallest


# stores midi note info in a list
def getNotes(f):
	notes = []
	global_tick = 0
	delta_tick = 0
	merged_tracks = mido.merge_tracks(f.tracks)
	for i,msg in enumerate(merged_tracks):
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


def _getPermutations(l):
	# If l is empty then there are no permutations 
	if len(l) == 0: 
		return [[]] 
  
	# If there is only one element in l then, only 
	# one permuatation is possible 
	if len(l) == 1: 
		return [l] 
  
	result = [] # empty set that will store current permutation 
  
	for i in range(len(l)): 
		m = l[i] 
		remaining = l[:i] + l[i+1:] 

		for p in _getPermutations(remaining):
			cur = [m] + p
			setCur = set(tuple(cur))
			setResult = set(map(tuple, result))
			if not setCur in setResult:
				result.append([m] + p)

	return result
  


def _getSeqVec(notes):
	vec = [[]]
	i = 0
	# print("notes: {}".format(notes))
	while (i < len(notes)):
		tmp = [notes[i][1]]

		# find chords
		j = i+1
		while (j < len(notes)) and (notes[j][-2] == 0):
			tmp.append(notes[j][1])
			j += 1
		permutations = _getPermutations(tmp)
		# print("tmp: {}, permutations: {}".format(tmp, permutations))

		i = j
		vec = [a+b for a in vec for b in permutations]
		# print("vec: {}".format(vec))

	return vec


def getSeqVecs(notes, window=WINDOW):
	info = []
	for start, (_, note_number, _, _, delta_tick, global_tick) in enumerate(notes):
		if (start+window) > len(notes):
			part = notes[start:]
		else:
			part = notes[start:start+window]
		vec = _getSeqVec(part)
		info.append({"global_tick": global_tick, "feature": vec})

	return info


# prev defines the point of match at the last matching
def matchDFs(live_notes, orig_vecs, prev_pos=0):
	minDist, pos, tick = None, None, None

	# search from the prev point to left/right simultaneously

	step = 0
	left_vec = None
	right_vec = orig_vecs[prev_pos+step]

	while (left_vec) or (right_vec):
		right_dist, left_dist = None, None

		if (right_vec):
			print("right_vec: {}".format(right_vec["feature"]))
			right_dist = getEuclideanDist(live_notes, right_vec["feature"])
			
		if (left_vec):
			print("left_vec: {}".format(left_vec["feature"]))
			left_dist = getEuclideanDist(live_notes, left_vec["feature"])
			

		print("step: {}, right_dist: {}, left_dist: {}".format(step, right_dist, left_dist))
		# right is picked with priority
		pick_right = (right_vec != None) and ((left_dist == None) or (right_dist <= left_dist))

		# print("step: {}, pick_right: {}".format(step, pick_right))

		if (minDist == None):
			if pick_right:
				minDist = right_dist
				pos = prev_pos + step
				tick = right_vec["global_tick"]
			else:
				minDist = left_dist
				pos = prev_pos - step
				tick = left_vec["global_tick"]
		elif ((right_dist != None) and (right_dist <= minDist))\
			 or ((left_dist != None) and (left_dist <= minDist)):
			if pick_right:
				if not math.isclose(right_dist, minDist, rel_tol=1e-5):
					minDist = right_dist
					pos = prev_pos + step
					tick = right_vec["global_tick"]
			else:
				if not math.isclose(left_dist, minDist, rel_tol=1e-5):
					minDist = left_dist
					pos = prev_pos - step
					tick = left_vec["global_tick"]

		# smallest distance possible
		if math.isclose(minDist, 0, rel_tol=1e-5):
			break

		step += 1
		left_vec, right_vec = None, None
		if prev_pos - step >= 0:
			left_vec = orig_vecs[prev_pos-step]
		if prev_pos + step < len(orig_vecs):
			right_vec = orig_vecs[prev_pos+step]

	return minDist, pos, tick

###############Matching Utils####################

###############MIDI Utils########################

def numberToNote(num):
	notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
	return notes[num%12]

def numberToSound(num):
	assert((num < 109) and (num > 20))
	note = num - 20


def isNoteOn(status, velocity):
	# Note on: Status byte: 1001 CCCC / 0x90 ..
	# Note off: Status byte: 1000 CCCC / 0x80 ..
	return (status == 144) and (velocity != 0)

###############MIDI Utils########################
	

def run(input_device, orig_vecs, orig_tick_measure_list):
	live_notes = []
	count = 0
	prev_pos = 0

	while True:
		if input_device.poll():
			m_e = input_device.read(1)[0] 
			data = m_e[0] # midi info
			timestamp = m_e[1] # timestamp
			velocity = data[2]

			if isNoteOn(data[0], velocity):
				note = numberToNote(data[1])
				print("note: {}".format(note))
				live_notes.append(data[1])

				count += 1
				if count == WINDOW:
					print("live_notes:{}\n{}".format(\
						list(map(lambda num: numberToNote(num), live_notes)),\
						live_notes))
					
					minDist, pos, tick = matchDFs(live_notes, orig_vecs, prev_pos=prev_pos)
					print("minDist: {}, pos: {}, tick: {} ".format(minDist, pos, tick))

					# find position
					num_measure_passed, fraction = \
					getPositionFromTick(orig_tick_measure_list, tick)
					print("measure: {}, position: {}".format(num_measure_passed, fraction))

					prev_pos = pos
					count = 0
					live_notes = []
				
				
def main():

	############prepare midi file#####################
	midi_file_name = "Piano_Man_Easy.mscz"
	midi_file_path = os.path.join(static_dir, midi_file_name + ".mid")
	f = mido.MidiFile(midi_file_path)
	orig_notes = getNotes(f)
	orig_vecs = getSeqVecs(orig_notes, window=WINDOW)

	orig_tick_measure_list = getTickMeasureDict(f)

	# print("tick_measure_list: {}".format(orig_tick_measure_list))

	pygame.init()
	pygame.midi.init()

	# # prints connected midi devices
	# for n in range(pygame.midi.get_count()):
	#     # (interf, name, input, output, opened) 
	#     print(n,pygame.midi.get_device_info(n))

	input_id = pygame.midi.get_default_input_id() # gets the first connected device
	input_device = pygame.midi.Input(input_id)
	print("midi input device: {}".format(pygame.midi.get_device_info(input_id)))

	run(input_device, orig_vecs, orig_tick_measure_list)

	return



	

if __name__ == '__main__':
	main()
"""
reads num_events midi events from the buffer.
Input.read(num_events): return midi_event_list
Reads from the Input buffer and gives back midi events. [[[status,data1,data2,data3],timestamp],
 [[status,data1,data2,data3],timestamp],...]
"""