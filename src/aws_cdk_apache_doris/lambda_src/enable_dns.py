import json
import urllib.request

import boto3


def sendResponse(event, context, responseData, responseStatus="FAILED"):
    response_body = json.dumps({
        "Status": responseStatus,
        "Reason": (
            "See the details in CloudWatch Log Stream: "
            + context.log_stream_name
        ),
        "PhysicalResourceId": context.log_stream_name,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "Data": responseData
    })
    enc_body = response_body.encode('utf-8')
    opener = urllib.request.build_opener(urllib.request.HTTPHandler)
    request = urllib.request.Request(event['ResponseURL'], data=enc_body)
    request.add_header('Content-Type', '')
    request.add_header('Content-Length', str(len(response_body)))
    request.get_method = lambda: 'PUT'
    response = opener.open(request)
    print(f"RESPONSE {response.getcode()}: {response.msg}")

def lambda_handler(event, context):
    if event['RequestType'] == 'Delete':
        sendResponse(event, context, {"Message": "DELETE"}, "SUCCESS")
        return '{}'
    response = {}
    try:
        ec2 = boto3.client('ec2')
        vpcId = event["ResourceProperties"].get("VpcId")
        ec2.modify_vpc_attribute(EnableDnsSupport={'Value': True}, VpcId=vpcId)
        ec2.modify_vpc_attribute(EnableDnsHostnames={'Value': True}, VpcId=vpcId)
        sendResponse(event, context, response, "SUCCESS")
    except Exception as e:
        print(str(e))
        sendResponse(event, context, {"Value": str(e)})
