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
    try:
        ec2 = boto3.client('ec2')
        subnet = event["ResourceProperties"].get("SubnetId")
        vpcId = event["ResourceProperties"].get("VpcId")
        region = event["ResourceProperties"].get("Region")
        resp = ec2.describe_route_tables(
            Filters=[{'Name': 'association.subnet-id', 'Values': [subnet]}]
        )
        if len(resp['RouteTables']) == 0:
            resp = ec2.describe_route_tables(
                Filters=[
                    {'Name': 'association.main', 'Values': ['true']},
                    {'Name': 'vpc-id', 'Values': [vpcId]},
                ]
            )
        fullS3Servicename = f"com.amazonaws.{region}.s3"
        getS3PrefixResponse = ec2.describe_prefix_lists(
            Filters=[{'Name': 'prefix-list-name', 'Values': [fullS3Servicename]}]
        )
        fullS3ServicePrefix = getS3PrefixResponse['PrefixLists'][0]['PrefixListId']
        needCreateS3 = True
        routetable = resp['RouteTables'][0]
        for route in routetable['Routes']:
            if (
                'DestinationPrefixListId' in route
                and route['DestinationPrefixListId'] == fullS3ServicePrefix
            ):
                needCreateS3 = False
        if needCreateS3:
            ec2.create_vpc_endpoint(
                VpcEndpointType='Gateway',
                VpcId=vpcId,
                ServiceName=fullS3Servicename,
                RouteTableIds=[routetable['RouteTableId']],
            )
            sendResponse(event, context, {"Message": "CREATED"}, "SUCCESS")
            return '{}'
        sendResponse(event, context, {"Message": "CREATE_SKIPPED"}, "SUCCESS")
    except Exception as e:
        print(str(e))
        sendResponse(event, context, {"Value": str(e)})
