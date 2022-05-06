#!/usr/bin/env python3

import bcc
import subprocess
import sys
import signal
import re
import json
import argparse
import os.path
import resource

prog = """
#include <linux/sched.h>

struct lb_info {
    // the time it took in the load_balancer() call,
    // in nanoseconds
    u64 delay; 
};

// hold percpu integer data
BPF_PERCPU_HASH(local_cpu_data);

BPF_HASH(ct_running, int, int);

// the key to access the load_balancer() timestamp
#define LB_TS_KEY 0

BPF_PERF_OUTPUT(events);
BPF_PERF_OUTPUT(stop);
BPF_PERF_OUTPUT(start);

static inline void send_stop(void *ctx)
{
    int dummy = 0;
    stop.perf_submit(ctx, &dummy, sizeof(dummy));
}

static inline void send_start(void *ctx)
{
    int dummy = 0;
    start.perf_submit(ctx, &dummy, sizeof(dummy));
}

// returns true if the current task is cyclictest
static inline int is_curr_task_cyclictest(void)
{
    const char compare[] = "cyclictest";
    char comm[TASK_COMM_LEN];

    if (bpf_get_current_comm(comm, sizeof(comm)))
        return 0;
    
    for (int i = 0; i < sizeof(compare); ++i)
        if (compare[i] != comm[i])
            return 0;

    return 1;
}

static inline u64 is_cyclictest_running()
{
    int key = 0;
    int zero = 0;
    int *running = ct_running.lookup_or_try_init(&key, &zero);
    return running && *running;
}

static inline void set_cyclictest_running(int val)
{
    int key = 0;
    ct_running.update(&key, &val);
}

int do_ret_sys_execve(struct pt_regs *ctx)
{
    if (is_curr_task_cyclictest()) {
        set_cyclictest_running(1);
        send_start(ctx);
    }

    return 0;
}

int syscall__exit(struct pt_regs *ctx)
{
    if (is_cyclictest_running() && is_curr_task_cyclictest()) {
        set_cyclictest_running(0);
        send_stop(ctx);
    }

    return 0;
}

int kfunc__newidle_balance(struct pt_regs *ctx)
{
    if (!is_cyclictest_running())
        return 0;

    u64 ts = bpf_ktime_get_ns();
    u64 key = LB_TS_KEY;
    local_cpu_data.update(&key, &ts);
    return 0;
}

int kretfunc__newidle_balance(struct pt_regs *ctx)
{
    if (!is_cyclictest_running())
        return 0;

    u64 key = LB_TS_KEY;
    u64 *ts = local_cpu_data.lookup(&key);
    if (!ts)
        return 0;

    struct lb_info data = {
        .delay = bpf_ktime_get_ns() - *ts,
    };

    events.perf_submit(ctx, &data, sizeof(data));

    local_cpu_data.delete(&key);

    return 0;
}
"""


class Tracer(object):

    def __init__(self, trace_callback):
        b = bcc.BPF(text=prog)
        b.get_syscall_fnname('execve')
        b.attach_kretprobe(event=b.get_syscall_fnname('execve'),
                           fn_name=b'do_ret_sys_execve')
        b.attach_kprobe(event=b.get_syscall_fnname('exit'),
                        fn_name=b'syscall__exit')
        b['events'].open_perf_buffer(self._on_lb_trace)
        b['stop'].open_perf_buffer(self._on_stop)
        b['start'].open_perf_buffer(self._on_start)
        self.b = b
        self.quit = False
        self.trace_cb = trace_callback

    def loop(self):
        try:
            while not self.quit:
                self.b.perf_buffer_poll()
        except KeyboardInterrupt:
            pass

    def _on_lb_trace(self, cpu, data, size):
        evt = self.b['events'].event(data)
        self.trace_cb(evt.delay)

    def _on_start(self, cpu, data, size):
        print('Starting tracer...')

    def _on_stop(self, cpu, data, size):
        print('Stopping tracer...')
        self.quit = True


