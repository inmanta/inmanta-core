#!groovy

stage('Checkout'} {
    node {
        checkout scm
    }
}

stage('Unit Tests') {
    node {
        img = docker.image "fedora-python3"
        img.inside {
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
