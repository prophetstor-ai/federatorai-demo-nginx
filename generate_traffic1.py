import os
import time
import sys
from define import warm_up


def init_traffic():
    print "--- Warm Up: %d Minutes ---" % warm_up
    for i in range(warm_up):
        print "warm up: generate %d/%d workloads" % (i, warm_up)
        start_time = time.time()
        cmd = "python ./run_ab.py %d &" % (0)
        ret = os.system(cmd)
        count = 0
        while True:
            end_time = time.time()
            if end_time - start_time >= 60:
                # print "go to next interval..."
                break
            count += 1
            # print "wait 1 seconds", count
            time.sleep(1)


def generate_traffic(time_count):
    print "--- Generate Traffic For %d Munites ---" % time_count
    for i in range(time_count):
        print "generate %d th workloads" % i
        start_time = time.time()
        cmd = "python ./run_ab.py %d &" % (i)
        ret = os.system(cmd)
        count = 0
        while True:
            end_time = time.time()
            if end_time - start_time >= 60:
                # print ("go to next interval...")
                break
            count += 1
            # print "wait 1 seconds", count
            time.sleep(1)


def main(time_count, action):
    total_start_time = time.time()
    print "=== Generate Traffic for %d Minutes ===" % time_count

    if action == "init":
        init_traffic()

    else:
        generate_traffic(time_count)

    total_end_time = time.time()
    print "completed!!!", (total_end_time - total_start_time)/60, "minutes"


if __name__ == "__main__":
    try:
        time_count = int(sys.argv[1])
        action = sys.argv[2]
        main(time_count, action)
    except Exception as e:
        print "failed to generate traffic: %s" % str(e)
