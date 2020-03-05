import pygame
import pygame.midi
from pygame.locals import *


def numberToNote(num):
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    return notes[num%12]

def isNoteOn(status):
    # Note on: Status byte: 1001 CCCC
    # Note off: Status byte: 1000 CCCC
    # print("status:{}".format(hex(status)))
    highest_byte = status>>4
    # print("highest_byte:{}".format(hex(highest_byte)))
    return (highest_byte & 0x1) == 1
    

def readFromInput(input_id):
    input_device = pygame.midi.Input(input_id)

    while True:
        if input_device.poll():
            e = input_device.read(1)[0] 
            data = e[0] # midi info
            timestamp = e[1] # timestamp
            
            if isNoteOn(data[0]):
                note = numberToNote(data[1])
                velocity = data[2]
                print("note: {}, velocity: {}, timestamp: {}".\
                    format(note, velocity, timestamp))

        key = pygame.key.get_pressed()
        if key[pygame.K_q]:
            pygame.quit()


def main():

    pygame.init()

    pygame.midi.init()

    # # prints connected midi devices
    # for n in range(pygame.midi.get_count()):
    #     # (interf, name, input, output, opened) 
    #     print(n,pygame.midi.get_device_info(n))

    input_id = pygame.midi.get_default_input_id() # gets the first connected device
    print("midi input device: {}".format(pygame.midi.get_device_info(input_id)))

    readFromInput(input_id)


    
    return



    

if __name__ == '__main__':
    main()
"""
reads num_events midi events from the buffer.
Input.read(num_events): return midi_event_list
Reads from the Input buffer and gives back midi events. [[[status,data1,data2,data3],timestamp],
 [[status,data1,data2,data3],timestamp],...]
"""