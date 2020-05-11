import sys
import time
import os
import yaml
import shutil
from oc import OC
from datetime import datetime
from define import warm_up, metrics_path,  picture_path #, overprovision_replica
from define import initial_replica, traffic_path, cpu_limit, memory_limit
from define import k8shpa_type, k8shpa_percent, traffic_interval, interactive_mode


def clean_data(algo, namespace, resource_type, resource):
    output = OC().scale_replica(namespace, resource_type, resource, 0)
    #if algo in ["k8shpa", "alameda"]:
    output = OC().scale_replica(namespace, resource_type, resource, initial_replica)
    # else:
    #     output = OC().scale_replica(namespace, resource_type, resource, overprovision_replica)
    return output


def create_directory():
    dir_list = [traffic_path, metrics_path, picture_path, "output"]

    for path in dir_list:
        if not os.path.exists(path):
            os.mkdir(path)
            print "%s is created" % path
        elif os.path.exists(path):
            print "%s is existed" % path


def remove_directory():
    shutil.rmtree(traffic_path)
    shutil.rmtree(metrics_path)
    shutil.rmtree(picture_path)


def change_directory_name(dir_name):
    if os.path.exists(traffic_path):
        os.rename(traffic_path, dir_name)
        print "change %s to %s" % (traffic_path, dir_name)
    else:
        print "dir: %s is not existed" % traffic_path


def find_pod_name(app_name, app_namespace):
    pod_name_list = []
    status = ""
    output = OC().get_pods(app_namespace)
    for line in output.split("\n"):
        if line.find(app_name) != -1:
            pod_name = line.split()[0]
            if pod_name.find("build") != -1:
                continue
            status = line.split()[2]
            if status not in ["Running"]:
                raise Exception("%s is %s" % (pod_name, status))
            pod_name_list.append(pod_name)
    if not pod_name_list:
        raise Exception("%s is not existed in %s" % (app_name, app_namespace))
    return pod_name_list


def find_alameda_namespace(app_name):
    namespace = ""
    output = OC().get_pods_all_namespace()
    for line in output.split("\n"):
        if line.find(app_name) != -1:
            namespace = line.split()[0]
            break
    if namespace:
        print "find %s's namespace: %s" % (app_name, namespace)
    else:
        raise Exception("ns: %s is not existed" % namespace)
    return namespace


def restart_pod(app_name, app_namespace):
    output = ""
    pod_name_list = find_pod_name(app_name, app_namespace)
    for pod_name in pod_name_list:
        output = OC().delete_pod(pod_name, app_namespace)
        print output
    return output


def enable_executor():
    print "enable executor"
    output = OC().apply_file("alameda-executor-true.yaml")
    alameda_namespace = find_alameda_namespace("alameda-executor")
    get_executor_status(alameda_namespace, "true")
    return output


def disable_executor():
    print "disable executor"
    output = OC().apply_file("alameda-executor-false.yaml")
    alameda_namespace = find_alameda_namespace("alameda-executor")
    get_executor_status(alameda_namespace, "false")
    return output


def update_k8shpa_yaml(file_name, namespace, resource, percent):
    try:
        tmp_file_name = "./%s.tmp" % file_name
        with open(file_name, "r") as f_r:
            output = yaml.load(f_r)
            output["metadata"]["name"] = resource
            output["metadata"]["namespace"] = namespace
            output["spec"]["metrics"][0]["resource"]["targetAverageUtilization"] = percent
        with open(tmp_file_name, "w") as f_w:
            yaml.dump(output, f_w)
            f_w.close()
    except Exception as e:
        print "failed to update %s: %s" % (file_name, str(e))
        return -1
    os.rename(tmp_file_name, new_file_name)
    # print "success to update %s" % (new_file_name)
    return 0


def start_k8shpa(namespace, resource_type, resource, num_replica_max, percent):
    print "=== Start K8sHPA ===", k8shpa_type
    if k8shpa_type == "cpu":
        output = OC().autoscale_replica(namespace, resource_type, resource, num_replica_max, percent)
    elif k8shpa_type == "memory":
        file_name = "./k8shpa_memory.yaml"
        output = update_k8shpa_yaml(file_name, namespace, resource, percent)
        output = OC().apply_file(file_name)
    return output


