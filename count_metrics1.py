import os
import sys
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from define import picture_x_axis, picture_y_ratio

upperbound = picture_x_axis
cpu_limit = 200
alpha = picture_y_ratio


def get_utilization(file_item, is_show):
    file_list = os.listdir("./metrics")
    utilization_list = {}
    total_replica_list = []
    optimal_replica_list = []
    total_restart_list = []
    total_node_cpu_list = []
    total_node_memory_list = []
    overlimit = 0
    count = 0
    for file_name in file_list:
        if file_name.find(file_item) != -1:
            cmd = "cat ./metrics/%s" % file_name
            output = os.popen(cmd).read()
            for line in output.split("\n"):
                if line:
                    if count > int(upperbound):
                        break
                    cpu = int(line.split()[1])
                    new_cpu_limit = int(float(line.split()[2]))
                    memory = int(line.split()[3])
                    new_memory_limit = int(float(line.split()[4]))

                    optimal_replica = int(math.ceil(cpu/cpu_limit))
                    optimal_replica_list.append(optimal_replica)

                    overlimit = int(line.split()[5])
                    oom = int(line.split()[6])
                    replica = int(line.split()[7])
                    total_replica_list.append(replica)
                    restart = int(line.split()[-5])
                    total_restart_list.append(restart)

                    node_cpu = int(float(line.split()[-3]))
                    total_node_cpu_list.append(node_cpu)

                    node_memory = int(float(line.split()[-2]))
                    total_node_memory_list.append(node_memory)

                    utilization_list[count] = {}
                    utilization_list[count]["cpu"] = cpu
                    utilization_list[count]["cpu_limit"] = new_cpu_limit
                    utilization_list[count]["memory"] = memory
                    utilization_list[count]["memory_limit"] = new_memory_limit
                    utilization_list[count]["replica"] = replica
                    utilization_list[count]["overlimit"] = overlimit
                    utilization_list[count]["oom"] = oom
                    utilization_list[count]["overlimit_diff"] = 0
                    utilization_list[count]["oom_diff"] = 0
                    utilization_list[count]["restart"] = restart
                    utilization_list[count]["restart_diff"] = 0
                    utilization_list[count]["node_cpu"] = node_cpu
                    utilization_list[count]["node_memory"] = node_memory
                    if count > 0:
                        utilization_list[count]["overlimit_diff"] = utilization_list[count]["overlimit"] - utilization_list[count-1]["overlimit"]
                        utilization_list[count]["oom_diff"] = utilization_list[count]["oom"] - utilization_list[count-1]["oom"]
                        utilization_list[count]["restart_diff"] = utilization_list[count]["restart"] - utilization_list[count-1]["restart"]
                    count += 1
    if is_show:
        print "max replica=", max(total_replica_list)
        print "min replica=", min(total_replica_list)
        print "avg replica=", sum(total_replica_list)/(len(total_replica_list)*1.0)
        print "avg node cpu=", sum(total_node_cpu_list)/(len(total_node_cpu_list)*1.0), "m"
        print "avg node memory=", sum(total_node_memory_list)/(len(total_node_memory_list)*1.0), "Mi"
        if file_item.find("nonhpa") != -1:
            print "max optimal replica=", max(optimal_replica_list)
            print "avg optimal replica=", sum(optimal_replica_list)/(len(optimal_replica_list)*1.0)
        print "overlimit=", overlimit
        print "oom=", oom
        print "restart=", restart
    return utilization_list


