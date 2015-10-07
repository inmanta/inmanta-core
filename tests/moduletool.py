from impera import app
from impera import module
from _io import StringIO

import os
import logging
import unittest
from unittest import mock

from nose import tools

from nose.tools import raises
import tempfile
import shutil
import subprocess
from impera.module import ModuleTool
from impera.config import Config
import yaml

tempdir = tempfile.mkdtemp()
shutil.rmtree("/tmp/unittest")
os.mkdir("/tmp/unittest")
tempdir = "/tmp/unittest"


goodIds={}

def setUpModule():
    createRepos()

def createRepos():
    reporoot = os.path.join(tempdir,"repos")
    os.makedirs(reporoot)
    
    mod1 = makemodule(reporoot,"mod1",[])
    commitmodule(mod1,"first commit")
    goodIds["mod1"]=addFile(mod1, "signal","present","second commit")
    
    mod2 = makemodule(reporoot,"mod2",[])
    commitmodule(mod2,"first commit")
    startbranch(mod2,"rc1")
    goodIds["mod2"]=addFile(mod2, "signal","present","second commit")
    
    
    mod3 = makemodule(reporoot,"mod3",[])
    commitmodule(mod3,"first commit")
    goodIds["mod3"]= addFile(mod3, "signal","present","second commit")
    addTag(mod3,"0.1")
    addFile(mod3, "badsignal","present","third commit")
    
    mod4 = makemodule(reporoot,"mod4",[])
    commitmodule(mod4,"first commit")
    m4tag = addFile(mod4, "signal","present","second commit")
    goodIds["mod4"]=m4tag
    addFile(mod4, "badsignal","present","third commit")
    
    
    proj = makemodule(reporoot,"testproject", [("mod1",""),("mod2","rc1"),("mod3","0.1"),("mod4",m4tag)],True)
    commitmodule(proj,"first commit")
    
    
def makemodule(reporoot,name,deps,project=False):
    path = os.path.join(reporoot,name)
    os.makedirs(path)
    mainfile="module.yml"
    if project:
       mainfile = "project.yml"
    with open(os.path.join(path,mainfile), "w") as projectfile:
        projectfile.write("name: " + name)
        projectfile.write("\nlicense: Apache 2.0")
        projectfile.write("\nversion: 1.0")
        if project:
            projectfile.write("""
modulepath: libs
downloadpath: libs""")
        if len(deps)!=0:
            projectfile.write("\nrequires:")
            for req in deps:
                mypath = os.path.join(reporoot,req[0])
                projectfile.write("\n    {}: {}, {}".format(req[0],mypath,req[1]))
    
    model = os.path.join(path,"model")
    os.makedirs(model)
    
    with open(os.path.join(model,"_init.cf"), "w") as projectfile:
        pass
    
    subprocess.check_call(["git" ,"init"], cwd=path)
    
    
    return path
        

def addFile(modpath, file,content,msg):
    with open(os.path.join(modpath,file), "w") as projectfile:
        projectfile.write(content)
    return commitmodule(modpath,msg)

def commitmodule(modpath,mesg):
    subprocess.check_call(["git" ,"add","*"], cwd=modpath)
    subprocess.check_call(["git" ,"commit","-a","-m",mesg], cwd=modpath)
    rev = subprocess.check_output(["git" ,"rev-parse","HEAD"], cwd=modpath).decode("utf-8") .strip()
    return rev
    
def startbranch(modpath,branch):
    subprocess.check_call(["git" ,"checkout","-b",branch], cwd=modpath)
    
def addTag(modpath,tag):
    subprocess.check_call(["git" ,"tag",tag], cwd=modpath)
    
class testModuleTool(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)

        self.stream = None
        self.handler = None
        self.log = None


    def setUp(self):
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.log = logging.getLogger(module.__name__)

        for handler in self.log.handlers:
            self.log.removeHandler(handler)

        self.log.addHandler(self.handler)
        
        

    def test_complexCheckoutAndFreeze(self):
        coroot = os.path.join(tempdir,"testproject")
        subprocess.check_call(["git" ,"clone",os.path.join(tempdir,"repos","testproject")], cwd=tempdir)
        os.chdir(coroot)
        os.curdir=coroot
        Config.load_config()
        
        ModuleTool().execute("install",[])
        for i in ["mod1","mod2","mod3","mod4"]:
            dir = os.path.join(coroot,"libs",i)
            assert os.path.exists(os.path.join(dir,"signal")),"could not find file: "+(os.path.join(dir,"signal"))
            assert not os.path.exists(os.path.join(dir,"badsignal")),"did find file: "+(os.path.join(dir,"badsignal"))  
            
        ModuleTool().execute("freeze",[])
        assert os.path.exists(os.path.join(coroot,"module.version")),"could not find file: "+(os.path.join(coroot,"module.version"))  
        with open(os.path.join(coroot,"module.version"), "r") as fd:
            locked = yaml.load(fd)
        
        reporoot = os.path.join(tempdir,"repos")
        def checkmodule(name,branch):
            other = locked[name]
            assert other["hash"]==goodIds[name],"bad hash on module " + name
            assert other["version"]=="1.0","bad version on module " + name
            assert other["branch"]==branch,"bad branch on module " + name
            assert other["repo"]==os.path.join(reporoot,name),"bad repo on module " + name
        checkmodule("mod1",'master')
        checkmodule("mod2",'rc1')
        checkmodule("mod3",'HEAD')
        checkmodule("mod4",'HEAD')

    def tearDown(self):
        self.log.removeHandler(self.handler)
        self.handler.close()
