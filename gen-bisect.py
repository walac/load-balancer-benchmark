#!/usr/bin/env python3

import argparse
import jinja2
import multiprocessing
import os.path
import os


def main():
    cmdline_parser = argparse.ArgumentParser(
        description='Generate the bisect.conf script')

    cmdline_parser.add_argument('-r',
                                '--root-directory',
                                dest='root_dir',
                                metavar='DIR',
                                action='store',
                                default=os.getcwd(),
                                help='the root directory')

    cmdline_parser.add_argument('-m',
                                '--machine',
                                dest='machine',
                                metavar='MACHINE',
                                action='store',
                                required=True,
                                help='the target machine host name')

    cmdline_parser.add_argument('-c',
                                '--config',
                                dest='config',
                                action='store',
                                metavar='CONFIG',
                                required=True,
                                help='Path to the kernel config file')

    cmdline_parser.add_argument(
        '-d',
        '--duration',
        dest='duration',
        metavar='DURATION',
        action='store',
        required=True,
        help='The duration to run the benchmark for each test case')

    cmdline_parser.add_argument(
        '-o',
        '--output-dir',
        dest='output_dir',
        metavar='DIR',
        action='store',
        default='ktest_confs',
        help='Output directory of the ktest config files')

    cmdline_parser.add_argument(
        '-k',
        dest='renew_krb_ticket',
        action='store_true',
        help='Renew the kerberos ticket after each test')

    cmdline_parser.add_argument('-e',
                                '--repo-path',
                                dest='repo',
                                metavar='REPO',
                                action='store',
                                required=True,
                                help='Path to the kernel repository')

    cmdline_parser.add_argument('-g',
                                '--good',
                                dest='good',
                                metavar='SHA1|TAG|BRANCH',
                                action='store',
                                required=True,
                                help='First good commit')

    cmdline_parser.add_argument('-b',
                                '--bad',
                                dest='bad',
                                metavar='SHA1|TAG|BRANCH',
                                action='store',
                                required=True,
                                help='First bad commit')

    cmdline_parser.add_argument(
        '-t',
        '--threshold',
        dest='threshold',
        action='store',
        metavar='THRES',
        required=True,
        type=int,
        help='Threshold value in us to define if the latency was too high')

    args = cmdline_parser.parse_args()

    loader = jinja2.FileSystemLoader('templates')
    env = jinja2.Environment(lstrip_blocks=True,
                             trim_blocks=True,
                             undefined=jinja2.StrictUndefined,
                             optimized=True,
                             loader=loader)

    template = env.get_template('bisect.conf.j2')

    kconf = template.render(log_dir=os.path.abspath('logs'),
                            repo=args.repo,
                            host_cpus=multiprocessing.cpu_count(),
                            config=args.config,
                            machine=args.machine,
                            good=args.good,
                            bad=args.bad,
                            duration=args.duration,
                            renew_krb_ticket=args.renew_krb_ticket,
                            threshold=args.threshold)

    with open(f'{args.output_dir}/bisect.conf', 'w') as f:
        f.write(kconf)


if __name__ == '__main__':
    main()
