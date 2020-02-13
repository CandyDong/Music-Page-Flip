import os, sys
from mido import MidiFile, merge_tracks

static_dir = "../static/"

# stores note_on/note values in a list of timestamps from merged tracks
def getNotes(merged_tracks):
	notes = [] # each entry: (tick, note) if a note_on event occurs
	global_tick = 0 # global tick starts at time 0
	for msg in merged_tracks:
		# skip meta messages
		if msg.is_meta:
			continue
		global_tick += msg.time
		if msg.type == "note_on":
			notes.append((global_tick, msg.note))
	return notes


def main():
	#clip the velocity of all notes to 127 if they are higher than that
	#Chopin_-_Nocturne_Op_9_No_2_E_Flat_Major.midi
	path = os.path.join(static_dir, "piano_test.mid")
	f = MidiFile(path, clip=True)
	print("midi file loaded at {}: {}\n".format(path, f))

	'''
	type 0 (single track): all messages are saved in one track
	type 1 (synchronous): all tracks start at the same time
	type 2 (asynchronous): each track is independent of the others
	delta time: how many ticks have passed since the last message
	'''
	# for track in f.tracks:
	# 	print(track)
	# 	for msg in track:
	# 		print(" ", msg)

	# print("merged tracks in playback order........................")
	# # merge tracks in playback order
	# for msg in merge_tracks(f.tracks):
	# 	print(msg)

	notes = getNotes(merge_tracks(f.tracks))
	print(notes)

	# # remove the duplicate tracks (tracks with same number of messages)
	# mes_num = set()
	# duplicates = []

	# for track in f.tracks:
	#     if len(track) in mes_num:
	#         duplicates.append(track)
	#     else:
	#         mes_num.add(len(track))

	# for track in duplicates:
	#     f.tracks.remove(track)

	# f.save(os.path.join(static_dir, 'VampireKillerCV1_no_dup.mid'))


if __name__ == "__main__":
	main()
