# Doris CDK vs CloudFormation Divergences

Date: 2025-11-22

## Bastion Host
- CloudFormation used an Auto Scaling Group of x86 `t2.micro` instances with health checks; the CDK construct deploys a single `BastionHostLinux` on `t4g.nano` with no ASG.
- The AMI mappings (`ami-02d7fd1c2af6eead0`, etc.) are x86_64, so the ARM `t4g` instance will fail to boot.
- Resolution: Instance type switched to `t3.nano` to match the AMI architecture, ASG dropped, Elastic IP kept.

## Cluster Security Groups
- Template security group opened specific Doris ports to the provided CIDR (parent stack defaulted to `0.0.0.0/0`).
- CDK construct defaults to the VPC CIDR, blocking outside clients unless `vpc_cidr` is overridden.
- CDK also allows all intra-cluster traffic (`self` ingress) plus unrestricted egress, which is broader east/west access than the template.
- Resolution: Added dedicated client-access security group support plus optional CIDR ingress so behavior now matches the template when configured, though defaults remain more restrictive (no public CIDR unless explicitly supplied).

## Front-End Topology
- CloudFormation supported `FeNodeCount = 3` to add follower FEs and a helper instance for quorum.
- CDK construct hard-codes `FE_NODE_COUNTS = [1]`, so only the master FE is ever launched and HA mode is unavailable.
- Resolution: Allow any positive integer number of nodes.

## Stack Health Signalling
- Template EC2 resources used `CreationPolicy/ResourceSignal` to wait for `/opt/aws/bin/cfn-signal` from bootstrap scripts.
- CDK instances used to omit creation policies, so CloudFormation treated them as successful even if user data (which still calls `cfn-signal`) failed.
- Resolution: Doris BE and FE instances now attach `CreationPolicy/ResourceSignal` blocks (10 minutes for BE, 60 minutes for FE) so stack progress pauses until the user data signals success.
