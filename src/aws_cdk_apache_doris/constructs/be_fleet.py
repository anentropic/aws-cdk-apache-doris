from collections.abc import Sequence
from typing import Any

from aws_cdk import Stack
from aws_cdk import (
    aws_ec2 as ec2,
)
from constructs import Construct

from aws_cdk_apache_doris.user_data import BE_USER_DATA_TEMPLATE, render_user_data


class DorisBeFleet(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        subnet: ec2.ISubnet,
        security_group: ec2.ISecurityGroup,
        key_pair_name: str,
        ami_id: str,
        instance_type: str,
        node_count: int,
        jdk_download_url: str,
        doris_download_url: str,
        be_log_dir: str,
        sys_log_level: str,
        volume_type: str,
        volume_size: str,
    ) -> None:
        super().__init__(scope, construct_id)

        volume_size_num = int(volume_size)
        iops_value = 1000 if volume_type == "io1" else None
        volume_type_enum = ec2.EbsDeviceVolumeType[volume_type.upper()]
        machine_image = ec2.MachineImage.generic_linux(
            {Stack.of(self).region: ami_id},
        )
        instance_type_obj = ec2.InstanceType(instance_type)

        self.instances: list[ec2.Instance] = []
        self.private_ips: list[str] = ["0.0.0.0"] * node_count

        block_devices = self._block_devices(
            volume_size_num,
            volume_type_enum,
            iops_value,
        )

        for index in range(node_count):
            logical_id = f"BeInstance{index + 1}"
            user_data = self._render_user_data(
                logical_id,
                jdk_download_url,
                doris_download_url,
                be_log_dir,
                sys_log_level,
            )
            instance = ec2.Instance(
                self,
                logical_id,
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(subnets=[subnet]),
                security_group=security_group,
                key_name=key_pair_name,
                machine_image=machine_image,
                instance_type=instance_type_obj,
                user_data=ec2.UserData.custom(user_data),
                block_devices=block_devices,
            )

            self.instances.append(instance)
            self.private_ips[index] = instance.instance_private_ip or "0.0.0.0"

    def add_launch_dependencies(self, *dependencies: Any) -> None:
        for dependency in dependencies:
            for instance in self.instances:
                instance.node.add_dependency(dependency)

    def _render_user_data(
        self,
        logical_id: str,
        jdk_download_url: str,
        doris_download_url: str,
        be_log_dir: str,
        sys_log_level: str,
    ) -> str:
        stack = Stack.of(self)
        stack_id = stack.stack_id
        region = stack.region
        return render_user_data(
            BE_USER_DATA_TEMPLATE,
            {
                "STACK_ID": stack_id,
                "LOGICAL_ID": logical_id,
                "REGION": region,
                "JDK_DOWNLOAD_URL": jdk_download_url,
                "DORIS_DOWNLOAD_URL": doris_download_url,
                "BE_LOG_DIR": be_log_dir,
                "SYS_LOG_LEVEL": sys_log_level,
            },
        )

    @staticmethod
    def _block_devices(
        volume_size: int,
        volume_type: ec2.EbsDeviceVolumeType,
        iops_value: int | None,
    ) -> Sequence[ec2.BlockDevice]:
        return [
            ec2.BlockDevice(
                device_name="/dev/xvdh",
                volume=ec2.BlockDeviceVolume.ebs(
                    volume_size=volume_size,
                    volume_type=volume_type,
                    iops=iops_value,
                    delete_on_termination=True,
                ),
            ),
            ec2.BlockDevice(
                device_name="/dev/xvdt",
                volume=ec2.BlockDeviceVolume.ebs(
                    volume_size=50,
                    volume_type=volume_type,
                    iops=iops_value,
                    delete_on_termination=True,
                ),
            ),
        ]
