#!/bin/env python

from troposphere import GetAZs, Join, Parameter, Ref, Select, Tags, Template
import troposphere.ec2 as ec2

if __name__ == "__main__":

    t = Template()

    ami = "ami-0b8b10b5bf11f3a22"

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

    nacl = t.add_resource(
        ec2.NetworkAcl(
            "NACL", VpcId=Ref(vpc), Tags=Tags(Name=Join("", [Ref(name), "-NACL"]))
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

    routeTable = t.add_resource(
        ec2.RouteTable(
            "PublicRouteTable",
            VpcId=Ref(vpc),
            Tags=Tags(Name=Join("", [Ref(name), "-PUBLIC"])),
        )
    )

    for i in range(0, 3):
        subnet = t.add_resource(
            ec2.Subnet(
                f"Subnet{i}",
                AvailabilityZone=Select(i, GetAZs(Ref("AWS::Region"))),
                CidrBlock=f"10.0.{i}.0/24",
                MapPublicIpOnLaunch=True,
                VpcId=Ref(vpc),
                Tags=Tags(Name=f"10.0.{i}.0/24"),
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

    securityGroup = t.add_resource(
        ec2.SecurityGroup(
            "SecurityGroup",
            GroupDescription=f"Jump-Box-SG",
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

    with open("template.yml", "w") as file:
        file.write(t.to_yaml())
