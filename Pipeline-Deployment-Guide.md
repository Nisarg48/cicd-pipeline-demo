# Jenkins + ArgoCD + EKS + RDS Pipeline Setup Guide

## Environment Setup

### Set region and get your public IP
```sh
export AWS_REGION=ap-southeast-2
export MY_PUBLIC_IP=$(curl -s https://checkip.amazonaws.com)
echo "MY_PUBLIC_IP=$MY_PUBLIC_IP"
```

## VPC & Networking

### Create a VPC
```sh
export VPC_ID=$(aws ec2 create-vpc \
                    --cidr-block 10.0.0.0/16 \
                    --region $AWS_REGION \
                    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=MyVpc}]' \
                    --query 'Vpc.VpcId' \
                    --output text)
echo "VPC_ID=$VPC_ID"
```

### Create IGW
```sh
export IGW_ID=$(aws ec2 create-internet-gateway \
                    --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=my-igw}]' \
                    --region $AWS_REGION \
                    --query 'InternetGateway.InternetGatewayId' \
                    --output text)
echo "IGW_ID=$IGW_ID"
```

### Attach IGW to VPC
```sh
aws ec2 attach-internet-gateway \
    --internet-gateway-id $IGW_ID \
    --vpc-id $VPC_ID \
    --region $AWS_REGION
```

### Create Public Subnet 1 in AZ A
```sh
export SUBNET_A_ID=$(aws ec2 create-subnet \
                        --vpc-id $VPC_ID \
                        --cidr-block 10.0.0.0/24 \
                        --availability-zone ${AWS_REGION}a \
                        --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-subnet-a}]' \
                        --region $AWS_REGION \
                        --query 'Subnet.SubnetId' \
                        --output text)
echo "SUBNET_A_ID=$SUBNET_A_ID"
```

### Create Public Subnet 2 in AZ B
```sh
export SUBNET_B_ID=$(aws ec2 create-subnet \
                        --vpc-id $VPC_ID \
                        --cidr-block 10.0.1.0/24 \
                        --availability-zone ${AWS_REGION}b \
                        --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-subnet-b}]' \
                        --region $AWS_REGION \
                        --query 'Subnet.SubnetId' \
                        --output text)
echo "SUBNET_B_ID=$SUBNET_B_ID"
```

### Create Route Table
```sh
export RT_ID=$(aws ec2 create-route-table \
                    --vpc-id $VPC_ID \
                    --region $AWS_REGION \
                    --query 'RouteTable.RouteTableId' \
                    --output text)
echo "RT_ID=$RT_ID"
```

### Add Route to IGW in Route Table
```sh
aws ec2 create-route \
    --route-table-id $RT_ID \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id $IGW_ID \
    --region $AWS_REGION
```

### Associate Route Table with Subnet A
```sh
aws ec2 associate-route-table \
    --route-table-id $RT_ID \
    --subnet-id $SUBNET_A_ID \
    --region $AWS_REGION
```

### Associate Route Table with Subnet B
```sh
aws ec2 associate-route-table \
    --route-table-id $RT_ID \
    --subnet-id $SUBNET_B_ID \
    --region $AWS_REGION
```

## EC2 (Jenkins Server)

### Create a Key pair
```sh
aws ec2 create-key-pair \
    --key-name my-ec2-keypair \
    --region $AWS_REGION \
    --query 'KeyMaterial' \
    --output text > my-ec2-keypair.pem
```
```sh
chmod 400 my-ec2-keypair.pem
```

### Create a Security Group
```sh
export SG_ID=$(aws ec2 create-security-group \
                    --group-name my-ec2-security-group \
                    --description "My ec2 security group for Jenkins instance." \
                    --vpc-id $VPC_ID \
                    --region $AWS_REGION \
                    --query 'GroupId' \
                    --output text)
echo "SG_ID=$SG_ID"
```

### Add Inbound rule in SG
```sh
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp --port 22 \
    --cidr $MY_PUBLIC_IP/32 \
    --region $AWS_REGION
```
```sh
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp --port 8080 \
    --cidr $MY_PUBLIC_IP/32 \
    --region $AWS_REGION
```

### Get Amazon Linux 2023 Image AMI Id
```sh
export AMI_ID=$(aws ec2 describe-images \
                    --owners amazon \
                    --region $AWS_REGION \
                    --filters "Name=name,Values=al2023-ami-*-x86_64" \
                    --query 'sort_by(Images,&CreationDate)[-1].ImageId' \
                    --output text)
echo "AMI_ID=$AMI_ID"
```

