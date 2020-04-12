import pygame
import pygame.midi
from pygame.locals import *

import os
import sys
import numpy as np
import math
import time
import json

import mido
import csv
from options import get_options
import pprint as pp

from fractions import Fraction
from itertools import permutations, combinations

import threading
import ctypes 

import socket, requests

HOST = "127.0.0.1"
PORT = 65432

TITLE = 0x01
END_SESSION = 0x02

FLIP_OFFSET = 10

NOTE_IND = 0
MSG_TYPE = 1
NOTE_NUM = 2 
NOTE = 3
VELOCITY = 4 
DELTA_TICK = 5
GLOBAL_TICK = 6

WINDOW = 5
STATIC_DIR = "../static/"


############### Matching Utils ####################
def createCSVFromListOfDict(l, csv_path):
	with open(csv_path, "w") as f_result:
			writer = csv.DictWriter(f_result, fieldnames=["index"] + list(l[0].keys()))   
			writer.writeheader()
			for i, row in enumerate(l):
				row["index"] = i
				writer.writerow(row)


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
	for (_, msg_type, msg_note_number, msg_note, _, msg_delta_tick, global_tick) in notes:
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
	def getDist(a, b):
		return np.linalg.norm(np.array(a)-np.array(b), ord=2)
	return np.amin(list(map(lambda a: getDist(a, test_vec), orig_vecs)))


# stores midi note info in a list
def getNotes(f):
	notes = []
	global_tick = 0
	delta_tick = 0
	note_id = 0
	merged_tracks = mido.merge_tracks(f.tracks)
	for i,msg in enumerate(merged_tracks):
		global_tick += msg.time
		if msg.is_meta:
			delta_tick += msg.time
			continue
		if (msg.type == "note_on") and (msg.velocity != 0):
			notes.append((note_id, msg.type, msg.note, numberToNote(msg.note), msg.velocity, \
				msg.time + delta_tick, global_tick))
			delta_tick = 0
			note_id += 1
			continue
		delta_tick += msg.time
	return notes


def _getPermutations(l):
	# If l is empty then there are no permutations 
	# print("l: {}".format(l))
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

		# print("m: {}, remaining: {}".format(m, remaining))

		for p in _getPermutations(remaining):
			cur = [m] + p
			# print("p: {}, cur:{}".format(p, cur))
			setCur = set(tuple(cur))
			setResult = set(map(tuple, result))
			if not setCur in setResult:
				result.append(cur)

		# print("result: {}".format(result))

	return result


def _getSubsets(l, n):
	return list(map(list, combinations(l, n)))


def getFlipInfo(filename):
	with open(filename + ".json") as f:
		data = json.load(f)
	for i, _ in enumerate(data["page"]):
		data["page"][i] -= FLIP_OFFSET
	return data


# n is the index of the note
# find the position of the nth note in noteGroups
def _findPosInNoteGroups(noteGroups, n):
	numNotes = sum(list(map(lambda x: len(x), noteGroups)))
	if n >= numNotes:
		return None

	i, count = 0, 0
	while (i < len(noteGroups)):
		cur = noteGroups[i]
		count += len(cur)
		if (count > n):
			return (i, len(cur) - (count-n))
		i += 1


def getNoteGroups(notes):
	noteGroups = []

	i = 0
	while (i < len(notes)):
		tmp = [notes[i][NOTE_NUM]]
		j = i+1
		while (j < len(notes)) and (notes[j][DELTA_TICK] == 0):
			tmp.append(notes[j][NOTE_NUM])
			j += 1
		noteGroups.append(tmp)
		i = j

	return noteGroups

