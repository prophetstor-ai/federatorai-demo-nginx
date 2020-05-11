import sys
import os
import traceback
import texttable
from count_metrics1 import main as generate_metrics
from count_ab1 import main as generate_ab
from define import show_details


def get_test_case():
    test_case_list = []
    dir_list = os.listdir(".")
    for dir in dir_list:
        if (dir.find("nonhpa") != -1 or dir.find("k8shpa") != -1 or dir.find("alameda") != -1) and not os.path.isfile(dir):
            algo = "%s-%s-%s" % (dir.split("-")[0], dir.split("-")[1], dir.split("-")[2])
            test_case_list.append(algo)
    print "find test case: ", ",".join(test_case_list)
    return test_case_list


def get_data():
    test_case_list = get_test_case()
    k8shpa_list = {}
    alameda_list = {}
    nonhpa_list = {}
    for test_case in test_case_list:
        metrics_result = generate_metrics(test_case, is_show=True)
        ab_result = generate_ab(test_case, is_show=True)
        metrics_list = ab_result.keys()
        if test_case.find("k8shpa") != -1:
            k8shpa_list["max. replica"] = []
            k8shpa_list["min. replica"] = []
            k8shpa_list["avg. replica"] = []
            for metrics in metrics_list:
                k8shpa_list[metrics] = []
        if test_case.find("alameda") != -1:
            alameda_list["max. replica"] = []
            alameda_list["min. replica"] = []
            alameda_list["avg. replica"] = []
            for metrics in metrics_list:
                alameda_list[metrics] = []
        if test_case.find("nonhpa") != -1:
            nonhpa_list["max. replica"] = []
            nonhpa_list["min. replica"] = []
            nonhpa_list["avg. replica"] = []
            for metrics in metrics_list:
                nonhpa_list[metrics] = []

    for test_case in test_case_list:
        replica_list = []
        metrics_result = generate_metrics(test_case, is_show=True)
        ab_result = generate_ab(test_case, is_show=True)
        for file_id in metrics_result.keys():
            replica = metrics_result[file_id]["replica"]
            replica_list.append(replica)
        if not replica_list:
            raise Exception("%s is not existed in ./metrics" % test_case)
        if test_case.find("k8shpa") != -1:
            k8shpa_list["max. replica"].append(max(replica_list))
            k8shpa_list["min. replica"].append(min(replica_list))
            k8shpa_list["avg. replica"].append(round(sum(replica_list)*1.0/len(replica_list),2))
            for metrics in ab_result.keys():
                k8shpa_list[metrics].append(ab_result[metrics])
        if test_case.find("alameda") != -1:
            alameda_list["max. replica"].append(max(replica_list))
            alameda_list["min. replica"].append(min(replica_list))
            alameda_list["avg. replica"].append(round(sum(replica_list)*1.0/len(replica_list),2))
            for metrics in ab_result.keys():
                alameda_list[metrics].append(ab_result[metrics])
        if test_case.find("nonhpa") != -1:
            nonhpa_list["max. replica"].append(max(replica_list))
            nonhpa_list["min. replica"].append(min(replica_list))
            nonhpa_list["avg. replica"].append(round(sum(replica_list)*1.0/len(replica_list),2))
            for metrics in ab_result.keys():
                nonhpa_list[metrics].append(ab_result[metrics])

    return k8shpa_list, alameda_list, nonhpa_list


def line_row(show_details):
    row = []
    line = "-" * 30
    row.append(line)
    num_row = 2
    if show_details:
        num_row = 3
    for i in range(num_row):
        line = "-" * 20
        row.append(line)
    row.append(line + " \n")
    return row


def line():
    row = []
    line = "-" * 100
    row.append(line + " \n")
    return row


def draw_table(k8shpa_list, alameda_list, nonhpa_list):
    print "\n"
    # title
    table = []
    row = line()
    table.append(row)
    row = [texttable.get_color_string(texttable.bcolors.GREEN, "Summary of Apache Benchmark for Kubernetes Native and Federator.ai")]
    table.append(row)
    row = line()
    table.append(row)
    ttable = texttable.Texttable()
    ttable.set_cols_align(["c"])
    ttable.add_rows(table)
    print ttable.draw()

    metrics_list = ["avg. time per request"]
    if show_details:
        metrics_list = k8shpa_list.keys()
    # context
    table = []
    row = line_row(show_details)
    table.append(row)
    if nonhpa_list and show_details:
        row = ["", " ", " ", " ", "\n"]
        row[0] = "Metrics"
        row[1] = "OverProvision"
        row[2] = "K8sHPA"
        row[3] = "Federator.ai"
        row[4] = "Comparison"
    else:
        row = ["", " ", " ", "\n"]
        row[0] = "Metrics"
        row[1] = "K8sHPA"
        row[2] = "Federator.ai"
        row[3] = "Comparison"
    table.append(row)
    for metrics in sorted(metrics_list):
        row = line_row(show_details)
        table.append(row)
        if nonhpa_list and show_details:
            row = ["", " ", " ", " ", "\n"]
        else:
            row = ["", " ", " ", "\n"]
        k8shpa = round(sum(k8shpa_list[metrics])*1.0/len(k8shpa_list[metrics]), 2)
        alameda = round(sum(alameda_list[metrics])*1.0/len(alameda_list[metrics]), 2)
        row[0] = texttable.get_color_string(texttable.bcolors.BOLD, metrics)
        if show_details:
            nonhpa = round(sum(nonhpa_list[metrics])*1.0/len(nonhpa_list[metrics]), 2)
            row[1] = str(nonhpa)
            row[2] = str(k8shpa) + "\n" + "(" + str(k8shpa_list[metrics])[1:-1] + ")"
            row[3] = str(alameda) + "\n" + "(" + str(alameda_list[metrics])[1:-1] + ")"
        else:
            row[1] = str(k8shpa)
            row[2] = str(alameda)
        if k8shpa == 0:
            k8shpa = 1
        value = round((k8shpa - alameda)/k8shpa * 100, 2)
        if metrics.find("complete requests") != -1 or metrics.find("requests per second") != -1:
            value = round((alameda - k8shpa)/k8shpa * 100, 2)
        if value < 0:
            if show_details:
                row[4] = str(value) + "%"
            else:
                row[3] = str(value) + "%"
        elif value > 0:
            if show_details:
                row[4] = str(value) + "%"
            else:
                row[3] = str(value) + "%"
        else:
            if show_details:
                row[4] = str(value)
            else:
                row[3] = str(value)
        table.append(row)
    row = line_row(show_details)
    table.append(row)
    ttable = texttable.Texttable()
    if show_details:
        ttable.set_cols_align(["l", "c", "c", "c", "c"])
    else:
        ttable.set_cols_align(["l", "c", "c", "c"])
    ttable.add_rows(table)
    print ttable.draw()
    return ttable.draw