### Launch the EC2 Instance
```sh
export INSTANCE_ID=$(aws ec2 run-instances \
                        --image-id $AMI_ID \
                        --count 1 \
                        --instance-type t2.micro \
                        --key-name my-ec2-keypair \
                        --security-group-ids $SG_ID \
                        --subnet-id $SUBNET_A_ID \
                        --region $AWS_REGION \
                        --associate-public-ip-address \
                        --query 'Instances[0].InstanceId' \
                        --output text)
echo "INSTANCE_ID=$INSTANCE_ID"
```

### Create IAM role
```sh
aws iam create-role \
    --role-name jenkins-iam-role \
    --assume-role-policy-document file://ec2-policy.json
```

### Create Instance Profile
```sh
aws iam create-instance-profile \
    --instance-profile-name jenkins-instance-profile
```

### Add IAM role to Instance profile
```sh
aws iam add-role-to-instance-profile \
    --instance-profile-name jenkins-instance-profile \
    --role-name jenkins-iam-role
```

### Attach an IAM Role
```sh
aws ec2 associate-iam-instance-profile \
    --instance-id $INSTANCE_ID \
    --iam-instance-profile Name="jenkins-instance-profile" \
    --region $AWS_REGION
```

### Get Public IPv4 address of EC2
```sh
export EC2_PUBLIC_IP=$(aws ec2 describe-instances \
                            --instance-ids $INSTANCE_ID \
                            --region $AWS_REGION \
                            --query 'Reservations[0].Instances[0].PublicIpAddress' \
                            --output text)
echo "EC2_PUBLIC_IP=$EC2_PUBLIC_IP"
```

### Use Key pair SSH to Instance
```sh
ssh -i my-ec2-keypair.pem ec2-user@$EC2_PUBLIC_IP
```

### Install Java, then Jenkins
```sh
sudo yum update -y
```
```sh
sudo yum install java-17-amazon-corretto -y
```
```sh
java -version
```
```sh
sudo yum install wget -y
sudo wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
sudo rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io.key
sudo yum install jenkins -y
sudo systemctl start jenkins
sudo systemctl enable jenkins
sudo systemctl status jenkins
```
```sh
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

### Access Jenkins UI
```text
http://$EC2_PUBLIC_IP:8080
```

## Jenkins to GitHub Connection — UI Steps

### Step 1: Confirm the GitHub plugin is installed (Jenkins UI)
```text
Go to Manage Jenkins > Plugins > Installed.
Search for "GitHub".
If not present, install it from the Available tab and restart Jenkins if prompted.
```

### Step 2: Create a Pipeline job (Jenkins UI)
```text
From the Jenkins dashboard, click "New Item".
Enter a name, select "Pipeline", click OK.
Under the "Pipeline" section, set Definition to "Pipeline script from SCM".
Set SCM to "Git".
Paste your GitHub repo URL.
Set Branch Specifier to "main".
Leave Script Path as "Jenkinsfile" (default, since it sits at repo root).
```

### Step 3: Enable the GitHub webhook trigger (Jenkins UI)
```text
In the same job's configuration page, scroll to "Build Triggers".
Check "GitHub hook trigger for GITScm polling".
Save the job.
```

### Step 4: Add the webhook (GitHub UI)
```text
Go to your repository on GitHub > Settings > Webhooks > Add webhook.
Payload URL: http://<jenkins-public-ip>:8080/github-webhook/
Content type: application/json
Which events: "Just the push event"
Click "Add webhook".
```

### Step 5: Test the connection
```text
Push a small commit to your repository.
Check the Jenkins dashboard — a new build should start automatically within a few seconds, with no manual trigger.
```

## ECR + Jenkins Setup

### Create ECR Repository
```sh
export ECR_REPO_NAME="jenkins-argocd-eks-demo/<App-Name>"
aws ecr create-repository \
    --repository-name $ECR_REPO_NAME \
    --region $AWS_REGION
```

### Add ECR push permission to Jenkins IAM role
```sh
aws iam attach-role-policy \
    --role-name jenkins-iam-role \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
```

## Verify the CI part
```text
Now write the CI half of the Jenkinsfile: Checkout → Build → Test → Push to ECR.
Push a commit, confirm the image actually lands in ECR. This is a complete,
testable milestone on its own, before anything touches Kubernetes.
```

## EKS Setup

### Create Cluster on EKS
```sh
eksctl create cluster \
    --name development-cluster \
    --region $AWS_REGION \
    --vpc-public-subnets $SUBNET_A_ID,$SUBNET_B_ID \
    --nodegroup-name standard-worker \
    --node-type t3.small \
    --nodes 2 \
    --managed
