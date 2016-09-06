#!groovy

stage('Checkout') {
    node {
        checkout scm
    }
}

stage('Unit Tests') {
    node {
        docker.image("fedora:24").inside {
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
