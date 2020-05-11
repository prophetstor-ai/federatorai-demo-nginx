import time
import os
import random
from oc import OC
import sys
from define import traffic_ratio, traffic_interval
from define import app_service_ip, app_service_port
from define import ab_concurrency, ab_timelimit


class Nginx:
    oc = OC()

    def __init__(self):
        pass

    def run_cmd(self, cmd):
        ret = os.popen(cmd).read()
        return ret

    def wait_time(self, waittime):
        # print "wait %d time" % waittime
        time.sleep(waittime)

    def find_pod_by_namespace(self, namespace, app_name):
        pod_name_list = []
        output = self.oc.get_pods(namespace)
        print output
        for line in output.split("\n"):
            if line.find(app_name) != -1:
                pod_name = line.split()[0]
                pod_name_list.append(pod_name)
        return pod_name_list

    def find_service_by_namespace(self, namespace, app_name):

        if app_service_ip and app_service_port:
            return app_service_ip, app_service_port

        ip = ""
        port = ""
        output = self.oc.get_service(namespace)
        for line in output.split("\n"):
            if line.find(app_name) != -1:
                ip = line.split()[2]
                port = line.split()[4].split("/")[0].split(":")[0]
                service = line.split()[0]
                if service == app_name:
                    break
        if not ip and not port:
            raise Exception("service (%s:%s) is not found" % (ip, port))
        return ip, port

    def generate_nginx_traffic(self, count, ratio=0):
        cmd = ""
        traffic_ratio1 = traffic_ratio
        if ratio != 0:
            traffic_ratio1 = ratio
            print "traffic ratio = ", ratio
        app_namespace = os.environ.get("NAMESPACE")
        app_type = os.environ.get("RESOURCE_TYPE")
        resource = os.environ.get("RESOURCE")
        ip, port = self.find_service_by_namespace(app_namespace, resource)
        transaction_list = self.get_transaction_list()
        transaction_num = transaction_list[count] * traffic_ratio1
        cmd = "ab -t %d -c %d -n %d -r http://%s:%s/index1.php" % (ab_timelimit, ab_concurrency, transaction_num, ip, port)
        print "--- start %d clients and %d transactions to host(%s:%s) %s ---" % \
                (ab_concurrency, transaction_num, ip, port, time.ctime())
        output = self.run_cmd(cmd)
        # print output
        self.write_workload(output, count)
        return output

    def get_transaction_list(self):
        transaction_list = []
        fn = "./transaction.txt"
        with open(fn, "r") as f:
            output = f.read()
            for line in output.split("\n"):
                if line:
                    transaction = int(float(line.split()[0]))
                    transaction_list.append(transaction)
        return transaction_list

    def write_workload(self, output, workload):
        fn = "./traffic/workload-%d" % workload
        with open(fn, "w") as f:
            for line in output.split("\n"):
                f.write("%s\n" % line)
        print "--- workload: %s/%d is completed ---" % (fn, traffic_interval)


if __name__ == "__main__":
    n = Nginx()
    request_count = int(sys.argv[1])
    ratio = 0
    if len(sys.argv) > 2:
        ratio = int(sys.argv[2])
    n.generate_nginx_traffic(request_count, ratio)