class RtEval(object):

    class ExitError(BaseException):

        def __init__(self, exitcode):
            self.returncode = exitcode

        def __str__(self):
            if self.returncode < 0:
                return f'Process received {self._get_signal_name()}'
            else:
                return f'Process returned with status {self.returncode}'

        def _get_signal_name(self):
            val = -self.returncode
            for s in dir(signal):
                if s.startswith('SIG') and getattr(signal, s) == val:
                    return s

    def __init__(self, duration, rteval='/usr/bin/rteval'):
        self.p = subprocess.Popen(args=[rteval, '-d', duration],
                                  stdout=subprocess.PIPE,
                                  stderr=sys.stderr,
                                  universal_newlines=True)

    def wait(self):
        return self.p.communicate()[0]


class RtEvalOutputParser(object):
    """Parse the rteval otuput."""

    # Pairs of field name and field value convertion function
    # if the field value if an string, use None for the convertion
    # function
    header_fields = (('Model:', None), ('BIOS version:', None),
                     ('CPU cores:',
                      lambda x: int(x.split(':')[1].strip()[:-1])),
                     ('NUMA Nodes:', int), ('Kernel:', None), ('Cmdline:',
                                                               None))

    cpu_re = re.compile(r'CPU core (\d+)\s+Priority: (\d+)')

    def __init__(self, output):
        """Initialize the object and parse the output.

        output is a string containing the stdout of the rteval process.
        """
        self.output = {}
        self._lines = output.splitlines()
        self._lines.reverse()
        self._parse_header()

        self._skip_lines('System:')
        self.output['statistics'] = {}

        stat = self._parse_statistics()
        # depending on the number of CPUs, rteval may suppress statistics
        if stat:
            self.output['statistics']['system'] = stat

            self.output['statistics']['cpus'] = [None
                                                 ] * self.output['cpuCores']
            cpu = self._find_core_field()
            while cpu != -1:
                self.output['statistics']['cpus'][
                    cpu] = self._parse_statistics()
                cpu = self._find_core_field()

    def _parse_header(self):
        processed = 0  # counts the number of processed fields

        # find a field of interest, return a pair
        # of field name and field value.
        # Returns None, None if no field was found
        def find_field(line):
            for f, c in self.header_fields:
                if line.startswith(f):
                    fields = line.split(':')
                    field = fields[0]
                    value = ':'.join(fields[1:]).strip()
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

    def _parse_statistics(self):
        self._skip_lines('Statistics:')

        stat = {}
        while True:
            line = self.pop()
            try:
                field, value = line.split(':')
            except ValueError:
                return stat

            stat[self._jsonfy_field_name(field)] = self._parse_statistic_value(
                value)

    def _find_core_field(self):
        """Find a field that match the 'CPU core #number' line."""
        while True:
            try:
                m = self.cpu_re.search(self.pop())
            except IndexError:
                return -1
            if m is not None:
                return int(m.group(1))

    def _jsonfy_field_name(self, field):
        """Convert a field name in the json naming pattern."""
        names = field.strip().replace('.', ' ').lower().split()
        return ''.join([names[0]] +
                       list(map(lambda x: x.capitalize(), names[1:])))

    def _skip_lines(self, key):
        """Skip lines until find one that matches the key."""
        while True:
            if self.pop() == key:
                return

    def _parse_statistic_value(self, val):
        val = val.strip()
        if not val.endswith('us'):
            return int(val)
        val = val[:-2]
        return float(val) if val.find('.') != -1 else int(val)

    def pop(self):
        return self._lines.pop().strip()


class Main(object):

    def __init__(self):
        cmdline_parser = argparse.ArgumentParser(
            description='Run the rteval benchmark')

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

        self.args = cmdline_parser.parse_args()

        self.measurements = []
        self.tracer = Tracer(self._lb_callback)
        self.rteval = RtEval(self.args.duration)

    def wait(self):
        self.tracer.loop()
        parser = RtEvalOutputParser(self.rteval.wait())
        o = parser.output
        o['loadBalanceTimes'] = self.measurements
        kernel = o['kernel']
        num_cpus = o['cpuCores']
        filename = f'{kernel}_{num_cpus}cpus.json'
        with open(os.path.join(self.args.output_dir, filename), 'w') as f:
            json.dump(o, f, indent=2)

    def _lb_callback(self, measurement):
        self.measurements.append(measurement)


if __name__ == '__main__':
    main = Main()
    main.wait()
