## Create a VPC
```sh
aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --region ap-southeast-2 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=MyVpc}]'
```

## Create IGW
```sh
aws ec2 create-internet-gateway \
    --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=my-igw}]'
```

## Attach IGW to VPC
```sh
aws ec2 attach-internet-gateway \
    --internet-gateway-id <IGW-ID> \
    --vpc-id <VPC-ID>
```

## Create Public Subnet 1 in AZ A
```sh
aws ec2 create-subnet \
    --vpc-id <VPC-ID> \
    --cidr-block 10.0.0.0/24 \
    --availability-zone ap-southeast-2a \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=my-subnet-a}]'
```

## Create Public Subnet 2 in AZ B
```sh
aws ec2 create-subnet \
    --vpc-id <VPC-ID> \
    --cidr-block 10.0.1.0/24 \
    --availability-zone ap-southeast-2b \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=my-subnet-b}]'
```

## Create Route Table
```sh
aws ec2 create-route-table \
    --vpc-id <VPC-ID>
```

## Add Route to IGW in Route Table
```sh
aws ec2 create-route \
    --route-table-id <RT-ID> \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id <IGW-ID>
```

## Associate Route Table with Subnet A
```sh
aws ec2 associate-route-table \
    --route-table-id <RT-ID> \
    --subnet-id <SUBNET-A-ID>
```

## Associate Route Table with Subnet B
```sh
aws ec2 associate-route-table \
    --route-table-id <RT-ID> \
    --subnet-id <SUBNET-B-ID>
```

# EC2

## Create a Key pair
```sh

```

## Create a Security Group
```sh

```

## Launch the EC2 Instance
```sh

```

## Attach an IAM Role
```sh

```

## Get Public IPv4 address of EC2
```sh

```

## Use Key pair SSH to Instance
```sh

```

## Install Java, then Jenkins
```sh

```

## Access Jenkins UI
```text
http://<Public_IP>:8080
```