import json
import logging
import os
import random
import string
import time

import boto3
import urllib3
from crhelper import CfnResource
from botocore.config import Config

SUCCESS = "SUCCESS"
FAILED = "FAILED"

STACK_SET_SUCCESS_STATES = ["SUCCEEDED"]
STACK_SET_RUNNING_STATES = ["RUNNING", "STOPPING"]

SEC_HUB_NAME_PREFIX = "LACEWORK-SEC-HUB_INGEST-"
DESCRIPTION = "Lacework's cloud-native threat detection, compliance, behavioral anomaly detection, "
"and automated AWS security monitoring."

http = urllib3.PoolManager()

LOGLEVEL = os.environ.get('LOGLEVEL', logging.INFO)
logger = logging.getLogger()
logger.setLevel(LOGLEVEL)

helper = CfnResource(json_logging=False, log_level="INFO", boto_level="CRITICAL", sleep_on_delete=15)

BOTO3_CONFIG = Config(retries={"max_attempts": 10, "mode": "standard"})

AUDIT_ACCT_NAME = "Audit"


def lambda_handler(event, context):
    logger.info("setup.lambda_handler called.")
    logger.info(json.dumps(event))
    try:
        if "RequestType" in event: helper(event, context)
    except Exception as e:
        helper.init_failure(e)


@helper.create
@helper.update
def create(event, context):
    logger.info("app.create called.")
    logger.info(json.dumps(event))

    cfn_client = boto3.client("cloudformation")
    management_account_id = context.invoked_function_arn.split(":")[4]
    lacework_url = os.environ['lacework_url']
    lacework_account_name = get_account_from_url(lacework_url)
    lacework_sub_account_name = os.environ['lacework_sub_account_name']
    sec_hub_ingest_template = os.environ['sec_hub_ingest_template']
    api_token = os.environ['api_token']
    audit_acct = get_account_id_by_name(AUDIT_ACCT_NAME)

    cfn_stack = os.environ['cfn_stack']
    cfn_stack_id = os.environ['cfn_stack_id']
    cfn_tags = get_stack_tags(cfn_stack, cfn_stack_id)

    audit_stack_set_name = SEC_HUB_NAME_PREFIX + \
                           (lacework_account_name if not lacework_sub_account_name else lacework_sub_account_name)
    external_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
    audit_role = "arn:aws:iam::" + management_account_id + ":role/service-role/AWSControlTowerStackSetRole"
    logger.info("Using role {} to create stack set url {}".format(audit_role, sec_hub_ingest_template))

    cfn_client.create_stack_set(
        StackSetName=audit_stack_set_name,
        Description=DESCRIPTION,
        TemplateURL=sec_hub_ingest_template,
        Parameters=[
            {
                "ParameterKey": "LaceworkAccount",
                "ParameterValue": lacework_account_name if not lacework_sub_account_name else lacework_sub_account_name,
                "UsePreviousValue": False,
                "ResolvedValue": "string"
            },
            {
                "ParameterKey": "ExternalID",
                "ParameterValue": external_id,
                "UsePreviousValue": False,
                "ResolvedValue": "string"
            },
            {
                "ParameterKey": "ApiToken",
                "ParameterValue": api_token,
                "UsePreviousValue": False,
                "ResolvedValue": "string"
            }
        ],
        Tags=cfn_tags,
        Capabilities=[
            "CAPABILITY_NAMED_IAM"
        ],
        AdministrationRoleARN=audit_role,
        ExecutionRoleName="AWSControlTowerExecution")

    try:
        cfn_client.describe_stack_set(StackSetName=audit_stack_set_name)
        logger.info("StackSet {} deployed".format(audit_stack_set_name))
    except cfn_client.exceptions.StackSetNotFoundException as describe_exception:
        raise error_exception("Exception getting new stack set, {}".format(describe_exception),
                              HONEY_API_KEY, DATASET, BUILD_VERSION, lacework_account_name,
                              lacework_sub_account_name)

    audit_stack_instance_response = create_stack_set_instances(audit_stack_set_name,
                                                               [audit_account_id], [region_name])

    wait_for_stack_set_operation(audit_stack_set_name, audit_stack_instance_response['OperationId'])

    logger.info("Audit stack set instance created {}".format(audit_stack_instance_response))