def ording_picture(picture_list):
    new_picture_list = {}
    for picture in sorted(picture_list):
        if len(picture.split("-")) != 4:
            continue
        algo = picture.split("-")[1]
        new_picture_list[algo] = {}
        date = "%s-%s" % (picture.split("-")[2], picture.split("-")[3].split(".")[0])
    for picture in sorted(picture_list):
        if len(picture.split("-")) != 4:
            continue
        algo = picture.split("-")[1]
        date = "%s-%s" % (picture.split("-")[2], picture.split("-")[3].split(".")[0])
        new_picture_list[algo][date] = []
    for picture in sorted(picture_list):
        if len(picture.split("-")) != 4:
            continue
        algo = picture.split("-")[1]
        date = "%s-%s" % (picture.split("-")[2], picture.split("-")[3].split(".")[0])
        new_picture_list[algo][date].append(picture)
    # print new_picture_list
    return new_picture_list


def add_line(length):
    line = "-" * length
    return line


def write_to_md(k8shpa_list, alameda_list, nonhpa_list, term):
    picture_list = os.listdir("./picture")
    new_picture_list = ording_picture(picture_list)
    file_name = "./summary.md"
    try:
        with open(file_name, "w") as f:
            f.write("# Summary of Apache Benchmark for Kubernetes Native and Federator.ai (%s)\n" % term)
            f.write("|metrics|overprovision|k8shpa|avg k8shpa|federator.ai|avg federator.ai|comparision|\n")
            line = "|:%s|:%s:|:%s:|:%s:|:%s:|:%s:|:%s:|\n" % (add_line(10), add_line(10), add_line(20), add_line(10), add_line(20), add_line(10), add_line(10))
            f.write(line)
            for metrics in sorted(k8shpa_list.keys()):
                nonhpa = str(nonhpa_list[metrics])[1:-1]
                k8shpa = str(k8shpa_list[metrics])[1:-1]
                alameda = str(alameda_list[metrics])[1:-1]
                avg_k8shpa = k8shpa_list[metrics][0]
                avg_alameda = alameda_list[metrics][0]
                if len(k8shpa) != 1:
                    avg_k8shpa = round(sum(k8shpa_list[metrics])/len(k8shpa_list[metrics]), 2)
                if len(alameda) != -1:
                    avg_alameda = round(sum(alameda_list[metrics])/len(alameda_list[metrics]), 2)
                if avg_k8shpa - avg_alameda == 0:
                    value = str(0)
                else:
                    value = str(round((avg_k8shpa - avg_alameda) / avg_k8shpa * 100, 2)) + "%"
                f.write("|%s|%s|%s|%s|%s|%s|%s|\n" % (metrics, nonhpa, k8shpa, avg_k8shpa, alameda, avg_alameda, value))

            # picture
            for algo in new_picture_list.keys():
                for date in new_picture_list[algo].keys():
                    f.write("<div style=\"page-break-after: always;\"></div>\n")
                    f.write("## %s %s:\n" % (algo, date))
                    count = 0
                    for picture in sorted(new_picture_list[algo][date]):
                        if picture.find("node") != -1:
                            continue
                        if count % 2 == 0 and count != 0:
                            f.write("<div style=\"page-break-after: always;\"></div>\n")
                        picture_path = "./picture/%s" % picture
                        f.write("![](%s)\n" % picture_path)
                        count += 1
            # parameters
            f.write("<div style=\"page-break-after: always;\"></div>\n")
            with open("./define.py", "r") as fs:
                for line in fs:
                    f.write("%s\n" % line)

    except Exception as e:
        print "failed to write to %s: %s" % (file_name, str(e))
        return -1
    print "success to write to %s" % (file_name)
    return 0


def main(argv):
    print "--- Skip Summary ---"
    # print "--- Start to Generate Summary ---"
    # try:
    #     k8shpa_list, alameda_list, nonhpa_list = get_data()
    #     if len(argv) == 1:
    #         draw_table(k8shpa_list, alameda_list, nonhpa_list)
    #     else:
    #         term = argv[1]
    #         write_to_md(k8shpa_list, alameda_list, nonhpa_list, term)
    # except Exception as e:
    #     print "failed to generate summary: %s" % str(e)
    #     traceback.print_exc()


if __name__ == "__main__":
    main(sys.argv)
