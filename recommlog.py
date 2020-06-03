import sys
import json
from tabulate import tabulate

def main(predict, fn):
    #keys = ["CurrentMetric", "CurrentReplicas", "HttpResponseTime", "PredictionMetric",
    #        "ReplicaCapacity", "Alpha", "DesiredReplicas"]
    keys = ["CurrentMetric", "CurrentReplicas", "PredictionMetric", "DesiredReplicas", 
            "ReplicaCapacity", "Alpha", "HttpResponseTime"]

    output = []
    lastMetric, lastRC, lastMaxRC = None, None, None
    with open(fn, "r") as f:
        o = f.read()
        for l in o.split("\n"):
            if "Evaluate method: %s" % predict in l:
                if predict == "moving-avg":
                    # moving average metrics: 64797.00, current replicas capacity: 2314.18(max: 6411.96)
                    s = l.find("moving average metrics: ") + len("moving average metrics: ")
                    e = l.find(",", s)
                    lastMetric = l[s:e]

                    s = l.find("current replicas capacity: ") + len("current replicas capacity: ")
                    e1 = l.find("(", s)
                    lastRC = l[s:e1]

                    s = l.find("(", e1)
                    s = l.find(": ", s) + len(": ")
                    e = l.find(")", s)
                    lastMaxRC = l[s:e]

                elif predict == "prediction":
                    # prediction metrics: 109763.63, current replicas capacity: 2314.18(max: 6411.96)
                    s = l.find("prediction metrics: ") + len("prediction metrics: ")
                    e = l.find(",", s)
                    lastMetric = l[s:e]

                    s = l.find("current replicas capacity: ") + len("current replicas capacity: ")
                    e1 = l.find("(", s)
                    lastRC = l[s:e1]

                    s = l.find("(", e1)
                    s = l.find(": ", s) + len(": ")
                    e = l.find(")", s)
                    lastMaxRC = l[s:e]

            d, r = None, []
            if "recommendation result:" in l:
                s = l.find("[")
                e = l.find("]")
                if s > 0 and e > 0:
                    d = json.loads(l[s + 1:e])

            if not d:
                continue

            if not output and d["CurrentMetric"] == 0:
                # skip rows without workload at begining
                continue

            # replace "PredictionMetric" and "ReplicaCapacity"
            if lastMetric != None and lastRC != None and lastMaxRC != None:
                d["PredictionMetric"] = lastMetric
                d["ReplicaCapacity"] = lastRC + "/" + lastMaxRC
                lastMetric = lastRC = lastMaxRC = None

            row = []
            row.append(len(output))
            for k in keys:
                row.append(d[k])
            output.append(row)

        print(tabulate(output, headers=["No"] + keys))


if __name__ == '__main__':
    import traceback
    try:
        predict = sys.argv[1]
        fn = sys.argv[2]
        main(predict, fn)
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

    sys.exit(0)
