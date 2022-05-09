This set of scripts run a benchmark test on the kernel load balancer.

What we analyze is the maximum time the load_balance function takes when called
from the newidle_balance (the CPU is about to sleep, then the scheduler calls
newidle_balance to try to pick running tasks from other CPUs).

Since the load balancer runs with interrupts disabled, it may impose significant
latency times when there are a reasonable big number of CPUs and under the
perfect storm.

We use [ktest](https://elinux.org/Ktest) to run the benchmark in several kernel
versions and number of CPUs.

Source tree
-----------

* configs/: this folder contains the base kernel config files.

* templates/: contains the jinja2 template files.

* scripts/: utility scripts

* repos/: upstream repos submodules.

* lb_bench.py: this is the script that runs the benchmark and saves the the
  results in a json file.

* gen-kconf.py: generate the configuration filew to use with ktest

* kconf.yml: input data file for the jinja template.

Running
-------

On the host machine:

* `git submodule update --init`

* `./gen-kconf.py --machine <target-machine-name>`

* `./ktest.pl ktest_confs/<ktest-file>`

