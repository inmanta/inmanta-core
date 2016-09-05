#!groovy

node {
    // -------------------------------------------------------------------------
    stage 'Checkout'
        checkout scm

    stage 'Unit Tests' 
        img = docker.image "python:3.5"
        img.inside("-v ${pwd()}:/app") {
            sh 'pip install tox'
            // Unit tests
            sh 'cd /app && tox'
        } 
   
    stage 'Integration'

    stage 'Dist'

    stage 'Package'

    stage 'Publish'
}
