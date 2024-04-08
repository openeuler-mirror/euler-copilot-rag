node {
    properties([
        parameters([
            string(name: "REPO", defaultValue: "rag", description: "当前项目名")
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

        def PORT = sh(returnStdout: true, script: "echo \$((( RANDOM % 1000 ) + 8000))").trim()
        def IP_RANGE = sh(returnStdout: true, script: "echo 172.\$(((RANDOM % 256))).\$(((RANDOM % 256)))").trim()
        def BUILD_HASH = sh(returnStdout: true, script: "echo ${BUILD} | md5sum | cut -c 1-12").trim()
        echo "本次构建ID为：${BUILD}，构建哈希为${BUILD_HASH}，分配的IP段为：${IP_RANGE}.0/24，分配的Web访问端口号为：${PORT}"
        
        // 临时使用Docker方案，后续切换至K8s
        stage("Re-run docker-compose") {
            sshCommand remote: remote, command: "sh -c \"docker rmi euler-copilot-${params.REPO}:${BUILD} || true\";"
            
            echo "正在创建配置文件..."
            sshCommand remote: remote, command: "cd /home/compose; sed -e \'s/branchname/${BUILD}/g\' docker-compose.example.yml | sed -e \'s/8080:8080/${PORT}:8080/g\' | sed -e \'s/172.168.0/${IP_RANGE}/g\' | sed -e \'s/branchhash/${BUILD_HASH}/g\' > compose/docker-compose_${params.REPO}_${BUILD}.yml;"
            echo "构建结束，请使用命令：\"cd /home/compose/compose; docker-compose -f docker-compose_${params.REPO}_${BUILD}.yml up -d;\" 启动所有容器"
            echo "测试结束后，使用命令 \"cd /home/compose/compose; docker-compose -f docker-compose_${params.REPO}_${BUILD}.yml down --rmi all; rm -f docker-compose_${params.REPO}_${BUILD}.yml;\" 清理现场"
            
            sshCommand remote: remote, command: "docker image prune -f;"
        }
    }
}