def stop_k8shpa(namespace, resource):
    output = OC().delete_hpa(namespace, resource)
    return output


def get_dir_name(term):
    timestamp = int(time.time())
    dt_object = str(datetime.fromtimestamp(timestamp)).split()[0]
    dir_list = os.listdir(".")
    count = 0
    for dir in dir_list:
        if dir.find(term) != -1 and not os.path.isfile(dir):
            count += 1
    dir_name = "%s_%s_%d" % (term, dt_object, count)
    return dir_name


def get_executor_status(namespace, desired_status):
    output = OC().get_configmap(namespace, "alameda-executor-config")
    if output.find(desired_status) == -1:
        raise Exception("executor must be %s" % desired_status)


def update_yaml(namespace, enable):
    ret = 0
    output = {}

    file_name = "./alameda-executor.yaml"
    new_file_name = "./alameda-executor-%s.yaml" % str(enable)
    tmp_file_name = "%s.tmp" % file_name

    old_address = "alameda-datahub.federatorai.svc"
    new_address = "alameda-datahub.%s.svc" % namespace
    old_enable_value = "enable: false"
    new_enable_value = "enable: %s" % str(enable)
    try:
        with open(file_name, "r") as f_r:
            output = yaml.load(f_r)
            output["data"]["config.yml"] = output["data"]["config.yml"].replace(old_address, new_address)
            output["data"]["config.yml"] = output["data"]["config.yml"].replace(old_enable_value, new_enable_value)
            output["metadata"]["namespace"] = namespace
        with open(tmp_file_name, "w") as f_w:
            yaml.dump(output, f_w)
            f_w.close()
    except Exception as e:
        print "failed to update %s: %s" % (file_name, str(e))
        ret = -1
        return ret
    os.rename(tmp_file_name, new_file_name)
    # print "success to update %s" % (new_file_name)
    return ret


def find_app_location(app_name, namespace=""):
    app_namespace = ""
    app_type = ""
    resource = ""
    app_list = []
    output = OC().get_deployments_all_namespace()
    if output.find(app_name) != -1:
        for line in output.split("\n"):
            if line.find(app_name) != -1:
                app_namespace = line.split()[0]
                app_type = "deployment"
                resource = line.split()[1]
                app = {}
                app["namespace"] = app_namespace
                app["resource_type"] = app_type
                app["resource"] = resource
                app_list.append(app)
    output = OC().get_deploymentconfigs_all_namespace()
    if output.find(app_name) != -1:
        for line in output.split("\n"):
            if line.find(app_name) != -1:
                app_namespace = line.split()[0]
                app_type = "deploymentconfig"
                app_type = "deploymentconfig"
                resource = line.split()[1]
                app = {}
                app["namespace"] = app_namespace
                app["resource_type"] = app_type
                app["resource"] = resource
                app_list.append(app)
    if not app_list:
        raise Exception("app: %s is not existed" % app_name)

    # do not choose
    if namespace:
        for app in app_list:
            if app["namespace"] == namespace and app["resource"] == app_name:
                break
        return app_namespace, app_type, resource

    # show app
    i = 0
    print "\n"
    print "*******************************************************************"
    print "   Applications:"
    for app in app_list:
        print "    %d) namespace: %s   %s: %s" % (i, app["namespace"], app["resource_type"], app["resource"])
        i = i + 1
    print "*******************************************************************\n"
    x = 0
    if interactive_mode:
        sys.stdin = open('/dev/tty')
        try:
            x = raw_input("input prefered application (default:0): ")
            if not x:
                x = 0
        except Exception:
            x = 0
    x = int(x)
    app_namespace = app_list[x]["namespace"]
    app_type = app_list[x]["resource_type"]
    resource = app_list[x]["resource"]
    print "preferred application is %s/%s" % (app_namespace, resource)
    os.environ["NAMESPACE"] = app_namespace
    os.environ["RESOURCE"] = resource
    os.environ["RESOURCE_TYPE"] = app_type
    return app_namespace, app_type, resource


