## Overview

With the Lacework AWS Built-in Package, enrolling a new AWS account ensures security best practices and monitoring are
automatically applied consistently across your organization. Account administrators can automatically add Lacework's
security auditing and monitoring to AWS accounts seamlessly. All the required Lacework and AWS account configurations
that allow access to AWS configuration and CloudTrail logs are managed for you by Lacework. Additionally, automatic
enablement of Amazon GuardDuty and AWS Security Hub means that your organization can benefit from enriched security
alerts from Lacework and AWS. This leads to higher fidelity alerts and quicker time to resolution due to additional
context provided by AWS Security Hub and Amazon GuardDuty.

![AWS Built-in Overview](https://lacework-alliances.s3.us-west-2.amazonaws.com/collateral/aws-built-in-overview.png)


## Prerequisites

* **Enable AWS Control Tower** - Follow these instructions to [enable AWS Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-with-control-tower.html) for your organization.
* Administrator privileges in the AWS Control Tower management account.
* A Lacework Cloud Security Platform SaaS account.

## Lacework AWS Built-in Package Architecture

CloudFormation is used to deploy the Lacework AWS Built-in Package. The CloudFormation template will create the following resources:
* A cross-account IAM role that will allow Lacework to query AWS APIs.
* An EventBridge rule for AWS Control Tower account creation events that will trigger a Lambda function.
* Lambda functions that perform initial setup and add accounts to Lacework.
* An SQS queue that will receive the AWS Control Tower centralized CloudTrail S3 bucket notifications.
* A cross-account IAM role that will allow Lacework to access the SQS queue in order to receive centralized CloudTrail S3 bucket updates.
* An EventBridge rule that will forward AWS Security Hub findings to an SQS queue.
* An SQS queue that will receive the AWS Security Hub findings.
* A cross-account IAM role that will allow Lacework to access the SQS queue in order to receive the AWS Security Hub findings.

![AWS Built-in Architecture](https://lacework-alliances.s3.us-west-2.amazonaws.com/collateral/aws-built-in-aws-arch.png)

## Deployment Scenarios

### 1. Without Lacework Organization
If the [Lacework Organization](https://docs.lacework.com/console/organization-overview) feature is not enabled, all AWS accounts go under the main Lacework account by default. Leave the **Single Sub-Account Configuration** and **Organization Configuration** sections blank in the CloudFormation stack parameters.

### 2. Single Lacework Sub-Account with Lacework Organization

If the [Lacework Organization](https://docs.lacework.com/console/organization-overview) feature is enabled, you can specify a Lacework Sub-Account for which all AWS accounts are added. This is specified in the **Single Sub-Account Configuration** section in the **Lacework Sub-Account Name** field (see below) in the CloudFormation stack parameters.

### 3. AWS Organizational Units (OUs) to Lacework Sub-Account Mapping with Lacework Organization

- You must have the <a href="https://docs.lacework.com/console/organization-overview">Lacework Organization</a> feature enabled.
- When naming the OUs, ensure to not include spaces in the names (hyphens are allowed). <br />
    - Dev Infra  :x: <br />
    - Dev-Infra :white_check_mark:

## Configure the Lacework AWS Built-in Package

### 1. Generate a Lacework API Access Key

1. In your console, go to **Settings > Configuration > API keys**.
2. Click on the **+ Add New** button in the upper right to create a new API key.
3. Provide a **name** and **description** and click Save.
4. Click the download button to download the API keys file.
5. Copy the **keyId** and **secret** from this file.

### 2. Log in to your AWS Control Tower Management Account

1. Log in to AWS Control Tower management account.
2. Select the AWS region where your AWS Control Tower is deployed.

### 3. Deploy the Lacework AWS Built-in Package with CloudFormation

1. Click the following **Launch Stack** button to go to your CloudFormation console and launch the AWS Control Integration template.

   [![Launch](https://user-images.githubusercontent.com/6440106/153987820-e1f32423-1e69-416d-8bca-2ee3a1e85df1.png)](https://console.aws.amazon.com/cloudformation/home?#/stacks/create/review?templateURL=https://lacework-alliances.s3.us-west-2.amazonaws.com/lacework-control-tower-cfn/templates/control-tower-integration.template.yml)

   For most deployments, you need only Basic Configuration parameters.
2. Specify the following Basic Configuration parameters:
    * Enter a **Stack name** for the stack.
    * Enter **Your Lacework URL**.
    * Enter your **Lacework Access Key ID** and **Secret Key** that you copied from your previous API keys file.
    * For **Capability Type**, the recommendation is to use **CloudTrail+Config** for the best capabilities.
    * Choose whether you want to **Monitor Existing Accounts**. This sets up monitoring of ACTIVE existing AWS accounts.
    * Enter the name of your **Existing AWS Control Tower CloudTrail Name**.
    * If your CloudTrail S3 logs are encrypted, specify the **KMS Key Identifier ARN**. Ensure that you update the KMS key policy to allow access to the Log account cross-account role used by Lacework. Add the following to the key policy.

      ```text
      "Sid": "Allow Lacework to decrypt logs",
      "Effect": "Allow",
      "Principal": {
      "AWS": [
      "arn:aws:iam::<log-archive-account-id>:role/<lacework-account-name>-laceworkcwssarole"
      ]
      },
      "Action": [
      "kms:Decrypt"
      ],
      "Resource": "*"
      ```

    * Update the Control Tower **Log Account Name** and **Audit Account Name** if necessary.
    * If using AWS organization units to Lacework Sub-Account mapping, specify a comma-separated lists of organization names in the **Organization Configuration** section in the **AWS Organizations to Lacework Sub-Account Names** field. AWS accounts are added to the appropriate Lacework Sub-Accounts based on this AWS OU-to-Lacework Sub-Account name mapping. AWS OU names and Lacework Sub-Account names must match. AWS accounts not in the specified organization units are not added to Lacework.
    * If using a single Lacework sub-account for all AWS accounts, specify a Lacework Sub-Account for which all AWS accounts will be added. This is specified in the **Single Sub-Account Configuration** section in the **Lacework Sub-Account Name** field.
3. Click **Next** through to your stack **Review**.
4. Accept the AWS CloudFormation terms and click **Create stack**.

### 4. CloudFormation Progress

1. Monitor the progress of the CloudFormation deployment. It takes several minutes for the stack to create the resources that enable the Lacework AWS Built-in Package.
2. When successfully completed, the stack shows `CREATE_COMPLETE`.

### 5. Validate the Solution

1. Log in to your Lacework Cloud Security Platform console.
2. Go to **Settings > Integration > Cloud Accounts**.
3. You should see a list of AWS accounts that are now being monitored by Lacework. The **Cloud Account** column values correspond to the AWS Account IDs.

Once the Control Tower CloudFormation deployment is competed, you need to setup an <a href="/onboarding/setup-of-organization-aws-cloudtrail-integration">Setup of Organization AWS CloudTrail Integration</a> and upload a mapping file. Any AWS accounts that are not included in the mapping will have your CloudTrail logs sent to the default Lacework Sub-Account.

## Remove the Lacework AWS Built-in Package

To remove the Lacework's AWS Built-in Pacakge, simply delete the main stack. All CloudFormation stacksets, stack instances, and Lambda functions will be deleted.

Lacework will no longer monitor your AWS cloud environment.

## Permissions

The following IAM permissions are required to allow Lacework to query AWS APIs, read CloudTrail events and receive AWS Security Hub findings. These are provisioned
as part of the CloudFormation deployment.

### Member Account SecurityAudit Cross-Account IAM Role

```yaml
  LaceworkCrossAccountAccessRole:
    Type: 'AWS::IAM::Role'
    Properties:
      RoleName: !Join
        - '-'
        - - !Ref ResourceNamePrefix
          - laceworkcwsrole-sa
      AssumeRolePolicyDocument:
        Version: 2012-10-17
        Statement:
          - Action: 'sts:AssumeRole'
            Effect: Allow
            Principal:
              AWS: !Join
                - ''
                - - 'arn:aws:iam::'
                  - !Ref LaceworkAWSAccountId
                  - ':root'
            Condition:
              StringEquals:
                'sts:ExternalId': !Ref ExternalID
      ManagedPolicyArns:
        - 'arn:aws:iam::aws:policy/SecurityAudit'
```

### Centralized CloudTrail Cross-Account IAM Role

```yaml
  LaceworkCWSSACrossAccountAccessRole:
    Type: 'AWS::IAM::Role'
    Properties:
      RoleName: !Join
        - ''
        - - !Ref ResourceNamePrefix
          - '-laceworkcwssarole'
      AssumeRolePolicyDocument:
        Version: 2012-10-17
        Statement:
          - Action: 'sts:AssumeRole'
            Effect: Allow
            Principal:
              AWS: !Join
                - ''
                - - 'arn:aws:iam::'
                  - !Ref LaceworkAWSAccountId
                  - ':root'
            Condition:
              StringEquals:
                'sts:ExternalId': !Ref ExternalID
      ManagedPolicyArns:
        - 'arn:aws:iam::aws:policy/SecurityAudit'
  LaceworkCWSPolicy:
    Type: 'AWS::IAM::Policy'
    Properties:
      PolicyName: LaceworkCWSPolicy
      PolicyDocument:
        Version: 2012-10-17
        Statement:
          - Sid: ConsumeNotifications
            Action:
              - 'sqs:GetQueueAttributes'
              - 'sqs:GetQueueUrl'
              - 'sqs:DeleteMessage'
              - 'sqs:ReceiveMessage'
            Effect: Allow
            Resource: !Ref SqsQueueArn
          - Sid: ListLogFiles
            Action:
              - 's3:ListBucket'
            Effect: Allow
            Resource: !Join ['',["arn:aws:s3:::", !Ref ExistingTrailBucketName, "/*AWSLogs/*" ]]
            Condition:
              StringLike:
                's3:prefix':
                  - '*AWSLogs/'
          - Sid: ReadLogFiles
            Action:
              - 's3:Get*'
            Effect: Allow
            Resource: !Join ['',["arn:aws:s3:::", !Ref ExistingTrailBucketName, "/*AWSLogs/*" ]]
          - Sid: GetAccountAlias
            Action:
              - 'iam:ListAccountAliases'
            Effect: Allow
            Resource: '*'
          - Sid: Debug
            Action:
              - 'cloudtrail:DescribeTrails'
              - 'cloudtrail:GetTrailTopics'
              - 'cloudtrail:GetTrailStatus'
              - 'cloudtrail:ListPublicKeys'
              - 's3:GetBucketAcl'
              - 's3:GetBucketPolicy'
              - 's3:ListAllMyBuckets'
              - 's3:GetBucketLocation'
              - 's3:GetBucketLogging'
              - 'sns:GetSubscriptionAttributes'
              - 'sns:GetTopicAttributes'
              - 'sns:ListSubscriptions'
              - 'sns:ListSubscriptionsByTopic'
              - 'sns:ListTopics'
            Effect: Allow
            Resource: '*'
      Roles:
        - !Ref LaceworkCWSSACrossAccountAccessRole
```

### Security Hub Cross-Account IAM Role

```yaml
  LaceworkSecHubCrossAccountAccessRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub "${ResourceNamePrefix}-Lacework-Sec-Hub-Role"
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Action:
              - sts:AssumeRole
            Principal:
               AWS: !Join
                  - ''
                  - - 'arn:aws:iam::'
                    - !Ref LaceworkAWSAccountId
                    - ':root'
            Condition:
              StringEquals:
                sts:ExternalId:
                  !Ref ExternalID
      Path: "/"
      Policies:
        - PolicyName: LaceworkSecHubCrossAccountAccessRolePolicy
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action:
                  - sqs:ListQueues
                  - sqs:GetQueueAttributes
                  - sqs:GetQueueUrl
                  - sqs:DeleteMessage
                  - sqs:ReceiveMessage
                Resource:
                  - !GetAtt LaceworkSecHubQueue.Arn
```

## Troubleshooting

The following sections provide guidance for resolving issues with deploying the Lacework AWS Built-in Package.

### Common Issues

* Ensure the **Existing AWS Control Tower CloudTrail Name** is correct. You can verify this on your AWS CloudTrail Dashboard.
* Ensure that your **Log Archive** and **Audit** account names are correct and these accounts are `ACTIVE`.
* If you are using the Lacework Organization feature to manage your accounts, specify the correct Sub-Account name, API key ID, and secret key.
* If Lacework returns an S3 access error for the CloudTrail account and a KMS key is used, ensure you update the KMS key policy to allow access to the Log account cross-account role used by Lacework.

  ```text
  "Sid": "Allow Lacework to decrypt logs",
  "Effect": "Allow",
  "Principal": {
      "AWS": [
          "arn:aws:iam::<log-archive-account-id>:role/<lacework-account-name>-laceworkcwssarole"
      ]
  },
  "Action": [
      "kms:Decrypt"
  ],
  "Resource": "*"
  ```

### Events and Logs

#### CloudFormation Events

You can monitor the CloudFormation events for the Lacework's AWS Built-in stack. Events may reveal issues with resource creation. The Lacework's AWS Built-in stack launches a main stack and three stacksets:

**Main Deployment Stack:**
* **control-tower-integration.template.yml** - Main stack that deploys all resources: IAM roles, access token credentials, IAM roles, SQS queues, Lambda functions and the stacksets below.

**Centralized CloudTrail Cloud Account in Lacework:** (Applied once during initial deployment)
* **lacework-aws-ct-audit.template.yml** -> **Lacework-Control-Tower-CloudTrail-Audit-Account-**_Lacework account_ - Creates a stack instance in the Audit account.
* **lacework-aws-ct-log.template.yml** -> **Lacework-Control-Tower-CloudTrail-Log-Account-**_Lacework account_ - Creates a stack instance in the Log account.

**Config Cloud Account in Lacework:** (Applied for each AWS account)
* **lacework-aws-cfg-member.template.yml** -> **Lacework-Control-Tower-Config-Member-**_Lacework account_ - Creates a stack instance in each AWS account.

Examining these stacksets for operation results, stack instance results and parameters may also provide debug information.

#### Lambda Function CloudWatch Logs

Two main Lambda functions are used to manage accounts. LaceworkSetupFunction manages the initial deployment of the integration. LaceworkAccountFunction manages setting up existing and new accounts. Both Lambda functions provide extensive debug messages that can be seen in their respective CloudWatch log streams.

## FAQs

<details>
<summary><b>Can I individually choose which accounts are added to Lacework within AWS Control Tower?</b></summary>Yes, our solution supports mapping of AWS organization names (aka AWS OU names) to Lacework Sub-Accounts. AWS accounts for our Config type will be added to Lacework Suub-Accounts based on the provided comma separated list of AWS organization names. These AWS organization names must match the Sub-Account names on our side. Any AWS accounts that are not included in the mapping will have your CloudTrail logs sent to the default Lacework Sub-Account.

</details>

<details>
<summary><b>How does Lacework integrate with AWS Control Tower's CloudTrail?</b></summary>Our solution simply adds the centralized CloudTrail in the Log Archive account to Lacework. It does not do any mapping. Separately and manually, the customer may use the CloudTrail JSON mapping. Once the Control Tower CloudFormation deployment is competed, you need to setup an <a href="/onboarding/setup-of-organization-aws-cloudtrail-integration">Setup of Organization AWS CloudTrail Integration</a> and upload a mapping file. Any AWS accounts that are not included in the mapping will have your CloudTrail logs sent to the default Lacework Sub-Account.
</details>