def draw_cpu_picture(nonhpa_list, hpa_list, item):
    if item.find("nonhpa") != -1:
        item = "overprovision"
    nonhpa_cpu_list = []
    hpa_cpu_list = []
    hpa_cpu_limit_list = []
    hpa_over_limit_list = []
    for i in sorted(hpa_list.keys()):
        if nonhpa_list:
            nonhpa_cpu = nonhpa_list[i]["cpu"]
            nonhpa_cpu_list.append(nonhpa_cpu)
        hpa_cpu = hpa_list[i]["cpu"]
        hpa_cpulimit = hpa_list[i]["cpu_limit"]
        hpa_overlimit = hpa_list[i]["overlimit_diff"]
        hpa_cpu_list.append(hpa_cpu)
        hpa_cpu_limit_list.append(hpa_cpulimit)
        hpa_over_limit_list.append(hpa_overlimit)

    x = hpa_list.keys()
    nonhpa_y = nonhpa_cpu_list
    hpa_y = hpa_cpu_list
    hpa_y_limit = hpa_cpu_limit_list
    hpa_y_overlimit = hpa_over_limit_list
    plt.figure(figsize=(8, 4))

    # sub-figure 1
    plt.subplot(2, 1, 1)
    if nonhpa_y:
        plt.plot(x, nonhpa_y, label="nonhpa", color="g", linewidth=1.5)
    plt.plot(x, hpa_y, label="observed(%s)" % item, color="k", linewidth=1.5)
    plt.plot(x, hpa_y_limit, label="hpa-limit (%s)" % item, color="b", linewidth=1.5)
    plt.xlabel("Time Intervals(per 30 sec)")
    plt.ylabel("CPU m")
    if nonhpa_y:
        ylim = max([max(hpa_y), max(hpa_y_limit), max(nonhpa_y)])*alpha
    else:
        ylim = max([max(hpa_y), max(hpa_y_limit)])*alpha
    plt.ylim(0, ylim)
    plt.title("CPU Utilization and CPU OverLimit")
    plt.legend(loc=1, ncol=3)

    # sub-figure 2
    plt.subplot(2, 1, 2)
    plt.bar(x, hpa_y_overlimit, label="hpa-overlimit (%s)" % item)
    plt.xlabel("Time Intervals(per 30 sec)")
    plt.ylabel("Number of CPU OverLimit")
    plt.legend(loc=0)
    # print "save file to ./picture/cpu-%s.png" % item
    plt.savefig("./picture/cpu-%s.png" % item)
    plt.close()


def draw_node_picture(nonhpa_list, hpa_list, item):
    if item.find("nonhpa") != -1:
        item = "overprovision"
    # cpu
    nonhpa_cpu_list = []
    hpa_cpu_list = []
    hpa_restart_list = []
    for i in hpa_list.keys():
        if nonhpa_list:
            nonhpa_cpu = nonhpa_list[i]["node_cpu"]
            nonhpa_cpu_list.append(nonhpa_cpu)
        hpa_cpu = hpa_list[i]["node_cpu"]
        restart = hpa_list[i]["restart_diff"]
        hpa_cpu_list.append(hpa_cpu)
        hpa_restart_list.append(restart)
    x = hpa_list.keys()
    nonhpa_y = nonhpa_cpu_list
    hpa_y = hpa_cpu_list
    plt.figure(figsize=(10, 4))

    # sub-figure 1
    plt.subplot(3, 1, 1)
    if nonhpa_y:
        plt.plot(x, nonhpa_y, label="nonhpa", color="g", linewidth=1.5)
    plt.plot(x, hpa_y, label="observed(%s)" % item, color="k", linewidth=1.5)
    plt.xlabel("Time Intervals(per 30 sec)")
    plt.ylabel("CPU m")
    if nonhpa_y:
        ylim = max([max(hpa_y), max(nonhpa_y)])*alpha
    else:
        ylim = max(hpa_y) * alpha
    plt.ylim(0, ylim)
    plt.legend(loc=2, ncol=3)
    plt.title(" Node CPU and Memory Utilization")

    # memory
    nonhpa_mem_list = []
    hpa_mem_list = []
    for i in hpa_list.keys():
        if nonhpa_list:
            nonhpa_mem = nonhpa_list[i]["node_memory"]
            nonhpa_mem_list.append(nonhpa_mem)
        hpa_mem = hpa_list[i]["node_memory"]
        hpa_mem_list.append(hpa_mem)

    nonhpa_y = nonhpa_mem_list
    hpa_y = hpa_mem_list

    # sub-figure 2
    plt.subplot(3, 1, 2)
    if nonhpa_y:
        plt.plot(x, nonhpa_y, label="nonhpa", color="g", linewidth=1.5)
    plt.plot(x, hpa_y, label="observed(%s)" % item, color="k", linewidth=1.5)
    plt.xlabel("Time Intervals(per 30 sec)")
    plt.ylabel("Memory Size (MB)")
    if nonhpa_y:
        ylim = max([max(hpa_y), max(nonhpa_y)])*alpha
    else:
        ylim = max(hpa_y) * alpha
    plt.ylim(0, ylim)
    plt.legend(loc=1, ncol=3)

    # sub-figure 3
    hpa_restart = hpa_restart_list
    plt.subplot(3, 1, 3)
    plt.bar(x, hpa_restart, label="hpa-restart (%s)" % item)
    plt.xlabel("Time Intervals(per 30 sec)")
    plt.ylabel("Number of Restart")
    ylim = 10
    if hpa_restart:
        ylim = max(hpa_restart)*alpha
        if ylim == 0:
            ylim = 10
    plt.ylim(0, ylim)
    plt.legend(loc=0)

    # print "save file to ./picture/node-%s.png" % item
    plt.savefig("./picture/node-%s.png" % item)
    plt.close()


