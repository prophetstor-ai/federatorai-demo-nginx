import os
import json


class Kubectl:

    cmd = "kubectl"

    def __init__(self):
        pass

    def get_pod_by_namespace(self, namespace):
        cmd = "%s get pods --show-labels -o wide -n %s" % (self.cmd, namespace)
        output = os.popen(cmd).read()
        return output

    def get_pod(self):
        cmd = "%s get pods --show-labels -o wide --all-namespaces" % self.cmd
        output = os.popen(cmd).read()
        return output

    def top_pod(self, pod_name, namespace):
        cmd = "%s top pod %s -n %s" % (self.cmd, pod_name, namespace)
        output = os.popen(cmd).read()
        return output

    def get_svc(self):
        cmd = "%s get svc --show-labels -o wide --all-namespaces" % self.cmd
        output = os.popen(cmd).read()
        return output

    def get_deployment(self):
        cmd = "%s get deployment --show-labels -o wide --all-namespaces" % self.cmd
        output = os.popen(cmd).read()
        return output

    def get_statefulset(self):
        cmd = "%s get statefulset --show-labels -o wide --all-namespaces" % self.cmd
        output = os.popen(cmd).read()
        return output

    def get_daemonset(self):
        cmd = "%s get daemonset --show-labels -o wide --all-namespaces" % self.cmd
        output = os.popen(cmd).read()
        return output

    def get_replicaset(self):
        cmd = "%s get replicaset --show-labels -o wide --all-namespaces" % self.cmd
        output = os.popen(cmd).read()
        return output

    def get_ns(self):
        cmd = "%s get ns" % self.cmd
        output = os.popen(cmd).read()
        return output

    def scale_replica(self, namespace, resource_type, resource, num_replica):
        ret = 0
        cmd = "%s scale --replica=%d %s/%s -n %s" % (self.cmd, num_replica, resource_type, resource, namespace)
        ret = os.system(cmd)
        return ret

    def get_deployment_by_jason(self, namespace, deployment):
        cmd = "%s get deployment %s -n %s -o json" % (self.cmd, deployment, namespace)
        output = json.loads(os.popen(cmd).read())
        return output

    def top_node(self, node_name):
        cmd = "%s top node %s" % (self.cmd, node_name)
        output = os.popen(cmd).read()
        return output

    def patch_deployment(self, namespace, deployment, output):
        cmd = '%s patch deployment %s --patch "$(cat %s)" -n %s' % (self.cmd, deployment, output, namespace)
        output = os.popen(cmd).read()
        return output
