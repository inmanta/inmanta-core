#!groovy

node {
    stage('Checkout') {
        checkout scm

        echo "My branch is: ${env.BRANCH_NAME}"
    }

    stage('Unit Tests') {
        docker.image("inmantaci/fedora-tox").inside {
            sh "pyenv local 3.4.5 3.5.2; ASYNC_TEST_TIMEOUT=60 tox"
        }
    }
}

/*
stage 'Integration'

stage 'Dist'

stage 'Package'

stage 'Publish'
*/

