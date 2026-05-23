pipeline {
    agent any

    environment {
        // Define repository and image details (adjust registry/credentials as needed)
        REGISTRY = 'docker.io'
        IMAGE_NAME = 'lexscan-ner-api'
        IMAGE_TAG = "${env.BUILD_NUMBER ?: 'latest'}"
        DOCKER_CREDENTIALS_ID = 'docker-hub-credentials'
    }

    stages {
        stage('Checkout') {
            steps {
                cleanWs()
                checkout scm
            }
        }

        stage('Prepare Environment') {
            steps {
                script {
                    echo "Preparing environment file (.env)..."
                    // On Unix-like agents, check if .env exists, if not copy from example
                    sh '''
                        if [ ! -f .env ]; then
                            cp .env.example .env
                            echo "Created default .env from .env.example"
                        else
                            echo ".env file already exists"
                        fi
                    '''
                }
            }
        }

        stage('Lint & Code Quality') {
            steps {
                script {
                    echo "Running Linting with flake8 inside Python container..."
                    // Runs flake8 inside a lightweight python:3.11-slim container to keep runner environment clean
                    sh 'docker run --rm -v "$(pwd):/app" -w /app python:3.11-slim sh -c "pip install flake8 && flake8 . --exclude=venv,.venv,logs,outputs,mlruns,models,data"'
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    echo "Building Docker image ${IMAGE_NAME}:${IMAGE_TAG}..."
                    sh "docker build -t ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} -t ${REGISTRY}/${IMAGE_NAME}:latest ."
                }
            }
        }

        stage('Run Tests') {
            steps {
                script {
                    echo "Running Unit Tests..."
                    sh "docker run --rm ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} pytest tests/unit --ignore=tests/unit/test_api.py -q"

                    echo "Running Integration Tests..."
                    sh "docker run --rm ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} pytest tests/integration -q"

                    echo "Running Performance Smoke Tests..."
                    sh "docker run --rm ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} pytest tests/performance/test_speed.py -q"
                }
            }
        }

        stage('Push Image') {
            when {
                // Change 'main' to your release branch name if different
                branch 'main'
            }
            steps {
                script {
                    echo "Logging into Docker Registry..."
                    withCredentials([usernamePassword(credentialsId: env.DOCKER_CREDENTIALS_ID, usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                        sh "echo \$DOCKER_PASS | docker login -u \$DOCKER_USER --password-stdin ${REGISTRY}"
                        echo "Pushing Docker image ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}..."
                        sh "docker push ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
                        sh "docker push ${REGISTRY}/${IMAGE_NAME}:latest"
                    }
                }
            }
        }

        stage('Deploy to Docker') {
            steps {
                script {
                    echo "Deploying update to production containers..."
                    // Execute Docker Compose up using the production compose file and the built image variables
                    sh "REGISTRY=${REGISTRY} IMAGE_NAME=${IMAGE_NAME} IMAGE_TAG=${IMAGE_TAG} docker compose -f docker-compose.prod.yml down || true"
                    sh "REGISTRY=${REGISTRY} IMAGE_NAME=${IMAGE_NAME} IMAGE_TAG=${IMAGE_TAG} docker compose -f docker-compose.prod.yml up -d"
                    echo "Application deployed and running in background!"
                }
            }
        }
    }

    post {
        always {
            script {
                echo "Cleaning up dangling/old build assets..."
                // Only prune dangling images to avoid deleting running production images
                sh "docker image prune -f || true"
            }
        }
        success {
            echo "CI/CD Pipeline Succeeded!"
        }
        failure {
            echo "CI/CD Pipeline Failed!"
        }
    }
}
