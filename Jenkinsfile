pipeline {
    agent any
    parameters{
        string(name: 'REGISTRY', defaultValue: 'hub.oepkgs.net/neocopilot', description: 'Docker镜像仓库地址')
        string(name: 'IMAGE', defaultValue: 'euler-copilot-rag', description: 'Docker镜像名')
        string(name: 'DOCKERFILE_PATH', defaultValue: 'Dockerfile', description: 'Dockerfile位置')
        booleanParam(name: 'IS_PYC', defaultValue: true, description: 'py转换为pyc')
        booleanParam(name: 'IS_DEPLOY', defaultValue: false, description: '联动更新K3s deployment')
        booleanParam(name: 'IS_BRANCH', defaultValue: false, description: '分支主镜像持久保存')
    }
    stages {
        stage('Prepare SCM') {
            steps {
                checkout scm
                script {
                    BRANCH = scm.branches[0].name.split("/")[1]
                    BUILD = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()

                    sh "sed -i 's|app.py|app.pyc|g' run.sh"
                }
            }
        }

        stage('Convert pyc') {
            when{
                expression {
                    return params.IS_PYC == true
                }
            }
            steps {
                sh 'python3 -m compileall -f -b .'
                sh 'find . -name *.py -exec rm -f {} +'
            }
        }

        stage('Image build and push') {
            steps {
                sh "sed -i 's|rag_base:latest|${params.REGISTRY}/rag-baseimg:${BRANCH}|g' Dockerfile"
                script {
                    docker.withRegistry("https://${params.REGISTRY}", "dockerAuth") {
                        image = docker.build("${params.REGISTRY}/${params.IMAGE}:${BUILD}", ". -f ${params.DOCKERFILE_PATH}")
                        image.push()
                        if (params.IS_PYC && params.IS_BRANCH) {
                            image.push("${BRANCH}")
                        }
                    }
                }
            }
        }
        
        stage('Image CleanUp') {
            steps {
                script {
                    sh "docker rmi ${params.REGISTRY}/${params.IMAGE}:${BUILD} || true"
                    sh "docker rmi ${params.REGISTRY}/${params.IMAGE}:${BRANCH} || true"

                    sh "docker image prune -f || true"
                    sh "docker builder prune -f || true"
                    sh "k3s crictl rmi --prune || true"
                }
            }
        }
        
        stage('Deploy') {
            when{
                expression {
                    return params.IS_DEPLOY == true
                }
            }
            steps {
                script {
                    sh "kubectl -n euler-copilot set image deployment/rag-deploy rag=${params.REGISTRY}/${params.IMAGE}:${BUILD}"
                }
            }
        }
    }

    post{
        always {
            cleanWs(cleanWhenNotBuilt: true, cleanWhenFailure: true)
        }
    }
}
