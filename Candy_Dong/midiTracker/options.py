import os
import argparse


def get_options(args=None):
    parser = argparse.ArgumentParser()

    parser.add_argument('--score', help="name of score", type=str, required=True)
    parser.add_argument('--static_dir', help="directory saving all static files", type=str, default="../static/")
    parser.add_argument('--window', help="adjust the agility of MIDI matching", default=5, type=int)

    opts = parser.parse_args(args)

    if not os.path.exists(opts.static_dir):
        os.mkdir(opts.static_dir)

    return opts