```

### Add the ArgoCD Helm repo
```sh
helm repo add argocd https://argoproj.github.io/argo-helm
helm repo update
```

### Create a namespace for ArgoCD
```sh
kubectl create namespace argocd
```

### Install ArgoCD Helm chart
```sh
helm install argocd argocd/argo-cd -n argocd
```

### Check pods
```sh
kubectl get pods -n argocd -w
```

### Retrieve the initial admin password
```sh
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### Expose the ArgoCD UI using LB
```sh
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'
```

### Restrict who can reach ArgoCD (Optional)
```sh
kubectl patch svc argocd-server -n argocd -p "{\"spec\": {\"loadBalancerSourceRanges\": [\"$MY_PUBLIC_IP/32\"]}}"
```

### Register the ArgoCD Application pointing at kubernetes/
```sh
kubectl apply -f ./argocd/argocd-app.yaml -n argocd
```

## Database

### Create Private Subnet 1 in AZ A
```sh
export PRIVATE_SUBNET_A_ID=$(aws ec2 create-subnet \
                                --vpc-id $VPC_ID \
                                --cidr-block 10.0.2.0/24 \
                                --availability-zone ${AWS_REGION}a \
                                --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=private-subnet-a}]' \
                                --region $AWS_REGION \
                                --query 'Subnet.SubnetId' \
                                --output text)
echo "PRIVATE_SUBNET_A_ID=$PRIVATE_SUBNET_A_ID"
```

### Create Private Subnet 2 in AZ B
```sh
export PRIVATE_SUBNET_B_ID=$(aws ec2 create-subnet \
                                --vpc-id $VPC_ID \
                                --cidr-block 10.0.3.0/24 \
                                --availability-zone ${AWS_REGION}b \
                                --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=private-subnet-b}]' \
                                --region $AWS_REGION \
                                --query 'Subnet.SubnetId' \
                                --output text)
echo "PRIVATE_SUBNET_B_ID=$PRIVATE_SUBNET_B_ID"
```

### Create DB Subnet group
```sh
aws rds create-db-subnet-group \
    --db-subnet-group-name blog-db-subnet-group \
    --db-subnet-group-description "This is DB subnet group of blog application" \
    --subnet-ids $PRIVATE_SUBNET_A_ID $PRIVATE_SUBNET_B_ID \
    --region $AWS_REGION
```

### Create a Security group for RDS
```sh
export RDS_SG_ID=$(aws ec2 create-security-group \
                        --group-name blog-db-sg \
                        --description "This is security group for MySQL DB" \
                        --vpc-id $VPC_ID \
                        --region $AWS_REGION \
                        --query 'GroupId' \
                        --output text)
echo "RDS_SG_ID=$RDS_SG_ID"
```

### Create a Customer Managed KMS key
```sh
export KMS_KEY_ID=$(aws kms create-key \
                        --description "This is encryption key for blog app database." \
                        --region $AWS_REGION \
                        --query 'KeyMetadata.KeyId' \
                        --output text)
echo "KMS_KEY_ID=$KMS_KEY_ID"
```

### Create the RDS MySQL Instance
```sh
export DB_MASTER_PASSWORD='admin_1234'
aws rds create-db-instance \
    --db-instance-identifier blog-app-db \
    --db-instance-class db.t3.micro \
    --engine mysql \
    --master-username admin \
    --master-user-password "$DB_MASTER_PASSWORD" \
    --allocated-storage 20 \
    --db-name blogdb \
    --db-subnet-group-name blog-db-subnet-group \
    --vpc-security-group-ids $RDS_SG_ID \
    --storage-encrypted \
    --kms-key-id $KMS_KEY_ID \
    --no-publicly-accessible \
    --region $AWS_REGION
```
```sh
aws rds wait db-instance-available \
    --db-instance-identifier blog-app-db \
    --region $AWS_REGION
```

### Get the connection endpoint
```sh
export RDS_ENDPOINT=$(aws rds describe-db-instances \
                            --db-instance-identifier blog-app-db \
                            --region $AWS_REGION \
                            --query 'DBInstances[0].Endpoint.Address' \
                            --output text)
echo "RDS_ENDPOINT=$RDS_ENDPOINT"
```

## Connect EKS to RDS

### Find the Node SG that eksctl created
```sh
export EKS_NODE_SG_ID=$(aws eks describe-cluster \
                            --name development-cluster \
                            --region $AWS_REGION \
                            --query 'cluster.resourcesVpcConfig.clusterSecurityGroupId' \
                            --output text)
echo "EKS_NODE_SG_ID=$EKS_NODE_SG_ID"
```

### Allow EKS to access RDS
```sh
aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 3306 \
    --source-group $EKS_NODE_SG_ID \
    --region $AWS_REGION
```

