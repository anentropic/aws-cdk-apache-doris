#!/usr/bin/env python3
"""CDK app for integration testing."""

import aws_cdk as cdk

from aws_cdk_apache_doris import __version__

app = cdk.App()

# Simple stack for testing cdk synth
stack = cdk.Stack(
    app,
    "DorisTestStack",
    description=f"Test stack for aws-cdk-apache-doris v{__version__}",
)

app.synth()
