import sys
import os
import time
import argparse
from oc import OC
from define import alameda_installed, interactive_mode
from define import traffic_interval, data_interval, number_k8shpa, number_alamedahpa
from define import warm_up, number_nonhpa
from run_hpa import get_dir_name, disable_executor, find_app_location, update_yaml
from run_hpa import find_pod_name, find_alameda_namespace, restart_pod, stop_k8shpa, check_metric_server
from generate_report import main as generate_report


def start_algo(algo, app_name):
    print "start algorithm (%s) for %s" % (algo, app_name)
    cmd = "python ./run_hpa.py %s start & " % (algo)
    ret = os.system(cmd)
    return ret


def stop_algo(algo, app_name):
    print "stop algorithm (%s) for %s" % (algo, app_name)
    cmd = "python ./run_hpa.py %s stop & " % (algo)
    ret = os.system(cmd)
    return ret


def init_algo(algo, app_name):
    print "init algorithm (%s) for %s" % (algo, app_name)
    cmd = "python ./run_hpa.py %s init & " % (algo)
    ret = os.system(cmd)
    return ret


def write_logs(algo_name, app_name):
    print "write logs for %s" % app_name
    cmd = "python ./write_log.py %s %d &" % (algo_name, data_interval)
    ret = os.system(cmd)
    return ret


def generate_traffic(app_name, action, interval):
    print "generate traffic for %s" % app_name
    cmd = "python ./generate_traffic1.py %d %s &" % (interval, action)
    ret = os.system(cmd)
    return ret


def wait_time(count):
    # print "wait %d seconds" % count
    time.sleep(count)


def run_scenario(test_case, app_name, i):
    algo = test_case
    if test_case == "federator.ai":
        algo = "alameda"

    # Prepare initial replicas
    print "--- Init to run HPA Test(%s): %d ---" % (algo, i)
    print "Preparing initial replicas..."
    init_algo(algo, app_name)
    wait_time(120)   # give sometime to wait replicas running

    # Warm up
    generate_traffic(app_name, "init", warm_up)
    wait_time(warm_up*60)
    print "======================================================\n\n"

    # Start workload
    print "\n%s" % time.ctime()
    print "--- Start to Run HPA Test(%s): %d ---" % (algo, i)
    generate_traffic(app_name, "start", traffic_interval)

    # Start algorithm
    start_algo(algo, app_name)

    # Start monitoring
    algo_name = get_dir_name(algo)
    write_logs(algo_name, app_name)
    wait_time((data_interval+2)*60)

    # Stop algorithm
    wait_time(120)
    print "Stop to Run HPA Test(%s)" % (algo)
    stop_algo(algo, app_name)
    wait_time(60)


def get_test_case_list():
    test_case_list = []
    for i in range(number_k8shpa):
        test_case_list.append("k8shpa")
    for i in range(number_alamedahpa):
        j = 2 * i + 1
        test_case_list.insert(j, "federator.ai")
    for i in range(number_nonhpa):
        test_case_list.insert(i, "nonhpa")
    print "the order of algorithms is: ", ",".join(test_case_list)
    return test_case_list


def main(app_name):
    print "=== HPA Test ==="
    print "--- Start to Run K8sHPA Test x %d and Federator.ai Test x %d ---" % (number_k8shpa, number_alamedahpa)
    start_time = time.time()
    i = 0
    test_case_list = get_test_case_list()
    for test_case in test_case_list:
        run_scenario(test_case, app_name, i)

    generate_report(["table"])
    end_time = time.time()
    duration = (end_time - start_time)/60
    print "It takes %d minutes" % duration


def kill_process():
    kill_process_list = ["write_log.py", "generate_traffic1.py", "run_ab.py", "run_hpa.py", "train_traffic.py", "run_alameda_hpa.py"]
    cmd = "ps aux | grep python"
    output = os.popen(cmd).read()
    for line in output.split("\n"):
        for process in kill_process_list:
            if line.find(process) != -1:
                pid = line.split()[1]
                cmd = "kill -9 %s" % pid
                # print cmd, process
                os.system(cmd)
    cmd = "killall -9 python"
    os.system(cmd)
    cmd = "killall -9 ab"
    os.system(cmd)


def check_execution(app_name):
    ret = 0
    print "\n"
    print "*******************************************************************"
    print "  Notice:                                                        "
    print "    The script would do the following actions:           "
    print "    1) Update %s cpu limit to 200m                       " % app_name
    print "    2) Scale up/down %s replicas by K8s HPA or Federator.ai    " % app_name
    print "    3) Use Apache Benchmark to forward traffic to %s's service " % app_name
    print "    4) Collect data and write logs to ./metrics                "
    print "    5) Generate the summary and related pictures to ./pictures "
    print "*******************************************************************\n"

    x = raw_input("Are you sure to run the test? (y/n): ")
    if x not in ["y", "Y"]:
        ret = -1
    print "\n"
    return ret


def check_environment(app_name):
    check_metric_server()
    app_namespace, app_type, resource = find_app_location(app_name)
    stop_k8shpa(app_namespace, resource)

    if alameda_installed:
        alameda_namespace = find_alameda_namespace("alameda-executor")
        pod_name = find_pod_name("alameda-executor", alameda_namespace)[0]
        pod_name = find_pod_name("alameda-recommender", alameda_namespace)[0]
        update_yaml(alameda_namespace, "true")
        update_yaml(alameda_namespace, "false")
        disable_executor()
        restart_pod("alameda-executor", alameda_namespace)


def do_main(args):
    app_name = args.app_name[0]
    # ret = OC().check_platform()
    # if ret == 0:
    #     user = args.user[0]
    #     passwd = args.password[0]
    #     OC().login(user, passwd)

    if interactive_mode:
        ret = check_execution(app_name)
        if ret != 0:
            print "exit"
            return 0

    try:
        check_environment(app_name)
        main(app_name)
    except KeyboardInterrupt:
        print "pgogram exit with keyboard interrupt"
        kill_process()
    except Exception as e:
        print "failed to test HPA: %s" % str(e)
        kill_process()
    return 0


def main_proc(argv):
    # ret = OC().check_platform()
    # if ret == 0:
    #     commands = [(do_main, "hpa", "Run HPA Test", [("app_name", "application name (deployment/deploymentconfig name)"), ("user", "login user name"), ("password", "password for login user")])]
    # else:
    commands = [(do_main, "hpa", "Run HPA Test", [("app_name", "application name (deployment/deploymentconfig name)")])]

    try:
        parser = argparse.ArgumentParser(prog="", usage=None, description="Federator.ai management tool", version=None, add_help=True)
        parser.print_usage = parser.print_help
        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit(1)

        # subparsers for commands
        subparsers = parser.add_subparsers(help="commands")

        for function, title, desc, args_list in commands:
            # format: (function_name, parser_name, parser_desc, [(args1, args1_desc), (args2, args2_desc), ...])
            # Add command parser
            p = subparsers.add_parser(title, help=desc)
            p.set_defaults(function=function)
            for arg, arg_desc in args_list:
                p.add_argument(arg, nargs=1, help=arg_desc)

        # Run the function
        args = parser.parse_args()
        retcode = args.function(args)  # args.function is the function that was set for the particular subparser
    except ValueError as e:
        print("Error in argument parsing. [%s]" % e)
        sys.exit(-1)

    sys.exit(retcode)


if __name__ == "__main__":
    main_proc(sys.argv)