def getSeqVecs(notes, window=5):
	info = []
	
	noteGroups = getNoteGroups(notes)

	print("size(noteGroups): {}, size(notes): {}".format(len(noteGroups), len(notes)))

	INFO_TIME_START = time.time()

	start, p = 0, (0, 0) # p points to the position of the note in the notegroup
	while (start < len(notes)):
		k = 0
		vec = [[]]
		while (k < window) and ((k+start) < len(notes)):
			cur = noteGroups[p[0]]
			part = noteGroups[p[0]][p[1]:]
			# print("start: {}, k: {}, ind: {}, p:{}, cur: {}".format(start, k, start+k, p, cur))

			if (len(part) <= (window-k)):
				n = len(part)
				p = (p[0]+1, 0)
				k += len(part)
			else: # length of vec smaller than window
				n = window-k
				p = (p[0], p[1]+window-k)
				k = window

			subSets = _getSubsets(cur, n)

			permutations = []
			for s in subSets:
				permutations.extend(_getPermutations(s))
			
			vec = [v + s for v in vec for s in permutations]

			# print("number of possible vecs: {:d}".format(len(vec)))
			# print("vec: {}".format(permutations, vec))
		end = start + k -1 if (start+k-1) < len(notes) else len(notes)-1
		info.append({
					"start_ind": notes[start][NOTE_IND],\
					"end_ind": notes[end][NOTE_IND],\
					"start_tick": notes[start][GLOBAL_TICK],\
					"end_tick": notes[end][GLOBAL_TICK], \
					"start_note": notes[start][NOTE],\
					"end_note": notes[end][NOTE],\
					"feature": vec
					})
		start += 1
		p = _findPosInNoteGroups(noteGroups, start)
		# print("updated p: {}".format(p))
	# print("info: {}".format(info))
	
	INFO_TIME_END = time.time()
	print("time elasped for getting the info structure ready: {}".format(INFO_TIME_END-INFO_TIME_START))
	return info


# prev defines the point of match at the last matching
def matchDFs(live_notes, orig_vecs, orig_flip, prev_pos):
	minDist, pos, tick, flip = None, None, None, False

	# search from the prev point to left/right simultaneously

	step = 0
	left_vec = None
	right_vec = orig_vecs[prev_pos+step]

	while (left_vec) or (right_vec):
		# if (step >= WINDOW*3):
		# 	return minDist, pos, tick

		right_dist, left_dist = None, None

		DIST_TIME_START = time.time()

		if (right_vec):
			# print("len(right_vec): {}".format(len(right_vec["feature"][0])))
			if not (len(right_vec["feature"][0]) < len(live_notes)):
				# print("right_vec: {}".format(right_vec["feature"]))
				right_dist = getEuclideanDist(live_notes, right_vec["feature"])
			
		if (left_vec):
			# print("len(left_vec): {}".format(len(left_vec["feature"][0])))
			if not (len(left_vec["feature"][0]) < len(live_notes)):
				# print("left_vec: {}".format(left_vec["feature"]))
				left_dist = getEuclideanDist(live_notes, left_vec["feature"])

		DIST_TIME_END = time.time()
		# print("time elapsed for dist calculation: {}".format(DIST_TIME_END-DIST_TIME_START))
		
		if (right_dist == None) and (left_dist == None):
			break

		# print("step: {}, right_dist: {}, left_dist: {}\n".format(step, right_dist, left_dist))
		# right is picked with priority
		pick_right = (right_dist != None) and ((left_dist == None) or (right_dist <= left_dist))

		# print("step: {}, pick_right: {}".format(step, pick_right))

		if (minDist == None):
			if pick_right:
				minDist = right_dist
				pos = prev_pos + step
				tick = right_vec["end_tick"]
			else:
				minDist = left_dist
				pos = prev_pos - step
				tick = left_vec["end_tick"]
		elif ((right_dist != None) and (right_dist <= minDist))\
			 or ((left_dist != None) and (left_dist <= minDist)):
			if pick_right:
				if not math.isclose(right_dist, minDist, rel_tol=1e-5):
					minDist = right_dist
					pos = prev_pos + step
					tick = right_vec["end_tick"]
			else:
				if not math.isclose(left_dist, minDist, rel_tol=1e-5):
					minDist = left_dist
					pos = prev_pos - step
					tick = left_vec["end_tick"]

		# smallest distance possible
		if math.isclose(minDist, 0, rel_tol=1e-5):
			break

		step += 1
		left_vec, right_vec = None, None
		if prev_pos - step >= 0:
			left_vec = orig_vecs[prev_pos-step]
		if prev_pos + step < len(orig_vecs):
			right_vec = orig_vecs[prev_pos+step]

	# find if prev_pos is before the page flip position
	flip_to = None
	prev_ind = orig_vecs[prev_pos]["end_ind"]
	if orig_flip["page"][-1] > prev_ind:
		nex = np.where(np.array(orig_flip["page"]) > prev_ind)[0][0]
		nex_ind = orig_flip["page"][nex]
		cur_ind = orig_vecs[pos]["end_ind"]

		print("nearest next flip point: {}, previous note#: {}, current note#:{}"\
			.format(nex_ind, \
				prev_ind, \
				cur_ind))
		if cur_ind >= nex_ind:
			flip = True
			flip_to = nex + 1


	return minDist, pos, tick, flip, flip_to

############### MIDI Utils ########################

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

