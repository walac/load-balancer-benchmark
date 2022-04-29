import lb_bench

sample_output = \
"""
got system topology: 1 node system (8 cores per node)
rteval run on 5.16.20-200.fc35.x86_64 started at Fri Apr 22 10:34:53 2022
started 3 loads on 8 cores 
started measurement threads on 8 cores
Run duration: 10.0 seconds
stopping run at Fri Apr 22 10:36:28 2022
  ===================================================================
   rteval (v3.1) report
  -------------------------------------------------------------------
   Test run:     2022-04-22 10:34:42
   Run time:     0 days 0h 1m 4s


   Tested node:  fedora
   Model:        Dell Inc. - Precision T1700
   BIOS version: Dell Inc. (ver: A08, rev :4.6, release date: 04/25/2014)

   CPU cores:    2 (online: 2)
   NUMA Nodes:   1
   Memory:       23969.984 MB
   Kernel:       5.16.20-200.fc35.x86_64
   Base OS:      Fedora release 35 (Thirty Five)
   Architecture: x86_64
   Clocksource:  tsc
   Available:    tsc hpet acpi_pm 

   System load:
       Load average: 196.34

       Executed loads:
         - kcompile: numactl --cpunodebind 0 make O=/home/wcosta/work/ktest/rteval-build/node0 -C /home/wcosta/work/ktest/rteval-build/linux-5.7 -j16 bzImage modules;
         - hackbench: hackbench -P -g 24 -l 1000 -s 1000

 Cmdline:        BOOT_IMAGE=(hd0,msdos1)/vmlinuz-5.16.20-200.fc35.x86_64

   Measurement profile 1: With loads, measurements in parallel
       Latency test
          Started: 2022-04-22 10:35:23.799678
          Stopped: 2022-04-22 10:36:23.983301
          Command: cyclictest  -qmu -h 2000 -p95 -t -a

          System:  
          Statistics: 
            Samples:           476376
            Mean:              8.0us
            Median:            6us
            Mode:              7us
            Range:             1975us
            Min:               3us
            Max:               1978us
            Mean Absolute Dev: 3.0us
            Std.dev:           34.0us

          CPU core 0       Priority: 95
          Statistics: 
            Samples:           59476
            Mean:              7.0us
            Median:            6us
            Mode:              6us
            Range:             1884us
            Min:               3us
            Max:               1887us
            Mean Absolute Dev: 2.0us
            Std.dev:           33.0us

          CPU core 1       Priority: 95
          Statistics: 
            Samples:           59531
            Mean:              7.0us
            Median:            0.0us
            Mode:              6us
            Range:             1858us
            Min:               3us
            Max:               1861us
            Mean Absolute Dev: 1.0us
            Std.dev:           21.0us


  ===================================================================
"""

expected = {
    'model': 'Dell Inc. - Precision T1700',
    'biosVersion': 'Dell Inc. (ver: A08, rev :4.6, release date: 04/25/2014)',
    'cpuCores': 2,
    'numaNodes': 1,
    'kernel': '5.16.20-200.fc35.x86_64',
    'cmdline': 'BOOT_IMAGE=(hd0,msdos1)/vmlinuz-5.16.20-200.fc35.x86_64',
    'statistics': {
        'system': {
            'samples': 476376,
            'mean': 8.0,
            'median': 6,
            'mode': 7,
            'range': 1975,
            'min': 3,
            'max': 1978,
            'meanAbsoluteDev': 3.0,
            'stdDev': 34.0,
        },
        'cpus': [
            {
                'samples': 59476,
                'mean': 7.0,
                'median': 6,
                'mode': 6,
                'range': 1884,
                'min': 3,
                'max': 1887,
                'meanAbsoluteDev': 2.0,
                'stdDev': 33.0,
            },
            {
                'samples': 59531,
                'mean': 7.0,
                'median': 0.0,
                'mode': 6,
                'range': 1858,
                'min': 3,
                'max': 1861,
                'meanAbsoluteDev': 1.0,
                'stdDev': 21.0,
            },
        ],
    },
}


def test_lb_bench():
    parser = lb_bench.RtEvalOutputParser(sample_output)
    assert parser.output == expected
