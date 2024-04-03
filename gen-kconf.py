#!/usr/bin/env python3

import argparse
import yaml
import jinja2
import multiprocessing


def set_value(val: str | None, key: str, data: dict[str, str]) -> None:
    if val is not None:
        data[key] = val


def main() -> None:
    cmdline_parser = argparse.ArgumentParser(
        description="Generate the ktest.conf script"
    )

    cmdline_parser.add_argument(
        "-r",
        "--root-directory",
        dest="root_dir",
        metavar="DIR",
        action="store",
        default=None,
        help="the root directory",
    )

    cmdline_parser.add_argument(
        "-m",
        "--machine",
        dest="machine",
        metavar="MACHINE",
        action="store",
        default=None,
        help="the target machine host name",
    )

    cmdline_parser.add_argument(
        "-d",
        "--duration",
        dest="duration",
        metavar="DURATION",
        action="store",
        default=None,
        help="The duration to run the benchmark for each test case",
    )

    cmdline_parser.add_argument(
        "-c",
        "--cfg",
        dest="cfg",
        metavar="CFG",
        action="store",
        default="kconf.yml",
        help="Path to the configuration file containing the data to the template",
    )

    cmdline_parser.add_argument(
        "-k",
        dest="renew_krb_ticket",
        action="store_true",
        help="Renew the kerberos ticket after each test",
    )

    cmdline_parser.add_argument(
        "--kernel-config",
        dest="kernel_config",
        metavar="CONFIG",
        action="store",
        default="config",
        help="Path to the kernel .config file",
    )

    cmdline_parser.add_argument(
        "-t",
        "--linux-tree",
        dest="build_dir",
        metavar="DIR",
        action="store",
        help="Path to the linux tree",
    )

    args = cmdline_parser.parse_args()

    with open(args.cfg, "r") as f:
        data = yaml.load(f, yaml.SafeLoader)

    set_value(args.root_dir, "root_dir", data)
    set_value(args.machine, "machine", data)
    set_value(args.duration, "duration", data)
    set_value(args.renew_krb_ticket, "renew_krb_ticket", data)
    set_value(args.build_dir, "build_dir", data)
    set_value(args.kernel_config, "config", data)

    data["host_cpus"] = multiprocessing.cpu_count()

    loader = jinja2.FileSystemLoader("templates")
    env = jinja2.Environment(
        lstrip_blocks=True,
        trim_blocks=True,
        undefined=jinja2.StrictUndefined,
        optimized=True,
        loader=loader,
    )

    template = env.get_template("ktest.conf.j2")

    kconf = template.render(data)
    with open("ktest.conf", "w") as f:
        f.write(kconf)


if __name__ == "__main__":
    main()
