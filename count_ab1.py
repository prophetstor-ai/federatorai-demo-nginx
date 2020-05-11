import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from define import traffic_ratio, picture_y_ratio, traffic_interval
alpha = picture_y_ratio


def get_metrics(term, dir_name, file_list, total_metrics_list):
    count = 0
    value = 0
    total_value = 0
    fail_count = 0
    for file_name in sorted(file_list):
        if file_name.find("workload") == -1:
            continue
        cmd = "cat %s/%s | grep '%s'" % (dir_name, file_name, term)
        output = os.popen(cmd).read()
        file_no = int(file_name.split("-")[1])
        if term == "Time taken for tests" and output.find(term) != -1:
            value = float(output.split()[-2])
            total_metrics_list[file_no]["Time taken for tests"] = value
        elif term == "Complete requests" and output.find(term) != -1:
            value = int(output.split()[-1])
            total_metrics_list[file_no]["Complete requests"] = value
        elif term == "Failed requests" and output.find(term) != -1:
            value = int(output.split()[-1])
            total_metrics_list[file_no]["Failed requests"] = value
        elif term == "Requests per second" and output.find(term) != -1:
            value = float(output.split()[-3])
            total_metrics_list[file_no]["Requests per second"] = value
        elif term == "Time per request" and output.find(term) != -1:
            for line in output.split("\n"):
                if len(line.split()) == 6:
                    value = float(line.split()[-3])
                    total_metrics_list[file_no]["Time per request"] = value
        elif term.find("%") != -1 and output.find(term) != -1:
            for line in output.split("\n"):
                if len(line.split()) == 2:
                    value = int(line.split()[1])
                    total_metrics_list[file_no]["%sth delay" % term.strip("%")] = value
        else:
            fail_count += 1
            cmd = "cat %s/%s | grep '%s'" % (dir_name, file_name, "Total of")
            value = 0
            if os.popen(cmd).read().split():
                value = int(os.popen(cmd).read().split()[2])
            total_metrics_list[file_no]["Complete requests"] = value
            total_metrics_list[file_no]["fails"] = True
            total_metrics_list[file_no]["Time per request"] = 0
            total_metrics_list[file_no]["Failed requests"] = total_metrics_list[file_no]["Send requests"] - total_metrics_list[file_no]["Complete requests"]
            total_metrics_list[file_no]["Requests per second"] = 0
            cmd = "cat %s/%s" % (dir_name, file_name)
            output = os.popen(cmd).read()
            reason = ""
            if output.find("timeout") != -1:
                reason = "timeout"
            if output.find("Connection reset by peer") != -1:
                reason = "Connection reset by peer"
            total_metrics_list[file_no]["Reason"] = reason

        if value != 0:
            total_value += float(value)
        count += 1
    return total_metrics_list


def get_send_requests(total_metrics_list):
    count = 0
    fn = "./transaction.txt"
    with open(fn, "r") as f:
        output = f.read()
        for i in range(len(output.split("\n"))):
            count = i % traffic_interval
            if i >= traffic_interval:
                break
            line = output.split("\n")[i]
            if line:
                transaction = int(float(line.split()[0]))*traffic_ratio
                total_metrics_list[count]["Send requests"] = transaction
    return total_metrics_list


def draw_ab_picture(send_requests_list, complete_requests_list, time_per_request_list, item):
    if item.find("nonhpa") != -1:
        item = "overprovision"
    time_list = []
    for i in range(len(send_requests_list)):
        time_list.append(i)
    x = time_list
    send_y = send_requests_list
    complete_y = complete_requests_list
    plt.figure(figsize=(8, 4))
    plt.title("Number of Send/Complete Requests and Time Per Request")
    # sub-figure 1
    plt.subplot(2, 1, 1)
    plt.plot(x, send_y, label="send requests", color="g", linewidth=1, marker="1")
    plt.plot(x, complete_y, label="complete requests(%s)" % item, color="r", linewidth=1, marker="+")
    ylim = 10
    if send_y:
        ylim = max(max(send_y)*alpha, max(complete_y)*alpha)
        if ylim == 0:
            ylim = 10
    plt.ylim(0, ylim)
    plt.xlabel("Time Intervals(per 1 min)")
    plt.ylabel("Number of Requests")
    plt.legend(loc=1, ncol=2)

    # sub-figure 2
    plt.subplot(2, 1, 2)
    time_y = time_per_request_list
    plt.bar(x, time_y, label="time per request (%s)" % item)
    plt.xlabel("Time Intervals(per 1 min)")
    plt.ylabel("Time Per Request (ms)")
    plt.legend(loc=0)
    ylim = 10
    if time_y:
        ylim = max(time_y)*alpha
        if ylim == 0:
            ylim = 10
    plt.ylim(0, ylim)

    # print ("save file to ./picture/request-%s.png" % item)
    plt.savefig("./picture/request-%s.png" % item)
    plt.close()


def get_tail_latency(total_metrics_list, percentile):
    total_latency = 0
    total_request = 0
    for job_id in total_metrics_list.keys():
        term = "%sth delay" % str(percentile)
        if not total_metrics_list[job_id].get(term):
            continue
        total_latency += total_metrics_list[job_id][term]*total_metrics_list[job_id]["Complete requests"]*percentile/100.0
        total_request += total_metrics_list[job_id]["Complete requests"]*percentile/100.0
    if total_request != 0:
        tail_latency = total_latency/total_request
    else:
        tail_latency = total_latency
    return tail_latency


