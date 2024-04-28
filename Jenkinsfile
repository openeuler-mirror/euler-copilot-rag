node {
    properties([
        parameters([
            string(name: "REPO", defaultValue: "rag", description: "当前项目名")
            string(name: "ACTIVE_BRANCH", defaultValue: "master", description: "活跃开发分支名")
        ])
    ])

    echo "拉取代码仓库"
    checkout scm
    
    def BUILD = env.BRANCH_NAME
    if (env.CHANGE_ID) {
        BUILD = env.BRANCH_NAME + "-" + env.CHANGE_ID
    }
    
    echo "构建当前分支Docker Image镜像"
    withCredentials([string(credentialsId: "host", variable: "HOST")]) {
        docker.withRegistry("http://${HOST}:30000") {
            def image = docker.build("${HOST}:30000/euler-copilot-${params.REPO}:${BUILD}", "-f ./deploy/Dockerfile .")
            image.push()
        }

        def remote = [:]
        remote.name = "machine"
        remote.host = "${HOST}"
        withCredentials([string(credentialsId: "ssh-username", variable: "USERNAME")]) {
            remote.user = USERNAME
        }
        withCredentials([string(credentialsId: "ssh-password", variable: "PASSWD")]) {
            remote.password = PASSWD
        }

        remote.allowAnyHosts = true

        stage("CD") {
            sshCommand remote: remote, command: "sh -c \"docker rmi ${HOST}/euler-copilot-${params.REPO}:${BUILD} || true\";"
            sshCommand remote: remote, command: "sh -c \"docker rmi euler-copilot-${params.REPO}:${BUILD} || true\";"
            sshCommand remote: remote, command: "sh -c \"docker image prune -f || true\";";
            sshCommand remote: remote, command: "sh -c \"docker builder prune -f || true\";";
            
            if (BUILD != params.ACTIVE_BRANCH) {
                echo "不是活跃开发分支的Commit行为，不自动部署"
            }
            else {
                echo "正在重新部署"
                sshCommand remote: remote, command: "sh -c \"k3s kubectl -n euler-copilot scale deployment rag-deploy --replicas=0\";"
                sshCommand remote: remote, command: "sh -c \"k3s kubectl -n euler-copilot scale deployment rag-deploy --replicas=1\";"
            }
        }
    }
}
