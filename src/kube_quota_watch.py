import sys
import re
from kubernetes import client, config
import yaml
from collections import OrderedDict
import json

# Ensure the script is executed with exactly 1 argument
if len(sys.argv) == 2:
    config_yaml = sys.argv[1]
else:
    raise ValueError('This script requires 1 argument')

# Takes a resource value with or without a unit and converts it to the base unit
# to allow a percentage to be calculated from the normalised / flat value
def flatten_value(resource_value):
    # Handles no suffix
    if re.match(r'^(\d+(\.\d+)?)$', resource_value):
        flat_val = float(resource_value)

    # Multiplier for kilo suffix
    elif re.match(r'^(\d+(\.\d+)?)k$', resource_value):
        flat_val = float(re.sub(r'k$', '', resource_value)) * 1000

    # Multiplier for millicpu/millicores suffix
    elif re.match(r'^(\d+(\.\d+)?)m$', resource_value):
        flat_val = float(re.sub(r'm$', '', resource_value)) * 0.001

    # Multiplier for power-of-two suffixes
    elif re.match(r'^(\d+(\.\d+)?)Ei$', resource_value):
        flat_val = float(re.sub(r'Ei$', '', resource_value)) * pow(2, 60)

    elif re.match(r'^(\d+(\.\d+)?)Pi$', resource_value):
        flat_val = float(re.sub(r'Pi$', '', resource_value)) * pow(2, 50)

    elif re.match(r'^(\d+(\.\d+)?)Ti$', resource_value):
        flat_val = float(re.sub(r'Ti$', '', resource_value)) * pow(2, 40)

    elif re.match(r'^(\d+(\.\d+)?)Gi$', resource_value):
        flat_val = float(re.sub(r'Gi$', '', resource_value)) * pow(2, 30)

    elif re.match(r'^(\d+(\.\d+)?)Mi$', resource_value):
        flat_val = float(re.sub(r'Mi$', '', resource_value)) * pow(2, 20)

    elif re.match(r'^(\d+(\.\d+)?)Ki$', resource_value):
        flat_val = float(re.sub(r'Ki$', '', resource_value)) * pow(2, 10)

    # Multiplier for fixed-point suffixes
    elif re.match(r'^(\d+(\.\d+)?)E$', resource_value):
        flat_val = float(re.sub(r'E$', '', resource_value)) * pow(10, 18)

    elif re.match(r'^(\d+(\.\d+)?)P$', resource_value):
        flat_val = float(re.sub(r'P$', '', resource_value)) * pow(10, 15)

    elif re.match(r'^(\d+(\.\d+)?)T$', resource_value):
        flat_val = float(re.sub(r'T$', '', resource_value)) * pow(10, 12)

    elif re.match(r'^(\d+(\.\d+)?)G$', resource_value):
        flat_val = float(re.sub(r'G$', '', resource_value)) * pow(10, 9)

    elif re.match(r'^(\d+(\.\d+)?)M$', resource_value):
        flat_val = float(re.sub(r'M$', '', resource_value)) * pow(10, 6)

    elif re.match(r'^(\d+(\.\d+)?)K$', resource_value):
        flat_val = float(re.sub(r'K$', '', resource_value)) * pow(10, 3)

    # Handle undefined value
    else:
        raise ValueError(f'Undefined unit: {resource_value}')
    
    return flat_val

# Gets the manifest of a quota resource in YAML format from Kubernetes API
# Then calculates the percentage used of each resource and outputs a dictionary of the results
def get_quota_percent(target_namespace, quota_object):
    config.load_incluster_config()
    # config.load_kube_config()

    v1 = client.CoreV1Api()
    client_out = v1.list_namespaced_resource_quota(
        namespace=target_namespace,
        watch=False
    )

    # Select quota object of interest
    for section in client_out.items:
        if section.metadata.name == quota_object:
            quota_dict = section

    status_hard = quota_dict.status.hard
    status_used = quota_dict.status.used
    quota_percent_dict = {}

    for resource in status_hard:
        base_val = flatten_value(status_hard[resource])
        percent_val = flatten_value(status_used[resource])
        percentage = ( percent_val / base_val ) * 100
        quota_percent_dict[resource] = round(percentage)

    return quota_percent_dict

# Injests a YAML configuration file and returns log format as list of dictionaries
def config_log_output(config_yaml):
    try:
        with open(config_yaml, 'r') as f:
            config_dict = yaml.safe_load(f)

    except IOError:
        print(f'File is not accessible: {config_yaml}')

    for section in config_dict['quotas']:
        namespace = section['namespace']
        quota_object = section['resourceQuotas']
        percent_dict = get_quota_percent(namespace, quota_object)
        threshold_dict = section.get('threshold')

        for k,v in percent_dict.items():
            log_level = "INFO" # Default log_level

            # Selector for WARNING log_level override
            if threshold_dict != None and k in threshold_dict:
                if v >= float(threshold_dict[k]):
                    log_level = "WARNING"
                
            elif threshold_dict != None and "default" in threshold_dict:
                if v >= float(threshold_dict['default']):
                    log_level = "WARNING"

            elif v >= float(config_dict['defaultThreshold']):
                log_level = "WARNING"

            log_item = OrderedDict(
                [
                    ("level", log_level),
                    ("percentage", v),
                    ("resource", k),
                    ("quota_object", quota_object),
                    ("namespace", namespace),
                ]
            )
            json_log = json.dumps(log_item)
            print(json_log, file=sys.stdout)

def main():
    config_log_output(config_yaml)

if __name__ == "__main__":
    main()