def get_image_name(app_namespace, app_type, resource):
    output = ""
    image_name = ""
    oc = OC()
    if app_type == "deploymentconfig":
        output = oc.get_specific_deploymentconfig(app_namespace, resource)
    elif app_type == "deployment":
        output = oc.get_specific_deployment(app_namespace, resource)
    if output:
        output = yaml.load(output)
        for container_info in output.get("spec").get("template").get("spec").get("containers"):
            if container_info.get("name") == resource:
                image_name = container_info.get("image")
                break
    return image_name


def update_app_limit(app_namespace, app_type, resource):
    output = {}
    result = ""
    if app_type == "deploymentconfig":
        result = OC().get_specific_deploymentconfig(app_namespace, resource)
    elif app_type == "deployment":
        result = OC().get_specific_deployment(app_namespace, resource)
    output = yaml.load(result)
    output["spec"]["template"]["spec"]["containers"][0]["resources"] = {}
    output["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"] = {}
    output["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"] = {}
    if cpu_limit != 0:
        output["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["cpu"] = str(cpu_limit) + "m"
        output["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]["cpu"] = str(cpu_limit) + "m"
    if memory_limit != 0:
        output["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["memory"] = str(memory_limit) + "Mi"
        output["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]["memory"] = str(memory_limit) + "Mi"
    output["metadata"].pop("creationTimestamp")
    output["metadata"].pop("generation")
    output["metadata"].pop("resourceVersion")
    output["metadata"].pop("selfLink")
    output["metadata"].pop("uid")
    output.pop("status")
    file_name = "./resource.yaml"
    tmp_file_name = "%s.tmp" % file_name
    try:
        with open(tmp_file_name, "w") as f_w:
            yaml.dump(output, f_w)
            f_w.close()
    except Exception as e:
        print "failed to update %s: %s" % (file_name, str(e))
        return -1
    os.rename(tmp_file_name, file_name)
    OC().apply_file(file_name)
    print "success to update limits(cpu=%dm and memory=%dMi) for %s" % (cpu_limit, memory_limit, resource)
    return 0


def check_metric_server():
    cmd = "kubectl top nodes >/dev/null; echo $? >/dev/null"
    ret = os.system(cmd)
    if ret != 0:
        raise Exception("failed to get metrics without metric-server")


def main(algo, action, namespace="", app_name=""):
    app_namespace = os.environ.get("NAMESPACE")
    app_type = os.environ.get("RESOURCE_TYPE")
    resource = os.environ.get("RESOURCE")
    if app_name:
        app_namespace, app_type, resource = find_app_location(app_name, namespace)
    if not resource or not app_namespace or not app_type:
        raise Exception("%s is not correct deployment/deploymentconfig" % resource)

    if algo == "alameda":
        if action == "start":
            pass
            # dir_name = get_dir_name("alameda")
            # cmd = "python ./run_alameda_hpa.py %s 2>&1 | tee output/%s.out &" % (traffic_interval, dir_name)
            # ret = os.system(cmd)

        elif action == "init":
            create_directory()
            clean_data(algo, app_namespace, app_type, resource)
            update_app_limit(app_namespace, app_type, resource)

        else:
            dir_name = get_dir_name("alameda")
            change_directory_name(dir_name)

    elif algo == "k8shpa":
        if action == "start":
            start_k8shpa(app_namespace, app_type, resource, 100, k8shpa_percent)

        elif action == "init":
            create_directory()
            clean_data(algo, app_namespace, app_type, resource)
            update_app_limit(app_namespace, app_type, resource)

        else:
            stop_k8shpa(app_namespace, resource)
            dir_name = get_dir_name("k8shpa")
            change_directory_name(dir_name)
    else:
        if action == "start":
            pass

        elif action == "init":
            create_directory()
            clean_data(algo, app_namespace, app_type, resource)
            update_app_limit(app_namespace, app_type, resource)

        else:
            dir_name = get_dir_name("nonhpa")
            change_directory_name(dir_name)


if __name__ == "__main__":
    algo = sys.argv[1]
    action = sys.argv[2]
    if len(sys.argv) == 3:
        main(algo, action)
    else:
        namespace = sys.argv[3]
        app_name = sys.argv[4]
        main(algo, action, namespace, app_name)
