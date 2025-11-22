from collections.abc import Sequence

from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class DorisSecurityGroups(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        vpc_cidr: str | None,
        use_client_access_security_group: bool,
        bastion_security_group: ec2.ISecurityGroup,
        doris_ports: Sequence[int],
    ) -> None:
        super().__init__(scope, construct_id)

        self.client_access_security_group: ec2.ISecurityGroup | None = None
        if use_client_access_security_group:
            self.client_access_security_group = ec2.SecurityGroup(
                self,
                "DorisClientAccessSecurityGroup",
                vpc=vpc,
                description=(
                    "Attach this security group to workloads that need Doris access"
                ),
            )

        self.security_group = ec2.SecurityGroup(
            self,
            "DorisSecurityGroup",
            vpc=vpc,
            description="Security group for Doris cluster nodes",
            allow_all_outbound=False,
        )
        self.security_group.add_egress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp_range(0, 65535),
            "Allow outbound TCP",
        )

        self.security_group.add_ingress_rule(
            bastion_security_group,
            ec2.Port.tcp(22),
            "Allow SSH from bastion",
        )

        for port in doris_ports:
            # Allow cluster members to talk to each other only on required Doris ports.
            self.security_group.add_ingress_rule(
                self.security_group,
                ec2.Port.tcp(port),
                f"Allow Doris port {port} within the cluster",
            )

            if self.client_access_security_group is not None:
                self.security_group.add_ingress_rule(
                    self.client_access_security_group,
                    ec2.Port.tcp(port),
                    f"Allow Doris port {port} from client access security group",
                )

            if vpc_cidr:
                self.security_group.add_ingress_rule(
                    ec2.Peer.ipv4(vpc_cidr),
                    ec2.Port.tcp(port),
                    f"Allow Doris port {port} from CIDR {vpc_cidr}",
                )

        # Note: client access is mutually exclusive with CIDR ingress. Both being
        # configured simultaneously indicates a caller error and should be
        # prevented by the higher-level construct.

    @property
    def security_group_id(self) -> str:
        return self.security_group.security_group_id

    @property
    def client_access_security_group_id(self) -> str:
        if self.client_access_security_group is None:
            raise ValueError(
                "Client access security group is disabled when CIDR ingress is used"
            )
        return self.client_access_security_group.security_group_id