def draw_memory_picture(nonhpa_list, hpa_list, item):
    if item.find("nonhpa") != -1:
        item = "overprovision"
    nonhpa_mem_list = []
    hpa_mem_list = []
    hpa_mem_limit_list = []
    hpa_over_limit_list = []
    for i in hpa_list.keys():
        if nonhpa_list:
            nonhpa_mem = nonhpa_list[i]["memory"]
            nonhpa_mem_list.append(nonhpa_mem)
        hpa_mem = hpa_list[i]["memory"]
        hpa_memlimit = hpa_list[i]["memory_limit"]
        hpa_overlimit = hpa_list[i]["oom_diff"]
        hpa_mem_list.append(hpa_mem)
        hpa_mem_limit_list.append(hpa_memlimit)
        hpa_over_limit_list.append(hpa_overlimit)

    x = hpa_list.keys()
    nonhpa_y = nonhpa_mem_list
    hpa_y = hpa_mem_list
    hpa_y_limit = hpa_mem_limit_list
    hpa_y_overlimit = hpa_over_limit_list
    plt.figure(figsize=(8, 4))
    # sub-figure 1
    plt.subplot(2, 1, 1)
    if nonhpa_y:
        plt.plot(x, nonhpa_y, label="nonhpa", color="g", linewidth=1.5)
    plt.plot(x, hpa_y, label="oberserved(%s)" % item, color="k", linewidth=1.5)
    plt.plot(x, hpa_y_limit, label="hpa-limit (%s)" % item, color="b", linewidth=1.5)
    plt.xlabel("Time Intervals(per 30 sec)")
    plt.ylabel("Memory Size (MB)")
    if nonhpa_y:
        ylim = max([max(hpa_y), max(nonhpa_y), max(hpa_y_limit)])*alpha
    else:
        ylim = max([max(hpa_y), max(hpa_y_limit)])*alpha
    plt.ylim(0, ylim)
    plt.title("Memory Utilization and Memory OverLimit")
    plt.legend(loc=1, ncol=3)
    # sub-figure 2
    plt.subplot(2, 1, 2)
    plt.bar(x, hpa_y_overlimit, label="hpa-oom (%s)" % item)
    plt.xlabel("Time Intervals(per 30 sec)")
    plt.ylabel("Number of OOM")
    plt.legend(loc=0)
    plt.savefig("./picture/mem-%s.png" % item)
    plt.close()


def main(file_item, is_show):
    # print "--- Generate Metrics for %s ---" % file_item
    result = {}
    file_list = os.listdir("./metrics")
    is_nonhpa = False
    is_k8shpa = False
    is_alameda = False
    nonhpa_list = []
    k8shpa_list = []
    ourhpa_list = []
    for file_name in file_list:
        if file_name.find("nonhpa") != -1:
            is_nonhpa = True
        if file_name.find("k8shpa") != -1 and file_name.find(file_item) != -1:
            is_k8shpa = True
        if file_name.find("alameda") != -1 and file_name.find(file_item) != -1:
            is_alameda = True
    if is_nonhpa:
        if is_show:
            print "=== Non-HPA ==="
        nonhpa_list = get_utilization(file_item, is_show)
        result = nonhpa_list
    if is_k8shpa:
        if is_show:
            print "=== K8s-HPA ==="
        k8shpa_list = get_utilization(file_item, is_show)
        result = k8shpa_list
    if is_alameda:
        if is_show:
            print "=== Alameda-HPA ==="
        ourhpa_list = get_utilization(file_item, is_show)
        result = ourhpa_list
    if nonhpa_list and not k8shpa_list and not ourhpa_list:
        draw_cpu_picture(nonhpa_list, nonhpa_list, file_item)
        draw_memory_picture(nonhpa_list, nonhpa_list, file_item)
        #draw_node_picture(nonhpa_list, nonhpa_list, file_item)
    if k8shpa_list:
        draw_cpu_picture(nonhpa_list, k8shpa_list, file_item)
        draw_memory_picture(nonhpa_list, k8shpa_list, file_item)
        #draw_node_picture(nonhpa_list, k8shpa_list, file_item)
    if ourhpa_list:
        draw_cpu_picture(nonhpa_list, ourhpa_list, file_item)
        draw_memory_picture(nonhpa_list, ourhpa_list, file_item)
        #draw_node_picture(nonhpa_list, ourhpa_list, file_item)
    return result


if __name__ == "__main__":
    file_item = sys.argv[1]
    main(file_item, is_show=True)
