#!/usr/bin/env bash

show_usage()
{
    cat << __EOF__

    Usage:
        Requirement:
            [-k OpenShift kubeconfig file] # e.g. -k .kubeconfig
              File .kubeconfig can be created by using the following command.
                (export KUBECONFIG=.kubeconfig; oc login [URL])
            [-i Initial nginx replica number] # e.g. -i 10
        Optional options:
            [-c Native HPA cpu percent] # For Native HPA (CPU) test, run with -o option. e.g. -o 40 -c 20
            [-z] # Install Nginx.
        Optional Tests: 
            #(Multiple choices supported)
            [-f Federator.ai HPA test duration(min)] # e.g. -f 60 
            [-n Non HPA test duration(min)] # e.g. -n 60
            [-o Native HPA (CPU) test duration(min)] # e.g. -o 40

__EOF__
    exit 1
}

check_python_command()
{
    which python > /dev/null 2>&1
    if [ "$?" != "0" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to locate python command. Pls make sure \"python\" command exist.$(tput sgr 0)"
        exit 1
    fi
}

check_version()
{
    oc version 2>/dev/null|grep -q "Server Version: 4"
    if [ "$?" != "0" ];then
        echo -e "\n$(tput setaf 10)Error! Only OpenShift version 4.x is supported.$(tput sgr 0)"
        exit 5
    fi
}

pods_ready()
{
  [[ "$#" == 0 ]] && return 0

  namespace="$1"

  kubectl get pod -n $namespace \
    -o=jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Ready")].status}{"\t"}{.status.phase}{"\t"}{.status.reason}{"\n"}{end}' \
      | while read name status phase reason _junk; do
          if [ "$status" != "True" ]; then
            msg="Waiting pod $name in namespace $namespace to be ready."
            [ "$phase" != "" ] && msg="$msg phase: [$phase]"
            [ "$reason" != "" ] && msg="$msg reason: [$reason]"
            echo "$msg"
            return 1
          fi
        done || return 1

  return 0
}

wait_until_pods_ready()
{
  period="$1"
  interval="$2"
  namespace="$3"
  target_pod_number="$4"

  wait_pod_creating=1
  for ((i=0; i<$period; i+=$interval)); do

    if [[ "$wait_pod_creating" = "1" ]]; then
        # check if pods created
        if [[ "`kubectl get po -n $namespace 2>/dev/null|wc -l`" -ge "$target_pod_number" ]]; then
            wait_pod_creating=0
            echo -e "\nChecking pods..."
        else
            echo "Waiting for pods in namespace $namespace to be created..."
        fi
    else
        # check if pods running
        if pods_ready $namespace; then
            echo -e "\nAll $namespace pods are ready."
            return 0
        fi
        echo "Waiting for pods in namespace $namespace to be ready..."
    fi

    sleep "$interval"

  done

  echo -e "\n$(tput setaf 1)Warning!! Waited for $period seconds, but all pods are not ready yet. Please check $namespace namespace$(tput sgr 0)"
  leave_prog
  exit 4
}

leave_prog()
{
    if [ ! -z "$(ls -A $file_folder)" ]; then      
        echo -e "\n$(tput setaf 6)Test result files are located under $file_folder $(tput sgr 0)"
    fi
 
    cd $current_location > /dev/null
}

get_variables_from_define_file()
{
    # String
    prometheus_namespace=`grep "prometheus_namespace" define.py| awk -F '"' '{print $2}'`
    if [ "$prometheus_namespace" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to parse prometheus_namespace setting from define.py\n$(tput sgr 0)"
        exit
    fi
    nginx_namespace=`grep "nginx_namespace" define.py| awk -F '"' '{print $2}'`
    if [ "$nginx_namespace" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to parse nginx_namespace setting from define.py\n$(tput sgr 0)"
        exit
    fi
    # Number
    #consumer_memory_limit=`grep "consumer_memory_limit" define.py| awk -F '=' '{print $NF}'| egrep -o "[0-9]*"`
}

check_nginx_env()
{
    nginx_deployment_name=`kubectl get deploy -n $nginx_namespace 2>/dev/null|grep -v NAME|head -1|awk '{print $1}'`
    if [ "$nginx_deployment_name" = "" ]; then
        nginx_deployment_name=`kubectl get dc -n $nginx_namespace 2>/dev/null|grep -v NAME|head -1|awk '{print $1}'`
        if [ "$nginx_deployment_name" = "" ]; then
            echo -e "\n$(tput setaf 1)Error! Failed to find Nginx deployment or deploymentconfig.\n$(tput sgr 0)"
            echo -e "$(tput setaf 2)Please install Nginx or check your nginx_namespace setting in define.py$(tput sgr 0)"
            exit
        fi
    fi

    nginx_svc_name=`oc get svc -n $nginx_namespace|grep -v NAME|head -1|awk '{print $1}'`
    if [ "$nginx_svc_name" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to get nginx svc name.\n$(tput sgr 0)"
        exit
    fi
}

modify_env_settings_in_define()
{
    # Prometheus (openshift4.x) endpoint
    prometheus_route=`oc get route -n $prometheus_namespace|grep 'prometheus-k8s'|awk '{print $2}'`
    if [ "$prometheus_route" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to get prometheus route.\n$(tput sgr 0)"
        exit
    fi
    prometheus_endpoint="https://$prometheus_route/api/v1"
    sed -i "s|prometheus_endpoint.*|prometheus_endpoint = \"$prometheus_endpoint\"|g" define.py

    # Prometheus (openshift4.x) token
    secret_name=`oc get secret -n $prometheus_namespace -o name|grep 'prometheus-k8s-token-'|head -1`
    prometheus_token=`oc describe $secret_name -n openshift-monitoring|grep "token:"|awk '{print $2}'`
    if [ "$prometheus_token" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to get prometheus token.\n$(tput sgr 0)"
        exit
    fi
    sed -i "s|prometheus_token.*|prometheus_token = \"$prometheus_token\"|g" define.py

    nginx_route=`oc get route -n $nginx_namespace|grep -v NAME|head -1|awk '{print $2}'`
    if [ "$nginx_route" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to get nginx route.\n$(tput sgr 0)"
        exit
    fi
    sed -i "s|app_service_ip.*|app_service_ip = \"$nginx_route\"|g" define.py
}

modify_define_parameter()
{
    run_duration="$1"
    
    sed -i "s/traffic_interval.*/traffic_interval = $run_duration # generate traffic per 1 minute during 72 minutes/g" define.py
    sed -i "s/data_interval.*/data_interval = $run_duration # collect pods' resource utilization # init: 80 minutes/g" define.py

    sed -i "s/initial_replica.*/initial_replica = $initial_nginx_number /g" define.py

    if [ "$cpu_percent_specified" = "y" ]; then
        sed -i "s/k8shpa_percent.*/k8shpa_percent = $cpu_percent /g" define.py
    fi

    if [ "$test_type" = "federatoraihpa" ]; then 
        sed -i "s/number_alamedahpa.*/number_alamedahpa = 1/g" define.py
        sed -i "s/number_k8shpa.*/number_k8shpa = 0/g" define.py
        sed -i "s/number_nonhpa.*/number_nonhpa = 0/g" define.py
    elif [ "$test_type" = "k8shpa_cpu" ]; then
        sed -i "s/number_alamedahpa.*/number_alamedahpa = 0/g" define.py
        sed -i "s/number_k8shpa.*/number_k8shpa = 1/g" define.py
        sed -i "s/number_nonhpa.*/number_nonhpa = 0/g" define.py
        sed -i "s/k8shpa_type.*/k8shpa_type = \"cpu\"/g" define.py
    elif [ "$test_type" = "nonhpa" ]; then
        sed -i "s/number_alamedahpa.*/number_alamedahpa = 0/g" define.py
        sed -i "s/number_k8shpa.*/number_k8shpa = 0/g" define.py
        sed -i "s/number_nonhpa.*/number_nonhpa = 1/g" define.py
    fi
}

patch_alamedaservice_for_nginx()
{
    nginx_enabled=`kubectl get alamedaservice $alamedaservice_name -n $install_namespace -o yaml|grep "nginx:" -A1|grep "enabled"|awk '{print $2}'`
    if [ "$nginx_enabled" != "true" ]; then
        alamedaservice_file="patch.alamedaservice.yaml"
        cat > ${alamedaservice_file} << __EOF__
spec:
  nginx:
    enabled: true
__EOF__
        echo "Patching alamedaservice for enabling nginx feature..."
        kubectl patch alamedaservice $alamedaservice_name -n $install_namespace --type merge --patch "$(cat $alamedaservice_file)"
        if [ "$?" != "0" ];then
            echo -e "\n$(tput setaf 1)Error! Failed to patch alamedaservice $alamedaservice_name.$(tput sgr 0)"
            exit 8
        fi
        nginx_enabled=`kubectl get alamedaservice $alamedaservice_name -n $install_namespace -o yaml|grep "nginx:" -A1|grep "enabled"|awk '{print $2}'`
        if [ "$nginx_enabled" != "true" ]; then
            echo -e "\n$(tput setaf 1)Error! Patch alamedaservice $alamedaservice_name failed.$(tput sgr 0)"
        fi
        wait_until_pods_ready $max_wait_pods_ready_time 30 $install_namespace 5
        echo "Done."
    fi
}

restart_recommender_pod()
{
    recommender_pod_name=`kubectl get pods -n $install_namespace -o name |grep "alameda-recommender-"|cut -d '/' -f2`
    kubectl delete pod $recommender_pod_name -n $install_namespace
    if [ "$?" != "0" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to delete recommender_pod_name pod $recommender_pod_name$(tput sgr 0)"
        leave_prog
        exit 8
    fi
    wait_until_pods_ready $max_wait_pods_ready_time 30 $install_namespace 5
}

apply_alamedascaler()
{
    execution_enabled="$1"
    sed -i "s/  namespace:.*/  namespace: $nginx_namespace/g" $alamedascaler_file
    sed -i "s/  enableExecution:.*/  enableExecution: $execution_enabled/g" $alamedascaler_file
    sed -i "s/    service:.*/    service: $nginx_svc_name/g" $alamedascaler_file
    kubectl apply -f $alamedascaler_file
    if [ "$?" != "0" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to apply $alamedascaler_file $(tput sgr 0)"
        leave_prog
        exit 8
    fi
}

sleep_interval_func()
{
    echo "Sleeping ${avoid_metrics_interference_sleep} seconds to avoid interference..."
    # Always restart recommender before testing
    restart_recommender_pod

    # Sleep 10 minutes to avoid metrics interfere
    if [ "$previous_test" = "y" ]; then
        sleep $avoid_metrics_interference_sleep
    fi
}

nonhpa_test_func()
{
    if [ "$nonhpa_test" = "y" ]; then
        sleep_interval_func
        scale_nginx_deployment
        previous_test="y"
        start=`date +%s`
        run_nonhpa_hpa_test
        end=`date +%s`
        duration=$((end-start))
        echo -e "\n$(tput setaf 6)It takes $(convertsecs $duration) to finish Non HPA test.$(tput sgr 0)"
    fi
}

native_hpa_cpu_test_func()
{
    if [ "$native_cpu_test" = "y" ]; then
        sleep_interval_func
        scale_nginx_deployment
        previous_test="y"
        start=`date +%s`
        run_native_k8s_hpa_cpu_test
        end=`date +%s`
        duration=$((end-start))
        echo -e "\n$(tput setaf 6)It takes $(convertsecs $duration) to finish Native HPA (CPU) test.$(tput sgr 0)"
    fi
}

federatorai_hpa_test_func()
{
    if [ "$federatorai_test" = "y" ]; then
        sleep_interval_func
        scale_nginx_deployment
        previous_test="y"
        start=`date +%s`
        run_federatorai_hpa_test
        end=`date +%s`
        duration=$((end-start))
        echo -e "\n$(tput setaf 6)It takes $(convertsecs $duration) to finish Federator.ai HPA test.$(tput sgr 0)"
    fi
}

get_alamedaservice_version()
{
    alameda_version=`kubectl get alamedaservice --all-namespaces|grep -v 'EXECUTION'|awk '{print $4}'|awk -F'.' '{print $NF}'`
}

convertsecs() 
{
    ((h=${1}/3600))
    ((m=(${1}%3600)/60))
    ((s=${1}%60))
    printf "%02d:%02d:%02d\n" $h $m $s
}

find_test_result_folder_name()
{
    if [ "$test_type" = "federatoraihpa" ]; then 
        result_folder_name=`find . -maxdepth 1 -type d -name 'alameda*'|head -n 1|awk -F '/' '{print $NF}'`
    elif [ "$test_type" = "k8shpa_cpu" ]; then
        result_folder_name=`find . -maxdepth 1 -type d -name 'k8shpa*'|head -n 1|awk -F '/' '{print $NF}'`
    elif [ "$test_type" = "nonhpa" ]; then
        result_folder_name=`find . -maxdepth 1 -type d -name 'nonhpa*'|head -n 1|awk -F '/' '{print $NF}'`
    fi

    if [ "$result_folder_name" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Can't find HPA test resuilt folder.$(tput sgr 0)"
        leave_prog
        exit 4
    fi
}

collect_results()
{
    target_folder="$1"
    target_folder_short_name="$2"
    target_start="$3"
    target_end="$4"

    target_duration=$((target_end-target_start))

    find_test_result_folder_name
    echo "test_result_folder= $result_folder_name"
    echo "====== count_ab1.py ======" > $file_folder/$target_folder/result_statistics
    python -u count_ab1.py $result_folder_name >> $file_folder/$target_folder/result_statistics
    echo "====== count_metrics1.py ======" >> $file_folder/$target_folder/result_statistics
    python -u count_metrics1.py $result_folder_name >> $file_folder/$target_folder/result_statistics
    echo "====== done ======" >> $file_folder/$target_folder/result_statistics
    mv $result_folder_name $target_folder_short_name
    echo "Test start - $target_start" >> $file_folder/$target_folder/result_statistics
    echo "Test end   - $target_end" >> $file_folder/$target_folder/result_statistics
    echo "It takes $(convertsecs $target_duration) to finish test." >> $file_folder/$target_folder/result_statistics

    # lag_result=`grep "avg. prom. query lag = " $file_folder/$target_folder/result_statistics |awk '{print $NF}'`
    # if [ "$lag_result" = "" ]; then
    #     echo -e "\n$(tput setaf 1)Error! Failed to parse average consumer lag result.\n$(tput sgr 0)"
    #     # continue test without exit
    # fi
    # replica_result=`grep "\-\-\- consumer" -A10 $file_folder/$target_folder/result_statistics |grep "avg. replicas"|awk '{print $NF}'`
    # if [ "$replica_result" = "" ]; then
    #     echo -e "\n$(tput setaf 1)Error! Failed to parse average replica(s) result.\n$(tput sgr 0)"
    #     # continue test without exit
    # fi

    # Get recommender & prediction log
    mkdir -p $file_folder/$target_folder/recommender
    mkdir -p $file_folder/$target_folder/prediction/log
    mkdir -p $file_folder/$target_folder/prediction/model

    recommender_pod_name=`kubectl get pods -n $install_namespace -o name |grep "alameda-recommender-"|cut -d '/' -f2`
    ai_pod_name=`kubectl get pods -n $install_namespace -o name |grep "alameda-ai-"|grep -v "alameda-ai-dispatcher"|cut -d '/' -f2`
    kubectl logs $recommender_pod_name -n $install_namespace > $file_folder/$target_folder/recommender/log
    kubectl exec $ai_pod_name -n $install_namespace -- tar -zcvf - /var/log/alameda/alameda-ai > $file_folder/$target_folder/prediction/log/log.tar.gz
    kubectl exec $ai_pod_name -n $install_namespace -- tar -zcvf - /var/lib/alameda/alameda-ai/models/online/workload_prediction > $file_folder/$target_folder/prediction/model/model.tar.gz

    mv $target_folder_short_name metrics picture output $file_folder/$target_folder
    cp define.py $file_folder/$target_folder

}

scale_nginx_deployment()
{
    kubectl scale deploy $nginx_deployment_name -n $nginx_namespace --replicas=$initial_nginx_number
    if [ "$?" != "0" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to scale nginx deployment $nginx_deployment_name in namespace $nginx_namespace $(tput sgr 0)"
        exit 1
    fi
    wait_until_pods_ready $max_wait_pods_ready_time 30 $nginx_namespace $initial_nginx_number
}

run_federatorai_hpa_test()
{
    # Federator.ai test
    cd $current_location

    # Do clean up
    hpa_cleanup
    ./cleanup.sh

    test_type="federatoraihpa"
    modify_define_parameter $federatorai_test_duration
    federatorai_test_folder_name="federatorai_hpa_${run_duration}min_${initial_nginx_number}init_${session_id}"
    federatorai_test_folder_short_name="fedai${run_duration}m${initial_nginx_number}i${alameda_version}B"
    mkdir -p $file_folder/$federatorai_test_folder_name
    apply_alamedascaler "true"

    start=`date +%s`
    echo -e "\n$(tput setaf 2)Running Federator.ai Nginx test...$(tput sgr 0)"
    python -u run_main.py hpa $nginx_deployment_name |tee -i $file_folder/$federatorai_test_folder_name/console_output.log
    end=`date +%s`

    echo "Collecting statistics..."
    collect_results "$federatorai_test_folder_name" "$federatorai_test_folder_short_name" "$start" "$end"
    # federatorai_avg_lag=$lag_result
    # federatorai_avg_replicas=$replica_result
    echo -e "\n$(tput setaf 6)Federator.ai test is finished.$(tput sgr 0)"
    # echo -e "$(tput setaf 6)Average Consumer Group Lag is $(tput sgr 0)$(tput setaf 10)\"$federatorai_avg_lag\"$(tput sgr 0)"
    # echo -e "$(tput setaf 6)Average Replica is $(tput sgr 0)$(tput setaf 10)\"$federatorai_avg_replicas\"$(tput sgr 0)"
    echo -e "$(tput setaf 6)Result files are under $file_folder/$federatorai_test_folder_name $(tput sgr 0)"

    # Turn off execution before next test
    apply_alamedascaler "false"
}

run_native_k8s_hpa_cpu_test()
{
    # Native HPA (CPU) test
    cd $current_location

    # Do clean up
    hpa_cleanup
    ./cleanup.sh

    test_type="k8shpa_cpu"
    modify_define_parameter $native_cpu_test_duration
    native_hpa_test_folder_name="native_hpa_cpu${cpu_percent}_${run_duration}min_${initial_nginx_number}init_${session_id}"
    native_hpa_test_folder_short_name="k8shpa${cpu_percent}c${run_duration}m${initial_nginx_number}i${alameda_version}B"
    mkdir -p $file_folder/$native_hpa_test_folder_name
    apply_alamedascaler "false"

    start=`date +%s`
    echo -e "\n$(tput setaf 2)Running Native HPA (CPU) Nginx test...$(tput sgr 0)"
    python -u run_main.py hpa $nginx_deployment_name |tee -i $file_folder/$native_hpa_test_folder_name/console_output.log
    end=`date +%s`

    echo "Collecting statistics..."
    collect_results "$native_hpa_test_folder_name" "$native_hpa_test_folder_short_name" "$start" "$end"
    # native_hpa_cpu_test_avg_lag=$lag_result
    # native_hpa_cpu_test_avg_replicas=$replica_result
    echo -e "\n$(tput setaf 6)Native HPA (CPU) test is finished.$(tput sgr 0)"
    # echo -e "$(tput setaf 6)Average Consumer Group Lag is $(tput sgr 0)$(tput setaf 10)\"$native_hpa_cpu_test_avg_lag\"$(tput sgr 0)"
    # echo -e "$(tput setaf 6)Average Replica is $(tput sgr 0)$(tput setaf 10)\"$native_hpa_cpu_test_avg_replicas\"$(tput sgr 0)"
    echo -e "Result files are under $file_folder/$native_hpa_test_folder_name $(tput sgr 0)"
}

run_nonhpa_hpa_test()
{
    # Non HPA test
    cd $current_location

    # Do clean up
    hpa_cleanup
    ./cleanup.sh

    test_type="nonhpa"
    modify_define_parameter $nonhpa_test_duration
    nonhpa_test_folder_name="non_hpa_${run_duration}min_${initial_nginx_number}init_${session_id}"
    nonhpa_test_folder_short_name="nonhpa${run_duration}m${initial_nginx_number}i${alameda_version}B"
    mkdir -p $file_folder/$nonhpa_test_folder_name
    apply_alamedascaler "false"

    start=`date +%s`
    echo -e "\n$(tput setaf 2)Running Non HPA Nginx test...$(tput sgr 0)"
    python -u run_main.py hpa $nginx_deployment_name |tee -i $file_folder/$nonhpa_test_folder_name/console_output.log
    end=`date +%s`

    echo "Collecting statistics..."
    collect_results "$nonhpa_test_folder_name" "$nonhpa_test_folder_short_name" "$start" "$end"
    # nonhpa_avg_lag=$lag_result
    # nonhpa_avg_replicas=$replica_result
    echo -e "\n$(tput setaf 6)NonHPA test is finished.$(tput sgr 0)"
    # echo -e "$(tput setaf 6)Average Consumer Group Lag is $(tput sgr 0)$(tput setaf 10)\"$nonhpa_avg_lag\"$(tput sgr 0)"
    # echo -e "$(tput setaf 6)Average Replica is $(tput sgr 0)$(tput setaf 10)\"$nonhpa_avg_replicas\"$(tput sgr 0)"
    echo -e "$(tput setaf 6)Result files are under $file_folder/$nonhpa_test_folder_name $(tput sgr 0)"
}

hpa_cleanup()
{
    for name in `kubectl get hpa -n $nginx_namespace -o name`
    do

        kubectl delete $name >/dev/null 2>&1

    done
}

install_nginx()
{
    kubectl get svc -n $nginx_namespace | grep -iq "nginx-service"
    retValue="$?"

    if [ "$retValue" != "0" ]; then
        echo -e "\n$(tput setaf 2)Installing Nginx...$(tput sgr 0)"
        oc projects 2>/dev/null|grep -q "$nginx_namespace"
        if [ "$?" != "0" ]; then
            oc new-project $nginx_namespace
        else
            oc project $nginx_namespace
        fi

        file_lists="nginx_route.yaml nginx_service.yaml nginx_deployment.yaml"
        # Modify nginx yamls
        for file in $file_lists
        do
            sed -i "s|namespace:.*|namespace: $nginx_namespace|g" nginx/$file
        done

        # Install NGINX
        oc adm policy add-scc-to-user anyuid -z default
        for file in $file_lists
        do
            oc apply -f nginx/$file
            if [ "$?" != "0" ]; then
                echo -e "\n$(tput setaf 1)Error! Failed to apply $file in namespace $nginx_namespace $(tput sgr 0)"
                exit 1
            fi
        done
        
        wait_until_pods_ready $max_wait_pods_ready_time 30 $nginx_namespace 2
        echo -e "\n$(tput setaf 2)Done.$(tput sgr 0)"
    fi
}

check_up_env()
{   
    get_variables_from_define_file
}   

do_install()
{
    get_variables_from_define_file
    install_nginx
    return $?
}

add_nginx_url_host_aliases()
{
    _nginx_route=`oc get route -n $nginx_namespace|grep -v NAME|head -1|awk '{print $2}'`
    if [ "$_nginx_route" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Failed to get nginx route.\n$(tput sgr 0)"
        exit
    fi
    oc -n federatorai-demo-manager patch deployments nginx-demo-manager --patch \
    '{
      "spec": {
        "template": {
          "spec": {
            "hostAliases": [
              {
                "hostnames": [
                  "'${_nginx_route}'"
                ],
                "ip": "'${NGINX_PUBLIC_IP}'"
              }
            ]
          }
        }
      }
    }'


}

##
## Main
##
if [ "$#" -eq "0" ]; then
    show_usage
    exit
fi

if [ "$1" = "install" ]; then
    do_install
    exit $?
fi

[ "${max_wait_pods_ready_time}" = "" ] && max_wait_pods_ready_time=900  # maximum wait time for pods become ready
[ "${avoid_metrics_interference_sleep}" = "" ] && avoid_metrics_interference_sleep=600  # maximum wait time for pods become ready

while getopts "hi:f:n:o:c:k:" o; do
    case "${o}" in
        k)
            kubeconfig="${OPTARG}"
            ;;
        i)
            initial_nginx_number_specified="y"
            initial_nginx_number=${OPTARG}
            ;;
        f)
            federatorai_test="y"
            federatorai_test_duration=${OPTARG}
            ;;
        n)
            nonhpa_test="y"
            nonhpa_test_duration=${OPTARG}
            ;;
        o)
            native_cpu_test="y"
            native_cpu_test_duration=${OPTARG}
            ;;
        c)
            cpu_percent_specified="y"
            cpu_percent=${OPTARG}
            ;;
        h)
            show_usage
            exit
            ;;
        *)
            echo "Error! Invalid parameter."
            show_usage
            ;;
    esac
done

## Global variables
file_folder="./test_result"
alamedascaler_file="config/nginx_alamedascaler.yaml"
[ "${session_id}" = "" ] && session_id="`date +%s`"
current_location=`pwd`

if [ "${kubeconfig}" = "" ]; then
    echo -e "\n$(tput setaf 1)Error! Need to use \"-k\" to specify openshift kubeconfig file.$(tput sgr 0)"
    echo -e "$(tput setaf 1)  You can run the following command to generate a kubeconfig file.$(tput sgr 0)"
    echo -e "$(tput setaf 1)   (export KUBECONFIG=.kubeconfig; oc login [URL])$(tput sgr 0)"
    show_usage
fi
export KUBECONFIG=${kubeconfig}

if [ "$native_cpu_test" = "y" ]; then
    if [ "$cpu_percent_specified" != "y" ] || [ "$cpu_percent" = "" ]; then
        echo -e "\n$(tput setaf 1)Error! Need to use \"-c\" to specify cpu percent for native HPA (CPU) test.$(tput sgr 0)" && show_usage
    fi
fi

if [ "$federatorai_test" = "y" ] || [ "$nonhpa_test" = "y" ] || [ "$native_cpu_test" = "y" ]; then
    if [ "$initial_nginx_number_specified" != "y" ]; then
        echo -e "\n$(tput setaf 1)Error! Need to use \"-i\" to specify initial nginx replica number.$(tput sgr 0)" && show_usage
    fi

    case $initial_nginx_number in
        ''|*[!0-9]*) echo -e "\n$(tput setaf 1)Error! Initial nginx replica number must be a number.$(tput sgr 0)" && show_usage;;
    esac
fi

# Check if kubectl connect to server.
result="`echo ""|kubectl cluster-info 2>/dev/null`"
if [ "$?" != "0" ]; then
    echo -e "\n$(tput setaf 1)Error! Please login into OpenShift cluster first.$(tput sgr 0)"
    exit
fi
current_server="`echo $result|sed 's/.*at //'|awk '{print $1}'`"
echo "You are connecting to cluster: $current_server"

install_namespace="`kubectl get pods --all-namespaces |grep "alameda-ai-"|awk '{print $1}'|head -1`"

if [ "$install_namespace" = "" ];then
    echo -e "\n$(tput setaf 1)Error! Please install Federatorai before running this script.$(tput sgr 0)"
    exit 3
fi

alamedaservice_name="`kubectl get alamedaservice -n $install_namespace -o jsonpath='{range .items[*]}{.metadata.name}'`"
if [ "$alamedaservice_name" = "" ]; then
    echo -e "\n$(tput setaf 1)Error! Failed to get alamedaservice name.$(tput sgr 0)"
    exit 8
fi

if [ ! -f "requirements.done" ]; then
    default="n"
    read -r -p "$(tput setaf 2)It seems install.sh has not been executed. Do you want to continue? [default: n]: $(tput sgr 0)" continue_anyway </dev/tty
    continue_anyway=${continue_anyway:-$default}
    if [ "$continue_anyway" = "y" ]; then
        touch requirements.done
    else
        exit 0
    fi
fi

echo "Checking OpenShift version..."
check_version
echo "...Passed"

echo "Checking environment..."
check_up_env
check_python_command

# Enable NGINX feature
patch_alamedaservice_for_nginx
get_alamedaservice_version

install_nginx


check_nginx_env
modify_env_settings_in_define
apply_alamedascaler "false"

previous_test="n"

cd ${current_location}
mkdir -pv $file_folder
nonhpa_test_func
federatorai_hpa_test_func
native_hpa_cpu_test_func

echo "Success in running all tests with session id ${session_id}."
exit 0
