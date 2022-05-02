#!/usr/bin/env python3

import argparse
import yaml
import jinja2
import multiprocessing


def main():
    cmdline_parser = argparse.ArgumentParser(
        description='Generate the ktest.conf script')

    cmdline_parser.add_argument('-r',
                                '--root-directory',
                                dest='root_dir',
                                metavar='DIR',
                                action='store',
                                default=None,
                                help='the root directory')

    cmdline_parser.add_argument('-m',
                                '--machine',
                                dest='machine',
                                metavar='MACHINE',
                                action='store',
                                default=None,
                                help='the target machine host name')

    args = cmdline_parser.parse_args()

    with open('kconf.yml', 'r') as f:
        data = yaml.load(f, yaml.SafeLoader)

    if args.root_dir is not None:
        data['root_dir'] = args.root_dir

    if args.machine is not None:
        data['machine'] = args.machine

    data['host_cpus'] = multiprocessing.cpu_count()

    loader = jinja2.FileSystemLoader('templates')
    env = jinja2.Environment(lstrip_blocks=True,
                             trim_blocks=True,
                             undefined=jinja2.StrictUndefined,
                             optimized=True,
                             loader=loader)

    template = env.get_template('ktest.conf.j2')

    repos = data['repos']
    for repo in filter(lambda r: repos[r]['versions'], repos):
        kconf = template.render(data, repo=repo)
        with open(f'ktest-{repo}.conf', 'w') as f:
            f.write(kconf)


if __name__ == '__main__':
    main()
