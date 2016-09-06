#!groovy

node {
    stage('Checkout') {
        checkout scm

        echo "My branch is: ${env.BRANCH_NAME}"
    }

    stage('Unit Tests') {
        img = docker.image("fedora-python3:24")
        img.withRun {
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
