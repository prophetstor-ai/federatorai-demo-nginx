import os
import json
import sys
import time
from define import data_interval
from define import cpu_limit as d_cpu_limit, memory_limit as d_memory_limit
from define import ingress_http_requests_name, ingress_namespace
from kubectl import Kubectl
from oc import OC
from prometheus_api import Prometheus


class OverLimit:
    k = Kubectl()
    wait_time = 30
    metric_item_list = ["cpu_value", "memory_value"]
    limit_item_list = ["pod_cpu_limits", "pod_memory_limits"]
    request_item_list = ["pod_cpu_requests", "pod_memory_requests"]
    app_list = {}
    app_name = ""
    namespace = ""
    cpu_limit = 0
    mem_limit = 0
    oc = OC()
    app_type = ""
    prometheus = Prometheus()

    def __init__(self):
        app_namespace = os.environ.get("NAMESPACE") or "nginx"
        app_type = os.environ.get("RESOURCE_TYPE") or "deployment"
        resource = os.environ.get("RESOURCE") or "nginx"
        self.namespace = app_namespace
        self.app_name = resource
        self.app_type = app_type

    def find_deploymentconfig_by_namespace(self, app_name):
        deployment_name_list = []
        output = {}
        if self.app_type == "deployment":
            output = self.oc.get_deployment(self.namespace)
        if self.app_type == "deploymentconfig":
            output = self.oc.get_deploymentconfig(self.namespace)
        for line in output.split("\n"):
            if line.find(app_name) != -1:
                deployment_name = line.split()[0]
                deployment_name_list.append(deployment_name)
        return deployment_name_list

    def find_pod_by_namespace(self, app_name):
        pod_name_list = []
        output = self.oc.get_pods(self.namespace)
        for line in output.split("\n"):
            if line.find(app_name) != -1:
                pod_name = line.split()[0]
                if pod_name.find("build") != -1:
                    continue
                pod_name_list.append(pod_name)
        return pod_name_list

    def get_deploymentconfig(self):
        self.app_list = {}
        # print ("---get deployment info---")
        deployment_name_list = self.find_deploymentconfig_by_namespace(self.app_name)
        for deployment in deployment_name_list:
            self.app_list[deployment] = {}
        # print self.app_list

    def get_pod_info(self):
        # print ("---get pod info---")
        pod_name_list = self.find_pod_by_namespace(self.app_name)
        for pod_name in pod_name_list:
            for deployment in self.app_list.keys():
                if pod_name.find(deployment) != -1:
                    self.app_list[deployment][pod_name] = {}
        # print self.app_list

    def get_metrics(self):
        # print ("---get metrics---")
        self.kubectl = Kubectl()
        for metric_item in self.metric_item_list:
            for deployment in self.app_list.keys():
                for pod_name in self.app_list[deployment]:
                    self.app_list[deployment][pod_name][metric_item] = 0
        for deployment in self.app_list.keys():
            for pod_name in self.app_list[deployment].keys():
                output = self.kubectl.top_pod(pod_name, self.namespace)
                for line in output.split("\n"):
                    if line.find(pod_name) != -1:
                        # by kubectl top
                        cpu = int(line.split()[-2].strip("m"))  # mCore
                        memory = int(line.split()[-1].strip("Mi"))  # MB
                        self.app_list[deployment][pod_name]["cpu_value"] = cpu
                        self.app_list[deployment][pod_name]["memory_value"] = memory
        # print self.app_list

    def get_pod_limit(self, pod_name):
        # print ("---get pod limit---")
        cpu_limit = d_cpu_limit
        memory_limit = d_memory_limit

        # data collect interval needs less than 30s
        # return cpu/memory limit from setting directly
        return cpu_limit, memory_limit


        output = self.oc.get_pod_json(pod_name, self.namespace)
        if output:
            try:
                output = json.loads(output)
                cpu_limit1 = output.get("spec", {}).get("containers", [])[0].get("resources").get("limits").get("cpu")
                if cpu_limit1 and cpu_limit1.find("m") != -1:
                    cpu_limit = float(cpu_limit1.split("m")[0])
                else:
                    cpu_limit = float(cpu_limit1) * 1000
                memory_limit1 = output.get("spec", {}).get("containers", [])[0].get("resources").get("limits").get("memory")
                if memory_limit1 and memory_limit1.find("M") != -1:
                    memory_limit = float(memory_limit1.split("M")[0])
                elif memory_limit1 and memory_limit1.find("G") != -1:
                    memory_limit = float(memory_limit1.split("G")[0]) * 1000
            except Exception as e:
                print "failed to get limits: %s" % str(e)
        return cpu_limit, memory_limit

    def get_limits(self):
        output = {}
        for metric_item in self.limit_item_list:
            for deployment in self.app_list.keys():
                for pod_name in self.app_list[deployment].keys():
                    cpu_limit, memory_limit = self.get_pod_limit(pod_name)
                    if metric_item == "pod_cpu_limits":
                        self.app_list[deployment][pod_name][metric_item] = cpu_limit
                    else:
                        self.app_list[deployment][pod_name][metric_item] = memory_limit

    def get_pod_reason(self, pod_name):
        reason_list = []
        output = self.oc.get_pod_json(pod_name, self.namespace)
        if output:
            output = json.loads(output)
            if output.get("status").get("containerStatuses")[0].get("lastState"):
                terminated = output.get("status").get("containerStatuses")[0].get("lastState").get("terminated")
                reason_list.append(terminated)
        return reason_list

    def get_status(self):
        output = self.oc.get_pods(self.namespace)
        for deployment in self.app_list.keys():
            for pod_name in self.app_list[deployment].keys():
                for line in output.split("\n"):
                    if line.find(self.app_name) != -1:
                        pod = line.split()[0]
                        if pod == pod_name:
                            reason_list = self.get_pod_reason(pod_name)
                            status = line.split()[2]
                            restart = int(line.split()[3])
                            self.app_list[deployment][pod_name]["status"] = status
                            self.app_list[deployment][pod_name]["restart"] = restart
                            self.app_list[deployment][pod_name]["reason"] = reason_list

    def get_node_status(self):
        # print "get node status"
        node_info = {}
        output = self.oc.get_nodes()
        for line in output.split("\n"):
            if line.find("NAME") == -1 and line:
                node_name = line.split()[0]
                status = line.split()[1]
                node_info[node_name] = {}
                node_info[node_name]["status"] = status
                usage_output = self.k.top_node(node_name)
                for line in usage_output.split("\n"):
                    if line.find(node_name) != -1:
                        cpu = int(line.split()[1].split("m")[0])
                        memory = int(line.split()[3].split("Mi")[0])
                        node_info[node_name]["cpu"] = cpu
                        node_info[node_name]["memory"] = memory
        # print node_info
        return node_info

    def get_http_requests(self):
        #query = "%s{namespace=\"%s\"}" % (ingress_http_requests_name, ingress_namespace)
        query = "sum(idelta(haproxy_server_http_responses_total{exported_namespace=\"nginx\",route=\"nginx-service\",code=\"2xx\"}[2m]))"
        output = self.prometheus.query_value(query)
        return float(output) / 2.0

    def calculate_overlimit(self, algo, time_count):
        cpu_count = 0
        memory_count = 0
        count = 0
        total_restart = 0
        total_terminated = 0
        data_count = int(time_count*60/self.wait_time)
        print "--- %s collect data and write to logs for %d minutes ---" % (algo.split("_")[0].upper(), time_count)

        start_time = time.time()
        for i in range(data_count):
            self.get_deploymentconfig()
            self.get_pod_info()
            self.get_limits()
            self.get_metrics()
            # self.get_status()

            print "--- %s start to collect data at %d/%d interval(in 30 sec), start: %s, current: %s ---" % (algo.split("_")[0], i, data_interval * 2, start_time, time.time())
            for deployment in self.app_list.keys():
                cpu_limit = 0
                memory_limit = 0
                total_cpu = 0
                total_memory = 0
                total_cpu_limit = 0
                total_memory_limit = 0
                # pod
                for pod in self.app_list[deployment].keys():
                    if self.app_list[deployment][pod].get("pod_cpu_limits"):
                        cpu_limit = self.app_list[deployment][pod]["pod_cpu_limits"]
                        memory_limit = self.app_list[deployment][pod]["pod_memory_limits"]
                    cpu = self.app_list[deployment][pod]["cpu_value"]
                    memory = self.app_list[deployment][pod]["memory_value"]
                    total_cpu += cpu
                    total_memory += memory
                    total_cpu_limit += cpu_limit
                    total_memory_limit += memory_limit
                    if cpu >= cpu_limit and cpu_limit != 0:
                        cpu_count += 1
                    if memory >= memory_limit and memory_limit != 0:
                        memory_count += 1
                    restart = self.app_list[deployment][pod].get("restart", 0)
                    total_restart += restart
                    reason = self.app_list[deployment][pod].get("reason", [])
                    total_terminated += len(reason)
                num_replica = len(self.app_list[deployment].keys())

                # http requests
                http_requests = self.get_http_requests()

                print self.app_name, "total_cpu=", total_cpu, "m"
                print self.app_name, "total_memory=", total_memory, "Mi"
                print self.app_name, "current replica=%d" % num_replica
                print self.app_name, "overflow=", cpu_count, "times"
                print self.app_name, "oom=", memory_count, "times"
                print self.app_name, "restart=", total_restart, "times"
                print self.app_name, "terminated=", total_terminated, "times"
                print self.app_name, "http_requests=%s" % http_requests
                print "\n"
                total_status = 0
                total_node_cpu = 0
                total_node_memory = 0

                # # skip collect node info (take too long)

                # node
                #node_info = self.get_node_status()
                #for node in node_info.keys():
                #    if node_info[node].get("status").find("NotReady") != -1:
                #        total_status += 1
                #    total_node_cpu += node_info[node]["cpu"]
                #    total_node_memory += node_info[node]["memory"]

                algo_name = "%s-%s" % (self.app_name, algo)
                data = [algo_name, total_cpu, total_cpu_limit, total_memory, total_memory_limit, cpu_count, memory_count, num_replica, restart, total_status, total_node_cpu, total_node_memory, http_requests]
                self.write_metric(data)
            # print "wait %d seconds" % self.wait_time
            # correct time
            interval = 30
            for j in range(interval):
                end_time = time.time()
                if end_time - start_time >= interval:
                    start_time = start_time + interval
                    break
                time.sleep(1)

    def write_metric(self, data):
        # print "write metrics"
        timestamp = str(int(time.time()))
        data.append(timestamp)
        try:
            pod_name = data[0]
            fn = "./metrics/%s" % pod_name
            with open(fn, "a") as f:
                line = " ".join([str(elem) for elem in data])
                f.write("%s\n" % str(line))
        except Exception as e:
            print "failed to write metrics:%s" % str(e)


if __name__ == "__main__":
    import traceback

    algo = sys.argv[1]
    time_count = int(sys.argv[2])
    print "Collect Data And Write Logs During %d for %s" % (time_count, algo)
    try:
        o = OverLimit()
        o.calculate_overlimit(algo, time_count)
    except Exception as e:
        print "failed to write logs:%s" % str(e)
        traceback.print_exc()
