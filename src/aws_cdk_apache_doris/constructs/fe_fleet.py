from typing import Any, Sequence

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

from aws_cdk_apache_doris.user_data import FE_USER_DATA_TEMPLATE, render_user_data


class DorisFeFleet(Construct):
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
        jdk_download_url: str,
        doris_download_url: str,
        meta_dir: str,
        log_dir: str,
        log_level: str,
        volume_type: str,
        be_private_ips: Sequence[str],
    ) -> None:
        super().__init__(scope, construct_id)

        iops_value = 1000 if volume_type == "io1" else None
        user_data = self._render_user_data(
            jdk_download_url,
            doris_download_url,
            meta_dir,
            log_dir,
            log_level,
            be_private_ips,
        )

        self.instance = ec2.CfnInstance(
            self,
            "FeMasterInstance",
            image_id=ami_id,
            instance_type=instance_type,
            subnet_id=subnet_id,
            security_group_ids=[security_group_id],
            key_name=key_pair_name,
            block_device_mappings=[
                ec2.CfnInstance.BlockDeviceMappingProperty(
                    device_name="/dev/xvdt",
                    ebs=ec2.CfnInstance.EbsProperty(
                        volume_size=50,
                        volume_type=volume_type,
                        iops=iops_value,
                        delete_on_termination=True,
                    ),
                )
            ],
            user_data=Fn.base64(user_data),
        )
        self.instance.cfn_options.creation_policy = CfnCreationPolicy(
            resource_signal=CfnResourceSignal(count=1, timeout="PT60M"),
        )

    def add_launch_dependencies(self, *dependencies: Any) -> None:
        for dependency in dependencies:
            self.instance.add_dependency(dependency)

    def _render_user_data(
        self,
        jdk_download_url: str,
        doris_download_url: str,
        meta_dir: str,
        log_dir: str,
        log_level: str,
        be_private_ips: Sequence[str],
    ) -> str:
        stack = Stack.of(self)
        be_ip_args = " ".join(str(ip) for ip in be_private_ips)
        return render_user_data(
            FE_USER_DATA_TEMPLATE,
            {
                "STACK_ID": stack.stack_id,
                "REGION": stack.region,
                "JDK_DOWNLOAD_URL": jdk_download_url,
                "DORIS_DOWNLOAD_URL": doris_download_url,
                "META_DIR": meta_dir,
                "LOG_DIR": log_dir,
                "LOG_LEVEL": log_level,
                "BE_IP_ARGS": be_ip_args,
            },
        )
