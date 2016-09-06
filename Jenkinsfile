#!groovy

node {
    stage('Checkout') {
        checkout scm

        echo "My branch is: ${env.BRANCH_NAME}"
    }

    stage('Unit Tests') {
        docker.image("fedora:24").inside {
            sh "ls -l"
            sh "id"
            sh "sudo ls /root"
        }
    }
}

/*
stage 'Integration'

stage 'Dist'

stage 'Package'

stage 'Publish'
*/
