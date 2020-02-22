import pygame
import pygame.midi
from pygame.locals import *

# TODO: change this
def wait_for_n_keypresses(self, key, n=1):
    """Waits till one key was pressed n times.

    :param key: the key to be pressed as defined by pygame. E.g.
        pygame.K_LEFT for the left arrow key
    :type key: int
    :param n: number of repetitions till the function returns
    :type n: int
    """
    my_const = "key_consumed"
    counter = 0

    def keypress_listener(e): return my_const \
        if e.type == pygame.KEYDOWN and e.key == key \
        else EventConsumerInfo.DONT_CARE

    while counter < n:
        if self.listen(keypress_listener) == my_const:
            counter += 1 


def numberToNote(num):
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    return notes[num%12]

def readFromInput(input_id):
    input_device = pygame.midi.Input(input_id)

    while True:
        if input_device.poll():
            # event = input_device.read(1)
            # print(event)
            event = input_device.read(1)[0] 
            data = event[0] # midi info
            timestamp = event[1] # timestamp
            note = numberToNote(data[1])
            velocity = data[2]
            print("note: {}, velocity: {}, timestamp: {}".\
                format(note, velocity, timestamp))


def main():

    pygame.init()

    pygame.fastevent.init()
    event_get = pygame.fastevent.get
    event_post = pygame.fastevent.post

    pygame.midi.init()

    # # prints connected midi devices
    # for n in range(pygame.midi.get_count()):
    #     # (interf, name, input, output, opened) 
    #     print(n,pygame.midi.get_device_info(n))

    input_id = pygame.midi.get_default_input_id() # gets the first connected device
    print("midi input device: {}".format(pygame.midi.get_device_info(input_id)))

    readFromInput(input_id)
    
    return

    going = True

    while going:

            events = event_get()
            for e in events:
                    if e.type in [QUIT]:
                            going = False
                    if e.type in [KEYDOWN]:
                            going = False

            if i.poll():
                    midi_events = i.read(10)
                    if int(midi_events[0][0][0]) in [224,225,226]:#Pitch Bender
                            print(str(midi_events[0][0][2]))#right(0)  center(64)  left(124)
                            
                    #print "full midi_events " + str(midi_events)
                        #print "my midi note is " + str(midi_events[0][0][1])
                    # converts midi events to pygame events
                    midi_evs = pygame.midi.midis2events(midi_events, i.device_id)

                    for m_e in midi_evs:
                            event_post(m_e)

    print("exit button clicked.")
    i.close()
    pygame.midi.quit()
    pygame.quit()
    exit()

if __name__ == '__main__':
    main()
"""
reads num_events midi events from the buffer.
Input.read(num_events): return midi_event_list
Reads from the Input buffer and gives back midi events. [[[status,data1,data2,data3],timestamp],
 [[status,data1,data2,data3],timestamp],...]
"""