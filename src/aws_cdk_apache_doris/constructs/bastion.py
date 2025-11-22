from typing import cast

from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from constructs import Construct


class DorisBastion(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        public_subnet: ec2.ISubnet,
        key_pair_name: str,
        remote_access_cidr: str,
        ami_id: str,
    ) -> None:
        super().__init__(scope, construct_id)

        self.security_group = ec2.SecurityGroup(
            self,
            "BastionSecurityGroup",
            vpc=vpc,
            description="Security group for Doris bastion host",
            allow_all_outbound=True,
        )
        self.security_group.add_ingress_rule(
            ec2.Peer.ipv4(remote_access_cidr),
            ec2.Port.tcp(22),
            "SSH access to bastion",
        )

        machine_image = ec2.MachineImage.generic_linux(
            {Stack.of(self).region: ami_id},
        )

        bastion_host = ec2.BastionHostLinux(
            self,
            "BastionHost",
            vpc=vpc,
            subnet_selection=ec2.SubnetSelection(subnets=[public_subnet]),
            security_group=self.security_group,
            instance_name="DorisBastion",
            machine_image=machine_image,
            instance_type=ec2.InstanceType("t4g.nano"),
        )
        self.instance = bastion_host.instance

        cfn_instance = cast(ec2.CfnInstance, self.instance.node.default_child)
        cfn_instance.key_name = key_pair_name

        self.instance.user_data.add_commands("yum install -y mysql")
        self.instance.role.add_to_principal_policy(
            iam.PolicyStatement(
                actions=["ec2:AssociateAddress"],
                resources=["*"],
            )
        )

        self.eip = ec2.CfnEIP(
            self,
            "BastionEip",
            domain="vpc",
        )
        ec2.CfnEIPAssociation(
            self,
            "BastionEipAssociation",
            allocation_id=self.eip.attr_allocation_id,
            instance_id=self.instance.instance_id,
        )

    @property
    def security_group_id(self) -> str:
        return self.security_group.security_group_id

    @property
    def public_ip(self) -> str:
        return self.eip.ref
