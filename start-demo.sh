#!/bin/sh
#
##!/usr/bin/env bash

show_usage()
{
    cat << __EOF__

    Usage: $0 [-c <define.py>] -k <kubeconfig> -p "<parameters>"
           [-k OpenShift kubeconfig file] # e.g. -k .kubeconfig
           [-p Running parameters] # e.g. -p "-i 2 -c 20 -f 1 -n 1"
    Notes:
        - File .kubeconfig can be created by using the following command.
          sh -c "export KUBECONFIG=.kubeconfig; oc login <K8s_LOGIN_URL>"
          e.g. sh -c "export KUBECONFIG=.kubeconfig; oc login https://api.ocp4.example.com:6443"
        - Optional define environment variable 'VERSION_TAG' to specify version tag of demo application
          e.g. export VERSION_TAG='v4.2.801'
        - Optional define environment variable 'REPO_URL_PREFIX' to specify image repository url prefix
          e.g. export REPO_URL_PREFIX='repo.prophetservice.com/federatorai'
    Examples:
        - Run a simple test
          $0 -k .kubeconfig -p "-i 2 -c 20 -f 1 -n 1"
        - Show options for 'parameters' argument
          $0 -k .kubeconfig -p "-h"
__EOF__
#    Notes:
#       environment variable NGINX_PUBLIC_IP manually specified IP address of nginx route
    exit 1
}

# TRAP exit
on_exit()
{
    ret=$?
    [ "${pid_helper}" != "" ] && kill ${pid_helper} 2> /dev/null
    trap - EXIT # Disable exit handler
    exit ${ret}
}

apply_manager_deployment()
{
    oc apply -f - << __EOF__
---
apiVersion: v1
kind: Namespace
metadata:
  name: ${MANAGER_NAMESPACE}

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-demo-manager
  namespace: ${MANAGER_NAMESPACE}
  labels:
    app: nginx-demo-manager
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx-demo-manager
  template:
    metadata:
      labels:
        app: nginx-demo-manager
    spec:
      containers:
      - name: nginx-demo-manager
        image: ${REPO_URL_PREFIX}/federatorai-demo-nginx-manager:${VERSION_TAG}
        imagePullPolicy: Always
      nodeSelector:
        node-role.kubernetes.io/master: ""
      tolerations:
      - effect: NoSchedule
        key: node-role.kubernetes.io/master
        operator: Exists
__EOF__
    ## wait until pod become Running
    while :; do
        echo "Waiting demo-manager is ready ..."
        sleep 30
        [ "`oc -n ${MANAGER_NAMESPACE} get pods | egrep Running | grep nginx-demo-manager-`" != "" ] && break
    done

    return 0
}


apply_nginx_deployment()
{
    ## preparing testing environment (deploy nginx pods and service endpoint)
    oc -n ${MANAGER_NAMESPACE} exec -t ${manager_pod} -- sh -c "export KUBECONFIG=\`pwd\`/.kubeconfig; export REPO_URL_PREFIX=${REPO_URL_PREFIX}; export VERSION_TAG=${VERSION_TAG}; bash -x ./run.sh install"
    ## wait until pod become Running
    while :; do
        echo "Waiting demo-nginx is ready ..."
        sleep 30
        [ "`oc -n ${NGINX_NAMESPACE} get pods | egrep Running | grep ${NGINX_DEPLOYMENT_NAME}-`" != "" ] && break
    done

    return 0
}


add_nginx_url_host_aliases()
{
    _nginx_route=$1
    _nginx_public_ip=$2
    echo "Adding host aliases ${_nginx_route}:${_nginx_public_ip} into nginx-demo-manager deployment..."
    oc -n ${MANAGER_NAMESPACE} patch deployments nginx-demo-manager --patch \
    '{
      "spec": {
        "template": {
          "spec": {
            "hostAliases": [
              {
                "hostnames": [
                  "'${_nginx_route}'"
                ],
                "ip": "'${_nginx_public_ip}'"
              }
            ]
          }
        }
      }
    }'
    if [ "$?" != "0" ]; then
        echo "Failed in applying hostAliases patch."
        exit 1
    fi
    return 0
}

##
## Main
##
export LANG=C
trap on_exit EXIT INT # Assign exit handler
while getopts "c:hk:p:" o; do
    case "${o}" in
        c)
            config_define="${OPTARG}"
            ;;
        h)
            show_usage
            exit 0
            ;;
        k)
            kubeconfig="${OPTARG}"
            ;;
        p)
            parameter="${OPTARG}"
            ;;
        *)
            echo "Error! Invalid argument."
            show_usage
            exit 1
            ;;
    esac
done
[ "${parameter}" = "" -o "${kubeconfig}" = "" ] && show_usage && exit 1

## Global variables
[ "${session_id}" = "" ] && export session_id="`date +%s`"
[ "${REPO_URL_PREFIX}" = "" ] && export REPO_URL_PREFIX="quay.io/prophetstor"
[ "${VERSION_TAG}" = "" ] && export VERSION_TAG="stable"
manager_pod=""

## Environment variables
[ "${max_wait_pods_ready_time}" = "" ] && max_wait_pods_ready_time=900  # maximum wait time for pods become ready
[ "${avoid_metrics_interferece_sleep}" = "" ] && avoid_metrics_interferece_sleep=600  # maximum wait time for pods become ready

