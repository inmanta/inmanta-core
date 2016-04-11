'''
Created on Apr 8, 2016

@author: wouter
'''

from antlr4 import *

import antlr3
from imperaLexer import imperaLexer
from imperaParser import imperaParser
import inmantaLexer
import inmantaParser
from antlr4.FileStream import FileStream
from antlr4.CommonTokenStream import CommonTokenStream
import time
import imperaGrako
import json

file = "/home/wouter/projects/inmanta-infra/main.cf"


def parserV3():
    char_stream = antlr3.ANTLRFileStream(file)

    lexer = imperaLexer(char_stream)
    tokens = antlr3.CommonTokenStream(lexer)
    parser = imperaParser(tokens)
    return parser.main()


def parserV4():
    input = FileStream(file)
    lexer = inmantaLexer.inmantaLexer(input)
    lexer._interp.mode = PredictionMode.SLL

    stream = CommonTokenStream(lexer)
    parser = inmantaParser.inmantaParser(stream)
    return parser.main()


def grako():
    parser = imperaGrako.imperaParser()
    with open(file, 'r') as myfile:
        data = myfile.read()
    ast = parser.parse(data, rule_name='main')
#    print(ast)
#    print(json.dumps(ast, indent=2))  # ASTs are JSON-friendy


pre = time.time()
parserV3()
post = time.time()
print("old: ", post - pre)

pre = time.time()
parserV4()
post = time.time()
print("new: ", post - pre)


pre = time.time()
grako()
post = time.time()
print("grako: ", post - pre)