@helper.delete  # crhelper method to delete stack set and stack instances
def delete(event, context):
    logger.info("app.delete called.")
    cfn_client = boto3.client("cloudformation")
    management_account_id = context.invoked_function_arn.split(":")[4]
    lacework_url = os.environ['lacework_url']
    lacework_account_name = get_account_from_url(lacework_url)
    lacework_sub_account_name = os.environ['lacework_sub_account_name']
    audit_acct = get_account_id_by_name(AUDIT_ACCT_NAME)
    region_name = context.invoked_function_arn.split(":")[3]
    audit_stack_set_name = SEC_HUB_NAME_PREFIX + \
                           (lacework_account_name if not lacework_sub_account_name else lacework_sub_account_name)
    try:
        if audit_acct is not None:
            audit_stack_instance_response = cfn_client.delete_stack_instances(
                StackSetName=audit_stack_set_name,
                Accounts=[audit_acct],
                Regions=[region_name],
                RetainStacks=False)
            logger.info(audit_stack_instance_response)
            wait_for_stack_set_operation(audit_stack_set_name, audit_stack_instance_response['OperationId'])
        else:
            logger.warning("Audit account with name {} was not found.")

    except Exception as delete_audit_stack_exception:
        logger.warning(
            "Problem occurred while deleting, Lacework-CloudTrail-Audit-Account-Setup still exist : {}".format(
                delete_audit_stack_exception))

    try:
        audit_stack_set_response = cfn_client.delete_stack_set(StackSetName=audit_stack_set_name)
        logger.info("StackSet {} template delete status {}".format(audit_stack_set_name, audit_stack_set_response))
    except Exception as stack_set_exception:
        logger.warning("Problem occurred while deleting StackSet {} : {}".format(audit_stack_set_name,
                                                                                 stack_set_exception))


def get_account_id_by_name(name):
    logger.info("get_account_id_by_name called.")
    org_client = boto3.client('organizations')
    paginator = org_client.get_paginator("list_accounts")
    page_iterator = paginator.paginate()
    for page in page_iterator:
        for acct in page['Accounts']:
            if acct['Name'] == name:
                return acct['Id']

    return None


def wait_for_stack_set_operation(stack_set_name, operation_id):
    logger.info("wait_for_stack_set_operation called.")
    logger.info("Waiting for StackSet Operation {} on StackSet {} to finish".format(operation_id, stack_set_name))
    cloudformation_client = boto3.client("cloudformation")
    finished = False
    status = ""
    count = 1
    while not finished:
        time.sleep(count * 20)
        status = \
            cloudformation_client.describe_stack_set_operation(StackSetName=stack_set_name, OperationId=operation_id)[
                "StackSetOperation"
            ]["Status"]
        if status in STACK_SET_RUNNING_STATES:
            logger.info("{} {} still running.".format(stack_set_name, operation_id))
        else:
            finished = True
        count += 1

    logger.info("StackSet Operation finished with Status: {}".format(status))
    if status not in STACK_SET_SUCCESS_STATES:
        return False
    else:
        return True


def create_stack_set_instances(stack_set_name, accounts, regions, parameter_overrides=[]):
    logger.info("create_stack_set_instances called.")
    logger.info("Create stack name={} accounts={} regions={} parameter_overrides={} ".format(stack_set_name, accounts,
                                                                                             regions,
                                                                                             parameter_overrides))
    cloud_formation_client = boto3.client("cloudformation")
    return cloud_formation_client.create_stack_instances(StackSetName=stack_set_name,
                                                         Accounts=accounts,
                                                         Regions=regions,
                                                         ParameterOverrides=parameter_overrides,
                                                         OperationPreferences={
                                                             'RegionConcurrencyType': "PARALLEL",
                                                             'MaxConcurrentCount': 100,
                                                             'FailureToleranceCount': 999
                                                         })


def get_account_from_url(lacework_url):
    return lacework_url.split('.')[0]


def get_stack_tags(stack_name, stack_id):
    logger.info("get_stack_tags.")
    try:
        cfn_client = boto3.client("cloudformation")
        response = cfn_client.describe_stacks(
            StackName=stack_name
        )

        logger.info("stacks_result: {}".format(response))
        for stack in response['Stacks']:
            if stack["StackId"] == stack_id:
                return stack["Tags"]

        return []
    except Exception as e:
        logger.error("List Stack Instance error: {}.".format(e))
        return []
