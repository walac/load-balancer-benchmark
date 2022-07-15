#!/usr/bin/local python3

import lb_bench as ben
import argparse
import sys


class Main(object):

    def __init__(self):
        cmdline_parser = argparse.ArgumentParser(description='Run bisect test')

        cmdline_parser.add_argument(
            '-d',
            '--duration',
            dest='duration',
            action='store',
            metavar='TIME',
            default='1h',
            help='test duration (the same format as rteval)')

        cmdline_parser.add_argument('-o',
                                    '--output-dir',
                                    dest='output_dir',
                                    action='store',
                                    metavar='DIR',
                                    default='/root',
                                    help='directory where to save the results')

        cmdline_parser.add_argument(
            '-n',
            '--num-measurements',
            dest='n',
            action='store',
            metavar='N',
            default=100000,
            type=int,
            help=
            'The number of measurements to collect. It keeps the N largest measurements'
        )

        cmdline_parser.add_argument(
            '-t',
            '--threshold',
            dest='threshold',
            action='store',
            metavar='THRES',
            type=int,
            help='Threshold value in us to define if the latency was too high')

        self.args = cmdline_parser.parse_args()

        self.runner = ben.Runner(self.args.duration, self.args.n)

    def wait(self):
        self.runner.wait()
        return int(self.runner.acc.mean() / 1000 >= self.args.threshold)


if __name__ == '__main__':
    main = Main()
    sys.exit(main.wait())
