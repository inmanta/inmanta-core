#!groovy

node {
    stage('Checkout') {
        checkout scm

        echo "My branch is: ${env.BRANCH_NAME}"
    }

    stage('Unit Tests') {
        docker.image("fedora:24").inside {
            sh "/bin/sleep 120"
        }
    }
}

/*
stage 'Integration'

stage 'Dist'

stage 'Package'

stage 'Publish'
*/