############### Tracker ##########################
def run(title, input_device, orig_vecs, 
		orig_flip_info, orig_tick_measure_list,
		reset):
	live_notes = []
	prev_pos = 0
	start_ticks = pygame.time.get_ticks() #starter tick

	while True:
		if reset.isSet():
			print("reset")
			break
		if input_device.poll():
			m_e = input_device.read(1)[0] 
			data = m_e[0] # midi info
			timestamp = m_e[1] # timestamp
			velocity = data[2]

			if isNoteOn(data[0], velocity):
				note = numberToNote(data[1])
				print("note: {}".format(note))
				live_notes.append(data[1])

			seconds = (pygame.time.get_ticks() - start_ticks)/1000 #calculate how many seconds
			if seconds > 2: # if more than 1 second
				if len(live_notes) > WINDOW:
					cur_notes = live_notes[-WINDOW:]
					
					minDist, pos, tick, flip, flip_to = \
						matchDFs(cur_notes, orig_vecs, \
						orig_flip_info, \
						prev_pos)
					# find position
					num_measure_passed, fraction = \
					getPositionFromTick(orig_tick_measure_list, tick)

					print("measure: {}, position: {}, page flip = {}, flip_to = {}".\
						format(num_measure_passed+1, fraction, flip, flip_to))

					if flip:
						make_post_request(title, flip_to)

					prev_pos = pos
					start_ticks = pygame.time.get_ticks() #starter tick
	return


############### Threading ########################
class tracker_thread(threading.Thread):
	def __init__(self, title, input_device):
		threading.Thread.__init__(self)
		self.title = title
		self.input_device = input_device
		self.reset = threading.Event()

	def run(self):
		try:
			############prepare midi file#####################
			print("preparing midi meta files...........")
			midi_file_name = self.title
			midi_file_path = os.path.join(STATIC_DIR, midi_file_name + ".mid")
			f = mido.MidiFile(midi_file_path)
			orig_notes = getNotes(f)
			orig_flip_info = getFlipInfo(os.path.join(STATIC_DIR, midi_file_name))
			orig_vecs = getSeqVecs(orig_notes, window=WINDOW)
			orig_tick_measure_list = getTickMeasureDict(f)

			print("tracker program running.............")
			run(self.title, self.input_device, orig_vecs, \
				orig_flip_info, orig_tick_measure_list, \
				self.reset)
		finally: 
			print("tracker program ended!")
			return

	def get_id(self):
		if hasattr(self, '_thread_id'):
			return self._thread_id
		for thread_id, thread in threading._active.items():
			if thread is self:
				return thread_id

	def raise_exception(self):
		thread_id = self.get_id()
		res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 
			  ctypes.py_object(SystemExit)) 
		if res > 1:
			ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0) 
			print('Exception raise failure') 


#################### TCP Requests #####################

def make_post_request(title, flip_to):
	# defining the api-endpoint  
	API_ENDPOINT = "http://{}:8000/pageFlipper/flip-page".format(HOST)

	# data to be sent to api 
	data = {'score_name': title, 
			'flip_to':flip_to+1
			} 
	  
	# sending post request and saving response as response object 
	r = requests.post(url = API_ENDPOINT, data = data)


# def send_reply(s, conn, code):
# 	reply = bytearray()
# 	reply.append(REPLY)
# 	reply.append(code)
# 	conn.sendall(reply)


def main():
	pygame.init()
	pygame.midi.init()
	input_id = pygame.midi.get_default_input_id() # gets the first connected device
	input_device = pygame.midi.Input(input_id)
	print("midi input device connected: {}".format(pygame.midi.get_device_info(input_id)))

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind((HOST, PORT))
	s.listen()
	print("Waiting for Django server to connect.........")
	conn, addr = s.accept()
	print("Connected!")

	# ############get command line arguments############
	# opts = get_options()
	# # Pretty print the run args
	# pp.pprint(vars(opts))
	tracker = None
	
	while True:
		msg = conn.recv(1024)
		if not msg:
			print("client disconnected.")
			s.close()
			sys.exit()
		elif msg[0] == TITLE:
			title = msg[1:].strip().decode('utf-8')
			print("received title is : {}".format(title))
			# start program
			tracker = tracker_thread(title, input_device)
			tracker.start()
		elif msg[0] == END_SESSION:
			print("resetting session.............")
			if (tracker == None):
				print("session reset.")
				continue
			tracker.reset.set()
			tracker.join()
			tracker.reset.clear()
			print("session reset.")
		


if __name__ == '__main__':
	main()

