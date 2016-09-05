#!groovy

node {
    // -------------------------------------------------------------------------
    stage 'Checkout'
        checkout scm

    stage 'Unit Tests' 
        img = docker.image "fedora-python3"
        img.inside("-u 1000:1000 -v ${pwd()}:/app") {
            // Unit tests
            sh 'cd /app && tox'
        } 
   
    stage 'Integration'

    stage 'Dist'

    stage 'Package'

    stage 'Publish'
}
