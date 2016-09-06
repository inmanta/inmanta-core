#!groovy

stage('Checkout') {
    node {
        checkout scm
    }
}

stage('Unit Tests') {
    node {
        img = docker.image "fedora:latest"
        img.inside {
            sh "sleep 120"
        }
    }
}

/*
stage 'Integration'

stage 'Dist'

stage 'Package'

stage 'Publish'
*/