## Deletion

This section assumes the same terminal session as creation, so every
exported variable above is still set. If it's a new session, re-export
AWS_REGION and the resource IDs first.

### Stop ArgoCD from re-creating things while you delete them
```sh
kubectl delete application blog-app -n argocd
```

### Delete the app namespace (also removes its Load Balancer)
```sh
kubectl delete namespace blog-app
```

### Delete the ArgoCD namespace (also removes its Load Balancer)
```sh
kubectl delete namespace argocd
```

### Confirm both Load Balancers are actually gone before proceeding
```sh
aws elb describe-load-balancers \
    --region $AWS_REGION \
    --query 'LoadBalancerDescriptions[].LoadBalancerName'
```
```text
If this still lists anything, wait a minute and run it again before continuing.
An empty list means it's safe to delete the cluster next.
```

### Delete the EKS cluster
```sh
eksctl delete cluster \
    --name development-cluster \
    --region $AWS_REGION
```
```text
This takes several minutes and blocks the terminal until finished — that's expected.
```

### Optional: take a manual RDS snapshot first, to practice the skill
```sh
aws rds create-db-snapshot \
    --db-instance-identifier blog-app-db \
    --db-snapshot-identifier blog-app-db-final-snapshot \
    --region $AWS_REGION
```
```sh
aws rds wait db-snapshot-available \
    --db-snapshot-identifier blog-app-db-final-snapshot \
    --region $AWS_REGION
```

### Delete the RDS instance
```sh
aws rds delete-db-instance \
    --db-instance-identifier blog-app-db \
    --skip-final-snapshot \
    --region $AWS_REGION
```
```sh
aws rds wait db-instance-deleted --db-instance-identifier blog-app-db --region $AWS_REGION
```

### Delete the DB subnet group
```sh
aws rds delete-db-subnet-group \
    --db-subnet-group-name blog-db-subnet-group \
    --region $AWS_REGION
```

### Delete the RDS security group
```sh
aws ec2 delete-security-group --group-id $RDS_SG_ID --region $AWS_REGION
```

### Schedule deletion of the KMS key
```sh
aws kms schedule-key-deletion \
    --key-id $KMS_KEY_ID \
    --pending-window-in-days 7 \
    --region $AWS_REGION
```
```text
KMS keys can't be deleted instantly — AWS enforces a minimum 7-day waiting
window. It stops being usable immediately, but fully disappears after that
window. Nothing more to do here.
```

### Delete the private subnets
```sh
aws ec2 delete-subnet --subnet-id $PRIVATE_SUBNET_A_ID --region $AWS_REGION
```
```sh
aws ec2 delete-subnet --subnet-id $PRIVATE_SUBNET_B_ID --region $AWS_REGION
```

### Terminate the Jenkins EC2 instance
```sh
aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $AWS_REGION
```
```sh
aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID --region $AWS_REGION
```

### Delete the Jenkins security group
```sh
aws ec2 delete-security-group --group-id $SG_ID --region $AWS_REGION
```

### Delete the key pair
```sh
aws ec2 delete-key-pair --key-name my-ec2-keypair --region $AWS_REGION
```
```sh
rm my-ec2-keypair.pem
```

### Clean up the IAM role and instance profile
```sh
aws iam detach-role-policy \
    --role-name jenkins-iam-role \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
```
```sh
aws iam remove-role-from-instance-profile \
    --instance-profile-name jenkins-instance-profile \
    --role-name jenkins-iam-role
```
```sh
aws iam delete-instance-profile --instance-profile-name jenkins-instance-profile
```
```sh
aws iam delete-role --role-name jenkins-iam-role
```

### Delete the ECR repository
```sh
aws ecr delete-repository \
    --repository-name $ECR_REPO_NAME \
    --force \
    --region $AWS_REGION
```

### Delete the public subnets
```sh
aws ec2 delete-subnet --subnet-id $SUBNET_A_ID --region $AWS_REGION
```
```sh
aws ec2 delete-subnet --subnet-id $SUBNET_B_ID --region $AWS_REGION
```

### Delete the route table
```sh
aws ec2 delete-route-table --route-table-id $RT_ID --region $AWS_REGION
```

### Detach the IGW from the VPC
```sh
aws ec2 detach-internet-gateway \
    --internet-gateway-id $IGW_ID \
    --vpc-id $VPC_ID \
    --region $AWS_REGION
```

### Delete the IGW
```sh
aws ec2 delete-internet-gateway --internet-gateway-id $IGW_ID --region $AWS_REGION
```

### Delete the VPC
```sh
aws ec2 delete-vpc --vpc-id $VPC_ID --region $AWS_REGION
```