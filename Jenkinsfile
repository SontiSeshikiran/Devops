pipeline {
    agent { label 'agent-1' }

    stages {

        stage('Test') {
            steps {
                sh 'echo "Running on agent 🚀"'
                sh 'hostname'
            }
        }

        stage('Terraform Init') {
            steps {
                dir('terraform') {
                    sh 'terraform init'
                }
            }
        }

        stage('Terraform Apply') {
            steps {
                dir('terraform') {
                    sh 'terraform apply -auto-approve'
                }
            }
        }
    }
}