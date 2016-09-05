#!groovy

node {
    // -------------------------------------------------------------------------
    stage 'Checkout'
        checkout scm

    stage 'Unit Tests' 
        img = docker.image "fedora-python3"
        img.runWith("tox")
   
    stage 'Integration'

    stage 'Dist'

    stage 'Package'

    stage 'Publish'
}
