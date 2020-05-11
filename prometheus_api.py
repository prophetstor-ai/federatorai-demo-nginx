import os
import sys
import json

import define
from oc import OC


class Prometheus(object):

    def __init__(self):
        self.oc_platform = not OC().check_platform()    # OC().check_platform() return 0 if oc command exists
        if self.oc_platform:
            self.endpoint = define.prometheus_endpoint
            self.token = define.prometheus_token
        else:
            self.endpoint = self._get_endpoint_from_service()

    def _get_endpoint_from_service(self):
        output = OC().get_service(define.prometheus_namespace).split("\n")
        for line in output:
            if line.find(define.prometheus_operator_name) != -1:
                ip = line.split()[2]
                port = line.split()[-2].split(":")[0]
                endpoint = "http://%s:%s/api/v1" % (ip, port)
                break

        print("Prometheus: find endpoint(%s)", endpoint)
        sys.exit()
        return endpoint

    def _json_loads(self, data):
        try:
            return json.loads(data)
        except Exception as e:
            # not JSON format
            print data
            return {}

    def query(self, metric):
        if self.oc_platform:
            cmd = "curl -k -g -s -H 'Authorization: Bearer %s' '%s/query?query=%s'" % (self.token, self.endpoint, metric)
        else:
            cmd = "curl -g -s '%s/query?query=%s'" % (self.endpoint, metric)

        output = os.popen(cmd).read()
        output = self._json_loads(output)

        return output

    def query_value(self, metric):
        output = self.query(metric)
        try:
            return output["data"]["result"][0]["value"][1]
        except Exception as e:
            print output
            return 0


if __name__ == '__main__':

    import traceback

    try:
        p = Prometheus()
        output = p.query("nginx_ingress_controller_nginx_process_requests_total")
        print json.dumps(output)

    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

    sys.exit(0)


