import os


class OC:
    cmd = "oc"

    def __init__(self):
        ret = self.check_platform()
        if ret != 0:
            self.cmd = "kubectl"

    def check_platform(self):
        cmd = "oc > /dev/null 2>&1"
        ret = os.system(cmd)
        return ret

    def run_cmd(self, cmd):
        output = os.popen(cmd).read()
        return output

    def run_os_cmd(self, cmd):
        ret = os.system(cmd)
        return ret

    def describe_secret(self, namespace, pod):
        cmd = "%s describe secret %s -n %s" % (self.cmd, pod, namespace)
        output = self.run_cmd(cmd)
        return output

    def get_secret_by_specific_name(self, namespace, name):
        cmd = "%s get secret -n %s | grep %s" % (self.cmd, namespace, name)
        output = self.run_cmd(cmd)
        return output

    def get_pods(self, namespace):
        cmd = "%s get pods -n %s" % (self.cmd, namespace)
        output = self.run_cmd(cmd)
        return output

    def login(self, user, password):
        cmd = "%s login -u %s -p %s 2>&1 > /dev/null" % (self.cmd, user, password)
        ret = self.run_os_cmd(cmd)
        print "login Openshift by %s" % user
        return ret

    def get_deploymentconfig(self, ns):
        cmd = "%s get deploymentconfig -n %s" % (self.cmd, ns)
        output = self.run_cmd(cmd)
        return output

    def get_deployment(self, ns):
        cmd = "%s get deployment -n %s" % (self.cmd, ns)
        output = self.run_cmd(cmd)
        return output

    def apply_file(self, file_name):
        cmd = "%s apply -f %s" % (self.cmd, file_name)
        output = self.run_cmd(cmd)
        return output

    def delete_file(self, file_name):
        cmd = "%s delete -f %s" % (self.cmd, file_name)
        output = self.run_cmd(cmd)
        return output

    def new_app_postgresql(self, username, password, database):
        cmd = "%s new-app -e POSTGRESQL_USER=%s -e POSTGRESQL_PASSWORD=%s -e POSTGRESQL_DATABASE=%s centos/postgresql-95-centos7" % (self.cmd, username, password, database)
        output = self.run_cmd(cmd)
        return output

    def set_pod_env_list(self, pod_name):
        cmd = "%s set env pod %s --list" % (self.cmd, pod_name)
        output = self.run_cmd(cmd)
        return output

    def exec_cmd(self, namespace, pod_name, command):
        cmd = "%s exec -it %s -- bash -c '%s' -n %s" % (self.cmd, pod_name, command, namespace)
        output = self.run_cmd(cmd)
        return output

    def expose_service(self, namespace, service_name):
        cmd = "%s expose %s -n %s" % (self.cmd, service_name, namespace)
        output = self.run_cmd(cmd)
        return output

    def get_routes(self, namespace):
        cmd = "%s get routes -n %s" % (self.cmd, namespace)
        output = self.run_cmd(cmd)
        return output

    def get_service(self, namespace):
        cmd = "%s get service -n %s" % (self.cmd, namespace)
        output = self.run_cmd(cmd)
        return output

    def scale_replica(self, namespace, resource_type, resource, num_replica):
        cmd = "%s scale %s %s --replicas=%d -n %s" % (self.cmd, resource_type, resource, num_replica, namespace)
        output = self.run_cmd(cmd)
        return output

    def enable_alamedascaler_execution(self, namespace, scaler_name):
        cmd = '%s patch alamedascaler %s --type merge --patch "{\\"spec\\":{\\"enableExecution\\": true}}" -n %s' % (self.cmd, scaler_name, namespace)
        print cmd
        output = self.run_cmd(cmd)
        return output

    def disable_alamedascaler_execution(self, namespace, scaler_name):
        cmd = '%s patch alamedascaler %s --type merge --patch "{\\"spec\\":{\\"enableExecution\\": false}}" -n %s' % (self.cmd, scaler_name, namespace)
        print cmd
        output = self.run_cmd(cmd)
        return output

    def get_pod_json(self, pod, namespace):
        cmd = "%s get pod %s -n %s -o json" % (self.cmd, pod, namespace)
        output = self.run_cmd(cmd)
        return output

    def get_nodes(self):
        cmd = "%s get nodes" % self.cmd
        output = self.run_cmd(cmd)
        return output

    def delete_pod(self, pod_name, namespace):
        cmd = "%s delete pod %s -n %s" % (self.cmd, pod_name, namespace)
        output = self.run_cmd(cmd)
        return output

    def autoscale_replica(self, namespace, resource_type, resource, num_replica_max, percent):
        cmd = "%s autoscale %s %s --max=%d --cpu-percent=%s -n %s" % (self.cmd, resource_type, resource, num_replica_max, percent, namespace)
        output = self.run_cmd(cmd)
        return output

    def delete_hpa(self, namespace, resource):
        cmd = "%s delete hpa %s -n %s 2>/dev/null" % (self.cmd, resource, namespace)
        output = self.run_cmd(cmd)
        return output

    def get_pods_all_namespace(self):
        cmd = "%s get pods --all-namespaces" % self.cmd
        output = self.run_cmd(cmd)
        return output

    def get_deployments_all_namespace(self):
        cmd = "%s get deployments --all-namespaces 2>/dev/null" % self.cmd
        output = self.run_cmd(cmd)
        return output

    def get_deploymentconfigs_all_namespace(self):
        cmd = "%s get deploymentconfigs --all-namespaces 2>/dev/null" % self.cmd
        output = self.run_cmd(cmd)
        return output

    def get_alamedascaler_name(self, app_namespace):
        cmd = "%s get alamedascaler -n %s -o=jsonpath='{.items[0].metadata.name}'" % (self.cmd, app_namespace)
        output = self.run_cmd(cmd)
        return output

    def get_specific_deploymentconfig(self, app_namespace, resource):
        cmd = "%s get deploymentconfig %s -n %s -o yaml" % (self.cmd, resource, app_namespace)
        output = self.run_cmd(cmd)
        return output

    def get_specific_deployment(self, app_namespace, resource):
        cmd = "%s get deployment %s -n %s -o yaml" % (self.cmd, resource, app_namespace)
        print cmd
        output = self.run_cmd(cmd)
        return output

    def patch_deployment(self, namespace, deployment, output):
        cmd = '%s patch deployment %s --patch "$(cat %s)" -n %s' % (self.cmd, deployment, output, namespace)
        print cmd
        output = self.run_cmd(cmd)
        return output

    def patch_deploymentconfig(self, namespace, deploymentconfig, output):
        cmd = '%s patch deploymentconfig %s --patch "$(cat %s)" -n %s' % (self.cmd, deploymentconfig, output, namespace)
        output = self.run_cmd(cmd)
        return output

    def get_configmap(self, namespace, configmap):
        cmd = "%s get configmap %s -n %s -o json" % (self.cmd, configmap, namespace)
        output = self.run_cmd(cmd)
        return output
