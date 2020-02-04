#!/bin/env python

from troposphere import GetAZs, Join, Parameter, Ref, Select, Tags, Template
from awacs.aws import Allow, Condition, Policy, Principal, Statement, Action
from awacs.aws import IpAddress
from awacs.sts import AssumeRole
import random
import troposphere.cloudfront as cloudfront
import troposphere.ec2 as ec2
import troposphere.iam as iam
import troposphere.s3 as s3

if __name__ == "__main__":

    t = Template()

    ami = "ami-0b8b10b5bf11f3a22"

    buckets = ["nameBucket", "cloudfrontBucket"]

    natAmi = "ami-0f113fc1f0244a121"

    name = t.add_parameter(
        Parameter(
            "Name",
            Description="Enter your name. Used for resource tagging",
            Type="String",
        )
    )

    sshAddress = t.add_parameter(
        Parameter("SSH", Description="Enter your public IP address", Type="String")
    )

    sshKey = t.add_parameter(
        Parameter(
            "sshKey",
            Description="SSH Key Pair Name",
            Type="String",
            Default="matt.empson",
        )
    )

    vpc = t.add_resource(
        ec2.VPC(
            "VPC",
            CidrBlock="10.0.0.0/16",
            Tags=Tags(Name=Join("", [Ref(name), "-VPC"])),
        )
    )

    igw = t.add_resource(
        ec2.InternetGateway("IGW", Tags=Tags(Name=Join("", [Ref(name), "-IGW"])))
    )

    # Jump box security group
    securityGroup = t.add_resource(
        ec2.SecurityGroup(
            "SecurityGroup",
            GroupDescription="Jump-Box-SG",
            GroupName="jumpbox",
            VpcId=Ref(vpc),
            Tags=Tags(Name=Join("", [Ref(name), "-jump-box"])),
        )
    )

    securityGroupINSSH = t.add_resource(
        ec2.SecurityGroupIngress(
            "SGSSHAllow",
            Description=Join("", [Ref(name), "s source IP"]),
            CidrIp=Join("", [Ref(sshAddress), "/32"]),
            FromPort=22,
            ToPort=22,
            IpProtocol="6",
            GroupId=Ref(securityGroup),
        )
    )

    securityGroupOUTICMP = t.add_resource(
        ec2.SecurityGroupEgress(
            "SGICMPAllow",
            CidrIp="0.0.0.0/0",
            FromPort=-1,
            ToPort=-1,
            IpProtocol="1",
            GroupId=Ref(securityGroup),
        )
    )

    # NAT instance security group
    natSecurityGroup = t.add_resource(
        ec2.SecurityGroup(
            "NatSecurityGroup",
            GroupDescription="NAT-SG",
            GroupName="nat",
            VpcId=Ref(vpc),
            Tags=Tags(Name=Join("", [Ref(name), "-nat-instance"])),
        )
    )

    natSecurityGroupIN = t.add_resource(
        ec2.SecurityGroupIngress(
            "NATAllowIN",
            Description="VPC CIDR",
            CidrIp="10.0.0.0/16",
            FromPort=-1,
            ToPort=-1,
            IpProtocol="-1",
            GroupId=Ref(natSecurityGroup),
        )
    )

    natSecurityGroupOUT = t.add_resource(
        ec2.SecurityGroupEgress(
            "NATAllowOUT",
            CidrIp="0.0.0.0/0",
            FromPort=-1,
            ToPort=-1,
            IpProtocol="-1",
            GroupId=Ref(natSecurityGroup),
        )
    )

    # S3 instance security group
    S3SecurityGroup = t.add_resource(
        ec2.SecurityGroup(
            "S3SecurityGroup",
            GroupDescription="S3-SG",
            GroupName="S3",
            VpcId=Ref(vpc),
            Tags=Tags(Name=Join("", [Ref(name), "-S3-instance"])),
        )
    )

    S3SecurityGroupIN = t.add_resource(
        ec2.SecurityGroupIngress(
            "S3NATAllowIN",
            Description="VPC CIDR",
            CidrIp="10.0.0.0/16",
            FromPort=-1,
            ToPort=-1,
            IpProtocol="-1",
            GroupId=Ref(S3SecurityGroup),
        )
    )

    S3SecurityGroupOUT = t.add_resource(
        ec2.SecurityGroupEgress(
            "S3AllowOUT",
            CidrIp="0.0.0.0/0",
            FromPort=-1,
            ToPort=-1,
            IpProtocol="-1",
            GroupId=Ref(S3SecurityGroup),
        )
    )

    # Jump Box
    instance = t.add_resource(
        ec2.Instance(
            "JumpBox",
            ImageId=ami,
            InstanceType="t2.micro",
            KeyName=Ref(sshKey),
            SecurityGroupIds=[Ref(securityGroup)],
            SubnetId=Ref("Subnet1"),
            Tags=Tags(Name=Join("", [Ref(name), "-jump-box"])),
        )
    )

    # NAT Instance
    natInstance = t.add_resource(
        ec2.Instance(
            "NatInstance",
            ImageId=natAmi,
            InstanceType="t2.micro",
            KeyName=Ref(sshKey),
            SecurityGroupIds=[Ref(natSecurityGroup)],
            SubnetId=Ref("Subnet1"),
            Tags=Tags(Name=Join("", [Ref(name), "-nat"])),
        )
    )

    # IAM Policy and Role for S3 instance
    S3Policy = iam.Policy(
        PolicyName="S3Policy",
        PolicyDocument=Policy(
            Statement=[
                Statement(
                    Sid="S3Policy",
                    Effect=Allow,
                    Action=[
                        Action("s3", "DeleteObject"),
                        Action("s3", "GetObject"),
                        Action("s3", "PutObject"),
                    ],
                    Resource=["arn:aws:s3:::namebucket-*/*"],
                    Condition=Condition([IpAddress("aws:SourceIp", "10.0.0.0/16")]),
                )
            ]
        ),
    )

    S3Role = t.add_resource(
        iam.Role(
            "S3Role",
            RoleName="S3Role",
            AssumeRolePolicyDocument=Policy(
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[AssumeRole],
                        Principal=Principal("Service", ["ec2.amazonaws.com"]),
                    )
                ]
            ),
            Policies=[S3Policy],
        )
    )

    S3InstanceProfile = t.add_resource(
        iam.InstanceProfile("InstanceProfile", Roles=[Ref(S3Role)])
    )

    # S3 Instance
    S3Instance = t.add_resource(
        ec2.Instance(
            "S3Instance",
            IamInstanceProfile=Ref(S3InstanceProfile),
            ImageId=ami,
            InstanceType="t2.micro",
            KeyName=Ref(sshKey),
            SecurityGroupIds=[Ref(S3SecurityGroup)],
            SubnetId=Ref("Subnet4"),
            Tags=Tags(Name=Join("", [Ref(name), "-S3-instance"])),
        )
    )

    # Public NACL
    nacl = t.add_resource(
        ec2.NetworkAcl(
            "NACL",
            VpcId=Ref(vpc),
            Tags=Tags(Name=Join("", [Ref(name), "-NACL-PUBLIC"])),
        )
    )

    naclIN = t.add_resource(
        ec2.NetworkAclEntry(
            "InboundDeny",
            CidrBlock="0.0.0.0/0",
            NetworkAclId=Ref(nacl),
            Protocol=-1,
            RuleAction="deny",
            RuleNumber=10,
        )
    )

    naclINSSH = t.add_resource(
        ec2.NetworkAclEntry(
            "SSHAllow",
            CidrBlock=Join("", [Ref(sshAddress), "/32"]),
            NetworkAclId=Ref(nacl),
            PortRange=ec2.PortRange(From=22, To=22),
            Protocol=6,
            RuleAction="allow",
            RuleNumber=20,
        )
    )

    naclOut = t.add_resource(
        ec2.NetworkAclEntry(
            "OutBoundAllow",
            CidrBlock="0.0.0.0/0",
            Egress=True,
            NetworkAclId=Ref(nacl),
            Protocol=-1,
            RuleAction="allow",
            RuleNumber=10,
        )
    )

    # Private NACL
    privateNacl = t.add_resource(
        ec2.NetworkAcl(
            "PrivateNACL",
            VpcId=Ref(vpc),
            Tags=Tags(Name=Join("", [Ref(name), "-NACL-PRIVATE"])),
        )
    )

    priavteNaclIN = t.add_resource(
        ec2.NetworkAclEntry(
            "PrivateInboundAllow",
            CidrBlock="0.0.0.0/0",
            NetworkAclId=Ref(privateNacl),
            Protocol=-1,
            RuleAction="allow",
            RuleNumber=10,
        )
    )

    privateNaclOut = t.add_resource(
        ec2.NetworkAclEntry(
            "PrivateOutBoundAllow",
            CidrBlock="0.0.0.0/0",
            Egress=True,
            NetworkAclId=Ref(privateNacl),
            Protocol=-1,
            RuleAction="allow",
            RuleNumber=10,
        )
    )

    # Public route table
    routeTable = t.add_resource(
        ec2.RouteTable(
            "PublicRouteTable",
            VpcId=Ref(vpc),
            Tags=Tags(Name=Join("", [Ref(name), "-PUBLIC"])),
        )
    )

    # Private route table
    privateRouteTable = t.add_resource(
        ec2.RouteTable(
            "PrivateRouteTable",
            VpcId=Ref(vpc),
            Tags=Tags(Name=Join("", [Ref(name), "-PRIVATE"])),
        )
    )

    privateDefaultRoute = t.add_resource(
        ec2.Route(
            "PrivateSubnetRoute",
            DestinationCidrBlock="0.0.0.0/0",
            InstanceId=Ref(natInstance),
            RouteTableId=Ref(privateRouteTable),
        )
    )

    # Public subnets
    for i in range(0, 3):
        subnet = t.add_resource(
            ec2.Subnet(
                f"Subnet{i}",
                AvailabilityZone=Select(i, GetAZs(Ref("AWS::Region"))),
                CidrBlock=f"10.0.{i}.0/24",
                MapPublicIpOnLaunch=True,
                VpcId=Ref(vpc),
                Tags=Tags(Name=f"10.0.{i}.0/24-PUBLIC"),
            )
        )

        subnetRouteTable = t.add_resource(
            ec2.SubnetRouteTableAssociation(
                f"Subnet{i}RT", RouteTableId=Ref(routeTable), SubnetId=Ref(subnet)
            )
        )

        subnetNACL = t.add_resource(
            ec2.SubnetNetworkAclAssociation(
                f"Subnet{i}NACL", NetworkAclId=Ref(nacl), SubnetId=Ref(subnet)
            )
        )

    # Private subnets
    for i in range(4, 7):
        privateSubnet = t.add_resource(
            ec2.Subnet(
                f"Subnet{i}",
                AvailabilityZone=Select(i - 4, GetAZs(Ref("AWS::Region"))),
                CidrBlock=f"10.0.{i}.0/24",
                MapPublicIpOnLaunch=False,
                VpcId=Ref(vpc),
                Tags=Tags(Name=f"10.0.{i}.0/24-PRIVATE"),
            )
        )

        privateSubnetRouteTable = t.add_resource(
            ec2.SubnetRouteTableAssociation(
                f"Subnet{i}RT",
                RouteTableId=Ref(privateRouteTable),
                SubnetId=Ref(privateSubnet),
            )
        )

        privateSubnetNACL = t.add_resource(
            ec2.SubnetNetworkAclAssociation(
                f"Subnet{i}NACL",
                NetworkAclId=Ref(privateNacl),
                SubnetId=Ref(privateSubnet),
            )
        )

    for bucket in buckets:
        randomPrefix = random.randrange(10 ** 15)

        s3bucket = t.add_resource(
            s3.Bucket(
                bucket,
                BucketName=f"{bucket.lower()}-{randomPrefix}",
                AccessControl="Private",
                PublicAccessBlockConfiguration=s3.PublicAccessBlockConfiguration(
                    BlockPublicAcls=True,
                    BlockPublicPolicy=True,
                    IgnorePublicAcls=True,
                    RestrictPublicBuckets=True,
                ),
                Tags=Tags(Name=f"{bucket}-{randomPrefix}"),
            )
        )

        if "cloudfront" in bucket:
            cloudfrontBucket = f"{bucket.lower()}-{randomPrefix}"

    cloudfront = t.add_resource(
        cloudfront.Distribution(
            "Cloudfront",
            DistributionConfig=cloudfront.DistributionConfig(
                Origins=[
                    cloudfront.Origin(
                        Id="1",
                        DomainName=f"{cloudfrontBucket}.s3-ap-southeast-2.amazonaws.com",
                        S3OriginConfig=cloudfront.S3OriginConfig(),
                    )
                ],
                DefaultCacheBehavior=cloudfront.DefaultCacheBehavior(
                    TargetOriginId="1",
                    ForwardedValues=cloudfront.ForwardedValues(QueryString=False),
                    ViewerProtocolPolicy="allow-all",
                ),
                Enabled=True,
                HttpVersion="http2",
            ),
        )
    )

    with open("template.yml", "w") as file:
        file.write(t.to_yaml())
