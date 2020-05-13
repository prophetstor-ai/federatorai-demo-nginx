#!/bin/sh
#
##!/usr/bin/env bash

show_usage()
{
    cat << __EOF__

    Usage: $0 -k <kubeconfig> -p "<parameters>" 
           [-k OpenShift kubeconfig file] # e.g. -k .kubeconfig
           [-p Running parameters] # e.g. -p "-i 2 -c 20 -f 1 -n 1"
    Notes:
        File .kubeconfig can be created by using the following command.
          (export KUBECONFIG=.kubeconfig; oc login [URL])
__EOF__
#    Notes:
#       environment variable NGINX_PUBLIC_IP manually specified IP address of nginx route
    exit 1
}

apply_manager_deployment()
{
    oc apply -f - << __EOF__
---
apiVersion: v1
kind: Namespace
metadata:
  name: federatorai-demo-manager

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-demo-manager
  namespace: federatorai-demo-manager
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
        image: quay.io/prophetstor/federatorai-demo-nginx-manager:stable
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
        [ "`oc -n federatorai-demo-manager get pods | egrep Running | grep nginx-demo-manager-`" != "" ] && break
    done

    return 0
}


apply_nginx_deployment()
{
    ## preparing testing environment (deploy nginx pods and service endpoint)
    oc -n federatorai-demo-manager exec -t ${manager_pod} -- sh -c "export KUBECONFIG=\`pwd\`/.kubeconfig; bash -x ./run.sh install"
    ## wait until pod become Running
    while :; do
        echo "Waiting demo-nginx is ready ..."
        sleep 30
        [ "`oc -n ${NGINX_NAMESPACE} get pods | egrep Running | grep ${NGINX_DEPLOYMENT_NAME}-`" != "" ] && break
    done

    return 0
}

##
## Main
##
while getopts "hk:p:" o; do
    case "${o}" in
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
[ "${session_id}" = "" ] && session_id="`date +%s`"
manager_pod=""

## Environment variables
[ "${max_wait_pods_ready_time}" = "" ] && max_wait_pods_ready_time=900  # maximum wait time for pods become ready
[ "${avoid_metrics_interferece_sleep}" = "" ] && avoid_metrics_interferece_sleep=600  # maximum wait time for pods become ready

## Internal variables
NGINX_NAMESPACE="federatorai-demo-nginx"
NGINX_DEPLOYMENT_NAME="nginx-deployment"
export KUBECONFIG=${kubeconfig}

## Checking if cluster ready to use
if [ "`oc get ns kube-system | grep '^kube-system'`" = "" ]; then
    echo "Error. Failed in using K8S cluster."
    exit 1
fi

## create manager deployment if it is not exists
while :; do
    oc -n federatorai-demo-manager get deployment nginx-demo-manager > /dev/null 2>&1
    [ "$?" = "0" ] && break
    echo "Start deploying manager deployment ..."
    apply_manager_deployment
done

## Retrieve manager pod name
manager_pod="`oc -n federatorai-demo-manager get pods | grep 'Running' | grep nginx-demo-manager | awk '{print $1}'`"
if [ "${manager_pod}" != "" ]; then
    export manager_pod
    break
fi

## Update .kubeconfig inside manager
oc -n federatorai-demo-manager cp ${KUBECONFIG} ${manager_pod}:.kubeconfig
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

oc -n federatorai-demo-manager exec ${manager_pod} -- sh -c "export avoid_metrics_interference_sleep=${avoid_metrics_interference_sleep}; export KUBECONFIG=\`pwd\`/.kubeconfig; nohup sh -x ./run.sh start -k \${KUBECONFIG} -z ${parameter} > run.log 2>&1 &"

## Wait until the test in pod finished running
while :; do
    msg="`oc -n federatorai-demo-manager exec ${manager_pod} -- tail run.log | grep 'Success in running all tests'`"
    [ "${msg}" != "" ] && break
    echo "Waiting the tests completely running..."
    sleep 60
done

echo "Collecting testing result..."
## msg example: Success in running all tests with session id 1589278863.
session_id="`echo ${msg} | tr -d '.' | awk '{print $NF}'`"
oc -n federatorai-demo-manager exec ${manager_pod} -- sh -c "tar cf - \`find ./test_result/ -type d | grep ${session_id}$\`" | tar xf -

##
echo "Testing result saved into test_result directory."
exit 0

