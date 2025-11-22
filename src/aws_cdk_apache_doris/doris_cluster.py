import os
from typing import (
    Any,
    List,
    Mapping,
    Sequence,
    cast,
)

from aws_cdk import (
    CfnOutput,
    CustomResource,
    Duration,
    IResolvable,
    Stack,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from constructs import Construct

from aws_cdk_apache_doris.constructs import (
    DorisBastion,
    DorisBeFleet,
    DorisFeFleet,
    DorisSecurityGroups,
)

LAMBDA_SRC_DIR = os.path.join(os.path.dirname(__file__), "lambda_src")

FE_INSTANCE_TYPES = [
    "t3.large",
    "t3.xlarge",
    "t3.2xlarge",
    "m5.large",
    "m5.xlarge",
    "m5.2xlarge",
    "m5.4xlarge",
    "m6i.large",
    "m6i.xlarge",
    "m6i.2xlarge",
    "m6i.4xlarge",
    "r5.large",
    "r5.xlarge",
    "r5.2xlarge",
    "r5.4xlarge",
    "r5.8xlarge",
    "r6i.large",
    "r6i.xlarge",
    "r6i.2xlarge",
    "r6i.4xlarge",
    "r6i.8xlarge",
]
BE_INSTANCE_TYPES = list(FE_INSTANCE_TYPES)
LOG_LEVELS = ["INFO", "WARN", "ERROR", "FATAL"]
VOLUME_TYPES = ["gp2", "gp3", "st1", "io1"]
DORIS_VERSIONS = ["213", "206"]
BE_NODE_COUNTS = [1, 3, 5]
FE_NODE_COUNTS = [1]

DORIS_PORTS = [9060, 8040, 9050, 8060, 8030, 9020, 9030, 9010, 443]

DORIS_DOWNLOADS = {
    "us-east-1": {
        "213": "https://selectdb-cloud-online-us-east-1.s3.amazonaws.com/doris/2.1.3/apache-doris-2.1.3-bin-x64.tar.gz",
        "206": "https://selectdb-cloud-online-us-east-1.s3.amazonaws.com/doris/2.0.6/apache-doris-2.0.6-bin-x64.tar.gz",
    },
    "us-west-1": {
        "213": "https://selectdb-cloud-online-us-west-1.s3.amazonaws.com/doris/2.1.3/apache-doris-2.1.3-bin-x64.tar.gz",
        "206": "https://selectdb-cloud-online-us-west-1.s3.amazonaws.com/doris/2.0.6/apache-doris-2.0.6-bin-x64.tar.gz",
    },
    "us-west-2": {
        "213": "https://selectdb-cloud-online-us-west-2.s3.amazonaws.com/doris/2.1.3/apache-doris-2.1.3-bin-x64.tar.gz",
        "206": "https://selectdb-cloud-online-us-west-2.s3.amazonaws.com/doris/2.0.6/apache-doris-2.0.6-bin-x64.tar.gz",
    },
}
JDK_DOWNLOADS = {
    "us-east-1": "https://selectdb-cloud-online-us-east-1.s3.amazonaws.com/doris/jdk-linux_x64.tar.gz",
    "us-west-1": "https://selectdb-cloud-online-us-west-1.s3.amazonaws.com/doris/jdk-linux_x64.tar.gz",
    "us-west-2": "https://selectdb-cloud-online-us-west-2.s3.amazonaws.com/doris/jdk-linux_x64.tar.gz",
}
IMAGE_AMIS = {
    "us-east-1": "ami-02d7fd1c2af6eead0",
    "us-west-1": "ami-0830c9faf0efc29ff",
    "us-west-2": "ami-0c7843ce70e666e51",
}


def _require_choice(value: Any, allowed: Sequence[Any], label: str) -> None:
    if value not in allowed:
        raise ValueError(f"{label} must be one of {allowed}")


def _require_region_lookup(mapping: Mapping[str, Any], key: str, label: str) -> Any:
    try:
        return mapping[key]
    except KeyError as err:
        raise ValueError(f"{label} not available for {key}") from err


class DorisCluster(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        public_subnet: ec2.ISubnet,
        key_pair_name: str,
        remote_access_cidr: str = "0.0.0.0/0",
        doris_version: str = "213",
        fe_node_count: int = 1,
        fe_node_instance_type: str = FE_INSTANCE_TYPES[0],
        be_node_count: int = 3,
        be_node_instance_type: str = BE_INSTANCE_TYPES[0],
        log_dir: str = "feDefaultLogPath",
        log_level: str = "INFO",
        meta_dir: str = "feDefaultMetaPath",
        be_log_dir: str = "beDefaultLogPath",
        sys_log_level: str = "INFO",
        volume_type: str = "gp2",
        volume_size: str = "50",
        vpc_cidr: str | None = None,
    ) -> None:
        super().__init__(scope, construct_id)

        self.vpc: ec2.IVpc = vpc
        self.public_subnet: ec2.ISubnet = public_subnet
        self.public_subnet_id = public_subnet.subnet_id
        self.key_pair_name = key_pair_name
        self.remote_access_cidr = remote_access_cidr
        self.doris_version = doris_version
        self.fe_node_count = fe_node_count
        self.fe_node_instance_type = fe_node_instance_type
        self.be_node_count = be_node_count
        self.be_node_instance_type = be_node_instance_type
        self.log_dir = log_dir
        self.log_level = log_level
        self.meta_dir = meta_dir
        self.be_log_dir = be_log_dir
        self.sys_log_level = sys_log_level
        self.volume_type = volume_type
        self.volume_size = volume_size
        self.vpc_cidr = vpc_cidr or getattr(vpc, "vpc_cidr_block", "0.0.0.0/0")

        self._validate_props()
        self._resolve_region_assets()

        self._create_custom_resource_role()
        self._create_custom_resources()
        self._create_security_components()
        self._create_cloudformation_endpoint()
        self._create_compute_components()
        self._expose_outputs()

    def _validate_props(self) -> None:
        _require_choice(
            self.fe_node_instance_type,
            FE_INSTANCE_TYPES,
            "FE instance type",
        )
        _require_choice(
            self.be_node_instance_type,
            BE_INSTANCE_TYPES,
            "BE instance type",
        )
        _require_choice(self.log_level, LOG_LEVELS, "FE log level")
        _require_choice(self.sys_log_level, LOG_LEVELS, "BE log level")
        _require_choice(self.volume_type, VOLUME_TYPES, "Volume type")
        _require_choice(self.doris_version, DORIS_VERSIONS, "Doris version")
        _require_choice(self.fe_node_count, FE_NODE_COUNTS, "FE node count")
        _require_choice(self.be_node_count, BE_NODE_COUNTS, "BE node count")

        try:
            int(self.volume_size)
        except ValueError as err:
            raise ValueError("Volume size must be a numeric string") from err

    def _resolve_region_assets(self) -> None:
        stack = Stack.of(self)
        self.region = stack.region
        version_map = _require_region_lookup(
            DORIS_DOWNLOADS,
            self.region,
            "Doris download availability",
        )
        self.doris_download_url = _require_region_lookup(
            version_map,
            self.doris_version,
            "Doris version download",
        )
        self.jdk_download_url = _require_region_lookup(
            JDK_DOWNLOADS,
            self.region,
            "JDK download availability",
        )
        self.ami_id = _require_region_lookup(
            IMAGE_AMIS,
            self.region,
            "Doris AMI",
        )

    def _create_custom_resource_role(self) -> None:
        self.custom_resource_role = iam.Role(
            self,
            "CustomResourceRole",
            assumed_by=cast(
                iam.IPrincipal,
                iam.ServicePrincipal("lambda.amazonaws.com"),
            ),
            inline_policies={
                "CustomResourcePolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            resources=["arn:aws:logs:*:*:*"],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "ec2:DescribeSubnets",
                                "ec2:DescribeRouteTables",
                                "ec2:DescribeVpcEndpoints",
                                "ec2:ModifyVpcAttribute",
                                "ec2:CreateVpcEndpoint",
                                "ec2:DescribePrefixLists",
                                "ec2:CreateInstanceConnectEndpoint",
                                "ec2:DescribeInstanceConnectEndpoints",
                                "ec2:CreateNetworkInterface",
                                "ec2:CreateTags",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            actions=["iam:CreateServiceLinkedRole"],
                            resources=["*"],
                        ),
                    ]
                )
            },
        )

    def _create_custom_resources(self) -> None:
        lambda_code = _lambda.Code.from_asset(LAMBDA_SRC_DIR)

        self.enable_dns_function = _lambda.Function(
            self,
            "EnableDnsFunction",
            code=lambda_code,
            handler="enable_dns.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            role=cast(iam.IRole, self.custom_resource_role),
            timeout=Duration.seconds(30),
        )
        self.s3_endpoint_function = _lambda.Function(
            self,
            "CreateS3EndpointFunction",
            code=lambda_code,
            handler="create_s3_endpoint.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            role=cast(iam.IRole, self.custom_resource_role),
            timeout=Duration.seconds(30),
        )
        self.private_dns_function = _lambda.Function(
            self,
            "GetEnablePvdFunction",
            code=lambda_code,
            handler="get_enable_pvd.lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            role=cast(iam.IRole, self.custom_resource_role),
            timeout=Duration.seconds(30),
        )

        self.enable_dns = CustomResource(
            self,
            "EnableVpcDns",
            service_token=self.enable_dns_function.function_arn,
            properties={"VpcId": self.vpc.vpc_id},
        )

        self.s3_gateway_endpoint = CustomResource(
            self,
            "EnsureS3Endpoint",
            service_token=self.s3_endpoint_function.function_arn,
            properties={
                "SubnetId": self.public_subnet_id,
                "VpcId": self.vpc.vpc_id,
                "Region": self.region,
            },
        )
        self.s3_gateway_endpoint.node.add_dependency(self.enable_dns)

        self.private_dns_query = CustomResource(
            self,
            "CheckPrivateDns",
            service_token=self.private_dns_function.function_arn,
            properties={
                "EndpointServiceName": f"com.amazonaws.{self.region}.cloudformation",
                "VpcId": self.vpc.vpc_id,
            },
        )
        self.private_dns_query.node.add_dependency(self.enable_dns)

    def _create_security_components(self) -> None:
        self.bastion = DorisBastion(
            self,
            "Bastion",
            vpc=self.vpc,
            public_subnet=self.public_subnet,
            key_pair_name=self.key_pair_name,
            remote_access_cidr=self.remote_access_cidr,
            ami_id=self.ami_id,
        )

        self.doris_security_groups = DorisSecurityGroups(
            self,
            "DorisSecurityGroups",
            vpc=self.vpc,
            vpc_cidr=self.vpc_cidr,
            bastion_security_group=self.bastion.security_group,
            doris_ports=DORIS_PORTS,
        )

        self.doris_security_group = self.doris_security_groups.security_group

    def _create_cloudformation_endpoint(self) -> None:
        private_dns_enabled = cast(
            IResolvable,
            self.private_dns_query.get_att("CanEnablePrivateDns"),
        )

        self.cfn_endpoint = ec2.CfnVPCEndpoint(
            self,
            "CloudFormationEndpoint",
            vpc_id=self.vpc.vpc_id,
            service_name=f"com.amazonaws.{self.region}.cloudformation",
            vpc_endpoint_type="Interface",
            private_dns_enabled=private_dns_enabled,
            subnet_ids=[self.public_subnet_id],
            security_group_ids=[
                self.doris_security_groups.security_group_id,
                self.bastion.security_group_id,
            ],
        )
        self.cfn_endpoint.node.add_dependency(self.enable_dns)

    def _create_compute_components(self) -> None:
        be_fleet = DorisBeFleet(
            self,
            "BeFleet",
            subnet_id=self.public_subnet_id,
            security_group_id=self.doris_security_groups.security_group_id,
            key_pair_name=self.key_pair_name,
            ami_id=self.ami_id,
            instance_type=self.be_node_instance_type,
            node_count=self.be_node_count,
            jdk_download_url=self.jdk_download_url,
            doris_download_url=self.doris_download_url,
            be_log_dir=self.be_log_dir,
            sys_log_level=self.sys_log_level,
            volume_type=self.volume_type,
            volume_size=self.volume_size,
        )
        be_fleet.add_launch_dependencies(self.s3_gateway_endpoint, self.cfn_endpoint)
        self.be_fleet = be_fleet
        self.be_instances = be_fleet.instances
        self.be_private_ips = be_fleet.private_ips

        fe_fleet = DorisFeFleet(
            self,
            "FeFleet",
            subnet_id=self.public_subnet_id,
            security_group_id=self.doris_security_groups.security_group_id,
            key_pair_name=self.key_pair_name,
            ami_id=self.ami_id,
            instance_type=self.fe_node_instance_type,
            jdk_download_url=self.jdk_download_url,
            doris_download_url=self.doris_download_url,
            meta_dir=self.meta_dir,
            log_dir=self.log_dir,
            log_level=self.log_level,
            volume_type=self.volume_type,
            be_private_ips=self.be_private_ips,
        )
        fe_fleet.add_launch_dependencies(self.s3_gateway_endpoint, self.cfn_endpoint)
        self.fe_fleet = fe_fleet
        self.fe_master_instance = fe_fleet.instance

    def _expose_outputs(self) -> None:
        CfnOutput(self, "BastionEip", value=self.bastion_public_ip)
        CfnOutput(self, "BastionSecurityGroupId", value=self.bastion_security_group_id)
        CfnOutput(self, "DorisSecurityGroupId", value=self.doris_security_group_id)
        CfnOutput(self, "FeMasterInstanceId", value=self.fe_master_instance.ref)
        CfnOutput(self, "FeMasterPrivateIp", value=self.fe_master_private_ip)

        for idx, instance in enumerate(self.be_instances, start=1):
            CfnOutput(self, f"BeInstance{idx}", value=instance.ref)
            CfnOutput(
                self,
                f"BeInstancePrivateIp{idx}",
                value=instance.attr_private_ip,
            )

    @property
    def bastion_public_ip(self) -> str:
        return self.bastion.public_ip

    @property
    def bastion_security_group_id(self) -> str:
        return self.bastion.security_group_id

    @property
    def doris_security_group_id(self) -> str:
        return self.doris_security_groups.security_group_id

    @property
    def fe_master_private_ip(self) -> str:
        return self.fe_master_instance.attr_private_ip

    @property
    def be_private_ip_addresses(self) -> List[str]:
        return self.be_private_ips[: self.be_node_count]

    @property
    def doris_download_package_url(self) -> str:
        return self.doris_download_url

    @property
    def jdk_download_package_url(self) -> str:
        return self.jdk_download_url
