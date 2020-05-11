import sys
import time
import os
import math
from define import training_interval, overprovision_replica
from kubectl import Kubectl
from oc import OC
from run_ab import Nginx
from run_main import kill_process, check_environment
from run_hpa import create_directory, find_app_location, clean_data, restart_pod, find_pod_name, update_app_limit

# test metrics by target server: 172.31.5.135
target_avg_node = 19
target_avg_pod = 36
target_avg_connect_latency = 5
target_ratio = 4000
a = 44.56
b = -123.73


class Training:
    k = Kubectl()
    o = OC()
    n = Nginx()

    def __init__(self):
        #self.o.login("admin", "password")
        test = ""

    def get_node_list(self):
        node_list = []
        output = self.o.get_nodes()
        for line in output.split("\n"):
            if line.find("NAME") == -1 and line:
                node_name = line.split()[0]
                node_list.append(node_name)
        return node_list

    def get_node_usage(self):
        # kubectl top node h5-135
        # NAME      CPU(cores)   CPU%      MEMORY(bytes)   MEMORY%
        # h5-135    655m         8%        5703Mi          17%
        node_usage = {}
        node_usage["cpu"] = {}
        node_usage["memory"] = {}
        node_list = self.get_node_list()
        for node in node_list:
            output = self.k.top_node(node)
            for line in output.split("\n"):
                if line.find("NAME") == -1 and line:
                    cpu_usage = int(line.split()[2].split("%")[0])
                    memory_usage = int(line.split()[-1].split("%")[0])
                    node_usage["cpu"][node] = cpu_usage
                    node_usage["memory"][node] = memory_usage
        avg_node_usage = sum(node_usage["cpu"].values())/len(node_usage["cpu"].values())
        max_node_usage = max(node_usage["cpu"].values())
        return max_node_usage, avg_node_usage

    def get_pod_usage(self, app_name, app_namespace):
        pod_usage = {}
        pod_usage["cpu"] = {}
        pod_usage["memory"] = {}
        pod_name_list = find_pod_name(app_name, app_namespace)
        for pod in pod_name_list:
            output = self.k.top_pod(pod, app_namespace)
            for line in output.split("\n"):
                if line.find("NAME") == -1 and line:
                    cpu_usage = int(line.split()[1].split("m")[0])
                    memory_usage = int(line.split()[-1].split("M")[0])
                    pod_usage["cpu"][pod] = cpu_usage
                    pod_usage["memory"][pod] = memory_usage
        avg_pod_usage = sum(pod_usage["cpu"].values())/len(pod_usage["cpu"].values())
        max_pod_usage = max(pod_usage["cpu"].values())
        num_pod = len(pod_name_list)
        return max_pod_usage, avg_pod_usage, num_pod

    def import_traffic(self, ratio, i):
        cmd = "python ./run_ab.py %d %d &" % (0, ratio)
        ret = os.system(cmd)
        return ret

    def get_traffic_info(self):
        dir_name = "./traffic"
        traffic_file_list = os.listdir(dir_name)
        latency_list = []
        for traffic in traffic_file_list:
            traffic_file = "./%s/%s" % (dir_name, traffic)
            if os.path.exists(traffic_file):
                with open(traffic_file, "r") as f:
                    output = f.read()
                    for line in output.split("\n"):
                        if line.find("Connect:  ") != -1:
                            avg_connect_latency = int(line.split()[2])
                            latency_list.append(avg_connect_latency)
        return latency_list

    def collect_usage(self, app_namespace, app_name):
        data = {}
        max_node_usage_list = []
        avg_node_usage_list = []
        max_pod_usage_list = []
        avg_pod_usage_list = []
        start_time = time.time()
        timeout = 120
        print "collect %ds resource usage" % timeout
        while True:
            end_time = time.time()
            if end_time - start_time > timeout:
                print "time is up to %ds..." % timeout
                break
            max_node_usage, avg_node_usage = self.get_node_usage()
            max_pod_usage, avg_pod_usage, num_pod = self.get_pod_usage(app_name, app_namespace)
            self.get_traffic_info()
            max_node_usage_list.append(max_node_usage)
            avg_node_usage_list.append(avg_node_usage)
            max_pod_usage_list.append(max_pod_usage)
            avg_pod_usage_list.append(avg_pod_usage)
            time.sleep(5)
        connect_latency_list = self.get_traffic_info()
        max_node_usage = sum(max_node_usage_list)/len(max_node_usage_list)
        avg_node_usage = sum(avg_node_usage_list)/len(avg_node_usage_list)
        max_pod_usage = sum(max_pod_usage_list)/len(max_pod_usage_list)
        avg_pod_usage = sum(avg_pod_usage_list)/len(avg_pod_usage_list)
        avg_connect_latency = sum(connect_latency_list)/len(connect_latency_list)
        print "max. node =", max_node_usage, "%"
        print "avg. node =", avg_node_usage, "%"
        print "max. pod = ", max_pod_usage, "m"
        print "avg. pod = ", avg_pod_usage, "m"
        print "avg. connect latency = ", avg_connect_latency, "ms"
        data["max_node"] = max_node_usage
        data["avg_node"] = avg_node_usage
        data["max_pod"] = max_pod_usage
        data["avg_pod"] = avg_pod_usage
        data["avg_connect_latency"] = avg_connect_latency
        return data


def main(argv):
    app_name = argv
    app_namespace, app_type, resource = find_app_location(app_name, namespace="")
    check_environment(app_name)
    update_app_limit(app_namespace, app_type, resource)
    create_directory()
    t = Training()
    current_node = 0
    current_pod = 0
    current_ratio = 0
    predicted_ratio = 0
    for i in range(training_interval):
        print "--- %dth training ---" % i
        clean_data("traffic training", app_namespace, app_type, resource)
        print "re-scale pods and wait 60 time"
        time.sleep(60)
        pod_name_list = find_pod_name(app_name, app_namespace)
        print "current replicas = ", len(pod_name_list)
        if len(pod_name_list) != overprovision_replica:
            raise Exception("current replicas(%d) should be %d" % (len(pod_name_list), overprovision_replica))
        ratio = 1000 * 1 * (i + 1)
        t.import_traffic(ratio, i)
        data = t.collect_usage(app_namespace, app_name)
        p = (data["avg_pod"] - b)/a
        predict_p = math.pow(10, p)
        current_ratio = ratio
        predict_ratio = int(math.ceil(predict_p/1000))*1000.0
        print "predicted ratio =", predict_ratio
        if predict_ratio >= target_ratio:
            current_node = data["avg_node"]
            current_pod = data["avg_pod"]
            predicted_ratio = current_ratio
            print "node(%spercent) and pod(%smCore) achieve the target level - predict ratio(%s)" % (current_node, current_pod, target_ratio)
            break
        if data.get("avg_connect_latency") > target_avg_connect_latency:
            current_latency = data["avg_connect_latency"]
            print "connect latency(%sms) is large than target level - latency(%sms)" % (current_latency, target_avg_connect_latency)
        print "wait 60 time"
        time.sleep(60)
    print "the optimal traffic ratio = %s" % (predicted_ratio)


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except KeyboardInterrupt:
        print "pgogram exit with keyboard interrupt"
        kill_process()
    except Exception as e:
        print "failed to train traffic: %s" % str(e)
        kill_process()
