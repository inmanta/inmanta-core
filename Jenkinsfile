#!groovy

node {
    stage('Checkout') {
        checkout scm

        echo "My branch is: ${env.BRANCH_NAME}"
    }

    stage('Unit Tests') {
        docker.image("inmantaci/fedora-tox").inside {
            sh "tox"
        }
    }
}

/*
stage 'Integration'

stage 'Dist'

stage 'Package'

stage 'Publish'
*/