def get_avg_latency(total_metrics_list):
    total_latency = 0
    total_request = 0
    term = "Time per request"
    for job_id in total_metrics_list.keys():
        if not total_metrics_list[job_id].get(term):
            continue
        total_latency += total_metrics_list[job_id][term]*total_metrics_list[job_id]["Complete requests"]
        total_request += total_metrics_list[job_id]["Complete requests"]
    avg_latency = total_latency/total_request
    return avg_latency


def main(dir_term, is_show):
    # print "--- Generate Statistics of Appach Benchmark for %s ---" % dir_term
    result = {}
    new_dir_list = os.listdir(".")
    dir_name = ""
    for n_dir_name in new_dir_list:
        if n_dir_name.find(dir_term) != -1:
            dir_name = n_dir_name
    file_list = os.listdir("./%s" % dir_name)
    if not dir_name:
        raise Exception("failed to find %s" % dir_term)

    total_metrics_list = {}
    for file_name in file_list:
        file_no = int(file_name.split("-")[1])
        total_metrics_list[file_no] = {}
    total_metrics_list = get_send_requests(total_metrics_list)
    total_metrics_list = get_metrics("Time taken for tests", dir_name, file_list, total_metrics_list)
    total_metrics_list = get_metrics("Complete requests", dir_name, file_list, total_metrics_list)
    total_metrics_list = get_metrics("Failed requests", dir_name, file_list, total_metrics_list)
    total_metrics_list = get_metrics("Requests per second", dir_name, file_list, total_metrics_list)
    total_metrics_list = get_metrics("Time per request", dir_name, file_list, total_metrics_list)
    total_metrics_list = get_metrics("50%", dir_name, file_list, total_metrics_list)
    total_metrics_list = get_metrics("90%", dir_name, file_list, total_metrics_list)
    total_metrics_list = get_metrics("95%", dir_name, file_list, total_metrics_list)
    total_metrics_list = get_metrics("99%", dir_name, file_list, total_metrics_list)

    time_taken_fot_tests_list = []
    complete_requests_list = []
    failed_requests_list = []
    requests_per_second_list = []
    time_per_request_list = []
    send_requests_list = []
    not_complete_job = 0
    if is_show:
        print ("=== %s not completed jobs ===" % dir_name)
    for file_no in total_metrics_list.keys():
        if total_metrics_list[file_no].get("Time taken for tests"):
            time_taken_fot_tests_list.append(total_metrics_list[file_no]["Time taken for tests"])
        else:
            if is_show:
                print "workload-", file_no, "fails", total_metrics_list[file_no]["Reason"]
            not_complete_job += 1
        complete_requests_list.append(total_metrics_list[file_no]["Complete requests"])
        send_requests_list.append(total_metrics_list[file_no]["Send requests"])
        failed_requests_list.append(total_metrics_list[file_no]["Failed requests"])
        requests_per_second_list.append(total_metrics_list[file_no]["Requests per second"])
        time_per_request_list.append(total_metrics_list[file_no]["Time per request"])
    if is_show:
        print ("=== %s results ===" % dir_name)
        print ("avg. time taken for tests=", sum(time_taken_fot_tests_list)/len(time_taken_fot_tests_list))
        print ("avg. complete requests=", sum(complete_requests_list)/len(complete_requests_list))
        # print "avg. send requests=", sum(send_requests_list)/len(send_requests_list)
        print ("avg. failed requests=", sum(failed_requests_list)/len(failed_requests_list))
        print ("avg. requests per second=", sum(requests_per_second_list)/len(requests_per_second_list))
        print ("avg. time per request=", get_avg_latency(total_metrics_list))
        print ("50th tail latency=", get_tail_latency(total_metrics_list, 50))
        print ("90th tail latency=", get_tail_latency(total_metrics_list, 90))
        print ("95th tail latency=", get_tail_latency(total_metrics_list, 95))
        print ("99th tail latency=", get_tail_latency(total_metrics_list, 99))
        print ("==============")

    draw_ab_picture(send_requests_list, complete_requests_list, time_per_request_list, dir_term)
    # get result
    result["not complete job"] = not_complete_job
    result["avg. time taken for tests"] = round(sum(time_taken_fot_tests_list)/len(time_taken_fot_tests_list), 2)
    result["avg. complete requests"] = sum(complete_requests_list)/len(complete_requests_list)
    result["avg. failed requests"] = sum(failed_requests_list)/len(failed_requests_list)
    result["avg. requests per second"] = round(sum(requests_per_second_list)/len(requests_per_second_list), 2)
    result["avg. time per request"] = round(get_avg_latency(total_metrics_list), 2)
    result["50th tail latency"] = round(get_tail_latency(total_metrics_list, 50), 2)
    result["90th tail latency"] = round(get_tail_latency(total_metrics_list, 90), 2)
    result["95th tail latency"] = round(get_tail_latency(total_metrics_list, 95), 2)
    result["99th tail latency"] = round(get_tail_latency(total_metrics_list, 99), 2)
    return result

if __name__ == "__main__":
    dir_term = sys.argv[1]
    main(dir_term, is_show=True)
