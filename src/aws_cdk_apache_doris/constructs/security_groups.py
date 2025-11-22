from typing import Sequence

from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class DorisSecurityGroups(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        vpc_cidr: str,
        bastion_security_group: ec2.ISecurityGroup,
        doris_ports: Sequence[int],
    ) -> None:
        super().__init__(scope, construct_id)

        self.security_group = ec2.SecurityGroup(
            self,
            "DorisSecurityGroup",
            vpc=vpc,
            description="Security group for Doris cluster nodes",
            allow_all_outbound=True,
        )

        for port in doris_ports:
            self.security_group.add_ingress_rule(
                ec2.Peer.ipv4(vpc_cidr),
                ec2.Port.tcp(port),
                f"Allow Doris port {port} inside VPC",
            )

        self.security_group.add_ingress_rule(
            bastion_security_group,
            ec2.Port.tcp(22),
            "Allow SSH from bastion",
        )
        self.security_group.add_ingress_rule(
            self.security_group,
            ec2.Port.all_traffic(),
            "Allow intra-cluster traffic",
        )

    @property
    def security_group_id(self) -> str:
        return self.security_group.security_group_id