## Internal variables
NGINX_NAMESPACE="federatorai-demo-nginx"
MANAGER_NAMESPACE="federatorai-demo-manager"
NGINX_DEPLOYMENT_NAME="nginx-deployment"
export KUBECONFIG=${kubeconfig}

## Checking if cluster ready to use
if [ "`oc get ns kube-system | grep '^kube-system'`" = "" ]; then
    echo "Error. Failed in using K8S cluster."
    exit 1
fi

## create manager deployment if it is not exists
while :; do
    oc -n ${MANAGER_NAMESPACE} get deployment nginx-demo-manager > /dev/null 2>&1
    [ "$?" = "0" ] && break
    echo "Start deploying manager deployment ..."
    apply_manager_deployment
done

## Retrieve manager pod name
manager_pod="`oc -n ${MANAGER_NAMESPACE} get pods | grep 'Running' | grep nginx-demo-manager | awk '{print $1}'`"
if [ "${manager_pod}" != "" ]; then
    export manager_pod
    break
fi

## Update .kubeconfig inside manager
oc -n ${MANAGER_NAMESPACE} cp ${KUBECONFIG} ${manager_pod}:.kubeconfig
if [ "$?" != "0" ]; then
    echo "Failed in updating KUBECONFIG file into manager pod."
    exit 1
fi

## create nginx deployment if it is not exists
while :; do
    oc -n ${NGINX_NAMESPACE} get deployment ${NGINX_DEPLOYMENT_NAME} > /dev/null 2>&1
    [ "$?" = "0" ] && break
    echo "Start deploying nginx deployment ..."
    apply_nginx_deployment
done

## Check if the nginx_route accessible, master may not able to perform dns resolver properly
nginx_route=`oc get route -n ${NGINX_NAMESPACE} | grep -v NAME | head -1 | awk '{print $2}'`
msg="`oc -n ${MANAGER_NAMESPACE} exec ${manager_pod} -- curl --retry-max-time 5 -s -v ${nginx_route} 2>&1 | grep 'Could not resolve host'`"
if [ "${msg}" != "" ]; then
    # example msg "nginx-service-nginx.apps.ocp4.172-31-8-49.nip.io has address 172.31.8.49"
    nginx_public_ip="`host ${nginx_route} | grep 'has address' | awk '{print $NF}'`"
    ## Add host_aliases to manager deployment
    if [ "${nginx_public_ip}" = "" ]; then
        echo -e "\nError! Failed in getting nginx route.\n"
        exit 1
    fi
    add_nginx_url_host_aliases ${nginx_route} ${nginx_public_ip}
    ## Wait until new demo-manager pod created
    while :; do
        manager_pod="`oc -n ${MANAGER_NAMESPACE} get pods | grep 'Running' | grep nginx-demo-manager | awk '{print $1}'`"
        if [ "${manager_pod}" != "" ]; then
            ## Wait until the new pod contain spec.hostAliases.hostnames: ${nginx_route}
            if [ "`oc -n ${MANAGER_NAMESPACE} get pod ${manager_pod} -o yaml | grep \"${nginx_route}\"`" != "" ]; then
                export manager_pod
                break
            fi
        fi
        echo "Waiting the manager pod restarting..."
        sleep 30
    done
fi

## Start background running run.sh inside demo-manager pod
oc -n ${MANAGER_NAMESPACE} cp ${KUBECONFIG} ${manager_pod}:.kubeconfig
## Replace remote's define.py if user specified its file
[ "${config_define}" != "" ] && oc -n ${MANAGER_NAMESPACE} cp ${config_define} ${manager_pod}:define.py
#oc -n ${MANAGER_NAMESPACE} exec ${manager_pod} -- tail -f run.log &
#pid_helper=$!
oc -n ${MANAGER_NAMESPACE} exec ${manager_pod} -- sh -c "export avoid_metrics_interference_sleep=${avoid_metrics_interference_sleep}; export KUBECONFIG=\`pwd\`/.kubeconfig; nohup bash ./run.sh -k \${KUBECONFIG} ${parameter} > run.log 2>&1 &"

## Wait until the test in pod finished running
while :; do
    msg="`oc -n ${MANAGER_NAMESPACE} exec ${manager_pod} -- tail run.log | egrep 'Success in running all tests|Failed in running all tests'`"
    [ "${msg}" != "" ] && break
    echo "Waiting the tests completely running..."
    sleep 60
done

if [ "`echo \"${msg}\" | grep '^Failed'`" ]; then
    oc -n ${MANAGER_NAMESPACE} exec ${manager_pod} -- tail -20 run.log
    exit 1
fi
echo "Collecting testing result..."
## msg example: Success in running all tests with session id 1589278863.
session_id="`echo ${msg} | tr -d '.' | awk '{print $NF}'`"
oc -n ${MANAGER_NAMESPACE} exec ${manager_pod} -- sh -c "tar cf - \`find ./test_result/ -type d | grep ${session_id}$\` ./test_result/comparison_${session_id}.out" | tar xf -

##
echo "Testing result saved into the following directory."
ls -d test_result/*${session_id}/
exit 0

