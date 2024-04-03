#!/usr/bin/env python3

import subprocess
import sys
import signal
import re
import json
import argparse
import os.path


class RtEval:

    class ExitError(BaseException):

        def __init__(self, exitcode: int) -> None:
            self.returncode = exitcode

        def __str__(self) -> str:
            if self.returncode < 0:
                return f"Process received {self._get_signal_name()}"
            return f"Process returned with status {self.returncode}"

        def _get_signal_name(self) -> str:
            val = -self.returncode
            for s in dir(signal):
                if s.startswith("SIG") and getattr(signal, s) == val:
                    return s
            return "unknown signal"

    def __init__(self, duration, rteval="/usr/bin/rteval") -> None:
        self.p = subprocess.Popen(
            args=[rteval, "-d", duration],
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            universal_newlines=True,
        )

    def wait(self) -> str:
        return self.p.communicate()[0]


class RtEvalOutputParser:
    """Parse the rteval otuput."""

    # Pairs of field name and field value convertion function
    # if the field value if an string, use None for the convertion
    # function
    header_fields = (
        ("Model:", None),
        ("BIOS version:", None),
        ("CPU cores:", lambda x: int(x.split(":")[1].strip()[:-1])),
        ("NUMA Nodes:", int),
        ("Kernel:", None),
        ("Cmdline:", None),
    )

    cpu_re = re.compile(r"CPU core (\d+)\s+Priority: (\d+)")

    def __init__(self, output: str) -> None:
        """Initialize the object and parse the output.

        output is a string containing the stdout of the rteval process.
        """
        self.output = {}
        self._lines = output.splitlines()
        self._lines.reverse()
        self._parse_header()

        self._skip_lines("System:")
        self.output["statistics"] = {}

        stat = self._parse_statistics()
        # depending on the number of CPUs, rteval may suppress statistics
        if stat:
            self.output["statistics"]["system"] = stat

            self.output["statistics"]["cpus"] = [None] * self.output["cpuCores"]
            cpu = self._find_core_field()
            while cpu != -1:
                self.output["statistics"]["cpus"][cpu] = self._parse_statistics()
                cpu = self._find_core_field()

    def _parse_header(self) -> None:
        processed = 0  # counts the number of processed fields

        # find a field of interest, return a pair
        # of field name and field value.
        # Returns None, None if no field was found
        def find_field(line):
            for f, c in self.header_fields:
                if line.startswith(f):
                    fields = line.split(":")
                    field = fields[0]
                    value = ":".join(fields[1:]).strip()
                    if c is not None:
                        value = c(value)
                    return field, value

            return None, None

        while True:
            field, value = find_field(self.pop())
            if field is not None:
                self.output[self._jsonfy_field_name(field)] = value
                processed += 1
                if processed == len(self.header_fields):
                    return

    def _parse_statistics(self) -> dict:
        self._skip_lines("Statistics:")

        stat = {}
        while True:
            line = self.pop()
            try:
                field, value = line.split(":")
            except ValueError:
                return stat

            stat[self._jsonfy_field_name(field)] = self._parse_statistic_value(value)

    def _find_core_field(self) -> int:
        """Find a field that match the 'CPU core #number' line."""
        while True:
            try:
                m = self.cpu_re.search(self.pop())
            except IndexError:
                return -1
            if m is not None:
                return int(m.group(1))

    def _jsonfy_field_name(self, field: str) -> str:
        """Convert a field name in the json naming pattern."""
        names = field.strip().replace(".", " ").lower().split()
        return "".join([names[0]] + [x.capitalize() for x in names[1:]])

    def _skip_lines(self, key: str) -> None:
        """Skip lines until find one that matches the key."""
        while True:
            if self.pop() == key:
                return

    def _parse_statistic_value(self, val: str) -> float:
        val = val.strip()
        if not val.endswith("us"):
            return int(val)
        val = val[:-2]
        return float(val) if val.find(".") != -1 else int(val)

    def pop(self) -> str:
        return self._lines.pop().strip()


class Main:

    def __init__(self) -> None:
        cmdline_parser = argparse.ArgumentParser(description="Run the rteval benchmark")

        cmdline_parser.add_argument(
            "-d",
            "--duration",
            dest="duration",
            action="store",
            metavar="TIME",
            default="1h",
            help="test duration (the same format as rteval)",
        )

        cmdline_parser.add_argument(
            "-o",
            "--output-dir",
            dest="output_dir",
            action="store",
            metavar="DIR",
            default="/root",
            help="directory where to save the results",
        )

        cmdline_parser.add_argument(
            "-n",
            "--num-measurements",
            dest="n",
            action="store",
            metavar="N",
            default=100000,
            type=int,
            help="The number of measurements to collect. It keeps the N largest measurements",
        )

        self.args = cmdline_parser.parse_args()
        subprocess.run(
            "echo 1 > /sys/kernel/debug/lb_profiler/sampling", check=True, shell=True
        )
        self.rteval = RtEval(self.args.duration)

    def wait(self) -> None:
        parser = RtEvalOutputParser(self.rteval.wait())
        subprocess.run(
            "echo 0 > /sys/kernel/debug/lb_profiler/sampling", check=True, shell=True
        )
        o = parser.output
        o["loadBalanceTimes"] = [
            int(x) for x in open("/sys/kernel/debug/lb_profiler/samples", "r")
        ]
        kernel = o["kernel"]
        num_cpus = o["cpuCores"]
        filename = f"{kernel}_{num_cpus}cpus.json"
        with open(os.path.join(self.args.output_dir, filename), "w") as f:
            json.dump(o, f, indent=2)


if __name__ == "__main__":
    main = Main()
    main.wait()
