pipeline {
    agent any

    environment {
        AWS_REGION     = 'ap-southeast-2'
        AWS_ACCOUNT_ID = sh(script: 'aws sts get-caller-identity --query Account --output text', returnStdout: true).trim()
        ECR_REGISTRY   = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        BACKEND_REPO   = 'jenkins-argocd-eks-demo/backend'
        FRONTEND_REPO  = 'jenkins-argocd-eks-demo/frontend'
        IMAGE_TAG      = "${env.BUILD_NUMBER}"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Skip if last commit was from Jenkins') {
            steps {
                script {
                    def lastCommitMsg = sh(script: 'git log -1 --pretty=%B', returnStdout: true).trim()
                    if (lastCommitMsg.contains('[skip ci]')) {
                        currentBuild.result = 'ABORTED'
                        error('Skipping build — this commit was Jenkins updating the manifest, not a real code change.')
                    }
                }
            }
        }

        stage('Build Backend Image') {
            steps {
                sh "docker build -t ${ECR_REGISTRY}/${BACKEND_REPO}:${IMAGE_TAG} application/backend"
            }
        }

        stage('Build Frontend Image') {
            steps {
                sh "docker build -t ${ECR_REGISTRY}/${FRONTEND_REPO}:${IMAGE_TAG} application/frontend"
            }
        }

        stage('Push Images to ECR') {
            steps {
                sh "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}"
                sh "docker push ${ECR_REGISTRY}/${BACKEND_REPO}:${IMAGE_TAG}"
                sh "docker push ${ECR_REGISTRY}/${FRONTEND_REPO}:${IMAGE_TAG}"
            }
        }

        stage('Update Kubernetes Manifests') {
            steps {
                sh """
                    sed -i "s|image: .*|image: ${ECR_REGISTRY}/${BACKEND_REPO}:${IMAGE_TAG}|" kubernetes/backend-deployment.yaml
                    sed -i "s|image: .*|image: ${ECR_REGISTRY}/${FRONTEND_REPO}:${IMAGE_TAG}|" kubernetes/frontend-deployment.yaml
                """
                withCredentials([usernamePassword(credentialsId: 'github-credentials', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_TOKEN')]) {
                    sh """
                        git config user.email "jenkins@ci.local"
                        git config user.name "Jenkins CI"
                        git add kubernetes/backend-deployment.yaml kubernetes/frontend-deployment.yaml
                        git commit -m "Update image tags to build ${IMAGE_TAG} [skip ci]"
                        git push https://\${GIT_USER}:\${GIT_TOKEN}@github.com/Nisarg48/cicd-pipeline-demo.git HEAD:main
                    """
                }
            }
        }
    }
}