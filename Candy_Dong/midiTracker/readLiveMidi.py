import pygame
import pygame.midi
from pygame.locals import *

import os
import numpy as np
import math

import mido

static_dir = "../static/"
WINDOW = 30

###############Matching Utils####################
def getEuclideanDist(test_freq_vec, orig_freq_vec):
    return np.linalg.norm(np.array(test_freq_vec)-np.array(orig_freq_vec), ord=2)

# stores midi note info in a list
def getNotes(f):
    notes = []
    merged_tracks = mido.merge_tracks(f.tracks)
    for i,msg in enumerate(merged_tracks):
        if msg.is_meta:
            continue
        if msg.type == "note_on":
            notes.append(int(msg.note))
    return notes


def _getSeqVec(notes):
    vec = [0] * WINDOW
    for i, note in enumerate(notes):
        vec[i] = note
    return vec


# flag = "L" -> live
# flag = "O" -> original
def getVecs(notes, flag="L"):
    info = []
    for start in range(len(notes)):
        if (start+WINDOW) > len(notes):
            part = notes[start:]
        else:
            part = notes[start:start+WINDOW]
        vec = _getSeqVec(part)
        info.append(vec) 
        if flag == "L":
            return info
    return info


# prev defines the point of match at the last matching
def matchDFs(live_vecs, orig_vecs, prev_pos=0):
    live_vec = live_vecs[0]
    minDist = None
    minPos = None

    # search from the prev point to left/right simultaneously

    step = 0
    left_vec = orig_vecs[prev_pos-step]
    right_vec = orig_vecs[prev_pos+step]

    while (left_vec) or (right_vec):
        right_dist, left_dist = None, None

        if (right_vec):
            right_dist = getEuclideanDist(live_vec, right_vec)
        if (left_vec):
            left_dist = getEuclideanDist(live_vec, left_vec)

        # right is picked with priority
        pick_right = (right_vec != None) and ((left_dist == None) or (right_dist <= left_dist))

        print("step: {}, pick_right: {}".format(step, pick_right))

        if (minDist == None):
            if pick_right:
                minDist = right_dist
                minPos = [prev_pos + step]
            else:
                minDist = left_dist
                minPos = [prev_pos - step]
        elif ((right_dist <= minDist) or (left_dist <= minDist)):
            if pick_right:
                if math.isclose(right_dist, minDist, rel_tol=1e-5):
                    minPos.append(right_dist)
                else:
                    minDist = right_dist
                    minPos = [prev_pos + step]
            else:
                if math.isclose(left_dist, minDist, rel_tol=1e-5):
                    minPos.append(left_dist)
                else:
                    minDist = left_dist
                    minPos = [prev_pos - step]

        step += 1
        left_vec = orig_vecs[prev_pos-step]
        right_vec = orig_vecs[prev_pos+step]

    return minDist, minPos[0]

###############Matching Utils####################

###############MIDI Utils########################

def numberToNote(num):
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    return notes[num%12]

def numberToSound(num):
    assert((num < 109) and (num > 20))
    note = num - 20


def isNoteOn(status):
    # Note on: Status byte: 1001 CCCC / 0x90 ..
    # Note off: Status byte: 1000 CCCC / 0x80 ..
    return status == int("90", 16)

###############MIDI Utils########################
    

def run(input_device, orig_vecs):
    live_notes = []
    count = 0
    prev_pos = 0

    while True:
        if input_device.poll():
            m_e = input_device.read(1)[0] 
            data = m_e[0] # midi info
            timestamp = m_e[1] # timestamp
            
            if isNoteOn(data[0]):
                note = numberToNote(data[1])
                velocity = data[2]
                print("note: {}".format(note))
                live_notes.append(data[1])

                print("live_notes:{}".format(live_notes))

                count += 1
                if count == WINDOW:
                    ###match
                    live_vecs = getVecs(live_notes, flag="L")
                    print("live_vecs:{}".format(live_vecs))

                    minDist, minPos = matchDFs(live_vecs, orig_vecs, prev_pos=prev_pos)
                    print("minPos: {} ".format(minPos))
                    prev_pos = minPos
                    count = 0
                    live_notes = []
                
                
def main():

    ############prepare midi file#####################
    midi_file_name = "Swans_on_the_lake_easy"
    midi_file_path = os.path.join(static_dir, midi_file_name + ".midi")
    f = mido.MidiFile(midi_file_path)
    orig_notes = getNotes(f)
    orig_vecs = getVecs(orig_notes, flag="O")

    pygame.init()
    pygame.midi.init()

    # # prints connected midi devices
    # for n in range(pygame.midi.get_count()):
    #     # (interf, name, input, output, opened) 
    #     print(n,pygame.midi.get_device_info(n))

    input_id = pygame.midi.get_default_input_id() # gets the first connected device
    input_device = pygame.midi.Input(input_id)
    print("midi input device: {}".format(pygame.midi.get_device_info(input_id)))

    run(input_device, orig_vecs)

    return



    

if __name__ == '__main__':
    main()
"""
reads num_events midi events from the buffer.
Input.read(num_events): return midi_event_list
Reads from the Input buffer and gives back midi events. [[[status,data1,data2,data3],timestamp],
 [[status,data1,data2,data3],timestamp],...]
"""