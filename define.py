# # environment
alameda_installed = False

# # prometheus
prometheus_namespace = "openshift-monitoring"
prometheus_operator_name = "prometheus-operator"

prometheus_endpoint = "https://prometheus-k8s-openshift-monitoring.apps.ocp4.172-31-7-15.nip.io/api/v1"
prometheus_token = ""

# # application info
cpu_limit = 100  # mCore
memory_limit = 0  # MB
initial_replica = 10
#overprovision_replica = 20  # overprovision without HPA

nginx_namespace = "federatorai-demo-nginx"
app_service_ip = "nginx-service-nginx.apps.ocp4.172-31-7-15.nip.io"
app_service_port = 80

ingress_http_requests_name = "nginx_ingress_controller_nginx_process_requests_total"
ingress_namespace = "ingress-nginx"

# # algorithm
ma_number = 5  # number of time periods of moving average
replica_margin = 40  # percentage of replica margin

# # test case
interactive_mode = False
k8shpa_percent = 80
number_alamedahpa = 0
number_k8shpa = 0
number_nonhpa = 1
k8shpa_type = "cpu"  # cpu: only cpu; memory: only memory

traffic_path = "./traffic"
metrics_path = "./metrics"
picture_path = "./picture"

# # traffic - ab info
traffic_ratio = 500
traffic_path = "./traffic"
traffic_interval = 1  # generate traffic per 1 minute during 72 minutes
data_interval = 1  # collect pods' resource utilization
warm_up = 0

training_interval = 100
training_scale = 100

ab_concurrency = 200  # Number of multiple requests to make at a time
ab_timelimit = 300  # Seconds to max. to spend on benchmarking

# # picture
picture_x_axis = 144
picture_y_ratio = 1.5
show_details = True
