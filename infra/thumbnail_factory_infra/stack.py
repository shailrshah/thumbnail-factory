import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_iam as iam
from constructs import Construct

IMAGES = ("backend", "frontend", "gateway")
COMPOSE_VERSION = "v5.5.1"
APP_DIR = "/opt/thumbnail-factory"


class ThumbnailFactoryStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repos = [
            ecr.Repository(
                self,
                f"{name.capitalize()}Repo",
                repository_name=f"thumbnail-factory/{name}",
                image_scan_on_push=True,
                lifecycle_rules=[ecr.LifecycleRule(max_image_count=10)],
                removal_policy=cdk.RemovalPolicy.DESTROY,
                empty_on_delete=True,
            )
            for name in IMAGES
        ]

        vpc = ec2.Vpc.from_lookup(self, "DefaultVpc", is_default=True)

        security_group = ec2.SecurityGroup(
            self,
            "WebSg",
            vpc=vpc,
            description="HTTP only; deploys use SSM, so no SSH",
            allow_all_outbound=True,
        )
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP")

        role = iam.Role(
            self,
            "InstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
            ],
        )
        for repo in repos:
            repo.grant_pull(role)

        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "set -euxo pipefail",
            "dnf install -y docker",
            "systemctl enable --now docker",
            "mkdir -p /usr/local/lib/docker/cli-plugins",
            "curl -fsSL -o /usr/local/lib/docker/cli-plugins/docker-compose "
            f"https://github.com/docker/compose/releases/download/{COMPOSE_VERSION}"
            "/docker-compose-linux-x86_64",
            "chmod +x /usr/local/lib/docker/cli-plugins/docker-compose",
            f"mkdir -p {APP_DIR}",
        )

        instance = ec2.Instance(
            self,
            "Host",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            instance_type=ec2.InstanceType("t3.small"),
            # Cached in cdk.context.json: resolving "latest" on every deploy would replace the
            # instance (and its data) whenever Amazon publishes a new AMI.
            machine_image=ec2.MachineImage.latest_amazon_linux2023(cached_in_context=True),
            security_group=security_group,
            role=role,
            user_data=user_data,
            # User data only runs on first boot, so a changed script needs a new instance.
            user_data_causes_replacement=True,
            require_imdsv2=True,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(
                        20, volume_type=ec2.EbsDeviceVolumeType.GP3, encrypted=True
                    ),
                )
            ],
        )

        eip = ec2.CfnEIP(self, "Eip", instance_id=instance.instance_id)

        # CI credentials. OIDC would be preferable, but the project's SCP denies iam:*Provider*.
        # Access keys are created outside CDK so the secret never lands in CloudFormation (D4).
        ci_user = iam.User(self, "CiUser", user_name="thumbnail-factory-ci")
        for repo in repos:
            repo.grant_pull_push(ci_user)
        ci_user.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:SendCommand"],
                resources=[
                    self.format_arn(
                        service="ec2", resource="instance", resource_name=instance.instance_id
                    ),
                    self.format_arn(
                        service="ssm",
                        account="",
                        resource="document",
                        resource_name="AWS-RunShellScript",
                    ),
                ],
            )
        )
        # GetCommandInvocation doesn't support resource-level permissions.
        ci_user.add_to_policy(
            iam.PolicyStatement(actions=["ssm:GetCommandInvocation"], resources=["*"])
        )

        cdk.CfnOutput(self, "PublicUrl", value=f"http://{eip.attr_public_ip}")
        cdk.CfnOutput(self, "InstanceId", value=instance.instance_id)
        cdk.CfnOutput(
            self, "EcrRegistry", value=f"{self.account}.dkr.ecr.{self.region}.amazonaws.com"
        )
        cdk.CfnOutput(self, "CiUserName", value=ci_user.user_name)
