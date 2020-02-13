import os, sys
import mido

static_dir = "../static/"

# stores note_on/note values in a list of timestamps from a midiFile object
def getNotes(f):
	notes = [] # each entry: (time, note) if a note_on event occurs
	global_time = 0 # global time starts at time 0
	for msg in f:
		# skip meta messages
		global_time += msg.time
		if msg.type == "note_on":
			notes.append((global_time, msg.note))
	return notes

# randomly slice merged_tracks and save as a new midi file 
# for testing purpose
def saveRandomMidiSlices(merged_tracks, save_path):

	pass


def main():
	#clip the velocity of all notes to 127 if they are higher than that
	#Chopin_-_Nocturne_Op_9_No_2_E_Flat_Major.midi
	path = os.path.join(static_dir, "Chopin_-_Nocturne_Op_9_No_2_E_Flat_Major.midi")
	f = mido.MidiFile(path, clip=True)
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
	print("ticks per beat: {}, file type: {}".format(f.ticks_per_beat, f.type))

	# print("merged tracks in playback order........................")
	# merge tracks in playback order
	# for msg in mido.merge_tracks(f.tracks):
	# 	if msg.is_meta:
	# 		print(msg)

	notes = getNotes(f)
	print(notes)

	print("time length: {}".format(f.length))
	# for msg in f:
	# 	print(msg)


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
