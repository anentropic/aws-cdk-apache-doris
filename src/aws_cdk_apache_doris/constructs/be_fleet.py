from typing import Any, List, Sequence

from aws_cdk import (
    CfnCreationPolicy,
    CfnResourceSignal,
    Fn,
    Stack,
)
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
        subnet_id: str,
        security_group_id: str,
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

        self.instances: List[ec2.CfnInstance] = []
        self.private_ips: List[str] = ["0.0.0.0"] * 5

        for index in range(node_count):
            logical_id = f"BeInstance{index + 1}"
            user_data = self._render_user_data(
                logical_id,
                jdk_download_url,
                doris_download_url,
                be_log_dir,
                sys_log_level,
            )
            instance = ec2.CfnInstance(
                self,
                logical_id,
                image_id=ami_id,
                instance_type=instance_type,
                subnet_id=subnet_id,
                security_group_ids=[security_group_id],
                key_name=key_pair_name,
                block_device_mappings=self._block_device_mappings(
                    volume_size_num,
                    volume_type,
                    iops_value,
                ),
                user_data=Fn.base64(user_data),
            )
            instance.cfn_options.creation_policy = CfnCreationPolicy(
                resource_signal=CfnResourceSignal(count=1, timeout="PT10M"),
            )

            self.instances.append(instance)
            self.private_ips[index] = instance.attr_private_ip

    def add_launch_dependencies(self, *dependencies: Any) -> None:
        for dependency in dependencies:
            for instance in self.instances:
                instance.add_dependency(dependency)

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
    def _block_device_mappings(
        volume_size: int,
        volume_type: str,
        iops_value: int | None,
    ) -> Sequence[ec2.CfnInstance.BlockDeviceMappingProperty]:
        return [
            ec2.CfnInstance.BlockDeviceMappingProperty(
                device_name="/dev/xvdh",
                ebs=ec2.CfnInstance.EbsProperty(
                    volume_size=volume_size,
                    volume_type=volume_type,
                    iops=iops_value,
                    delete_on_termination=True,
                ),
            ),
            ec2.CfnInstance.BlockDeviceMappingProperty(
                device_name="/dev/xvdt",
                ebs=ec2.CfnInstance.EbsProperty(
                    volume_size=50,
                    volume_type=volume_type,
                    iops=iops_value,
                    delete_on_termination=True,
                ),
            ),
        ]
