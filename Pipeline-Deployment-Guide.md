## VPC & Networking

### Create a VPC
```sh
aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --region ap-southeast-2 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=MyVpc}]'
```

### Create IGW
```sh
aws ec2 create-internet-gateway \
    --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=my-igw}]' \
    --region ap-southeast-2
```

### Attach IGW to VPC
```sh
aws ec2 attach-internet-gateway \
    --internet-gateway-id <IGW-ID> \
    --vpc-id <VPC-ID> \
    --region ap-southeast-2
```

### Create Public Subnet 1 in AZ A
```sh
aws ec2 create-subnet \
    --vpc-id <VPC-ID> \
    --cidr-block 10.0.0.0/24 \
    --availability-zone ap-southeast-2a \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=my-subnet-a}]' \
    --region ap-southeast-2
```

### Create Public Subnet 2 in AZ B
```sh
aws ec2 create-subnet \
    --vpc-id <VPC-ID> \
    --cidr-block 10.0.1.0/24 \
    --availability-zone ap-southeast-2b \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=my-subnet-b}]' \
    --region ap-southeast-2
```

### Create Route Table
```sh
aws ec2 create-route-table \
    --vpc-id <VPC-ID> \
    --region ap-southeast-2
```

### Add Route to IGW in Route Table
```sh
aws ec2 create-route \
    --route-table-id <RT-ID> \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id <IGW-ID> \
    --region ap-southeast-2
```

### Associate Route Table with Subnet A
```sh
aws ec2 associate-route-table \
    --route-table-id <RT-ID> \
    --subnet-id <SUBNET-A-ID> \
    --region ap-southeast-2
```

### Associate Route Table with Subnet B
```sh
aws ec2 associate-route-table \
    --route-table-id <RT-ID> \
    --subnet-id <SUBNET-B-ID> \
    --region ap-southeast-2
```

## EC2 (Jenkins Server)

### Create a Key pair
```sh
aws ec2 create-key-pair \
    --key-name my-ec2-keypair \
    --region ap-southeast-2 \
    --query 'KeyMaterial' \
    --output text > my-ec2-keypair.pem
```
```sh
chmod 400 my-ec2-keypair.pem
```

### Create a Security Group
```sh
aws ec2 create-security-group \
    --group-name my-ec2-security-group \
    --description "My ec2 security group for Jenkins instance." \
    --vpc-id <VPC-ID> \
    --region ap-southeast-2
```

### Get Your Public IP
```sh
curl https://checkip.amazonaws.com
```

### Add Inboud rule in SG
```sh
aws ec2 authorize-security-group-ingress \
    --group-id <SG-ID> \
    --protocol tcp --port 22 \
    --cidr <Public-IP>/32 \
    --region ap-southeast-2
```
```sh
aws ec2 authorize-security-group-ingress \
    --group-id <SG-ID> \
    --protocol tcp --port 8080 \
    --cidr <Public-IP>/32 \
    --region ap-southeast-2
```

### Get Amazon Linux 2023 Image AMI Id
```sh
aws ec2 describe-images \
    --owners amazon \
    --region ap-southeast-2 \
    --filters "Name=name,Values=al2023-ami-*-x86_64" \
    --query 'sort_by(Images,&CreationDate)[-1].ImageId' \
    --output text
```

### Launch the EC2 Instance
```sh
aws ec2 run-instances \
    --image-id <IMAGE-AMI-ID> \
    --count 1 \
    --instance-type t2.micro \
    --key-name my-ec2-keypair \
    --security-group-ids <SG-ID> \
    --subnet-id <SUBNET-A-ID> \
    --region ap-southeast-2 \
    --associate-public-ip-address
```

### Create IAM role
```sh
aws iam create-role \
    --role-name jenkins-iam-role \
    --assume-role-policy-document file://ec2-policy.json
```

### Crate Instance Profile
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
    --instance-id <EC2-Instance-ID> \
    --iam-instance-profile Name="jenkins-instance-profile" \
    --region ap-southeast-2
```

### Get Public IPv4 address of EC2
```sh
aws ec2 describe-instances \
    --instance-ids <Instance-ID> \
    --region ap-southeast-2 \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text
```

### Use Key pair SSH to Instance
```sh
ssh -i my-ec2-keypair.pem ec2-user@<EC2-Public-IP>
```

### Install Java, then Jenkins
```sh
sudo yum update -y
```
```sh
# Install OpenJDK 17
sudo yum install java-17-amazon-corretto -y
```
```sh
java -version
```
```sh
# Add Jenkins repository and import key
sudo yum install wget -y
sudo wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
sudo rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io.key
# Install Jenkins
sudo yum install jenkins -y
# Start and enable Jenkins service
sudo systemctl start jenkins
sudo systemctl enable jenkins
# Check Jenkins status
sudo systemctl status jenkins
```
```sh
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

### Access Jenkins UI
```text
http://<Public_IP>:8080
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
aws ecr create-repository \
    --repository-name jenkins-argocd-eks-demo/<App-Name> \
    --region ap-southeast-2
```

### Add ECR push permission to Jenkins IAM role
```sh
aws iam attach-role-policy \
    --role-name jenkins-iam-role \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
```

## Verify the CI part
```text
Now write the CI half of the Jenkinsfile: Checkout → Build → Test → Push to ECR. Push a commit, confirm the image actually lands in ECR. This is a complete, testable milestone on its own, before anything touches Kubernetes.
```

## EKS Setup

### Create Cluster on EKS
```sh
eksctl create cluster \
    --name development-cluster \
    --region ap-southeast-2 \
    --vpc-public-subnets <Subnet-A-ID>,<Subnet-B-ID> \
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
kubectl get namespaces
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

### Expose the Argocd UI using LB
```sh
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'
```

### Restrict who can reach ArgoCD (Optional)
```sh
kubectl patch svc argocd-server -n argocd -p '{"spec": {"loadBalancerSourceRanges": ["<YOUR-IP>/32"]}}'
```

### Register the ArgoCD Application pointing at kubernetes/
```sh
kubectl apply -f ./argocd/argocd-app.yaml -n argocd
```

### Create Deployment and Sevice file inside kubernetes/