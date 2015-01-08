# @PydevCodeAnalysisIgnore
# $ANTLR 3.4.1-SNAPSHOT impera.g 2015-01-08 13:02:46

import sys
from antlr3 import *

from antlr3.tree import *




# for convenience in actions
HIDDEN = BaseRecognizer.HIDDEN

# token types
EOF=-1
T__49=49
T__50=50
T__51=51
T__52=52
T__53=53
T__54=54
T__55=55
T__56=56
T__57=57
T__58=58
T__59=59
T__60=60
T__61=61
T__62=62
T__63=63
T__64=64
T__65=65
T__66=66
T__67=67
T__68=68
T__69=69
T__70=70
T__71=71
T__72=72
T__73=73
T__74=74
T__75=75
T__76=76
T__77=77
T__78=78
T__79=79
T__80=80
T__81=81
T__82=82
T__83=83
T__84=84
T__85=85
T__86=86
ANON=4
ASSIGN=5
ATTR=6
CALL=7
CLASS_ID=8
CLASS_REF=9
COMMENT=10
CONSTRUCT=11
DEF_DEFAULT=12
DEF_ENTITY=13
DEF_IMPLEMENT=14
DEF_IMPLEMENTATION=15
DEF_RELATION=16
DEF_TYPE=17
ENUM=18
ESC_SEQ=19
EXPONENT=20
EXPRESSION=21
FALSE=22
FLOAT=23
FOR=24
HASH=25
HEX_DIGIT=26
ID=27
INCLUDE=28
INDEX=29
INT=30
LAMBDA=31
LIST=32
METHOD=33
ML_STRING=34
MULT=35
NONE=36
NS=37
OCTAL_ESC=38
OP=39
ORPHAN=40
REF=41
REGEX=42
STATEMENT=43
STRING=44
TRUE=45
UNICODE_ESC=46
VAR_REF=47
WS=48

# token names
tokenNamesMap = {
    0: "<invalid>", 1: "<EOR>", 2: "<DOWN>", 3: "<UP>",
    -1: "EOF", 49: "T__49", 50: "T__50", 51: "T__51", 52: "T__52", 53: "T__53", 
    54: "T__54", 55: "T__55", 56: "T__56", 57: "T__57", 58: "T__58", 59: "T__59", 
    60: "T__60", 61: "T__61", 62: "T__62", 63: "T__63", 64: "T__64", 65: "T__65", 
    66: "T__66", 67: "T__67", 68: "T__68", 69: "T__69", 70: "T__70", 71: "T__71", 
    72: "T__72", 73: "T__73", 74: "T__74", 75: "T__75", 76: "T__76", 77: "T__77", 
    78: "T__78", 79: "T__79", 80: "T__80", 81: "T__81", 82: "T__82", 83: "T__83", 
    84: "T__84", 85: "T__85", 86: "T__86", 4: "ANON", 5: "ASSIGN", 6: "ATTR", 
    7: "CALL", 8: "CLASS_ID", 9: "CLASS_REF", 10: "COMMENT", 11: "CONSTRUCT", 
    12: "DEF_DEFAULT", 13: "DEF_ENTITY", 14: "DEF_IMPLEMENT", 15: "DEF_IMPLEMENTATION", 
    16: "DEF_RELATION", 17: "DEF_TYPE", 18: "ENUM", 19: "ESC_SEQ", 20: "EXPONENT", 
    21: "EXPRESSION", 22: "FALSE", 23: "FLOAT", 24: "FOR", 25: "HASH", 26: "HEX_DIGIT", 
    27: "ID", 28: "INCLUDE", 29: "INDEX", 30: "INT", 31: "LAMBDA", 32: "LIST", 
    33: "METHOD", 34: "ML_STRING", 35: "MULT", 36: "NONE", 37: "NS", 38: "OCTAL_ESC", 
    39: "OP", 40: "ORPHAN", 41: "REF", 42: "REGEX", 43: "STATEMENT", 44: "STRING", 
    45: "TRUE", 46: "UNICODE_ESC", 47: "VAR_REF", 48: "WS"
}
Token.registerTokenNamesMap(tokenNamesMap)

# token names
tokenNames = [
    "<invalid>", "<EOR>", "<DOWN>", "<UP>",
    "ANON", "ASSIGN", "ATTR", "CALL", "CLASS_ID", "CLASS_REF", "COMMENT", 
    "CONSTRUCT", "DEF_DEFAULT", "DEF_ENTITY", "DEF_IMPLEMENT", "DEF_IMPLEMENTATION", 
    "DEF_RELATION", "DEF_TYPE", "ENUM", "ESC_SEQ", "EXPONENT", "EXPRESSION", 
    "FALSE", "FLOAT", "FOR", "HASH", "HEX_DIGIT", "ID", "INCLUDE", "INDEX", 
    "INT", "LAMBDA", "LIST", "METHOD", "ML_STRING", "MULT", "NONE", "NS", 
    "OCTAL_ESC", "OP", "ORPHAN", "REF", "REGEX", "STATEMENT", "STRING", 
    "TRUE", "UNICODE_ESC", "VAR_REF", "WS", "'!='", "'('", "')'", "','", 
    "'--'", "'->'", "'.'", "':'", "'::'", "'<'", "'<-'", "'<='", "'='", 
    "'=='", "'>'", "'>='", "'['", "']'", "'and'", "'as'", "'end'", "'entity'", 
    "'extends'", "'for'", "'implement'", "'implementation'", "'in'", "'include'", 
    "'index'", "'matching'", "'not'", "'or'", "'typedef'", "'using'", "'when'", 
    "'{'", "'|'", "'}'"
]



class imperaParser(Parser):
    grammarFileName = "impera.g"
    api_version = 1
    tokenNames = tokenNames

    def __init__(self, input, state=None, *args, **kwargs):
        if state is None:
            state = RecognizerSharedState()

        super().__init__(input, state, *args, **kwargs)

        self.dfa1 = self.DFA1(
            self, 1,
            eot = self.DFA1_eot,
            eof = self.DFA1_eof,
            min = self.DFA1_min,
            max = self.DFA1_max,
            accept = self.DFA1_accept,
            special = self.DFA1_special,
            transition = self.DFA1_transition
            )

        self.dfa4 = self.DFA4(
            self, 4,
            eot = self.DFA4_eot,
            eof = self.DFA4_eof,
            min = self.DFA4_min,
            max = self.DFA4_max,
            accept = self.DFA4_accept,
            special = self.DFA4_special,
            transition = self.DFA4_transition
            )

        self.dfa6 = self.DFA6(
            self, 6,
            eot = self.DFA6_eot,
            eof = self.DFA6_eof,
            min = self.DFA6_min,
            max = self.DFA6_max,
            accept = self.DFA6_accept,
            special = self.DFA6_special,
            transition = self.DFA6_transition
            )

        self.dfa5 = self.DFA5(
            self, 5,
            eot = self.DFA5_eot,
            eof = self.DFA5_eof,
            min = self.DFA5_min,
            max = self.DFA5_max,
            accept = self.DFA5_accept,
            special = self.DFA5_special,
            transition = self.DFA5_transition
            )

        self.dfa8 = self.DFA8(
            self, 8,
            eot = self.DFA8_eot,
            eof = self.DFA8_eof,
            min = self.DFA8_min,
            max = self.DFA8_max,
            accept = self.DFA8_accept,
            special = self.DFA8_special,
            transition = self.DFA8_transition
            )

        self.dfa20 = self.DFA20(
            self, 20,
            eot = self.DFA20_eot,
            eof = self.DFA20_eof,
            min = self.DFA20_min,
            max = self.DFA20_max,
            accept = self.DFA20_accept,
            special = self.DFA20_special,
            transition = self.DFA20_transition
            )

        self.dfa27 = self.DFA27(
            self, 27,
            eot = self.DFA27_eot,
            eof = self.DFA27_eof,
            min = self.DFA27_min,
            max = self.DFA27_max,
            accept = self.DFA27_accept,
            special = self.DFA27_special,
            transition = self.DFA27_transition
            )

        self.dfa38 = self.DFA38(
            self, 38,
            eot = self.DFA38_eot,
            eof = self.DFA38_eof,
            min = self.DFA38_min,
            max = self.DFA38_max,
            accept = self.DFA38_accept,
            special = self.DFA38_special,
            transition = self.DFA38_transition
            )

        self.dfa40 = self.DFA40(
            self, 40,
            eot = self.DFA40_eot,
            eof = self.DFA40_eof,
            min = self.DFA40_min,
            max = self.DFA40_max,
            accept = self.DFA40_accept,
            special = self.DFA40_special,
            transition = self.DFA40_transition
            )




        self.delegates = []

        self._adaptor = None
        self.adaptor = CommonTreeAdaptor()



    def getTreeAdaptor(self):
        return self._adaptor

    def setTreeAdaptor(self, adaptor):
        self._adaptor = adaptor

    adaptor = property(getTreeAdaptor, setTreeAdaptor)


    class main_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "main"
    # impera.g:47:1: main : ( def_statement | top_statement | ML_STRING )* -> ^( LIST ( def_statement )* ( top_statement )* ( ML_STRING )* ) ;
    def main(self, ):
        retval = self.main_return()
        retval.start = self.input.LT(1)


        root_0 = None

        ML_STRING3 = None
        def_statement1 = None
        top_statement2 = None

        ML_STRING3_tree = None
        stream_ML_STRING = RewriteRuleTokenStream(self._adaptor, "token ML_STRING")
        stream_def_statement = RewriteRuleSubtreeStream(self._adaptor, "rule def_statement")
        stream_top_statement = RewriteRuleSubtreeStream(self._adaptor, "rule top_statement")
        try:
            try:
                # impera.g:48:2: ( ( def_statement | top_statement | ML_STRING )* -> ^( LIST ( def_statement )* ( top_statement )* ( ML_STRING )* ) )
                # impera.g:48:4: ( def_statement | top_statement | ML_STRING )*
                pass 
                # impera.g:48:4: ( def_statement | top_statement | ML_STRING )*
                while True: #loop1
                    alt1 = 4
                    alt1 = self.dfa1.predict(self.input)
                    if alt1 == 1:
                        # impera.g:48:5: def_statement
                        pass 
                        self._state.following.append(self.FOLLOW_def_statement_in_main172)
                        def_statement1 = self.def_statement()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_def_statement.add(def_statement1.tree)



                    elif alt1 == 2:
                        # impera.g:48:21: top_statement
                        pass 
                        self._state.following.append(self.FOLLOW_top_statement_in_main176)
                        top_statement2 = self.top_statement()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_top_statement.add(top_statement2.tree)



                    elif alt1 == 3:
                        # impera.g:48:37: ML_STRING
                        pass 
                        ML_STRING3 = self.match(self.input, ML_STRING, self.FOLLOW_ML_STRING_in_main180) 
                        if self._state.backtracking == 0:
                            stream_ML_STRING.add(ML_STRING3)



                    else:
                        break #loop1


                # AST Rewrite
                # elements: top_statement, ML_STRING, def_statement
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 48:49: -> ^( LIST ( def_statement )* ( top_statement )* ( ML_STRING )* )
                    # impera.g:48:52: ^( LIST ( def_statement )* ( top_statement )* ( ML_STRING )* )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_1)

                    # impera.g:48:59: ( def_statement )*
                    while stream_def_statement.hasNext():
                        self._adaptor.addChild(root_1, stream_def_statement.nextTree())


                    stream_def_statement.reset();

                    # impera.g:48:74: ( top_statement )*
                    while stream_top_statement.hasNext():
                        self._adaptor.addChild(root_1, stream_top_statement.nextTree())


                    stream_top_statement.reset();

                    # impera.g:48:89: ( ML_STRING )*
                    while stream_ML_STRING.hasNext():
                        self._adaptor.addChild(root_1, 
                        stream_ML_STRING.nextNode()
                        )


                    stream_ML_STRING.reset();

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "main"


    class def_statement_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "def_statement"
    # impera.g:51:1: def_statement : ( typedef | entity_def | implementation_def | relation | index | implement_def );
    def def_statement(self, ):
        retval = self.def_statement_return()
        retval.start = self.input.LT(1)


        root_0 = None

        typedef4 = None
        entity_def5 = None
        implementation_def6 = None
        relation7 = None
        index8 = None
        implement_def9 = None


        try:
            try:
                # impera.g:52:2: ( typedef | entity_def | implementation_def | relation | index | implement_def )
                alt2 = 6
                LA2 = self.input.LA(1)
                if LA2 in {81}:
                    alt2 = 1
                elif LA2 in {70}:
                    alt2 = 2
                elif LA2 in {74}:
                    alt2 = 3
                elif LA2 in {CLASS_ID, ID}:
                    alt2 = 4
                elif LA2 in {77}:
                    alt2 = 5
                elif LA2 in {73}:
                    alt2 = 6
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 2, 0, self.input)

                    raise nvae


                if alt2 == 1:
                    # impera.g:52:4: typedef
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_typedef_in_def_statement208)
                    typedef4 = self.typedef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, typedef4.tree)



                elif alt2 == 2:
                    # impera.g:52:14: entity_def
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_entity_def_in_def_statement212)
                    entity_def5 = self.entity_def()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, entity_def5.tree)



                elif alt2 == 3:
                    # impera.g:52:27: implementation_def
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_implementation_def_in_def_statement216)
                    implementation_def6 = self.implementation_def()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, implementation_def6.tree)



                elif alt2 == 4:
                    # impera.g:52:48: relation
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_relation_in_def_statement220)
                    relation7 = self.relation()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, relation7.tree)



                elif alt2 == 5:
                    # impera.g:52:59: index
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_index_in_def_statement224)
                    index8 = self.index()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, index8.tree)



                elif alt2 == 6:
                    # impera.g:52:67: implement_def
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_implement_def_in_def_statement228)
                    implement_def9 = self.implement_def()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, implement_def9.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "def_statement"


    class index_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "index"
    # impera.g:55:1: index : 'index' class_ref '(' ID ( ',' ID )* ')' -> ^( INDEX class_ref ^( LIST ( ID )+ ) ) ;
    def index(self, ):
        retval = self.index_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal10 = None
        char_literal12 = None
        ID13 = None
        char_literal14 = None
        ID15 = None
        char_literal16 = None
        class_ref11 = None

        string_literal10_tree = None
        char_literal12_tree = None
        ID13_tree = None
        char_literal14_tree = None
        ID15_tree = None
        char_literal16_tree = None
        stream_77 = RewriteRuleTokenStream(self._adaptor, "token 77")
        stream_50 = RewriteRuleTokenStream(self._adaptor, "token 50")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_51 = RewriteRuleTokenStream(self._adaptor, "token 51")
        stream_52 = RewriteRuleTokenStream(self._adaptor, "token 52")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        try:
            try:
                # impera.g:56:2: ( 'index' class_ref '(' ID ( ',' ID )* ')' -> ^( INDEX class_ref ^( LIST ( ID )+ ) ) )
                # impera.g:56:4: 'index' class_ref '(' ID ( ',' ID )* ')'
                pass 
                string_literal10 = self.match(self.input, 77, self.FOLLOW_77_in_index240) 
                if self._state.backtracking == 0:
                    stream_77.add(string_literal10)


                self._state.following.append(self.FOLLOW_class_ref_in_index242)
                class_ref11 = self.class_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_class_ref.add(class_ref11.tree)


                char_literal12 = self.match(self.input, 50, self.FOLLOW_50_in_index244) 
                if self._state.backtracking == 0:
                    stream_50.add(char_literal12)


                ID13 = self.match(self.input, ID, self.FOLLOW_ID_in_index246) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID13)


                # impera.g:56:29: ( ',' ID )*
                while True: #loop3
                    alt3 = 2
                    LA3_0 = self.input.LA(1)

                    if (LA3_0 == 52) :
                        alt3 = 1


                    if alt3 == 1:
                        # impera.g:56:30: ',' ID
                        pass 
                        char_literal14 = self.match(self.input, 52, self.FOLLOW_52_in_index249) 
                        if self._state.backtracking == 0:
                            stream_52.add(char_literal14)


                        ID15 = self.match(self.input, ID, self.FOLLOW_ID_in_index251) 
                        if self._state.backtracking == 0:
                            stream_ID.add(ID15)



                    else:
                        break #loop3


                char_literal16 = self.match(self.input, 51, self.FOLLOW_51_in_index255) 
                if self._state.backtracking == 0:
                    stream_51.add(char_literal16)


                # AST Rewrite
                # elements: class_ref, ID
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 56:43: -> ^( INDEX class_ref ^( LIST ( ID )+ ) )
                    # impera.g:56:46: ^( INDEX class_ref ^( LIST ( ID )+ ) )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(INDEX, "INDEX")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_class_ref.nextTree())

                    # impera.g:56:64: ^( LIST ( ID )+ )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_2)

                    # impera.g:56:71: ( ID )+
                    if not (stream_ID.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_ID.hasNext():
                        self._adaptor.addChild(root_2, 
                        stream_ID.nextNode()
                        )


                    stream_ID.reset()

                    self._adaptor.addChild(root_1, root_2)

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "index"


    class rhs_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "rhs"
    # impera.g:59:1: rhs : ( ( class_ref '(' )=> anon_ctor | operand );
    def rhs(self, ):
        retval = self.rhs_return()
        retval.start = self.input.LT(1)


        root_0 = None

        anon_ctor17 = None
        operand18 = None


        try:
            try:
                # impera.g:60:2: ( ( class_ref '(' )=> anon_ctor | operand )
                alt4 = 2
                alt4 = self.dfa4.predict(self.input)
                if alt4 == 1:
                    # impera.g:60:4: ( class_ref '(' )=> anon_ctor
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_anon_ctor_in_rhs291)
                    anon_ctor17 = self.anon_ctor()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, anon_ctor17.tree)



                elif alt4 == 2:
                    # impera.g:61:4: operand
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_operand_in_rhs296)
                    operand18 = self.operand()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, operand18.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "rhs"


    class top_statement_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "top_statement"
    # impera.g:64:1: top_statement : ( 'include' ns_ref -> ^( INCLUDE ns_ref ) | ( 'for' )=> 'for' ID 'in' ( variable | class_ref ) implementation -> ^( FOR ID ( variable )? ( class_ref )? implementation ) | variable '=' rhs -> ^( ASSIGN variable rhs ) | ( class_ref '(' )=> anon_ctor -> ^( ORPHAN anon_ctor ) | function_call | method_call );
    def top_statement(self, ):
        retval = self.top_statement_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal19 = None
        string_literal21 = None
        ID22 = None
        string_literal23 = None
        char_literal28 = None
        ns_ref20 = None
        variable24 = None
        class_ref25 = None
        implementation26 = None
        variable27 = None
        rhs29 = None
        anon_ctor30 = None
        function_call31 = None
        method_call32 = None

        string_literal19_tree = None
        string_literal21_tree = None
        ID22_tree = None
        string_literal23_tree = None
        char_literal28_tree = None
        stream_72 = RewriteRuleTokenStream(self._adaptor, "token 72")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_61 = RewriteRuleTokenStream(self._adaptor, "token 61")
        stream_75 = RewriteRuleTokenStream(self._adaptor, "token 75")
        stream_76 = RewriteRuleTokenStream(self._adaptor, "token 76")
        stream_anon_ctor = RewriteRuleSubtreeStream(self._adaptor, "rule anon_ctor")
        stream_implementation = RewriteRuleSubtreeStream(self._adaptor, "rule implementation")
        stream_variable = RewriteRuleSubtreeStream(self._adaptor, "rule variable")
        stream_rhs = RewriteRuleSubtreeStream(self._adaptor, "rule rhs")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        stream_ns_ref = RewriteRuleSubtreeStream(self._adaptor, "rule ns_ref")
        try:
            try:
                # impera.g:66:2: ( 'include' ns_ref -> ^( INCLUDE ns_ref ) | ( 'for' )=> 'for' ID 'in' ( variable | class_ref ) implementation -> ^( FOR ID ( variable )? ( class_ref )? implementation ) | variable '=' rhs -> ^( ASSIGN variable rhs ) | ( class_ref '(' )=> anon_ctor -> ^( ORPHAN anon_ctor ) | function_call | method_call )
                alt6 = 6
                alt6 = self.dfa6.predict(self.input)
                if alt6 == 1:
                    # impera.g:66:4: 'include' ns_ref
                    pass 
                    string_literal19 = self.match(self.input, 76, self.FOLLOW_76_in_top_statement309) 
                    if self._state.backtracking == 0:
                        stream_76.add(string_literal19)


                    self._state.following.append(self.FOLLOW_ns_ref_in_top_statement311)
                    ns_ref20 = self.ns_ref()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_ns_ref.add(ns_ref20.tree)


                    # AST Rewrite
                    # elements: ns_ref
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 66:21: -> ^( INCLUDE ns_ref )
                        # impera.g:66:24: ^( INCLUDE ns_ref )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(INCLUDE, "INCLUDE")
                        , root_1)

                        self._adaptor.addChild(root_1, stream_ns_ref.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt6 == 2:
                    # impera.g:67:4: ( 'for' )=> 'for' ID 'in' ( variable | class_ref ) implementation
                    pass 
                    string_literal21 = self.match(self.input, 72, self.FOLLOW_72_in_top_statement331) 
                    if self._state.backtracking == 0:
                        stream_72.add(string_literal21)


                    ID22 = self.match(self.input, ID, self.FOLLOW_ID_in_top_statement333) 
                    if self._state.backtracking == 0:
                        stream_ID.add(ID22)


                    string_literal23 = self.match(self.input, 75, self.FOLLOW_75_in_top_statement335) 
                    if self._state.backtracking == 0:
                        stream_75.add(string_literal23)


                    # impera.g:67:29: ( variable | class_ref )
                    alt5 = 2
                    alt5 = self.dfa5.predict(self.input)
                    if alt5 == 1:
                        # impera.g:67:30: variable
                        pass 
                        self._state.following.append(self.FOLLOW_variable_in_top_statement338)
                        variable24 = self.variable()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_variable.add(variable24.tree)



                    elif alt5 == 2:
                        # impera.g:67:41: class_ref
                        pass 
                        self._state.following.append(self.FOLLOW_class_ref_in_top_statement342)
                        class_ref25 = self.class_ref()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_class_ref.add(class_ref25.tree)





                    self._state.following.append(self.FOLLOW_implementation_in_top_statement346)
                    implementation26 = self.implementation()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_implementation.add(implementation26.tree)


                    # AST Rewrite
                    # elements: variable, implementation, ID, class_ref
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 67:68: -> ^( FOR ID ( variable )? ( class_ref )? implementation )
                        # impera.g:67:71: ^( FOR ID ( variable )? ( class_ref )? implementation )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(FOR, "FOR")
                        , root_1)

                        self._adaptor.addChild(root_1, 
                        stream_ID.nextNode()
                        )

                        # impera.g:67:80: ( variable )?
                        if stream_variable.hasNext():
                            self._adaptor.addChild(root_1, stream_variable.nextTree())


                        stream_variable.reset();

                        # impera.g:67:90: ( class_ref )?
                        if stream_class_ref.hasNext():
                            self._adaptor.addChild(root_1, stream_class_ref.nextTree())


                        stream_class_ref.reset();

                        self._adaptor.addChild(root_1, stream_implementation.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt6 == 3:
                    # impera.g:68:4: variable '=' rhs
                    pass 
                    self._state.following.append(self.FOLLOW_variable_in_top_statement367)
                    variable27 = self.variable()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_variable.add(variable27.tree)


                    char_literal28 = self.match(self.input, 61, self.FOLLOW_61_in_top_statement369) 
                    if self._state.backtracking == 0:
                        stream_61.add(char_literal28)


                    self._state.following.append(self.FOLLOW_rhs_in_top_statement371)
                    rhs29 = self.rhs()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_rhs.add(rhs29.tree)


                    # AST Rewrite
                    # elements: rhs, variable
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 68:21: -> ^( ASSIGN variable rhs )
                        # impera.g:68:24: ^( ASSIGN variable rhs )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(ASSIGN, "ASSIGN")
                        , root_1)

                        self._adaptor.addChild(root_1, stream_variable.nextTree())

                        self._adaptor.addChild(root_1, stream_rhs.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt6 == 4:
                    # impera.g:69:4: ( class_ref '(' )=> anon_ctor
                    pass 
                    self._state.following.append(self.FOLLOW_anon_ctor_in_top_statement394)
                    anon_ctor30 = self.anon_ctor()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_anon_ctor.add(anon_ctor30.tree)


                    # AST Rewrite
                    # elements: anon_ctor
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 69:33: -> ^( ORPHAN anon_ctor )
                        # impera.g:69:36: ^( ORPHAN anon_ctor )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(ORPHAN, "ORPHAN")
                        , root_1)

                        self._adaptor.addChild(root_1, stream_anon_ctor.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt6 == 5:
                    # impera.g:70:4: function_call
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_function_call_in_top_statement407)
                    function_call31 = self.function_call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, function_call31.tree)



                elif alt6 == 6:
                    # impera.g:71:4: method_call
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_method_call_in_top_statement412)
                    method_call32 = self.method_call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, method_call32.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "top_statement"


    class anon_ctor_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "anon_ctor"
    # impera.g:74:1: anon_ctor : constructor ( implementation )? -> ^( ANON constructor ( implementation )? ) ;
    def anon_ctor(self, ):
        retval = self.anon_ctor_return()
        retval.start = self.input.LT(1)


        root_0 = None

        constructor33 = None
        implementation34 = None

        stream_implementation = RewriteRuleSubtreeStream(self._adaptor, "rule implementation")
        stream_constructor = RewriteRuleSubtreeStream(self._adaptor, "rule constructor")
        try:
            try:
                # impera.g:75:2: ( constructor ( implementation )? -> ^( ANON constructor ( implementation )? ) )
                # impera.g:75:4: constructor ( implementation )?
                pass 
                self._state.following.append(self.FOLLOW_constructor_in_anon_ctor424)
                constructor33 = self.constructor()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_constructor.add(constructor33.tree)


                # impera.g:75:16: ( implementation )?
                alt7 = 2
                LA7_0 = self.input.LA(1)

                if (LA7_0 == 56) :
                    alt7 = 1
                if alt7 == 1:
                    # impera.g:75:16: implementation
                    pass 
                    self._state.following.append(self.FOLLOW_implementation_in_anon_ctor426)
                    implementation34 = self.implementation()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_implementation.add(implementation34.tree)





                # AST Rewrite
                # elements: implementation, constructor
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 75:32: -> ^( ANON constructor ( implementation )? )
                    # impera.g:75:35: ^( ANON constructor ( implementation )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(ANON, "ANON")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_constructor.nextTree())

                    # impera.g:75:54: ( implementation )?
                    if stream_implementation.hasNext():
                        self._adaptor.addChild(root_1, stream_implementation.nextTree())


                    stream_implementation.reset();

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "anon_ctor"


    class lambda_ctor_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "lambda_ctor"
    # impera.g:78:1: lambda_ctor : constructor -> ^( ORPHAN constructor ) ;
    def lambda_ctor(self, ):
        retval = self.lambda_ctor_return()
        retval.start = self.input.LT(1)


        root_0 = None

        constructor35 = None

        stream_constructor = RewriteRuleSubtreeStream(self._adaptor, "rule constructor")
        try:
            try:
                # impera.g:79:2: ( constructor -> ^( ORPHAN constructor ) )
                # impera.g:79:4: constructor
                pass 
                self._state.following.append(self.FOLLOW_constructor_in_lambda_ctor450)
                constructor35 = self.constructor()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_constructor.add(constructor35.tree)


                # AST Rewrite
                # elements: constructor
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 79:16: -> ^( ORPHAN constructor )
                    # impera.g:79:19: ^( ORPHAN constructor )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(ORPHAN, "ORPHAN")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_constructor.nextTree())

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "lambda_ctor"


    class lambda_func_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "lambda_func"
    # impera.g:82:1: lambda_func : ID '|' ( function_call | method_call | lambda_ctor ) -> ^( LAMBDA ID ( function_call )? ( method_call )? ( lambda_ctor )? ) ;
    def lambda_func(self, ):
        retval = self.lambda_func_return()
        retval.start = self.input.LT(1)


        root_0 = None

        ID36 = None
        char_literal37 = None
        function_call38 = None
        method_call39 = None
        lambda_ctor40 = None

        ID36_tree = None
        char_literal37_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_85 = RewriteRuleTokenStream(self._adaptor, "token 85")
        stream_function_call = RewriteRuleSubtreeStream(self._adaptor, "rule function_call")
        stream_lambda_ctor = RewriteRuleSubtreeStream(self._adaptor, "rule lambda_ctor")
        stream_method_call = RewriteRuleSubtreeStream(self._adaptor, "rule method_call")
        try:
            try:
                # impera.g:83:2: ( ID '|' ( function_call | method_call | lambda_ctor ) -> ^( LAMBDA ID ( function_call )? ( method_call )? ( lambda_ctor )? ) )
                # impera.g:83:4: ID '|' ( function_call | method_call | lambda_ctor )
                pass 
                ID36 = self.match(self.input, ID, self.FOLLOW_ID_in_lambda_func470) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID36)


                char_literal37 = self.match(self.input, 85, self.FOLLOW_85_in_lambda_func472) 
                if self._state.backtracking == 0:
                    stream_85.add(char_literal37)


                # impera.g:83:11: ( function_call | method_call | lambda_ctor )
                alt8 = 3
                alt8 = self.dfa8.predict(self.input)
                if alt8 == 1:
                    # impera.g:83:12: function_call
                    pass 
                    self._state.following.append(self.FOLLOW_function_call_in_lambda_func475)
                    function_call38 = self.function_call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_function_call.add(function_call38.tree)



                elif alt8 == 2:
                    # impera.g:83:28: method_call
                    pass 
                    self._state.following.append(self.FOLLOW_method_call_in_lambda_func479)
                    method_call39 = self.method_call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_method_call.add(method_call39.tree)



                elif alt8 == 3:
                    # impera.g:83:42: lambda_ctor
                    pass 
                    self._state.following.append(self.FOLLOW_lambda_ctor_in_lambda_func483)
                    lambda_ctor40 = self.lambda_ctor()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_lambda_ctor.add(lambda_ctor40.tree)





                # AST Rewrite
                # elements: lambda_ctor, method_call, ID, function_call
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 83:55: -> ^( LAMBDA ID ( function_call )? ( method_call )? ( lambda_ctor )? )
                    # impera.g:83:58: ^( LAMBDA ID ( function_call )? ( method_call )? ( lambda_ctor )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LAMBDA, "LAMBDA")
                    , root_1)

                    self._adaptor.addChild(root_1, 
                    stream_ID.nextNode()
                    )

                    # impera.g:83:70: ( function_call )?
                    if stream_function_call.hasNext():
                        self._adaptor.addChild(root_1, stream_function_call.nextTree())


                    stream_function_call.reset();

                    # impera.g:83:85: ( method_call )?
                    if stream_method_call.hasNext():
                        self._adaptor.addChild(root_1, stream_method_call.nextTree())


                    stream_method_call.reset();

                    # impera.g:83:98: ( lambda_ctor )?
                    if stream_lambda_ctor.hasNext():
                        self._adaptor.addChild(root_1, stream_lambda_ctor.nextTree())


                    stream_lambda_ctor.reset();

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "lambda_func"


    class implementation_def_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "implementation_def"
    # impera.g:86:1: implementation_def : 'implementation' ID ( 'for' class_ref )? implementation -> ^( DEF_IMPLEMENTATION ID implementation ( class_ref )? ) ;
    def implementation_def(self, ):
        retval = self.implementation_def_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal41 = None
        ID42 = None
        string_literal43 = None
        class_ref44 = None
        implementation45 = None

        string_literal41_tree = None
        ID42_tree = None
        string_literal43_tree = None
        stream_72 = RewriteRuleTokenStream(self._adaptor, "token 72")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_74 = RewriteRuleTokenStream(self._adaptor, "token 74")
        stream_implementation = RewriteRuleSubtreeStream(self._adaptor, "rule implementation")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        try:
            try:
                # impera.g:87:2: ( 'implementation' ID ( 'for' class_ref )? implementation -> ^( DEF_IMPLEMENTATION ID implementation ( class_ref )? ) )
                # impera.g:87:4: 'implementation' ID ( 'for' class_ref )? implementation
                pass 
                string_literal41 = self.match(self.input, 74, self.FOLLOW_74_in_implementation_def512) 
                if self._state.backtracking == 0:
                    stream_74.add(string_literal41)


                ID42 = self.match(self.input, ID, self.FOLLOW_ID_in_implementation_def514) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID42)


                # impera.g:87:24: ( 'for' class_ref )?
                alt9 = 2
                LA9_0 = self.input.LA(1)

                if (LA9_0 == 72) :
                    alt9 = 1
                if alt9 == 1:
                    # impera.g:87:25: 'for' class_ref
                    pass 
                    string_literal43 = self.match(self.input, 72, self.FOLLOW_72_in_implementation_def517) 
                    if self._state.backtracking == 0:
                        stream_72.add(string_literal43)


                    self._state.following.append(self.FOLLOW_class_ref_in_implementation_def519)
                    class_ref44 = self.class_ref()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_class_ref.add(class_ref44.tree)





                self._state.following.append(self.FOLLOW_implementation_in_implementation_def523)
                implementation45 = self.implementation()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_implementation.add(implementation45.tree)


                # AST Rewrite
                # elements: ID, implementation, class_ref
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 87:58: -> ^( DEF_IMPLEMENTATION ID implementation ( class_ref )? )
                    # impera.g:87:61: ^( DEF_IMPLEMENTATION ID implementation ( class_ref )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(DEF_IMPLEMENTATION, "DEF_IMPLEMENTATION")
                    , root_1)

                    self._adaptor.addChild(root_1, 
                    stream_ID.nextNode()
                    )

                    self._adaptor.addChild(root_1, stream_implementation.nextTree())

                    # impera.g:87:100: ( class_ref )?
                    if stream_class_ref.hasNext():
                        self._adaptor.addChild(root_1, stream_class_ref.nextTree())


                    stream_class_ref.reset();

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "implementation_def"


    class implement_def_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "implement_def"
    # impera.g:91:1: implement_def : 'implement' class_ref 'using' ns_ref ( ',' ns_ref )* ( 'when' expression )? -> ^( DEF_IMPLEMENT class_ref ^( LIST ( ns_ref )+ ) ( expression )? ) ;
    def implement_def(self, ):
        retval = self.implement_def_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal46 = None
        string_literal48 = None
        char_literal50 = None
        string_literal52 = None
        class_ref47 = None
        ns_ref49 = None
        ns_ref51 = None
        expression53 = None

        string_literal46_tree = None
        string_literal48_tree = None
        char_literal50_tree = None
        string_literal52_tree = None
        stream_82 = RewriteRuleTokenStream(self._adaptor, "token 82")
        stream_83 = RewriteRuleTokenStream(self._adaptor, "token 83")
        stream_73 = RewriteRuleTokenStream(self._adaptor, "token 73")
        stream_52 = RewriteRuleTokenStream(self._adaptor, "token 52")
        stream_expression = RewriteRuleSubtreeStream(self._adaptor, "rule expression")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        stream_ns_ref = RewriteRuleSubtreeStream(self._adaptor, "rule ns_ref")
        try:
            try:
                # impera.g:92:2: ( 'implement' class_ref 'using' ns_ref ( ',' ns_ref )* ( 'when' expression )? -> ^( DEF_IMPLEMENT class_ref ^( LIST ( ns_ref )+ ) ( expression )? ) )
                # impera.g:92:4: 'implement' class_ref 'using' ns_ref ( ',' ns_ref )* ( 'when' expression )?
                pass 
                string_literal46 = self.match(self.input, 73, self.FOLLOW_73_in_implement_def548) 
                if self._state.backtracking == 0:
                    stream_73.add(string_literal46)


                self._state.following.append(self.FOLLOW_class_ref_in_implement_def550)
                class_ref47 = self.class_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_class_ref.add(class_ref47.tree)


                string_literal48 = self.match(self.input, 82, self.FOLLOW_82_in_implement_def552) 
                if self._state.backtracking == 0:
                    stream_82.add(string_literal48)


                self._state.following.append(self.FOLLOW_ns_ref_in_implement_def554)
                ns_ref49 = self.ns_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_ns_ref.add(ns_ref49.tree)


                # impera.g:92:41: ( ',' ns_ref )*
                while True: #loop10
                    alt10 = 2
                    LA10_0 = self.input.LA(1)

                    if (LA10_0 == 52) :
                        alt10 = 1


                    if alt10 == 1:
                        # impera.g:92:42: ',' ns_ref
                        pass 
                        char_literal50 = self.match(self.input, 52, self.FOLLOW_52_in_implement_def557) 
                        if self._state.backtracking == 0:
                            stream_52.add(char_literal50)


                        self._state.following.append(self.FOLLOW_ns_ref_in_implement_def559)
                        ns_ref51 = self.ns_ref()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_ns_ref.add(ns_ref51.tree)



                    else:
                        break #loop10


                # impera.g:92:55: ( 'when' expression )?
                alt11 = 2
                LA11_0 = self.input.LA(1)

                if (LA11_0 == 83) :
                    alt11 = 1
                if alt11 == 1:
                    # impera.g:92:56: 'when' expression
                    pass 
                    string_literal52 = self.match(self.input, 83, self.FOLLOW_83_in_implement_def564) 
                    if self._state.backtracking == 0:
                        stream_83.add(string_literal52)


                    self._state.following.append(self.FOLLOW_expression_in_implement_def566)
                    expression53 = self.expression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_expression.add(expression53.tree)





                # AST Rewrite
                # elements: expression, class_ref, ns_ref
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 92:76: -> ^( DEF_IMPLEMENT class_ref ^( LIST ( ns_ref )+ ) ( expression )? )
                    # impera.g:92:79: ^( DEF_IMPLEMENT class_ref ^( LIST ( ns_ref )+ ) ( expression )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(DEF_IMPLEMENT, "DEF_IMPLEMENT")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_class_ref.nextTree())

                    # impera.g:92:105: ^( LIST ( ns_ref )+ )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_2)

                    # impera.g:92:112: ( ns_ref )+
                    if not (stream_ns_ref.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_ns_ref.hasNext():
                        self._adaptor.addChild(root_2, stream_ns_ref.nextTree())


                    stream_ns_ref.reset()

                    self._adaptor.addChild(root_1, root_2)

                    # impera.g:92:121: ( expression )?
                    if stream_expression.hasNext():
                        self._adaptor.addChild(root_1, stream_expression.nextTree())


                    stream_expression.reset();

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "implement_def"


    class implementation_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "implementation"
    # impera.g:95:1: implementation : ':' ( ML_STRING )? ( statement )* 'end' -> ^( LIST ( statement )* ) ;
    def implementation(self, ):
        retval = self.implementation_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal54 = None
        ML_STRING55 = None
        string_literal57 = None
        statement56 = None

        char_literal54_tree = None
        ML_STRING55_tree = None
        string_literal57_tree = None
        stream_56 = RewriteRuleTokenStream(self._adaptor, "token 56")
        stream_69 = RewriteRuleTokenStream(self._adaptor, "token 69")
        stream_ML_STRING = RewriteRuleTokenStream(self._adaptor, "token ML_STRING")
        stream_statement = RewriteRuleSubtreeStream(self._adaptor, "rule statement")
        try:
            try:
                # impera.g:96:2: ( ':' ( ML_STRING )? ( statement )* 'end' -> ^( LIST ( statement )* ) )
                # impera.g:96:4: ':' ( ML_STRING )? ( statement )* 'end'
                pass 
                char_literal54 = self.match(self.input, 56, self.FOLLOW_56_in_implementation598) 
                if self._state.backtracking == 0:
                    stream_56.add(char_literal54)


                # impera.g:96:8: ( ML_STRING )?
                alt12 = 2
                LA12_0 = self.input.LA(1)

                if (LA12_0 == ML_STRING) :
                    alt12 = 1
                if alt12 == 1:
                    # impera.g:96:8: ML_STRING
                    pass 
                    ML_STRING55 = self.match(self.input, ML_STRING, self.FOLLOW_ML_STRING_in_implementation600) 
                    if self._state.backtracking == 0:
                        stream_ML_STRING.add(ML_STRING55)





                # impera.g:96:19: ( statement )*
                while True: #loop13
                    alt13 = 2
                    LA13_0 = self.input.LA(1)

                    if (LA13_0 == CLASS_ID or LA13_0 == ID or LA13_0 == 72 or LA13_0 == 76) :
                        alt13 = 1


                    if alt13 == 1:
                        # impera.g:96:19: statement
                        pass 
                        self._state.following.append(self.FOLLOW_statement_in_implementation603)
                        statement56 = self.statement()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_statement.add(statement56.tree)



                    else:
                        break #loop13


                string_literal57 = self.match(self.input, 69, self.FOLLOW_69_in_implementation606) 
                if self._state.backtracking == 0:
                    stream_69.add(string_literal57)


                # AST Rewrite
                # elements: statement
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 96:36: -> ^( LIST ( statement )* )
                    # impera.g:96:39: ^( LIST ( statement )* )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_1)

                    # impera.g:96:46: ( statement )*
                    while stream_statement.hasNext():
                        self._adaptor.addChild(root_1, stream_statement.nextTree())


                    stream_statement.reset();

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "implementation"


    class statement_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "statement"
    # impera.g:99:1: statement : top_statement -> ^( STATEMENT top_statement ) ;
    def statement(self, ):
        retval = self.statement_return()
        retval.start = self.input.LT(1)


        root_0 = None

        top_statement58 = None

        stream_top_statement = RewriteRuleSubtreeStream(self._adaptor, "rule top_statement")
        try:
            try:
                # impera.g:100:2: ( top_statement -> ^( STATEMENT top_statement ) )
                # impera.g:100:4: top_statement
                pass 
                self._state.following.append(self.FOLLOW_top_statement_in_statement626)
                top_statement58 = self.top_statement()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_top_statement.add(top_statement58.tree)


                # AST Rewrite
                # elements: top_statement
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 100:18: -> ^( STATEMENT top_statement )
                    # impera.g:100:21: ^( STATEMENT top_statement )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(STATEMENT, "STATEMENT")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_top_statement.nextTree())

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "statement"


    class parameter_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "parameter"
    # impera.g:103:1: parameter : ID '=' operand -> ^( ASSIGN ID operand ) ;
    def parameter(self, ):
        retval = self.parameter_return()
        retval.start = self.input.LT(1)


        root_0 = None

        ID59 = None
        char_literal60 = None
        operand61 = None

        ID59_tree = None
        char_literal60_tree = None
        stream_61 = RewriteRuleTokenStream(self._adaptor, "token 61")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_operand = RewriteRuleSubtreeStream(self._adaptor, "rule operand")
        try:
            try:
                # impera.g:104:2: ( ID '=' operand -> ^( ASSIGN ID operand ) )
                # impera.g:104:4: ID '=' operand
                pass 
                ID59 = self.match(self.input, ID, self.FOLLOW_ID_in_parameter646) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID59)


                char_literal60 = self.match(self.input, 61, self.FOLLOW_61_in_parameter648) 
                if self._state.backtracking == 0:
                    stream_61.add(char_literal60)


                self._state.following.append(self.FOLLOW_operand_in_parameter650)
                operand61 = self.operand()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_operand.add(operand61.tree)


                # AST Rewrite
                # elements: operand, ID
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 104:19: -> ^( ASSIGN ID operand )
                    # impera.g:104:22: ^( ASSIGN ID operand )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(ASSIGN, "ASSIGN")
                    , root_1)

                    self._adaptor.addChild(root_1, 
                    stream_ID.nextNode()
                    )

                    self._adaptor.addChild(root_1, stream_operand.nextTree())

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "parameter"


    class constructor_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "constructor"
    # impera.g:107:1: constructor : class_ref '(' ( param_list )? ')' -> ^( CONSTRUCT class_ref ( param_list )? ) ;
    def constructor(self, ):
        retval = self.constructor_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal63 = None
        char_literal65 = None
        class_ref62 = None
        param_list64 = None

        char_literal63_tree = None
        char_literal65_tree = None
        stream_50 = RewriteRuleTokenStream(self._adaptor, "token 50")
        stream_51 = RewriteRuleTokenStream(self._adaptor, "token 51")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        stream_param_list = RewriteRuleSubtreeStream(self._adaptor, "rule param_list")
        try:
            try:
                # impera.g:108:2: ( class_ref '(' ( param_list )? ')' -> ^( CONSTRUCT class_ref ( param_list )? ) )
                # impera.g:108:4: class_ref '(' ( param_list )? ')'
                pass 
                self._state.following.append(self.FOLLOW_class_ref_in_constructor671)
                class_ref62 = self.class_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_class_ref.add(class_ref62.tree)


                char_literal63 = self.match(self.input, 50, self.FOLLOW_50_in_constructor673) 
                if self._state.backtracking == 0:
                    stream_50.add(char_literal63)


                # impera.g:108:18: ( param_list )?
                alt14 = 2
                LA14_0 = self.input.LA(1)

                if (LA14_0 == ID) :
                    alt14 = 1
                if alt14 == 1:
                    # impera.g:108:18: param_list
                    pass 
                    self._state.following.append(self.FOLLOW_param_list_in_constructor675)
                    param_list64 = self.param_list()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_param_list.add(param_list64.tree)





                char_literal65 = self.match(self.input, 51, self.FOLLOW_51_in_constructor678) 
                if self._state.backtracking == 0:
                    stream_51.add(char_literal65)


                # AST Rewrite
                # elements: param_list, class_ref
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 108:34: -> ^( CONSTRUCT class_ref ( param_list )? )
                    # impera.g:108:37: ^( CONSTRUCT class_ref ( param_list )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(CONSTRUCT, "CONSTRUCT")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_class_ref.nextTree())

                    # impera.g:108:59: ( param_list )?
                    if stream_param_list.hasNext():
                        self._adaptor.addChild(root_1, stream_param_list.nextTree())


                    stream_param_list.reset();

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "constructor"


    class param_list_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "param_list"
    # impera.g:111:1: param_list : parameter ( ',' parameter )* ( ',' )? -> ^( LIST ( parameter )+ ) ;
    def param_list(self, ):
        retval = self.param_list_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal67 = None
        char_literal69 = None
        parameter66 = None
        parameter68 = None

        char_literal67_tree = None
        char_literal69_tree = None
        stream_52 = RewriteRuleTokenStream(self._adaptor, "token 52")
        stream_parameter = RewriteRuleSubtreeStream(self._adaptor, "rule parameter")
        try:
            try:
                # impera.g:112:2: ( parameter ( ',' parameter )* ( ',' )? -> ^( LIST ( parameter )+ ) )
                # impera.g:112:4: parameter ( ',' parameter )* ( ',' )?
                pass 
                self._state.following.append(self.FOLLOW_parameter_in_param_list703)
                parameter66 = self.parameter()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_parameter.add(parameter66.tree)


                # impera.g:112:14: ( ',' parameter )*
                while True: #loop15
                    alt15 = 2
                    LA15_0 = self.input.LA(1)

                    if (LA15_0 == 52) :
                        LA15_1 = self.input.LA(2)

                        if (LA15_1 == ID) :
                            alt15 = 1




                    if alt15 == 1:
                        # impera.g:112:15: ',' parameter
                        pass 
                        char_literal67 = self.match(self.input, 52, self.FOLLOW_52_in_param_list706) 
                        if self._state.backtracking == 0:
                            stream_52.add(char_literal67)


                        self._state.following.append(self.FOLLOW_parameter_in_param_list708)
                        parameter68 = self.parameter()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_parameter.add(parameter68.tree)



                    else:
                        break #loop15


                # impera.g:112:31: ( ',' )?
                alt16 = 2
                LA16_0 = self.input.LA(1)

                if (LA16_0 == 52) :
                    alt16 = 1
                if alt16 == 1:
                    # impera.g:112:31: ','
                    pass 
                    char_literal69 = self.match(self.input, 52, self.FOLLOW_52_in_param_list712) 
                    if self._state.backtracking == 0:
                        stream_52.add(char_literal69)





                # AST Rewrite
                # elements: parameter
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 112:36: -> ^( LIST ( parameter )+ )
                    # impera.g:112:39: ^( LIST ( parameter )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_1)

                    # impera.g:112:46: ( parameter )+
                    if not (stream_parameter.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_parameter.hasNext():
                        self._adaptor.addChild(root_1, stream_parameter.nextTree())


                    stream_parameter.reset()

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "param_list"


    class typedef_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "typedef"
    # impera.g:115:1: typedef : ( 'typedef' ID 'as' ns_ref 'matching' ( REGEX | expression ) -> ^( DEF_TYPE ID ns_ref ( expression )? ( REGEX )? ) | 'typedef' CLASS_ID 'as' constructor -> ^( DEF_DEFAULT CLASS_ID constructor ) );
    def typedef(self, ):
        retval = self.typedef_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal70 = None
        ID71 = None
        string_literal72 = None
        string_literal74 = None
        REGEX75 = None
        string_literal77 = None
        CLASS_ID78 = None
        string_literal79 = None
        ns_ref73 = None
        expression76 = None
        constructor80 = None

        string_literal70_tree = None
        ID71_tree = None
        string_literal72_tree = None
        string_literal74_tree = None
        REGEX75_tree = None
        string_literal77_tree = None
        CLASS_ID78_tree = None
        string_literal79_tree = None
        stream_78 = RewriteRuleTokenStream(self._adaptor, "token 78")
        stream_68 = RewriteRuleTokenStream(self._adaptor, "token 68")
        stream_REGEX = RewriteRuleTokenStream(self._adaptor, "token REGEX")
        stream_81 = RewriteRuleTokenStream(self._adaptor, "token 81")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_CLASS_ID = RewriteRuleTokenStream(self._adaptor, "token CLASS_ID")
        stream_expression = RewriteRuleSubtreeStream(self._adaptor, "rule expression")
        stream_constructor = RewriteRuleSubtreeStream(self._adaptor, "rule constructor")
        stream_ns_ref = RewriteRuleSubtreeStream(self._adaptor, "rule ns_ref")
        try:
            try:
                # impera.g:116:2: ( 'typedef' ID 'as' ns_ref 'matching' ( REGEX | expression ) -> ^( DEF_TYPE ID ns_ref ( expression )? ( REGEX )? ) | 'typedef' CLASS_ID 'as' constructor -> ^( DEF_DEFAULT CLASS_ID constructor ) )
                alt18 = 2
                LA18_0 = self.input.LA(1)

                if (LA18_0 == 81) :
                    LA18_1 = self.input.LA(2)

                    if (LA18_1 == ID) :
                        alt18 = 1
                    elif (LA18_1 == CLASS_ID) :
                        alt18 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 18, 1, self.input)

                        raise nvae


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 18, 0, self.input)

                    raise nvae


                if alt18 == 1:
                    # impera.g:116:4: 'typedef' ID 'as' ns_ref 'matching' ( REGEX | expression )
                    pass 
                    string_literal70 = self.match(self.input, 81, self.FOLLOW_81_in_typedef733) 
                    if self._state.backtracking == 0:
                        stream_81.add(string_literal70)


                    ID71 = self.match(self.input, ID, self.FOLLOW_ID_in_typedef735) 
                    if self._state.backtracking == 0:
                        stream_ID.add(ID71)


                    string_literal72 = self.match(self.input, 68, self.FOLLOW_68_in_typedef737) 
                    if self._state.backtracking == 0:
                        stream_68.add(string_literal72)


                    self._state.following.append(self.FOLLOW_ns_ref_in_typedef739)
                    ns_ref73 = self.ns_ref()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_ns_ref.add(ns_ref73.tree)


                    string_literal74 = self.match(self.input, 78, self.FOLLOW_78_in_typedef741) 
                    if self._state.backtracking == 0:
                        stream_78.add(string_literal74)


                    # impera.g:116:40: ( REGEX | expression )
                    alt17 = 2
                    LA17_0 = self.input.LA(1)

                    if (LA17_0 == REGEX) :
                        LA17_1 = self.input.LA(2)

                        if (LA17_1 == EOF or LA17_1 == CLASS_ID or LA17_1 == ID or LA17_1 == ML_STRING or LA17_1 == 70 or (72 <= LA17_1 <= 74) or (76 <= LA17_1 <= 77) or LA17_1 == 81) :
                            alt17 = 1
                        elif (LA17_1 == 49 or LA17_1 == 58 or LA17_1 == 60 or (62 <= LA17_1 <= 64) or LA17_1 == 75) :
                            alt17 = 2
                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed


                            nvae = NoViableAltException("", 17, 1, self.input)

                            raise nvae


                    elif (LA17_0 == CLASS_ID or (FALSE <= LA17_0 <= FLOAT) or LA17_0 == ID or LA17_0 == INT or LA17_0 == ML_STRING or (STRING <= LA17_0 <= TRUE) or LA17_0 == 50) :
                        alt17 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 17, 0, self.input)

                        raise nvae


                    if alt17 == 1:
                        # impera.g:116:41: REGEX
                        pass 
                        REGEX75 = self.match(self.input, REGEX, self.FOLLOW_REGEX_in_typedef744) 
                        if self._state.backtracking == 0:
                            stream_REGEX.add(REGEX75)



                    elif alt17 == 2:
                        # impera.g:116:49: expression
                        pass 
                        self._state.following.append(self.FOLLOW_expression_in_typedef748)
                        expression76 = self.expression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_expression.add(expression76.tree)





                    # AST Rewrite
                    # elements: REGEX, ID, ns_ref, expression
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 116:61: -> ^( DEF_TYPE ID ns_ref ( expression )? ( REGEX )? )
                        # impera.g:116:64: ^( DEF_TYPE ID ns_ref ( expression )? ( REGEX )? )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(DEF_TYPE, "DEF_TYPE")
                        , root_1)

                        self._adaptor.addChild(root_1, 
                        stream_ID.nextNode()
                        )

                        self._adaptor.addChild(root_1, stream_ns_ref.nextTree())

                        # impera.g:116:85: ( expression )?
                        if stream_expression.hasNext():
                            self._adaptor.addChild(root_1, stream_expression.nextTree())


                        stream_expression.reset();

                        # impera.g:116:97: ( REGEX )?
                        if stream_REGEX.hasNext():
                            self._adaptor.addChild(root_1, 
                            stream_REGEX.nextNode()
                            )


                        stream_REGEX.reset();

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt18 == 2:
                    # impera.g:117:4: 'typedef' CLASS_ID 'as' constructor
                    pass 
                    string_literal77 = self.match(self.input, 81, self.FOLLOW_81_in_typedef770) 
                    if self._state.backtracking == 0:
                        stream_81.add(string_literal77)


                    CLASS_ID78 = self.match(self.input, CLASS_ID, self.FOLLOW_CLASS_ID_in_typedef772) 
                    if self._state.backtracking == 0:
                        stream_CLASS_ID.add(CLASS_ID78)


                    string_literal79 = self.match(self.input, 68, self.FOLLOW_68_in_typedef774) 
                    if self._state.backtracking == 0:
                        stream_68.add(string_literal79)


                    self._state.following.append(self.FOLLOW_constructor_in_typedef776)
                    constructor80 = self.constructor()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_constructor.add(constructor80.tree)


                    # AST Rewrite
                    # elements: constructor, CLASS_ID
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 117:40: -> ^( DEF_DEFAULT CLASS_ID constructor )
                        # impera.g:117:43: ^( DEF_DEFAULT CLASS_ID constructor )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(DEF_DEFAULT, "DEF_DEFAULT")
                        , root_1)

                        self._adaptor.addChild(root_1, 
                        stream_CLASS_ID.nextNode()
                        )

                        self._adaptor.addChild(root_1, stream_constructor.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "typedef"


    class multiplicity_body_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "multiplicity_body"
    # impera.g:120:1: multiplicity_body : ( ( INT )=> INT -> ^( MULT INT ) | ( INT ':' )=> INT ':' -> ^( MULT INT NONE ) | ( INT ':' INT )=> INT ':' INT -> ^( MULT INT INT ) | ( ':' INT )=> ':' INT -> ^( MULT NONE INT ) );
    def multiplicity_body(self, ):
        retval = self.multiplicity_body_return()
        retval.start = self.input.LT(1)


        root_0 = None

        INT81 = None
        INT82 = None
        char_literal83 = None
        INT84 = None
        char_literal85 = None
        INT86 = None
        char_literal87 = None
        INT88 = None

        INT81_tree = None
        INT82_tree = None
        char_literal83_tree = None
        INT84_tree = None
        char_literal85_tree = None
        INT86_tree = None
        char_literal87_tree = None
        INT88_tree = None
        stream_56 = RewriteRuleTokenStream(self._adaptor, "token 56")
        stream_INT = RewriteRuleTokenStream(self._adaptor, "token INT")

        try:
            try:
                # impera.g:121:2: ( ( INT )=> INT -> ^( MULT INT ) | ( INT ':' )=> INT ':' -> ^( MULT INT NONE ) | ( INT ':' INT )=> INT ':' INT -> ^( MULT INT INT ) | ( ':' INT )=> ':' INT -> ^( MULT NONE INT ) )
                alt19 = 4
                LA19_0 = self.input.LA(1)

                if (LA19_0 == INT) :
                    LA19_1 = self.input.LA(2)

                    if (LA19_1 == 56) :
                        LA19_3 = self.input.LA(3)

                        if (LA19_3 == INT) and (self.synpred6_impera()):
                            alt19 = 3
                        elif (LA19_3 == 66) and (self.synpred5_impera()):
                            alt19 = 2
                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed


                            nvae = NoViableAltException("", 19, 3, self.input)

                            raise nvae


                    elif (LA19_1 == 66) and (self.synpred4_impera()):
                        alt19 = 1
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 19, 1, self.input)

                        raise nvae


                elif (LA19_0 == 56) and (self.synpred7_impera()):
                    alt19 = 4
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 19, 0, self.input)

                    raise nvae


                if alt19 == 1:
                    # impera.g:121:4: ( INT )=> INT
                    pass 
                    INT81 = self.match(self.input, INT, self.FOLLOW_INT_in_multiplicity_body804) 
                    if self._state.backtracking == 0:
                        stream_INT.add(INT81)


                    # AST Rewrite
                    # elements: INT
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 121:17: -> ^( MULT INT )
                        # impera.g:121:20: ^( MULT INT )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(MULT, "MULT")
                        , root_1)

                        self._adaptor.addChild(root_1, 
                        stream_INT.nextNode()
                        )

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt19 == 2:
                    # impera.g:122:4: ( INT ':' )=> INT ':'
                    pass 
                    INT82 = self.match(self.input, INT, self.FOLLOW_INT_in_multiplicity_body825) 
                    if self._state.backtracking == 0:
                        stream_INT.add(INT82)


                    char_literal83 = self.match(self.input, 56, self.FOLLOW_56_in_multiplicity_body827) 
                    if self._state.backtracking == 0:
                        stream_56.add(char_literal83)


                    # AST Rewrite
                    # elements: INT
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 122:25: -> ^( MULT INT NONE )
                        # impera.g:122:28: ^( MULT INT NONE )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(MULT, "MULT")
                        , root_1)

                        self._adaptor.addChild(root_1, 
                        stream_INT.nextNode()
                        )

                        self._adaptor.addChild(root_1, 
                        self._adaptor.createFromType(NONE, "NONE")
                        )

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt19 == 3:
                    # impera.g:123:4: ( INT ':' INT )=> INT ':' INT
                    pass 
                    INT84 = self.match(self.input, INT, self.FOLLOW_INT_in_multiplicity_body852) 
                    if self._state.backtracking == 0:
                        stream_INT.add(INT84)


                    char_literal85 = self.match(self.input, 56, self.FOLLOW_56_in_multiplicity_body854) 
                    if self._state.backtracking == 0:
                        stream_56.add(char_literal85)


                    INT86 = self.match(self.input, INT, self.FOLLOW_INT_in_multiplicity_body856) 
                    if self._state.backtracking == 0:
                        stream_INT.add(INT86)


                    # AST Rewrite
                    # elements: INT, INT
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 123:33: -> ^( MULT INT INT )
                        # impera.g:123:36: ^( MULT INT INT )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(MULT, "MULT")
                        , root_1)

                        self._adaptor.addChild(root_1, 
                        stream_INT.nextNode()
                        )

                        self._adaptor.addChild(root_1, 
                        stream_INT.nextNode()
                        )

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt19 == 4:
                    # impera.g:124:4: ( ':' INT )=> ':' INT
                    pass 
                    char_literal87 = self.match(self.input, 56, self.FOLLOW_56_in_multiplicity_body879) 
                    if self._state.backtracking == 0:
                        stream_56.add(char_literal87)


                    INT88 = self.match(self.input, INT, self.FOLLOW_INT_in_multiplicity_body881) 
                    if self._state.backtracking == 0:
                        stream_INT.add(INT88)


                    # AST Rewrite
                    # elements: INT
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 124:25: -> ^( MULT NONE INT )
                        # impera.g:124:28: ^( MULT NONE INT )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(MULT, "MULT")
                        , root_1)

                        self._adaptor.addChild(root_1, 
                        self._adaptor.createFromType(NONE, "NONE")
                        )

                        self._adaptor.addChild(root_1, 
                        stream_INT.nextNode()
                        )

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "multiplicity_body"


    class multiplicity_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "multiplicity"
    # impera.g:128:1: multiplicity : '[' multiplicity_body ']' -> multiplicity_body ;
    def multiplicity(self, ):
        retval = self.multiplicity_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal89 = None
        char_literal91 = None
        multiplicity_body90 = None

        char_literal89_tree = None
        char_literal91_tree = None
        stream_66 = RewriteRuleTokenStream(self._adaptor, "token 66")
        stream_65 = RewriteRuleTokenStream(self._adaptor, "token 65")
        stream_multiplicity_body = RewriteRuleSubtreeStream(self._adaptor, "rule multiplicity_body")
        try:
            try:
                # impera.g:129:2: ( '[' multiplicity_body ']' -> multiplicity_body )
                # impera.g:129:4: '[' multiplicity_body ']'
                pass 
                char_literal89 = self.match(self.input, 65, self.FOLLOW_65_in_multiplicity903) 
                if self._state.backtracking == 0:
                    stream_65.add(char_literal89)


                self._state.following.append(self.FOLLOW_multiplicity_body_in_multiplicity905)
                multiplicity_body90 = self.multiplicity_body()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_multiplicity_body.add(multiplicity_body90.tree)


                char_literal91 = self.match(self.input, 66, self.FOLLOW_66_in_multiplicity907) 
                if self._state.backtracking == 0:
                    stream_66.add(char_literal91)


                # AST Rewrite
                # elements: multiplicity_body
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 129:30: -> multiplicity_body
                    self._adaptor.addChild(root_0, stream_multiplicity_body.nextTree())




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "multiplicity"


    class relation_end_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "relation_end"
    # impera.g:132:1: relation_end : class_ref ID -> class_ref ID ;
    def relation_end(self, ):
        retval = self.relation_end_return()
        retval.start = self.input.LT(1)


        root_0 = None

        ID93 = None
        class_ref92 = None

        ID93_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        try:
            try:
                # impera.g:133:2: ( class_ref ID -> class_ref ID )
                # impera.g:133:4: class_ref ID
                pass 
                self._state.following.append(self.FOLLOW_class_ref_in_relation_end922)
                class_ref92 = self.class_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_class_ref.add(class_ref92.tree)


                ID93 = self.match(self.input, ID, self.FOLLOW_ID_in_relation_end924) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID93)


                # AST Rewrite
                # elements: ID, class_ref
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 133:17: -> class_ref ID
                    self._adaptor.addChild(root_0, stream_class_ref.nextTree())

                    self._adaptor.addChild(root_0, 
                    stream_ID.nextNode()
                    )




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "relation_end"


    class relation_link_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "relation_link"
    # impera.g:136:1: relation_link : ( '<-' | '->' | '--' );
    def relation_link(self, ):
        retval = self.relation_link_return()
        retval.start = self.input.LT(1)


        root_0 = None

        set94 = None

        set94_tree = None

        try:
            try:
                # impera.g:137:2: ( '<-' | '->' | '--' )
                # impera.g:
                pass 
                root_0 = self._adaptor.nil()


                set94 = self.input.LT(1)

                if (53 <= self.input.LA(1) <= 54) or self.input.LA(1) == 59:
                    self.input.consume()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set94))

                    self._state.errorRecovery = False


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    mse = MismatchedSetException(None, self.input)
                    raise mse





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "relation_link"


    class relation_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "relation"
    # impera.g:140:1: relation : (left_end= relation_end left_m= multiplicity ) relation_link (right_m= multiplicity right_end= relation_end ) -> ^( DEF_RELATION relation_link ^( LIST $left_end $left_m) ^( LIST $right_end $right_m) ) ;
    def relation(self, ):
        retval = self.relation_return()
        retval.start = self.input.LT(1)


        root_0 = None

        left_end = None
        left_m = None
        right_m = None
        right_end = None
        relation_link95 = None

        stream_multiplicity = RewriteRuleSubtreeStream(self._adaptor, "rule multiplicity")
        stream_relation_end = RewriteRuleSubtreeStream(self._adaptor, "rule relation_end")
        stream_relation_link = RewriteRuleSubtreeStream(self._adaptor, "rule relation_link")
        try:
            try:
                # impera.g:141:2: ( (left_end= relation_end left_m= multiplicity ) relation_link (right_m= multiplicity right_end= relation_end ) -> ^( DEF_RELATION relation_link ^( LIST $left_end $left_m) ^( LIST $right_end $right_m) ) )
                # impera.g:141:4: (left_end= relation_end left_m= multiplicity ) relation_link (right_m= multiplicity right_end= relation_end )
                pass 
                # impera.g:141:4: (left_end= relation_end left_m= multiplicity )
                # impera.g:141:5: left_end= relation_end left_m= multiplicity
                pass 
                self._state.following.append(self.FOLLOW_relation_end_in_relation965)
                left_end = self.relation_end()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_relation_end.add(left_end.tree)


                self._state.following.append(self.FOLLOW_multiplicity_in_relation969)
                left_m = self.multiplicity()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_multiplicity.add(left_m.tree)





                self._state.following.append(self.FOLLOW_relation_link_in_relation972)
                relation_link95 = self.relation_link()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_relation_link.add(relation_link95.tree)


                # impera.g:141:62: (right_m= multiplicity right_end= relation_end )
                # impera.g:141:63: right_m= multiplicity right_end= relation_end
                pass 
                self._state.following.append(self.FOLLOW_multiplicity_in_relation977)
                right_m = self.multiplicity()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_multiplicity.add(right_m.tree)


                self._state.following.append(self.FOLLOW_relation_end_in_relation981)
                right_end = self.relation_end()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_relation_end.add(right_end.tree)





                # AST Rewrite
                # elements: right_m, left_m, right_end, relation_link, left_end
                # token labels: 
                # rule labels: left_end, right_m, right_end, retval, left_m
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if left_end is not None:
                        stream_left_end = RewriteRuleSubtreeStream(self._adaptor, "rule left_end", left_end.tree)
                    else:
                        stream_left_end = RewriteRuleSubtreeStream(self._adaptor, "token left_end", None)

                    if right_m is not None:
                        stream_right_m = RewriteRuleSubtreeStream(self._adaptor, "rule right_m", right_m.tree)
                    else:
                        stream_right_m = RewriteRuleSubtreeStream(self._adaptor, "token right_m", None)

                    if right_end is not None:
                        stream_right_end = RewriteRuleSubtreeStream(self._adaptor, "rule right_end", right_end.tree)
                    else:
                        stream_right_end = RewriteRuleSubtreeStream(self._adaptor, "token right_end", None)

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)

                    if left_m is not None:
                        stream_left_m = RewriteRuleSubtreeStream(self._adaptor, "rule left_m", left_m.tree)
                    else:
                        stream_left_m = RewriteRuleSubtreeStream(self._adaptor, "token left_m", None)


                    root_0 = self._adaptor.nil()
                    # 141:108: -> ^( DEF_RELATION relation_link ^( LIST $left_end $left_m) ^( LIST $right_end $right_m) )
                    # impera.g:142:3: ^( DEF_RELATION relation_link ^( LIST $left_end $left_m) ^( LIST $right_end $right_m) )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(DEF_RELATION, "DEF_RELATION")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_relation_link.nextTree())

                    # impera.g:142:32: ^( LIST $left_end $left_m)
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_2)

                    self._adaptor.addChild(root_2, stream_left_end.nextTree())

                    self._adaptor.addChild(root_2, stream_left_m.nextTree())

                    self._adaptor.addChild(root_1, root_2)

                    # impera.g:142:58: ^( LIST $right_end $right_m)
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_2)

                    self._adaptor.addChild(root_2, stream_right_end.nextTree())

                    self._adaptor.addChild(root_2, stream_right_m.nextTree())

                    self._adaptor.addChild(root_1, root_2)

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "relation"


    class operand_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "operand"
    # impera.g:145:1: operand : ( constant | list_def | index_lookup | ( ns_ref '(' )=> function_call | class_ref | variable | method_call | ( '{' )=> '{' expression '}' -> ^( EXPRESSION expression ) );
    def operand(self, ):
        retval = self.operand_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal103 = None
        char_literal105 = None
        constant96 = None
        list_def97 = None
        index_lookup98 = None
        function_call99 = None
        class_ref100 = None
        variable101 = None
        method_call102 = None
        expression104 = None

        char_literal103_tree = None
        char_literal105_tree = None
        stream_84 = RewriteRuleTokenStream(self._adaptor, "token 84")
        stream_86 = RewriteRuleTokenStream(self._adaptor, "token 86")
        stream_expression = RewriteRuleSubtreeStream(self._adaptor, "rule expression")
        try:
            try:
                # impera.g:146:2: ( constant | list_def | index_lookup | ( ns_ref '(' )=> function_call | class_ref | variable | method_call | ( '{' )=> '{' expression '}' -> ^( EXPRESSION expression ) )
                alt20 = 8
                alt20 = self.dfa20.predict(self.input)
                if alt20 == 1:
                    # impera.g:146:4: constant
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_constant_in_operand1024)
                    constant96 = self.constant()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, constant96.tree)



                elif alt20 == 2:
                    # impera.g:147:4: list_def
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_list_def_in_operand1029)
                    list_def97 = self.list_def()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, list_def97.tree)



                elif alt20 == 3:
                    # impera.g:148:4: index_lookup
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_index_lookup_in_operand1034)
                    index_lookup98 = self.index_lookup()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, index_lookup98.tree)



                elif alt20 == 4:
                    # impera.g:149:4: ( ns_ref '(' )=> function_call
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_function_call_in_operand1047)
                    function_call99 = self.function_call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, function_call99.tree)



                elif alt20 == 5:
                    # impera.g:150:4: class_ref
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_class_ref_in_operand1052)
                    class_ref100 = self.class_ref()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, class_ref100.tree)



                elif alt20 == 6:
                    # impera.g:151:4: variable
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_variable_in_operand1057)
                    variable101 = self.variable()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, variable101.tree)



                elif alt20 == 7:
                    # impera.g:152:4: method_call
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_method_call_in_operand1062)
                    method_call102 = self.method_call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, method_call102.tree)



                elif alt20 == 8:
                    # impera.g:153:4: ( '{' )=> '{' expression '}'
                    pass 
                    char_literal103 = self.match(self.input, 84, self.FOLLOW_84_in_operand1073) 
                    if self._state.backtracking == 0:
                        stream_84.add(char_literal103)


                    self._state.following.append(self.FOLLOW_expression_in_operand1075)
                    expression104 = self.expression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_expression.add(expression104.tree)


                    char_literal105 = self.match(self.input, 86, self.FOLLOW_86_in_operand1077) 
                    if self._state.backtracking == 0:
                        stream_86.add(char_literal105)


                    # AST Rewrite
                    # elements: expression
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 153:32: -> ^( EXPRESSION expression )
                        # impera.g:153:35: ^( EXPRESSION expression )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(EXPRESSION, "EXPRESSION")
                        , root_1)

                        self._adaptor.addChild(root_1, stream_expression.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "operand"


    class constant_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "constant"
    # impera.g:157:1: constant : ( TRUE | FALSE | STRING | INT | FLOAT | REGEX | ML_STRING );
    def constant(self, ):
        retval = self.constant_return()
        retval.start = self.input.LT(1)


        root_0 = None

        set106 = None

        set106_tree = None

        try:
            try:
                # impera.g:158:2: ( TRUE | FALSE | STRING | INT | FLOAT | REGEX | ML_STRING )
                # impera.g:
                pass 
                root_0 = self._adaptor.nil()


                set106 = self.input.LT(1)

                if (FALSE <= self.input.LA(1) <= FLOAT) or self.input.LA(1) == INT or self.input.LA(1) == ML_STRING or self.input.LA(1) == REGEX or (STRING <= self.input.LA(1) <= TRUE):
                    self.input.consume()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set106))

                    self._state.errorRecovery = False


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    mse = MismatchedSetException(None, self.input)
                    raise mse





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "constant"


    class list_def_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "list_def"
    # impera.g:161:1: list_def : '[' operand ( ',' operand )* ( ',' )? ']' -> ^( LIST ( operand )+ ) ;
    def list_def(self, ):
        retval = self.list_def_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal107 = None
        char_literal109 = None
        char_literal111 = None
        char_literal112 = None
        operand108 = None
        operand110 = None

        char_literal107_tree = None
        char_literal109_tree = None
        char_literal111_tree = None
        char_literal112_tree = None
        stream_66 = RewriteRuleTokenStream(self._adaptor, "token 66")
        stream_52 = RewriteRuleTokenStream(self._adaptor, "token 52")
        stream_65 = RewriteRuleTokenStream(self._adaptor, "token 65")
        stream_operand = RewriteRuleSubtreeStream(self._adaptor, "rule operand")
        try:
            try:
                # impera.g:162:2: ( '[' operand ( ',' operand )* ( ',' )? ']' -> ^( LIST ( operand )+ ) )
                # impera.g:162:4: '[' operand ( ',' operand )* ( ',' )? ']'
                pass 
                char_literal107 = self.match(self.input, 65, self.FOLLOW_65_in_list_def1143) 
                if self._state.backtracking == 0:
                    stream_65.add(char_literal107)


                self._state.following.append(self.FOLLOW_operand_in_list_def1145)
                operand108 = self.operand()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_operand.add(operand108.tree)


                # impera.g:162:16: ( ',' operand )*
                while True: #loop21
                    alt21 = 2
                    LA21_0 = self.input.LA(1)

                    if (LA21_0 == 52) :
                        LA21_1 = self.input.LA(2)

                        if (LA21_1 == CLASS_ID or (FALSE <= LA21_1 <= FLOAT) or LA21_1 == ID or LA21_1 == INT or LA21_1 == ML_STRING or LA21_1 == REGEX or (STRING <= LA21_1 <= TRUE) or LA21_1 == 65 or LA21_1 == 84) :
                            alt21 = 1




                    if alt21 == 1:
                        # impera.g:162:17: ',' operand
                        pass 
                        char_literal109 = self.match(self.input, 52, self.FOLLOW_52_in_list_def1148) 
                        if self._state.backtracking == 0:
                            stream_52.add(char_literal109)


                        self._state.following.append(self.FOLLOW_operand_in_list_def1150)
                        operand110 = self.operand()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_operand.add(operand110.tree)



                    else:
                        break #loop21


                # impera.g:162:31: ( ',' )?
                alt22 = 2
                LA22_0 = self.input.LA(1)

                if (LA22_0 == 52) :
                    alt22 = 1
                if alt22 == 1:
                    # impera.g:162:31: ','
                    pass 
                    char_literal111 = self.match(self.input, 52, self.FOLLOW_52_in_list_def1154) 
                    if self._state.backtracking == 0:
                        stream_52.add(char_literal111)





                char_literal112 = self.match(self.input, 66, self.FOLLOW_66_in_list_def1157) 
                if self._state.backtracking == 0:
                    stream_66.add(char_literal112)


                # AST Rewrite
                # elements: operand
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 162:40: -> ^( LIST ( operand )+ )
                    # impera.g:162:43: ^( LIST ( operand )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_1)

                    # impera.g:162:50: ( operand )+
                    if not (stream_operand.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_operand.hasNext():
                        self._adaptor.addChild(root_1, stream_operand.nextTree())


                    stream_operand.reset()

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "list_def"


    class index_arg_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "index_arg"
    # impera.g:165:1: index_arg : param_list ;
    def index_arg(self, ):
        retval = self.index_arg_return()
        retval.start = self.input.LT(1)


        root_0 = None

        param_list113 = None


        try:
            try:
                # impera.g:166:2: ( param_list )
                # impera.g:166:4: param_list
                pass 
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_param_list_in_index_arg1178)
                param_list113 = self.param_list()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, param_list113.tree)




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "index_arg"


    class index_lookup_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "index_lookup"
    # impera.g:169:1: index_lookup : class_ref '[' index_arg ']' -> ^( HASH class_ref index_arg ) ;
    def index_lookup(self, ):
        retval = self.index_lookup_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal115 = None
        char_literal117 = None
        class_ref114 = None
        index_arg116 = None

        char_literal115_tree = None
        char_literal117_tree = None
        stream_66 = RewriteRuleTokenStream(self._adaptor, "token 66")
        stream_65 = RewriteRuleTokenStream(self._adaptor, "token 65")
        stream_index_arg = RewriteRuleSubtreeStream(self._adaptor, "rule index_arg")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        try:
            try:
                # impera.g:171:2: ( class_ref '[' index_arg ']' -> ^( HASH class_ref index_arg ) )
                # impera.g:171:4: class_ref '[' index_arg ']'
                pass 
                self._state.following.append(self.FOLLOW_class_ref_in_index_lookup1191)
                class_ref114 = self.class_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_class_ref.add(class_ref114.tree)


                char_literal115 = self.match(self.input, 65, self.FOLLOW_65_in_index_lookup1193) 
                if self._state.backtracking == 0:
                    stream_65.add(char_literal115)


                self._state.following.append(self.FOLLOW_index_arg_in_index_lookup1195)
                index_arg116 = self.index_arg()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_index_arg.add(index_arg116.tree)


                char_literal117 = self.match(self.input, 66, self.FOLLOW_66_in_index_lookup1197) 
                if self._state.backtracking == 0:
                    stream_66.add(char_literal117)


                # AST Rewrite
                # elements: class_ref, index_arg
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 171:32: -> ^( HASH class_ref index_arg )
                    # impera.g:171:35: ^( HASH class_ref index_arg )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(HASH, "HASH")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_class_ref.nextTree())

                    self._adaptor.addChild(root_1, stream_index_arg.nextTree())

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "index_lookup"


    class entity_def_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "entity_def"
    # impera.g:174:1: entity_def : ( 'entity' CLASS_ID ( 'extends' class_ref ( ',' class_ref )* )? ) ':' ( ML_STRING )? ( entity_body )* 'end' -> ^( DEF_ENTITY CLASS_ID ^( LIST ( class_ref )* ) ^( LIST ( entity_body )* ) ( ML_STRING )? ) ;
    def entity_def(self, ):
        retval = self.entity_def_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal118 = None
        CLASS_ID119 = None
        string_literal120 = None
        char_literal122 = None
        char_literal124 = None
        ML_STRING125 = None
        string_literal127 = None
        class_ref121 = None
        class_ref123 = None
        entity_body126 = None

        string_literal118_tree = None
        CLASS_ID119_tree = None
        string_literal120_tree = None
        char_literal122_tree = None
        char_literal124_tree = None
        ML_STRING125_tree = None
        string_literal127_tree = None
        stream_56 = RewriteRuleTokenStream(self._adaptor, "token 56")
        stream_69 = RewriteRuleTokenStream(self._adaptor, "token 69")
        stream_ML_STRING = RewriteRuleTokenStream(self._adaptor, "token ML_STRING")
        stream_70 = RewriteRuleTokenStream(self._adaptor, "token 70")
        stream_71 = RewriteRuleTokenStream(self._adaptor, "token 71")
        stream_52 = RewriteRuleTokenStream(self._adaptor, "token 52")
        stream_CLASS_ID = RewriteRuleTokenStream(self._adaptor, "token CLASS_ID")
        stream_entity_body = RewriteRuleSubtreeStream(self._adaptor, "rule entity_body")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        try:
            try:
                # impera.g:175:2: ( ( 'entity' CLASS_ID ( 'extends' class_ref ( ',' class_ref )* )? ) ':' ( ML_STRING )? ( entity_body )* 'end' -> ^( DEF_ENTITY CLASS_ID ^( LIST ( class_ref )* ) ^( LIST ( entity_body )* ) ( ML_STRING )? ) )
                # impera.g:175:4: ( 'entity' CLASS_ID ( 'extends' class_ref ( ',' class_ref )* )? ) ':' ( ML_STRING )? ( entity_body )* 'end'
                pass 
                # impera.g:175:4: ( 'entity' CLASS_ID ( 'extends' class_ref ( ',' class_ref )* )? )
                # impera.g:175:5: 'entity' CLASS_ID ( 'extends' class_ref ( ',' class_ref )* )?
                pass 
                string_literal118 = self.match(self.input, 70, self.FOLLOW_70_in_entity_def1219) 
                if self._state.backtracking == 0:
                    stream_70.add(string_literal118)


                CLASS_ID119 = self.match(self.input, CLASS_ID, self.FOLLOW_CLASS_ID_in_entity_def1221) 
                if self._state.backtracking == 0:
                    stream_CLASS_ID.add(CLASS_ID119)


                # impera.g:175:23: ( 'extends' class_ref ( ',' class_ref )* )?
                alt24 = 2
                LA24_0 = self.input.LA(1)

                if (LA24_0 == 71) :
                    alt24 = 1
                if alt24 == 1:
                    # impera.g:175:24: 'extends' class_ref ( ',' class_ref )*
                    pass 
                    string_literal120 = self.match(self.input, 71, self.FOLLOW_71_in_entity_def1224) 
                    if self._state.backtracking == 0:
                        stream_71.add(string_literal120)


                    self._state.following.append(self.FOLLOW_class_ref_in_entity_def1226)
                    class_ref121 = self.class_ref()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_class_ref.add(class_ref121.tree)


                    # impera.g:175:44: ( ',' class_ref )*
                    while True: #loop23
                        alt23 = 2
                        LA23_0 = self.input.LA(1)

                        if (LA23_0 == 52) :
                            alt23 = 1


                        if alt23 == 1:
                            # impera.g:175:45: ',' class_ref
                            pass 
                            char_literal122 = self.match(self.input, 52, self.FOLLOW_52_in_entity_def1229) 
                            if self._state.backtracking == 0:
                                stream_52.add(char_literal122)


                            self._state.following.append(self.FOLLOW_class_ref_in_entity_def1231)
                            class_ref123 = self.class_ref()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                stream_class_ref.add(class_ref123.tree)



                        else:
                            break #loop23








                char_literal124 = self.match(self.input, 56, self.FOLLOW_56_in_entity_def1238) 
                if self._state.backtracking == 0:
                    stream_56.add(char_literal124)


                # impera.g:175:68: ( ML_STRING )?
                alt25 = 2
                LA25_0 = self.input.LA(1)

                if (LA25_0 == ML_STRING) :
                    alt25 = 1
                if alt25 == 1:
                    # impera.g:175:68: ML_STRING
                    pass 
                    ML_STRING125 = self.match(self.input, ML_STRING, self.FOLLOW_ML_STRING_in_entity_def1240) 
                    if self._state.backtracking == 0:
                        stream_ML_STRING.add(ML_STRING125)





                # impera.g:175:79: ( entity_body )*
                while True: #loop26
                    alt26 = 2
                    LA26_0 = self.input.LA(1)

                    if (LA26_0 == CLASS_ID or LA26_0 == ID) :
                        alt26 = 1


                    if alt26 == 1:
                        # impera.g:175:80: entity_body
                        pass 
                        self._state.following.append(self.FOLLOW_entity_body_in_entity_def1244)
                        entity_body126 = self.entity_body()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_entity_body.add(entity_body126.tree)



                    else:
                        break #loop26


                string_literal127 = self.match(self.input, 69, self.FOLLOW_69_in_entity_def1248) 
                if self._state.backtracking == 0:
                    stream_69.add(string_literal127)


                # AST Rewrite
                # elements: class_ref, ML_STRING, entity_body, CLASS_ID
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 176:3: -> ^( DEF_ENTITY CLASS_ID ^( LIST ( class_ref )* ) ^( LIST ( entity_body )* ) ( ML_STRING )? )
                    # impera.g:176:6: ^( DEF_ENTITY CLASS_ID ^( LIST ( class_ref )* ) ^( LIST ( entity_body )* ) ( ML_STRING )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(DEF_ENTITY, "DEF_ENTITY")
                    , root_1)

                    self._adaptor.addChild(root_1, 
                    stream_CLASS_ID.nextNode()
                    )

                    # impera.g:176:28: ^( LIST ( class_ref )* )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_2)

                    # impera.g:176:35: ( class_ref )*
                    while stream_class_ref.hasNext():
                        self._adaptor.addChild(root_2, stream_class_ref.nextTree())


                    stream_class_ref.reset();

                    self._adaptor.addChild(root_1, root_2)

                    # impera.g:176:47: ^( LIST ( entity_body )* )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_2)

                    # impera.g:176:54: ( entity_body )*
                    while stream_entity_body.hasNext():
                        self._adaptor.addChild(root_2, stream_entity_body.nextTree())


                    stream_entity_body.reset();

                    self._adaptor.addChild(root_1, root_2)

                    # impera.g:176:68: ( ML_STRING )?
                    if stream_ML_STRING.hasNext():
                        self._adaptor.addChild(root_1, 
                        stream_ML_STRING.nextNode()
                        )


                    stream_ML_STRING.reset();

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "entity_def"


    class type_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "type"
    # impera.g:179:1: type : ( ns_ref | class_ref );
    def type(self, ):
        retval = self.type_return()
        retval.start = self.input.LT(1)


        root_0 = None

        ns_ref128 = None
        class_ref129 = None


        try:
            try:
                # impera.g:180:2: ( ns_ref | class_ref )
                alt27 = 2
                alt27 = self.dfa27.predict(self.input)
                if alt27 == 1:
                    # impera.g:180:4: ns_ref
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_ns_ref_in_type1290)
                    ns_ref128 = self.ns_ref()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, ns_ref128.tree)



                elif alt27 == 2:
                    # impera.g:180:13: class_ref
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_class_ref_in_type1294)
                    class_ref129 = self.class_ref()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, class_ref129.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "type"


    class entity_body_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "entity_body"
    # impera.g:183:1: entity_body : type ID ( '=' constant )? -> ^( STATEMENT type ID ( constant )? ) ;
    def entity_body(self, ):
        retval = self.entity_body_return()
        retval.start = self.input.LT(1)


        root_0 = None

        ID131 = None
        char_literal132 = None
        type130 = None
        constant133 = None

        ID131_tree = None
        char_literal132_tree = None
        stream_61 = RewriteRuleTokenStream(self._adaptor, "token 61")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_constant = RewriteRuleSubtreeStream(self._adaptor, "rule constant")
        stream_type = RewriteRuleSubtreeStream(self._adaptor, "rule type")
        try:
            try:
                # impera.g:184:2: ( type ID ( '=' constant )? -> ^( STATEMENT type ID ( constant )? ) )
                # impera.g:184:4: type ID ( '=' constant )?
                pass 
                self._state.following.append(self.FOLLOW_type_in_entity_body1305)
                type130 = self.type()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_type.add(type130.tree)


                ID131 = self.match(self.input, ID, self.FOLLOW_ID_in_entity_body1307) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID131)


                # impera.g:184:12: ( '=' constant )?
                alt28 = 2
                LA28_0 = self.input.LA(1)

                if (LA28_0 == 61) :
                    alt28 = 1
                if alt28 == 1:
                    # impera.g:184:13: '=' constant
                    pass 
                    char_literal132 = self.match(self.input, 61, self.FOLLOW_61_in_entity_body1310) 
                    if self._state.backtracking == 0:
                        stream_61.add(char_literal132)


                    self._state.following.append(self.FOLLOW_constant_in_entity_body1312)
                    constant133 = self.constant()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_constant.add(constant133.tree)





                # AST Rewrite
                # elements: constant, type, ID
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 184:28: -> ^( STATEMENT type ID ( constant )? )
                    # impera.g:184:31: ^( STATEMENT type ID ( constant )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(STATEMENT, "STATEMENT")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_type.nextTree())

                    self._adaptor.addChild(root_1, 
                    stream_ID.nextNode()
                    )

                    # impera.g:184:51: ( constant )?
                    if stream_constant.hasNext():
                        self._adaptor.addChild(root_1, stream_constant.nextTree())


                    stream_constant.reset();

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "entity_body"


    class ns_ref_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "ns_ref"
    # impera.g:187:1: ns_ref : ID ( '::' ID )* -> ^( REF ( ID )+ ) ;
    def ns_ref(self, ):
        retval = self.ns_ref_return()
        retval.start = self.input.LT(1)


        root_0 = None

        ID134 = None
        string_literal135 = None
        ID136 = None

        ID134_tree = None
        string_literal135_tree = None
        ID136_tree = None
        stream_57 = RewriteRuleTokenStream(self._adaptor, "token 57")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")

        try:
            try:
                # impera.g:188:2: ( ID ( '::' ID )* -> ^( REF ( ID )+ ) )
                # impera.g:188:4: ID ( '::' ID )*
                pass 
                ID134 = self.match(self.input, ID, self.FOLLOW_ID_in_ns_ref1339) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID134)


                # impera.g:188:7: ( '::' ID )*
                while True: #loop29
                    alt29 = 2
                    LA29_0 = self.input.LA(1)

                    if (LA29_0 == 57) :
                        alt29 = 1


                    if alt29 == 1:
                        # impera.g:188:8: '::' ID
                        pass 
                        string_literal135 = self.match(self.input, 57, self.FOLLOW_57_in_ns_ref1342) 
                        if self._state.backtracking == 0:
                            stream_57.add(string_literal135)


                        ID136 = self.match(self.input, ID, self.FOLLOW_ID_in_ns_ref1344) 
                        if self._state.backtracking == 0:
                            stream_ID.add(ID136)



                    else:
                        break #loop29


                # AST Rewrite
                # elements: ID
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 188:18: -> ^( REF ( ID )+ )
                    # impera.g:188:21: ^( REF ( ID )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(REF, "REF")
                    , root_1)

                    # impera.g:188:27: ( ID )+
                    if not (stream_ID.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_ID.hasNext():
                        self._adaptor.addChild(root_1, 
                        stream_ID.nextNode()
                        )


                    stream_ID.reset()

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "ns_ref"


    class class_ref_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "class_ref"
    # impera.g:191:1: class_ref : (ns+= ID '::' )* CLASS_ID -> ^( CLASS_REF ^( NS ( $ns)* ) CLASS_ID ) ;
    def class_ref(self, ):
        retval = self.class_ref_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal137 = None
        CLASS_ID138 = None
        ns = None
        list_ns = None

        string_literal137_tree = None
        CLASS_ID138_tree = None
        ns_tree = None
        stream_57 = RewriteRuleTokenStream(self._adaptor, "token 57")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_CLASS_ID = RewriteRuleTokenStream(self._adaptor, "token CLASS_ID")

        try:
            try:
                # impera.g:192:5: ( (ns+= ID '::' )* CLASS_ID -> ^( CLASS_REF ^( NS ( $ns)* ) CLASS_ID ) )
                # impera.g:192:7: (ns+= ID '::' )* CLASS_ID
                pass 
                # impera.g:192:7: (ns+= ID '::' )*
                while True: #loop30
                    alt30 = 2
                    LA30_0 = self.input.LA(1)

                    if (LA30_0 == ID) :
                        alt30 = 1


                    if alt30 == 1:
                        # impera.g:192:8: ns+= ID '::'
                        pass 
                        ns = self.match(self.input, ID, self.FOLLOW_ID_in_class_ref1373) 
                        if self._state.backtracking == 0:
                            stream_ID.add(ns)

                        if list_ns is None:
                            list_ns = []
                        list_ns.append(ns)


                        string_literal137 = self.match(self.input, 57, self.FOLLOW_57_in_class_ref1375) 
                        if self._state.backtracking == 0:
                            stream_57.add(string_literal137)



                    else:
                        break #loop30


                CLASS_ID138 = self.match(self.input, CLASS_ID, self.FOLLOW_CLASS_ID_in_class_ref1379) 
                if self._state.backtracking == 0:
                    stream_CLASS_ID.add(CLASS_ID138)


                # AST Rewrite
                # elements: ns, CLASS_ID
                # token labels: 
                # rule labels: retval
                # token list labels: ns
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    stream_ns = RewriteRuleTokenStream(self._adaptor, "token ns", list_ns)
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 192:31: -> ^( CLASS_REF ^( NS ( $ns)* ) CLASS_ID )
                    # impera.g:192:34: ^( CLASS_REF ^( NS ( $ns)* ) CLASS_ID )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(CLASS_REF, "CLASS_REF")
                    , root_1)

                    # impera.g:192:46: ^( NS ( $ns)* )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(NS, "NS")
                    , root_2)

                    # impera.g:192:52: ( $ns)*
                    while stream_ns.hasNext():
                        self._adaptor.addChild(root_2, stream_ns.nextNode())


                    stream_ns.reset();

                    self._adaptor.addChild(root_1, root_2)

                    self._adaptor.addChild(root_1, 
                    stream_CLASS_ID.nextNode()
                    )

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "class_ref"


    class variable_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "variable"
    # impera.g:195:1: variable : (ns+= ID '::' )* var= ID ( '.' attr+= ID )* -> ^( VAR_REF ^( NS ( $ns)* ) $var ^( ATTR ( $attr)* ) ) ;
    def variable(self, ):
        retval = self.variable_return()
        retval.start = self.input.LT(1)


        root_0 = None

        var = None
        string_literal139 = None
        char_literal140 = None
        ns = None
        attr = None
        list_ns = None
        list_attr = None

        var_tree = None
        string_literal139_tree = None
        char_literal140_tree = None
        ns_tree = None
        attr_tree = None
        stream_55 = RewriteRuleTokenStream(self._adaptor, "token 55")
        stream_57 = RewriteRuleTokenStream(self._adaptor, "token 57")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")

        try:
            try:
                # impera.g:196:2: ( (ns+= ID '::' )* var= ID ( '.' attr+= ID )* -> ^( VAR_REF ^( NS ( $ns)* ) $var ^( ATTR ( $attr)* ) ) )
                # impera.g:196:4: (ns+= ID '::' )* var= ID ( '.' attr+= ID )*
                pass 
                # impera.g:196:4: (ns+= ID '::' )*
                while True: #loop31
                    alt31 = 2
                    LA31_0 = self.input.LA(1)

                    if (LA31_0 == ID) :
                        LA31_1 = self.input.LA(2)

                        if (LA31_1 == 57) :
                            alt31 = 1




                    if alt31 == 1:
                        # impera.g:196:5: ns+= ID '::'
                        pass 
                        ns = self.match(self.input, ID, self.FOLLOW_ID_in_variable1413) 
                        if self._state.backtracking == 0:
                            stream_ID.add(ns)

                        if list_ns is None:
                            list_ns = []
                        list_ns.append(ns)


                        string_literal139 = self.match(self.input, 57, self.FOLLOW_57_in_variable1415) 
                        if self._state.backtracking == 0:
                            stream_57.add(string_literal139)



                    else:
                        break #loop31


                var = self.match(self.input, ID, self.FOLLOW_ID_in_variable1421) 
                if self._state.backtracking == 0:
                    stream_ID.add(var)


                # impera.g:196:26: ( '.' attr+= ID )*
                while True: #loop32
                    alt32 = 2
                    LA32_0 = self.input.LA(1)

                    if (LA32_0 == 55) :
                        alt32 = 1


                    if alt32 == 1:
                        # impera.g:196:27: '.' attr+= ID
                        pass 
                        char_literal140 = self.match(self.input, 55, self.FOLLOW_55_in_variable1424) 
                        if self._state.backtracking == 0:
                            stream_55.add(char_literal140)


                        attr = self.match(self.input, ID, self.FOLLOW_ID_in_variable1428) 
                        if self._state.backtracking == 0:
                            stream_ID.add(attr)

                        if list_attr is None:
                            list_attr = []
                        list_attr.append(attr)



                    else:
                        break #loop32


                # AST Rewrite
                # elements: ns, attr, var
                # token labels: var
                # rule labels: retval
                # token list labels: ns, attr
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    stream_var = RewriteRuleTokenStream(self._adaptor, "token var", var)
                    stream_ns = RewriteRuleTokenStream(self._adaptor, "token ns", list_ns)
                    stream_attr = RewriteRuleTokenStream(self._adaptor, "token attr", list_attr)
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 196:42: -> ^( VAR_REF ^( NS ( $ns)* ) $var ^( ATTR ( $attr)* ) )
                    # impera.g:196:45: ^( VAR_REF ^( NS ( $ns)* ) $var ^( ATTR ( $attr)* ) )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(VAR_REF, "VAR_REF")
                    , root_1)

                    # impera.g:196:55: ^( NS ( $ns)* )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(NS, "NS")
                    , root_2)

                    # impera.g:196:61: ( $ns)*
                    while stream_ns.hasNext():
                        self._adaptor.addChild(root_2, stream_ns.nextNode())


                    stream_ns.reset();

                    self._adaptor.addChild(root_1, root_2)

                    self._adaptor.addChild(root_1, stream_var.nextNode())

                    # impera.g:196:71: ^( ATTR ( $attr)* )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(ATTR, "ATTR")
                    , root_2)

                    # impera.g:196:79: ( $attr)*
                    while stream_attr.hasNext():
                        self._adaptor.addChild(root_2, stream_attr.nextNode())


                    stream_attr.reset();

                    self._adaptor.addChild(root_1, root_2)

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "variable"


    class arg_list_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "arg_list"
    # impera.g:199:1: arg_list : operand ( ',' operand )* ( ',' )? -> ^( LIST ( operand )+ ) ;
    def arg_list(self, ):
        retval = self.arg_list_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal142 = None
        char_literal144 = None
        operand141 = None
        operand143 = None

        char_literal142_tree = None
        char_literal144_tree = None
        stream_52 = RewriteRuleTokenStream(self._adaptor, "token 52")
        stream_operand = RewriteRuleSubtreeStream(self._adaptor, "rule operand")
        try:
            try:
                # impera.g:200:2: ( operand ( ',' operand )* ( ',' )? -> ^( LIST ( operand )+ ) )
                # impera.g:200:4: operand ( ',' operand )* ( ',' )?
                pass 
                self._state.following.append(self.FOLLOW_operand_in_arg_list1467)
                operand141 = self.operand()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_operand.add(operand141.tree)


                # impera.g:200:12: ( ',' operand )*
                while True: #loop33
                    alt33 = 2
                    LA33_0 = self.input.LA(1)

                    if (LA33_0 == 52) :
                        LA33_1 = self.input.LA(2)

                        if (LA33_1 == CLASS_ID or (FALSE <= LA33_1 <= FLOAT) or LA33_1 == ID or LA33_1 == INT or LA33_1 == ML_STRING or LA33_1 == REGEX or (STRING <= LA33_1 <= TRUE) or LA33_1 == 65 or LA33_1 == 84) :
                            alt33 = 1




                    if alt33 == 1:
                        # impera.g:200:13: ',' operand
                        pass 
                        char_literal142 = self.match(self.input, 52, self.FOLLOW_52_in_arg_list1470) 
                        if self._state.backtracking == 0:
                            stream_52.add(char_literal142)


                        self._state.following.append(self.FOLLOW_operand_in_arg_list1472)
                        operand143 = self.operand()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_operand.add(operand143.tree)



                    else:
                        break #loop33


                # impera.g:200:27: ( ',' )?
                alt34 = 2
                LA34_0 = self.input.LA(1)

                if (LA34_0 == 52) :
                    alt34 = 1
                if alt34 == 1:
                    # impera.g:200:27: ','
                    pass 
                    char_literal144 = self.match(self.input, 52, self.FOLLOW_52_in_arg_list1476) 
                    if self._state.backtracking == 0:
                        stream_52.add(char_literal144)





                # AST Rewrite
                # elements: operand
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 200:32: -> ^( LIST ( operand )+ )
                    # impera.g:200:35: ^( LIST ( operand )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_1)

                    # impera.g:200:42: ( operand )+
                    if not (stream_operand.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_operand.hasNext():
                        self._adaptor.addChild(root_1, stream_operand.nextTree())


                    stream_operand.reset()

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "arg_list"


    class function_call_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "function_call"
    # impera.g:203:1: function_call : ns_ref '(' ( call_arg )? ')' -> ^( CALL ns_ref ( call_arg )? ) ;
    def function_call(self, ):
        retval = self.function_call_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal146 = None
        char_literal148 = None
        ns_ref145 = None
        call_arg147 = None

        char_literal146_tree = None
        char_literal148_tree = None
        stream_50 = RewriteRuleTokenStream(self._adaptor, "token 50")
        stream_51 = RewriteRuleTokenStream(self._adaptor, "token 51")
        stream_ns_ref = RewriteRuleSubtreeStream(self._adaptor, "rule ns_ref")
        stream_call_arg = RewriteRuleSubtreeStream(self._adaptor, "rule call_arg")
        try:
            try:
                # impera.g:204:2: ( ns_ref '(' ( call_arg )? ')' -> ^( CALL ns_ref ( call_arg )? ) )
                # impera.g:204:4: ns_ref '(' ( call_arg )? ')'
                pass 
                self._state.following.append(self.FOLLOW_ns_ref_in_function_call1498)
                ns_ref145 = self.ns_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_ns_ref.add(ns_ref145.tree)


                char_literal146 = self.match(self.input, 50, self.FOLLOW_50_in_function_call1500) 
                if self._state.backtracking == 0:
                    stream_50.add(char_literal146)


                # impera.g:204:15: ( call_arg )?
                alt35 = 2
                LA35_0 = self.input.LA(1)

                if (LA35_0 == CLASS_ID or (FALSE <= LA35_0 <= FLOAT) or LA35_0 == ID or LA35_0 == INT or LA35_0 == ML_STRING or LA35_0 == REGEX or (STRING <= LA35_0 <= TRUE) or LA35_0 == 65 or LA35_0 == 84) :
                    alt35 = 1
                if alt35 == 1:
                    # impera.g:204:15: call_arg
                    pass 
                    self._state.following.append(self.FOLLOW_call_arg_in_function_call1502)
                    call_arg147 = self.call_arg()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_call_arg.add(call_arg147.tree)





                char_literal148 = self.match(self.input, 51, self.FOLLOW_51_in_function_call1505) 
                if self._state.backtracking == 0:
                    stream_51.add(char_literal148)


                # AST Rewrite
                # elements: ns_ref, call_arg
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 204:29: -> ^( CALL ns_ref ( call_arg )? )
                    # impera.g:204:32: ^( CALL ns_ref ( call_arg )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(CALL, "CALL")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_ns_ref.nextTree())

                    # impera.g:204:46: ( call_arg )?
                    if stream_call_arg.hasNext():
                        self._adaptor.addChild(root_1, stream_call_arg.nextTree())


                    stream_call_arg.reset();

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "function_call"


    class call_arg_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "call_arg"
    # impera.g:207:1: call_arg : arg_list ;
    def call_arg(self, ):
        retval = self.call_arg_return()
        retval.start = self.input.LT(1)


        root_0 = None

        arg_list149 = None


        try:
            try:
                # impera.g:208:2: ( arg_list )
                # impera.g:210:3: arg_list
                pass 
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_arg_list_in_call_arg1533)
                arg_list149 = self.arg_list()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, arg_list149.tree)




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "call_arg"


    class method_pipe_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "method_pipe"
    # impera.g:213:1: method_pipe : '|' ns_ref ( '(' ( call_arg )? ')' )? -> ^( CALL ns_ref ( call_arg )? ) ;
    def method_pipe(self, ):
        retval = self.method_pipe_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal150 = None
        char_literal152 = None
        char_literal154 = None
        ns_ref151 = None
        call_arg153 = None

        char_literal150_tree = None
        char_literal152_tree = None
        char_literal154_tree = None
        stream_50 = RewriteRuleTokenStream(self._adaptor, "token 50")
        stream_51 = RewriteRuleTokenStream(self._adaptor, "token 51")
        stream_85 = RewriteRuleTokenStream(self._adaptor, "token 85")
        stream_ns_ref = RewriteRuleSubtreeStream(self._adaptor, "rule ns_ref")
        stream_call_arg = RewriteRuleSubtreeStream(self._adaptor, "rule call_arg")
        try:
            try:
                # impera.g:214:2: ( '|' ns_ref ( '(' ( call_arg )? ')' )? -> ^( CALL ns_ref ( call_arg )? ) )
                # impera.g:214:4: '|' ns_ref ( '(' ( call_arg )? ')' )?
                pass 
                char_literal150 = self.match(self.input, 85, self.FOLLOW_85_in_method_pipe1544) 
                if self._state.backtracking == 0:
                    stream_85.add(char_literal150)


                self._state.following.append(self.FOLLOW_ns_ref_in_method_pipe1546)
                ns_ref151 = self.ns_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_ns_ref.add(ns_ref151.tree)


                # impera.g:214:15: ( '(' ( call_arg )? ')' )?
                alt37 = 2
                LA37_0 = self.input.LA(1)

                if (LA37_0 == 50) :
                    alt37 = 1
                if alt37 == 1:
                    # impera.g:214:16: '(' ( call_arg )? ')'
                    pass 
                    char_literal152 = self.match(self.input, 50, self.FOLLOW_50_in_method_pipe1549) 
                    if self._state.backtracking == 0:
                        stream_50.add(char_literal152)


                    # impera.g:214:20: ( call_arg )?
                    alt36 = 2
                    LA36_0 = self.input.LA(1)

                    if (LA36_0 == CLASS_ID or (FALSE <= LA36_0 <= FLOAT) or LA36_0 == ID or LA36_0 == INT or LA36_0 == ML_STRING or LA36_0 == REGEX or (STRING <= LA36_0 <= TRUE) or LA36_0 == 65 or LA36_0 == 84) :
                        alt36 = 1
                    if alt36 == 1:
                        # impera.g:214:20: call_arg
                        pass 
                        self._state.following.append(self.FOLLOW_call_arg_in_method_pipe1551)
                        call_arg153 = self.call_arg()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_call_arg.add(call_arg153.tree)





                    char_literal154 = self.match(self.input, 51, self.FOLLOW_51_in_method_pipe1554) 
                    if self._state.backtracking == 0:
                        stream_51.add(char_literal154)





                # AST Rewrite
                # elements: call_arg, ns_ref
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 214:36: -> ^( CALL ns_ref ( call_arg )? )
                    # impera.g:214:40: ^( CALL ns_ref ( call_arg )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(CALL, "CALL")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_ns_ref.nextTree())

                    # impera.g:214:54: ( call_arg )?
                    if stream_call_arg.hasNext():
                        self._adaptor.addChild(root_1, stream_call_arg.nextTree())


                    stream_call_arg.reset();

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "method_pipe"


    class method_call_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "method_call"
    # impera.g:217:1: method_call : (cl= class_ref |var= variable ) ( method_pipe )+ -> ^( METHOD ( $cl)? ( $var)? ( method_pipe )+ ) ;
    def method_call(self, ):
        retval = self.method_call_return()
        retval.start = self.input.LT(1)


        root_0 = None

        cl = None
        var = None
        method_pipe155 = None

        stream_method_pipe = RewriteRuleSubtreeStream(self._adaptor, "rule method_pipe")
        stream_variable = RewriteRuleSubtreeStream(self._adaptor, "rule variable")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        try:
            try:
                # impera.g:218:2: ( (cl= class_ref |var= variable ) ( method_pipe )+ -> ^( METHOD ( $cl)? ( $var)? ( method_pipe )+ ) )
                # impera.g:218:4: (cl= class_ref |var= variable ) ( method_pipe )+
                pass 
                # impera.g:218:4: (cl= class_ref |var= variable )
                alt38 = 2
                alt38 = self.dfa38.predict(self.input)
                if alt38 == 1:
                    # impera.g:218:5: cl= class_ref
                    pass 
                    self._state.following.append(self.FOLLOW_class_ref_in_method_call1583)
                    cl = self.class_ref()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_class_ref.add(cl.tree)



                elif alt38 == 2:
                    # impera.g:218:20: var= variable
                    pass 
                    self._state.following.append(self.FOLLOW_variable_in_method_call1589)
                    var = self.variable()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_variable.add(var.tree)





                # impera.g:218:34: ( method_pipe )+
                cnt39 = 0
                while True: #loop39
                    alt39 = 2
                    LA39_0 = self.input.LA(1)

                    if (LA39_0 == 85) :
                        alt39 = 1


                    if alt39 == 1:
                        # impera.g:218:35: method_pipe
                        pass 
                        self._state.following.append(self.FOLLOW_method_pipe_in_method_call1593)
                        method_pipe155 = self.method_pipe()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_method_pipe.add(method_pipe155.tree)



                    else:
                        if cnt39 >= 1:
                            break #loop39

                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        eee = EarlyExitException(39, self.input)
                        raise eee

                    cnt39 += 1


                # AST Rewrite
                # elements: method_pipe, cl, var
                # token labels: 
                # rule labels: var, cl, retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:
                    retval.tree = root_0
                    if var is not None:
                        stream_var = RewriteRuleSubtreeStream(self._adaptor, "rule var", var.tree)
                    else:
                        stream_var = RewriteRuleSubtreeStream(self._adaptor, "token var", None)

                    if cl is not None:
                        stream_cl = RewriteRuleSubtreeStream(self._adaptor, "rule cl", cl.tree)
                    else:
                        stream_cl = RewriteRuleSubtreeStream(self._adaptor, "token cl", None)

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 218:49: -> ^( METHOD ( $cl)? ( $var)? ( method_pipe )+ )
                    # impera.g:218:52: ^( METHOD ( $cl)? ( $var)? ( method_pipe )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(METHOD, "METHOD")
                    , root_1)

                    # impera.g:218:62: ( $cl)?
                    if stream_cl.hasNext():
                        self._adaptor.addChild(root_1, stream_cl.nextTree())


                    stream_cl.reset();

                    # impera.g:218:67: ( $var)?
                    if stream_var.hasNext():
                        self._adaptor.addChild(root_1, stream_var.nextTree())


                    stream_var.reset();

                    # impera.g:218:72: ( method_pipe )+
                    if not (stream_method_pipe.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_method_pipe.hasNext():
                        self._adaptor.addChild(root_1, stream_method_pipe.nextTree())


                    stream_method_pipe.reset()

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "method_call"


    class un_op_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "un_op"
    # impera.g:221:1: un_op : 'not' ;
    def un_op(self, ):
        retval = self.un_op_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal156 = None

        string_literal156_tree = None

        try:
            try:
                # impera.g:222:2: ( 'not' )
                # impera.g:222:4: 'not'
                pass 
                root_0 = self._adaptor.nil()


                string_literal156 = self.match(self.input, 79, self.FOLLOW_79_in_un_op1623)
                if self._state.backtracking == 0:
                    string_literal156_tree = self._adaptor.createWithPayload(string_literal156)
                    self._adaptor.addChild(root_0, string_literal156_tree)





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "un_op"


    class cmp_op_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "cmp_op"
    # impera.g:225:1: cmp_op : ( '==' | '!=' | '<=' | '>=' | '<' | '>' );
    def cmp_op(self, ):
        retval = self.cmp_op_return()
        retval.start = self.input.LT(1)


        root_0 = None

        set157 = None

        set157_tree = None

        try:
            try:
                # impera.g:226:2: ( '==' | '!=' | '<=' | '>=' | '<' | '>' )
                # impera.g:
                pass 
                root_0 = self._adaptor.nil()


                set157 = self.input.LT(1)

                if self.input.LA(1) == 49 or self.input.LA(1) == 58 or self.input.LA(1) == 60 or (62 <= self.input.LA(1) <= 64):
                    self.input.consume()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set157))

                    self._state.errorRecovery = False


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    mse = MismatchedSetException(None, self.input)
                    raise mse





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "cmp_op"


    class cmp_oper_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "cmp_oper"
    # impera.g:229:1: cmp_oper : ( variable | function_call | method_call | index_lookup | constant | class_ref );
    def cmp_oper(self, ):
        retval = self.cmp_oper_return()
        retval.start = self.input.LT(1)


        root_0 = None

        variable158 = None
        function_call159 = None
        method_call160 = None
        index_lookup161 = None
        constant162 = None
        class_ref163 = None


        try:
            try:
                # impera.g:230:2: ( variable | function_call | method_call | index_lookup | constant | class_ref )
                alt40 = 6
                alt40 = self.dfa40.predict(self.input)
                if alt40 == 1:
                    # impera.g:230:4: variable
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_variable_in_cmp_oper1667)
                    variable158 = self.variable()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, variable158.tree)



                elif alt40 == 2:
                    # impera.g:230:15: function_call
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_function_call_in_cmp_oper1671)
                    function_call159 = self.function_call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, function_call159.tree)



                elif alt40 == 3:
                    # impera.g:230:31: method_call
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_method_call_in_cmp_oper1675)
                    method_call160 = self.method_call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, method_call160.tree)



                elif alt40 == 4:
                    # impera.g:230:45: index_lookup
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_index_lookup_in_cmp_oper1679)
                    index_lookup161 = self.index_lookup()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, index_lookup161.tree)



                elif alt40 == 5:
                    # impera.g:230:60: constant
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_constant_in_cmp_oper1683)
                    constant162 = self.constant()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, constant162.tree)



                elif alt40 == 6:
                    # impera.g:230:71: class_ref
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_class_ref_in_cmp_oper1687)
                    class_ref163 = self.class_ref()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, class_ref163.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "cmp_oper"


    class cmp_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "cmp"
    # impera.g:233:1: cmp : ( ( cmp_oper 'in' )=> cmp_oper 'in' in_oper -> ^( OP 'in' cmp_oper in_oper ) | ( cmp_oper cmp_op )=> cmp_oper cmp_op cmp_oper -> ^( OP cmp_op ( cmp_oper )+ ) | function_call -> ^( OP function_call ) );
    def cmp(self, ):
        retval = self.cmp_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal165 = None
        cmp_oper164 = None
        in_oper166 = None
        cmp_oper167 = None
        cmp_op168 = None
        cmp_oper169 = None
        function_call170 = None

        string_literal165_tree = None
        stream_75 = RewriteRuleTokenStream(self._adaptor, "token 75")
        stream_function_call = RewriteRuleSubtreeStream(self._adaptor, "rule function_call")
        stream_in_oper = RewriteRuleSubtreeStream(self._adaptor, "rule in_oper")
        stream_cmp_oper = RewriteRuleSubtreeStream(self._adaptor, "rule cmp_oper")
        stream_cmp_op = RewriteRuleSubtreeStream(self._adaptor, "rule cmp_op")
        try:
            try:
                # impera.g:234:2: ( ( cmp_oper 'in' )=> cmp_oper 'in' in_oper -> ^( OP 'in' cmp_oper in_oper ) | ( cmp_oper cmp_op )=> cmp_oper cmp_op cmp_oper -> ^( OP cmp_op ( cmp_oper )+ ) | function_call -> ^( OP function_call ) )
                alt41 = 3
                LA41 = self.input.LA(1)
                if LA41 in {ID}:
                    LA41_1 = self.input.LA(2)

                    if (self.synpred10_impera()) :
                        alt41 = 1
                    elif (self.synpred11_impera()) :
                        alt41 = 2
                    elif (True) :
                        alt41 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 41, 1, self.input)

                        raise nvae


                elif LA41 in {CLASS_ID}:
                    LA41_2 = self.input.LA(2)

                    if (self.synpred10_impera()) :
                        alt41 = 1
                    elif (self.synpred11_impera()) :
                        alt41 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 41, 2, self.input)

                        raise nvae


                elif LA41 in {FALSE, FLOAT, INT, ML_STRING, REGEX, STRING, TRUE}:
                    LA41_3 = self.input.LA(2)

                    if (self.synpred10_impera()) :
                        alt41 = 1
                    elif (self.synpred11_impera()) :
                        alt41 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 41, 3, self.input)

                        raise nvae


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 41, 0, self.input)

                    raise nvae


                if alt41 == 1:
                    # impera.g:234:4: ( cmp_oper 'in' )=> cmp_oper 'in' in_oper
                    pass 
                    self._state.following.append(self.FOLLOW_cmp_oper_in_cmp1708)
                    cmp_oper164 = self.cmp_oper()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_cmp_oper.add(cmp_oper164.tree)


                    string_literal165 = self.match(self.input, 75, self.FOLLOW_75_in_cmp1710) 
                    if self._state.backtracking == 0:
                        stream_75.add(string_literal165)


                    self._state.following.append(self.FOLLOW_in_oper_in_cmp1712)
                    in_oper166 = self.in_oper()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_in_oper.add(in_oper166.tree)


                    # AST Rewrite
                    # elements: cmp_oper, 75, in_oper
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 234:45: -> ^( OP 'in' cmp_oper in_oper )
                        # impera.g:234:48: ^( OP 'in' cmp_oper in_oper )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(OP, "OP")
                        , root_1)

                        self._adaptor.addChild(root_1, 
                        stream_75.nextNode()
                        )

                        self._adaptor.addChild(root_1, stream_cmp_oper.nextTree())

                        self._adaptor.addChild(root_1, stream_in_oper.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt41 == 2:
                    # impera.g:235:4: ( cmp_oper cmp_op )=> cmp_oper cmp_op cmp_oper
                    pass 
                    self._state.following.append(self.FOLLOW_cmp_oper_in_cmp1737)
                    cmp_oper167 = self.cmp_oper()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_cmp_oper.add(cmp_oper167.tree)


                    self._state.following.append(self.FOLLOW_cmp_op_in_cmp1739)
                    cmp_op168 = self.cmp_op()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_cmp_op.add(cmp_op168.tree)


                    self._state.following.append(self.FOLLOW_cmp_oper_in_cmp1741)
                    cmp_oper169 = self.cmp_oper()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_cmp_oper.add(cmp_oper169.tree)


                    # AST Rewrite
                    # elements: cmp_op, cmp_oper
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 235:50: -> ^( OP cmp_op ( cmp_oper )+ )
                        # impera.g:235:53: ^( OP cmp_op ( cmp_oper )+ )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(OP, "OP")
                        , root_1)

                        self._adaptor.addChild(root_1, stream_cmp_op.nextTree())

                        # impera.g:235:65: ( cmp_oper )+
                        if not (stream_cmp_oper.hasNext()):
                            raise RewriteEarlyExitException()

                        while stream_cmp_oper.hasNext():
                            self._adaptor.addChild(root_1, stream_cmp_oper.nextTree())


                        stream_cmp_oper.reset()

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt41 == 3:
                    # impera.g:236:4: function_call
                    pass 
                    self._state.following.append(self.FOLLOW_function_call_in_cmp1757)
                    function_call170 = self.function_call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_function_call.add(function_call170.tree)


                    # AST Rewrite
                    # elements: function_call
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 236:18: -> ^( OP function_call )
                        # impera.g:236:21: ^( OP function_call )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(OP, "OP")
                        , root_1)

                        self._adaptor.addChild(root_1, stream_function_call.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "cmp"


    class log_op_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "log_op"
    # impera.g:239:1: log_op : ( 'and' | 'or' );
    def log_op(self, ):
        retval = self.log_op_return()
        retval.start = self.input.LT(1)


        root_0 = None

        set171 = None

        set171_tree = None

        try:
            try:
                # impera.g:240:2: ( 'and' | 'or' )
                # impera.g:
                pass 
                root_0 = self._adaptor.nil()


                set171 = self.input.LT(1)

                if self.input.LA(1) == 67 or self.input.LA(1) == 80:
                    self.input.consume()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set171))

                    self._state.errorRecovery = False


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    mse = MismatchedSetException(None, self.input)
                    raise mse





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "log_op"


    class in_oper_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "in_oper"
    # impera.g:243:1: in_oper : ( list_def | variable );
    def in_oper(self, ):
        retval = self.in_oper_return()
        retval.start = self.input.LT(1)


        root_0 = None

        list_def172 = None
        variable173 = None


        try:
            try:
                # impera.g:244:2: ( list_def | variable )
                alt42 = 2
                LA42_0 = self.input.LA(1)

                if (LA42_0 == 65) :
                    alt42 = 1
                elif (LA42_0 == ID) :
                    alt42 = 2
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 42, 0, self.input)

                    raise nvae


                if alt42 == 1:
                    # impera.g:244:4: list_def
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_list_def_in_in_oper1793)
                    list_def172 = self.list_def()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, list_def172.tree)



                elif alt42 == 2:
                    # impera.g:244:15: variable
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_variable_in_in_oper1797)
                    variable173 = self.variable()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, variable173.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "in_oper"


    class log_oper_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "log_oper"
    # impera.g:247:1: log_oper : ( cmp | TRUE | FALSE );
    def log_oper(self, ):
        retval = self.log_oper_return()
        retval.start = self.input.LT(1)


        root_0 = None

        TRUE175 = None
        FALSE176 = None
        cmp174 = None

        TRUE175_tree = None
        FALSE176_tree = None

        try:
            try:
                # impera.g:248:2: ( cmp | TRUE | FALSE )
                alt43 = 3
                LA43 = self.input.LA(1)
                if LA43 in {CLASS_ID, FLOAT, ID, INT, ML_STRING, REGEX, STRING}:
                    alt43 = 1
                elif LA43 in {TRUE}:
                    LA43_2 = self.input.LA(2)

                    if (LA43_2 == 49 or LA43_2 == 58 or LA43_2 == 60 or (62 <= LA43_2 <= 64) or LA43_2 == 75) :
                        alt43 = 1
                    elif (LA43_2 == EOF or LA43_2 == CLASS_ID or LA43_2 == ID or LA43_2 == ML_STRING or LA43_2 == 51 or LA43_2 == 67 or LA43_2 == 70 or (72 <= LA43_2 <= 74) or (76 <= LA43_2 <= 77) or (80 <= LA43_2 <= 81) or LA43_2 == 86) :
                        alt43 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 43, 2, self.input)

                        raise nvae


                elif LA43 in {FALSE}:
                    LA43_3 = self.input.LA(2)

                    if (LA43_3 == 49 or LA43_3 == 58 or LA43_3 == 60 or (62 <= LA43_3 <= 64) or LA43_3 == 75) :
                        alt43 = 1
                    elif (LA43_3 == EOF or LA43_3 == CLASS_ID or LA43_3 == ID or LA43_3 == ML_STRING or LA43_3 == 51 or LA43_3 == 67 or LA43_3 == 70 or (72 <= LA43_3 <= 74) or (76 <= LA43_3 <= 77) or (80 <= LA43_3 <= 81) or LA43_3 == 86) :
                        alt43 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 43, 3, self.input)

                        raise nvae


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 43, 0, self.input)

                    raise nvae


                if alt43 == 1:
                    # impera.g:248:4: cmp
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_cmp_in_log_oper1810)
                    cmp174 = self.cmp()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, cmp174.tree)



                elif alt43 == 2:
                    # impera.g:248:10: TRUE
                    pass 
                    root_0 = self._adaptor.nil()


                    TRUE175 = self.match(self.input, TRUE, self.FOLLOW_TRUE_in_log_oper1814)
                    if self._state.backtracking == 0:
                        TRUE175_tree = self._adaptor.createWithPayload(TRUE175)
                        self._adaptor.addChild(root_0, TRUE175_tree)




                elif alt43 == 3:
                    # impera.g:248:17: FALSE
                    pass 
                    root_0 = self._adaptor.nil()


                    FALSE176 = self.match(self.input, FALSE, self.FOLLOW_FALSE_in_log_oper1818)
                    if self._state.backtracking == 0:
                        FALSE176_tree = self._adaptor.createWithPayload(FALSE176)
                        self._adaptor.addChild(root_0, FALSE176_tree)




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "log_oper"


    class log_expr_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "log_expr"
    # impera.g:251:1: log_expr : ( ( log_oper log_op )=> log_oper log_op log_expr -> ^( OP log_op log_oper log_expr ) | log_oper );
    def log_expr(self, ):
        retval = self.log_expr_return()
        retval.start = self.input.LT(1)


        root_0 = None

        log_oper177 = None
        log_op178 = None
        log_expr179 = None
        log_oper180 = None

        stream_log_expr = RewriteRuleSubtreeStream(self._adaptor, "rule log_expr")
        stream_log_op = RewriteRuleSubtreeStream(self._adaptor, "rule log_op")
        stream_log_oper = RewriteRuleSubtreeStream(self._adaptor, "rule log_oper")
        try:
            try:
                # impera.g:253:2: ( ( log_oper log_op )=> log_oper log_op log_expr -> ^( OP log_op log_oper log_expr ) | log_oper )
                alt44 = 2
                LA44 = self.input.LA(1)
                if LA44 in {ID}:
                    LA44_1 = self.input.LA(2)

                    if (self.synpred12_impera()) :
                        alt44 = 1
                    elif (True) :
                        alt44 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 44, 1, self.input)

                        raise nvae


                elif LA44 in {CLASS_ID}:
                    LA44_2 = self.input.LA(2)

                    if (self.synpred12_impera()) :
                        alt44 = 1
                    elif (True) :
                        alt44 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 44, 2, self.input)

                        raise nvae


                elif LA44 in {TRUE}:
                    LA44_3 = self.input.LA(2)

                    if (self.synpred12_impera()) :
                        alt44 = 1
                    elif (True) :
                        alt44 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 44, 3, self.input)

                        raise nvae


                elif LA44 in {FALSE}:
                    LA44_4 = self.input.LA(2)

                    if (self.synpred12_impera()) :
                        alt44 = 1
                    elif (True) :
                        alt44 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 44, 4, self.input)

                        raise nvae


                elif LA44 in {FLOAT, INT, ML_STRING, REGEX, STRING}:
                    LA44_5 = self.input.LA(2)

                    if (self.synpred12_impera()) :
                        alt44 = 1
                    elif (True) :
                        alt44 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 44, 5, self.input)

                        raise nvae


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 44, 0, self.input)

                    raise nvae


                if alt44 == 1:
                    # impera.g:253:4: ( log_oper log_op )=> log_oper log_op log_expr
                    pass 
                    self._state.following.append(self.FOLLOW_log_oper_in_log_expr1839)
                    log_oper177 = self.log_oper()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_log_oper.add(log_oper177.tree)


                    self._state.following.append(self.FOLLOW_log_op_in_log_expr1841)
                    log_op178 = self.log_op()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_log_op.add(log_op178.tree)


                    self._state.following.append(self.FOLLOW_log_expr_in_log_expr1843)
                    log_expr179 = self.log_expr()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_log_expr.add(log_expr179.tree)


                    # AST Rewrite
                    # elements: log_expr, log_op, log_oper
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 253:50: -> ^( OP log_op log_oper log_expr )
                        # impera.g:253:53: ^( OP log_op log_oper log_expr )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(OP, "OP")
                        , root_1)

                        self._adaptor.addChild(root_1, stream_log_op.nextTree())

                        self._adaptor.addChild(root_1, stream_log_oper.nextTree())

                        self._adaptor.addChild(root_1, stream_log_expr.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt44 == 2:
                    # impera.g:254:4: log_oper
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_log_oper_in_log_expr1860)
                    log_oper180 = self.log_oper()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, log_oper180.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "log_expr"


    class expression_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "expression"
    # impera.g:257:1: expression : ( '(' expression ')' ( log_op expression )? -> ^( OP ( log_op )? ( expression )+ ) | ( log_expr log_op )=> log_expr log_op '(' expression ')' -> ^( OP log_op log_expr expression ) | log_expr );
    def expression(self, ):
        retval = self.expression_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal181 = None
        char_literal183 = None
        char_literal188 = None
        char_literal190 = None
        expression182 = None
        log_op184 = None
        expression185 = None
        log_expr186 = None
        log_op187 = None
        expression189 = None
        log_expr191 = None

        char_literal181_tree = None
        char_literal183_tree = None
        char_literal188_tree = None
        char_literal190_tree = None
        stream_50 = RewriteRuleTokenStream(self._adaptor, "token 50")
        stream_51 = RewriteRuleTokenStream(self._adaptor, "token 51")
        stream_log_expr = RewriteRuleSubtreeStream(self._adaptor, "rule log_expr")
        stream_expression = RewriteRuleSubtreeStream(self._adaptor, "rule expression")
        stream_log_op = RewriteRuleSubtreeStream(self._adaptor, "rule log_op")
        try:
            try:
                # impera.g:258:2: ( '(' expression ')' ( log_op expression )? -> ^( OP ( log_op )? ( expression )+ ) | ( log_expr log_op )=> log_expr log_op '(' expression ')' -> ^( OP log_op log_expr expression ) | log_expr )
                alt46 = 3
                LA46 = self.input.LA(1)
                if LA46 in {50}:
                    alt46 = 1
                elif LA46 in {ID}:
                    LA46_2 = self.input.LA(2)

                    if (self.synpred13_impera()) :
                        alt46 = 2
                    elif (True) :
                        alt46 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 46, 2, self.input)

                        raise nvae


                elif LA46 in {CLASS_ID}:
                    LA46_3 = self.input.LA(2)

                    if (self.synpred13_impera()) :
                        alt46 = 2
                    elif (True) :
                        alt46 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 46, 3, self.input)

                        raise nvae


                elif LA46 in {TRUE}:
                    LA46_4 = self.input.LA(2)

                    if (self.synpred13_impera()) :
                        alt46 = 2
                    elif (True) :
                        alt46 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 46, 4, self.input)

                        raise nvae


                elif LA46 in {FALSE}:
                    LA46_5 = self.input.LA(2)

                    if (self.synpred13_impera()) :
                        alt46 = 2
                    elif (True) :
                        alt46 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 46, 5, self.input)

                        raise nvae


                elif LA46 in {FLOAT, INT, ML_STRING, REGEX, STRING}:
                    LA46_6 = self.input.LA(2)

                    if (self.synpred13_impera()) :
                        alt46 = 2
                    elif (True) :
                        alt46 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 46, 6, self.input)

                        raise nvae


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 46, 0, self.input)

                    raise nvae


                if alt46 == 1:
                    # impera.g:258:4: '(' expression ')' ( log_op expression )?
                    pass 
                    char_literal181 = self.match(self.input, 50, self.FOLLOW_50_in_expression1872) 
                    if self._state.backtracking == 0:
                        stream_50.add(char_literal181)


                    self._state.following.append(self.FOLLOW_expression_in_expression1874)
                    expression182 = self.expression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_expression.add(expression182.tree)


                    char_literal183 = self.match(self.input, 51, self.FOLLOW_51_in_expression1876) 
                    if self._state.backtracking == 0:
                        stream_51.add(char_literal183)


                    # impera.g:258:23: ( log_op expression )?
                    alt45 = 2
                    LA45_0 = self.input.LA(1)

                    if (LA45_0 == 67 or LA45_0 == 80) :
                        alt45 = 1
                    if alt45 == 1:
                        # impera.g:258:24: log_op expression
                        pass 
                        self._state.following.append(self.FOLLOW_log_op_in_expression1879)
                        log_op184 = self.log_op()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_log_op.add(log_op184.tree)


                        self._state.following.append(self.FOLLOW_expression_in_expression1881)
                        expression185 = self.expression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_expression.add(expression185.tree)





                    # AST Rewrite
                    # elements: log_op, expression
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 258:44: -> ^( OP ( log_op )? ( expression )+ )
                        # impera.g:258:47: ^( OP ( log_op )? ( expression )+ )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(OP, "OP")
                        , root_1)

                        # impera.g:258:52: ( log_op )?
                        if stream_log_op.hasNext():
                            self._adaptor.addChild(root_1, stream_log_op.nextTree())


                        stream_log_op.reset();

                        # impera.g:258:60: ( expression )+
                        if not (stream_expression.hasNext()):
                            raise RewriteEarlyExitException()

                        while stream_expression.hasNext():
                            self._adaptor.addChild(root_1, stream_expression.nextTree())


                        stream_expression.reset()

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt46 == 2:
                    # impera.g:259:4: ( log_expr log_op )=> log_expr log_op '(' expression ')'
                    pass 
                    self._state.following.append(self.FOLLOW_log_expr_in_expression1908)
                    log_expr186 = self.log_expr()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_log_expr.add(log_expr186.tree)


                    self._state.following.append(self.FOLLOW_log_op_in_expression1910)
                    log_op187 = self.log_op()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_log_op.add(log_op187.tree)


                    char_literal188 = self.match(self.input, 50, self.FOLLOW_50_in_expression1912) 
                    if self._state.backtracking == 0:
                        stream_50.add(char_literal188)


                    self._state.following.append(self.FOLLOW_expression_in_expression1914)
                    expression189 = self.expression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_expression.add(expression189.tree)


                    char_literal190 = self.match(self.input, 51, self.FOLLOW_51_in_expression1916) 
                    if self._state.backtracking == 0:
                        stream_51.add(char_literal190)


                    # AST Rewrite
                    # elements: expression, log_op, log_expr
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:
                        retval.tree = root_0
                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 259:60: -> ^( OP log_op log_expr expression )
                        # impera.g:259:63: ^( OP log_op log_expr expression )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(OP, "OP")
                        , root_1)

                        self._adaptor.addChild(root_1, stream_log_op.nextTree())

                        self._adaptor.addChild(root_1, stream_log_expr.nextTree())

                        self._adaptor.addChild(root_1, stream_expression.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt46 == 3:
                    # impera.g:260:4: log_expr
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_log_expr_in_expression1933)
                    log_expr191 = self.log_expr()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, log_expr191.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



                       
            except RecognitionException as re:
            	raise re

        finally:
            pass
        return retval

    # $ANTLR end "expression"

    # $ANTLR start "synpred1_impera"
    def synpred1_impera_fragment(self, ):
        # impera.g:60:4: ( class_ref '(' )
        # impera.g:60:5: class_ref '('
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_class_ref_in_synpred1_impera284)
        self.class_ref()

        self._state.following.pop()


        self.match(self.input, 50, self.FOLLOW_50_in_synpred1_impera286)




    # $ANTLR end "synpred1_impera"



    # $ANTLR start "synpred2_impera"
    def synpred2_impera_fragment(self, ):
        # impera.g:67:4: ( 'for' )
        # impera.g:67:5: 'for'
        pass 
        root_0 = self._adaptor.nil()


        self.match(self.input, 72, self.FOLLOW_72_in_synpred2_impera326)




    # $ANTLR end "synpred2_impera"



    # $ANTLR start "synpred3_impera"
    def synpred3_impera_fragment(self, ):
        # impera.g:69:4: ( class_ref '(' )
        # impera.g:69:5: class_ref '('
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_class_ref_in_synpred3_impera387)
        self.class_ref()

        self._state.following.pop()


        self.match(self.input, 50, self.FOLLOW_50_in_synpred3_impera389)




    # $ANTLR end "synpred3_impera"



    # $ANTLR start "synpred4_impera"
    def synpred4_impera_fragment(self, ):
        # impera.g:121:4: ( INT )
        # impera.g:121:5: INT
        pass 
        root_0 = self._adaptor.nil()


        self.match(self.input, INT, self.FOLLOW_INT_in_synpred4_impera799)




    # $ANTLR end "synpred4_impera"



    # $ANTLR start "synpred5_impera"
    def synpred5_impera_fragment(self, ):
        # impera.g:122:4: ( INT ':' )
        # impera.g:122:5: INT ':'
        pass 
        root_0 = self._adaptor.nil()


        self.match(self.input, INT, self.FOLLOW_INT_in_synpred5_impera818)


        self.match(self.input, 56, self.FOLLOW_56_in_synpred5_impera820)




    # $ANTLR end "synpred5_impera"



    # $ANTLR start "synpred6_impera"
    def synpred6_impera_fragment(self, ):
        # impera.g:123:4: ( INT ':' INT )
        # impera.g:123:5: INT ':' INT
        pass 
        root_0 = self._adaptor.nil()


        self.match(self.input, INT, self.FOLLOW_INT_in_synpred6_impera843)


        self.match(self.input, 56, self.FOLLOW_56_in_synpred6_impera845)


        self.match(self.input, INT, self.FOLLOW_INT_in_synpred6_impera847)




    # $ANTLR end "synpred6_impera"



    # $ANTLR start "synpred7_impera"
    def synpred7_impera_fragment(self, ):
        # impera.g:124:4: ( ':' INT )
        # impera.g:124:5: ':' INT
        pass 
        root_0 = self._adaptor.nil()


        self.match(self.input, 56, self.FOLLOW_56_in_synpred7_impera872)


        self.match(self.input, INT, self.FOLLOW_INT_in_synpred7_impera874)




    # $ANTLR end "synpred7_impera"



    # $ANTLR start "synpred8_impera"
    def synpred8_impera_fragment(self, ):
        # impera.g:149:4: ( ns_ref '(' )
        # impera.g:149:5: ns_ref '('
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_ns_ref_in_synpred8_impera1040)
        self.ns_ref()

        self._state.following.pop()


        self.match(self.input, 50, self.FOLLOW_50_in_synpred8_impera1042)




    # $ANTLR end "synpred8_impera"



    # $ANTLR start "synpred9_impera"
    def synpred9_impera_fragment(self, ):
        # impera.g:153:4: ( '{' )
        # impera.g:153:5: '{'
        pass 
        root_0 = self._adaptor.nil()


        self.match(self.input, 84, self.FOLLOW_84_in_synpred9_impera1068)




    # $ANTLR end "synpred9_impera"



    # $ANTLR start "synpred10_impera"
    def synpred10_impera_fragment(self, ):
        # impera.g:234:4: ( cmp_oper 'in' )
        # impera.g:234:5: cmp_oper 'in'
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_cmp_oper_in_synpred10_impera1701)
        self.cmp_oper()

        self._state.following.pop()


        self.match(self.input, 75, self.FOLLOW_75_in_synpred10_impera1703)




    # $ANTLR end "synpred10_impera"



    # $ANTLR start "synpred11_impera"
    def synpred11_impera_fragment(self, ):
        # impera.g:235:4: ( cmp_oper cmp_op )
        # impera.g:235:5: cmp_oper cmp_op
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_cmp_oper_in_synpred11_impera1730)
        self.cmp_oper()

        self._state.following.pop()


        self._state.following.append(self.FOLLOW_cmp_op_in_synpred11_impera1732)
        self.cmp_op()

        self._state.following.pop()




    # $ANTLR end "synpred11_impera"



    # $ANTLR start "synpred12_impera"
    def synpred12_impera_fragment(self, ):
        # impera.g:253:4: ( log_oper log_op )
        # impera.g:253:5: log_oper log_op
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_log_oper_in_synpred12_impera1832)
        self.log_oper()

        self._state.following.pop()


        self._state.following.append(self.FOLLOW_log_op_in_synpred12_impera1834)
        self.log_op()

        self._state.following.pop()




    # $ANTLR end "synpred12_impera"



    # $ANTLR start "synpred13_impera"
    def synpred13_impera_fragment(self, ):
        # impera.g:259:4: ( log_expr log_op )
        # impera.g:259:5: log_expr log_op
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_log_expr_in_synpred13_impera1901)
        self.log_expr()

        self._state.following.pop()


        self._state.following.append(self.FOLLOW_log_op_in_synpred13_impera1903)
        self.log_op()

        self._state.following.pop()




    # $ANTLR end "synpred13_impera"




    def synpred7_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred7_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred8_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred8_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred13_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred13_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred4_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred4_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred12_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred12_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred10_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred10_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred11_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred11_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred2_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred2_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred9_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred9_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred5_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred5_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred6_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred6_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred1_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred1_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success

    def synpred3_impera(self):
        self._state.backtracking += 1
        start = self.input.mark()
        try:
            self.synpred3_impera_fragment()
        except BacktrackingFailed:
            success = False
        else:
            success = True
        self.input.rewind(start)
        self._state.backtracking -= 1
        return success



    # lookup tables for DFA #1

    DFA1_eot = DFA.unpack(
        "\11\uffff"
        )

    DFA1_eof = DFA.unpack(
        "\1\1\10\uffff"
        )

    DFA1_min = DFA.unpack(
        "\1\10\2\uffff\1\62\1\33\2\uffff\1\10\1\62"
        )

    DFA1_max = DFA.unpack(
        "\1\121\2\uffff\2\125\2\uffff\1\33\1\125"
        )

    DFA1_accept = DFA.unpack(
        "\1\uffff\1\4\1\1\2\uffff\1\2\1\3\2\uffff"
        )

    DFA1_special = DFA.unpack(
        "\11\uffff"
        )


    DFA1_transition = [
        DFA.unpack("\1\4\22\uffff\1\3\6\uffff\1\6\43\uffff\1\2\1\uffff\1"
        "\5\2\2\1\uffff\1\5\1\2\3\uffff\1\2"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\5\4\uffff\1\5\1\uffff\1\7\3\uffff\1\5\27\uffff\1"
        "\5"),
        DFA.unpack("\1\2\26\uffff\1\5\42\uffff\1\5"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\4\22\uffff\1\10"),
        DFA.unpack("\1\5\4\uffff\1\5\1\uffff\1\7\3\uffff\1\5\27\uffff\1"
        "\5")
    ]

    # class definition for DFA #1

    class DFA1(DFA):
        pass


    # lookup tables for DFA #4

    DFA4_eot = DFA.unpack(
        "\7\uffff"
        )

    DFA4_eof = DFA.unpack(
        "\1\uffff\2\3\3\uffff\1\3"
        )

    DFA4_min = DFA.unpack(
        "\3\10\1\uffff\1\10\1\uffff\1\10"
        )

    DFA4_max = DFA.unpack(
        "\1\124\2\125\1\uffff\1\33\1\uffff\1\125"
        )

    DFA4_accept = DFA.unpack(
        "\3\uffff\1\2\1\uffff\1\1\1\uffff"
        )

    DFA4_special = DFA.unpack(
        "\2\uffff\1\0\4\uffff"
        )


    DFA4_transition = [
        DFA.unpack("\1\2\15\uffff\2\3\3\uffff\1\1\2\uffff\1\3\3\uffff\1\3"
        "\7\uffff\1\3\1\uffff\2\3\23\uffff\1\3\22\uffff\1\3"),
        DFA.unpack("\1\3\22\uffff\1\3\6\uffff\1\3\17\uffff\1\3\4\uffff\1"
        "\3\1\uffff\1\4\13\uffff\2\3\1\uffff\3\3\1\uffff\2\3\3\uffff\1\3"
        "\3\uffff\1\3"),
        DFA.unpack("\1\3\22\uffff\1\3\6\uffff\1\3\17\uffff\1\5\16\uffff"
        "\1\3\3\uffff\2\3\1\uffff\3\3\1\uffff\2\3\3\uffff\1\3\3\uffff\1\3"),
        DFA.unpack(""),
        DFA.unpack("\1\2\22\uffff\1\6"),
        DFA.unpack(""),
        DFA.unpack("\1\3\22\uffff\1\3\6\uffff\1\3\17\uffff\1\3\4\uffff\1"
        "\3\1\uffff\1\4\13\uffff\2\3\1\uffff\3\3\1\uffff\2\3\3\uffff\1\3"
        "\3\uffff\1\3")
    ]

    # class definition for DFA #4

    class DFA4(DFA):
        pass


        def specialStateTransition(self_, s, input):
            # convince pylint that my self_ magic is ok ;)
            # pylint: disable-msg=E0213

            # pretend we are a member of the recognizer
            # thus semantic predicates can be evaluated
            self = self_.recognizer

            _s = s

            if s == 0: 
                LA4_2 = input.LA(1)

                 
                index4_2 = input.index()
                input.rewind()

                s = -1
                if (LA4_2 == 50) and (self.synpred1_impera()):
                    s = 5

                elif (LA4_2 == EOF or LA4_2 == CLASS_ID or LA4_2 == ID or LA4_2 == ML_STRING or LA4_2 == 65 or (69 <= LA4_2 <= 70) or (72 <= LA4_2 <= 74) or (76 <= LA4_2 <= 77) or LA4_2 == 81 or LA4_2 == 85):
                    s = 3

                 
                input.seek(index4_2)

                if s >= 0:
                    return s

            if self._state.backtracking > 0:
                raise BacktrackingFailed

            nvae = NoViableAltException(self_.getDescription(), 4, _s, input)
            self_.error(nvae)
            raise nvae

    # lookup tables for DFA #6

    DFA6_eot = DFA.unpack(
        "\15\uffff"
        )

    DFA6_eof = DFA.unpack(
        "\15\uffff"
        )

    DFA6_min = DFA.unpack(
        "\1\10\2\uffff\2\62\1\10\1\33\4\uffff\1\62\1\67"
        )

    DFA6_max = DFA.unpack(
        "\1\114\2\uffff\2\125\2\33\4\uffff\2\125"
        )

    DFA6_accept = DFA.unpack(
        "\1\uffff\1\1\1\2\4\uffff\1\3\1\5\1\6\1\4\2\uffff"
        )

    DFA6_special = DFA.unpack(
        "\1\1\3\uffff\1\0\10\uffff"
        )


    DFA6_transition = [
        DFA.unpack("\1\4\22\uffff\1\3\54\uffff\1\2\3\uffff\1\1"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\10\4\uffff\1\6\1\uffff\1\5\3\uffff\1\7\27\uffff\1"
        "\11"),
        DFA.unpack("\1\12\42\uffff\1\11"),
        DFA.unpack("\1\4\22\uffff\1\13"),
        DFA.unpack("\1\14"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\10\4\uffff\1\6\1\uffff\1\5\3\uffff\1\7\27\uffff\1"
        "\11"),
        DFA.unpack("\1\6\5\uffff\1\7\27\uffff\1\11")
    ]

    # class definition for DFA #6

    class DFA6(DFA):
        pass


        def specialStateTransition(self_, s, input):
            # convince pylint that my self_ magic is ok ;)
            # pylint: disable-msg=E0213

            # pretend we are a member of the recognizer
            # thus semantic predicates can be evaluated
            self = self_.recognizer

            _s = s

            if s == 0: 
                LA6_4 = input.LA(1)

                 
                index6_4 = input.index()
                input.rewind()

                s = -1
                if (LA6_4 == 50) and (self.synpred3_impera()):
                    s = 10

                elif (LA6_4 == 85):
                    s = 9

                 
                input.seek(index6_4)

                if s >= 0:
                    return s
            elif s == 1: 
                LA6_0 = input.LA(1)

                 
                index6_0 = input.index()
                input.rewind()

                s = -1
                if (LA6_0 == 76):
                    s = 1

                elif (LA6_0 == 72) and (self.synpred2_impera()):
                    s = 2

                elif (LA6_0 == ID):
                    s = 3

                elif (LA6_0 == CLASS_ID):
                    s = 4

                 
                input.seek(index6_0)

                if s >= 0:
                    return s

            if self._state.backtracking > 0:
                raise BacktrackingFailed

            nvae = NoViableAltException(self_.getDescription(), 6, _s, input)
            self_.error(nvae)
            raise nvae

    # lookup tables for DFA #5

    DFA5_eot = DFA.unpack(
        "\5\uffff"
        )

    DFA5_eof = DFA.unpack(
        "\5\uffff"
        )

    DFA5_min = DFA.unpack(
        "\1\10\1\67\1\uffff\1\10\1\uffff"
        )

    DFA5_max = DFA.unpack(
        "\1\33\1\71\1\uffff\1\33\1\uffff"
        )

    DFA5_accept = DFA.unpack(
        "\2\uffff\1\2\1\uffff\1\1"
        )

    DFA5_special = DFA.unpack(
        "\5\uffff"
        )


    DFA5_transition = [
        DFA.unpack("\1\2\22\uffff\1\1"),
        DFA.unpack("\2\4\1\3"),
        DFA.unpack(""),
        DFA.unpack("\1\2\22\uffff\1\1"),
        DFA.unpack("")
    ]

    # class definition for DFA #5

    class DFA5(DFA):
        pass


    # lookup tables for DFA #8

    DFA8_eot = DFA.unpack(
        "\10\uffff"
        )

    DFA8_eof = DFA.unpack(
        "\10\uffff"
        )

    DFA8_min = DFA.unpack(
        "\1\10\2\62\1\10\3\uffff\1\62"
        )

    DFA8_max = DFA.unpack(
        "\1\33\2\125\1\33\3\uffff\1\125"
        )

    DFA8_accept = DFA.unpack(
        "\4\uffff\1\1\1\2\1\3\1\uffff"
        )

    DFA8_special = DFA.unpack(
        "\10\uffff"
        )


    DFA8_transition = [
        DFA.unpack("\1\2\22\uffff\1\1"),
        DFA.unpack("\1\4\4\uffff\1\5\1\uffff\1\3\33\uffff\1\5"),
        DFA.unpack("\1\6\42\uffff\1\5"),
        DFA.unpack("\1\2\22\uffff\1\7"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\4\4\uffff\1\5\1\uffff\1\3\33\uffff\1\5")
    ]

    # class definition for DFA #8

    class DFA8(DFA):
        pass


    # lookup tables for DFA #20

    DFA20_eot = DFA.unpack(
        "\17\uffff"
        )

    DFA20_eof = DFA.unpack(
        "\3\uffff\1\11\1\14\10\uffff\2\11"
        )

    DFA20_min = DFA.unpack(
        "\1\10\2\uffff\2\10\1\uffff\1\10\1\uffff\1\33\4\uffff\2\10"
        )

    DFA20_max = DFA.unpack(
        "\1\124\2\uffff\2\125\1\uffff\1\33\1\uffff\1\33\4\uffff\2\125"
        )

    DFA20_accept = DFA.unpack(
        "\1\uffff\1\1\1\2\2\uffff\1\10\1\uffff\1\4\1\uffff\1\6\1\7\1\3\1"
        "\5\2\uffff"
        )

    DFA20_special = DFA.unpack(
        "\1\0\2\uffff\1\1\11\uffff\1\2\1\uffff"
        )


    DFA20_transition = [
        DFA.unpack("\1\4\15\uffff\2\1\3\uffff\1\3\2\uffff\1\1\3\uffff\1\1"
        "\7\uffff\1\1\1\uffff\2\1\23\uffff\1\2\22\uffff\1\5"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\11\22\uffff\1\11\6\uffff\1\11\17\uffff\1\7\2\11\2"
        "\uffff\1\10\1\uffff\1\6\10\uffff\1\11\2\uffff\2\11\1\uffff\3\11"
        "\1\uffff\2\11\3\uffff\1\11\3\uffff\1\12"),
        DFA.unpack("\1\14\22\uffff\1\14\6\uffff\1\14\20\uffff\2\14\14\uffff"
        "\1\13\1\14\2\uffff\2\14\1\uffff\3\14\1\uffff\2\14\3\uffff\1\14\3"
        "\uffff\1\12"),
        DFA.unpack(""),
        DFA.unpack("\1\4\22\uffff\1\15"),
        DFA.unpack(""),
        DFA.unpack("\1\16"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\11\22\uffff\1\11\6\uffff\1\11\17\uffff\1\7\2\11\2"
        "\uffff\1\10\1\uffff\1\6\10\uffff\1\11\2\uffff\2\11\1\uffff\3\11"
        "\1\uffff\2\11\3\uffff\1\11\3\uffff\1\12"),
        DFA.unpack("\1\11\22\uffff\1\11\6\uffff\1\11\20\uffff\2\11\2\uffff"
        "\1\10\12\uffff\1\11\2\uffff\2\11\1\uffff\3\11\1\uffff\2\11\3\uffff"
        "\1\11\3\uffff\1\12")
    ]

    # class definition for DFA #20

    class DFA20(DFA):
        pass


        def specialStateTransition(self_, s, input):
            # convince pylint that my self_ magic is ok ;)
            # pylint: disable-msg=E0213

            # pretend we are a member of the recognizer
            # thus semantic predicates can be evaluated
            self = self_.recognizer

            _s = s

            if s == 0: 
                LA20_0 = input.LA(1)

                 
                index20_0 = input.index()
                input.rewind()

                s = -1
                if ((FALSE <= LA20_0 <= FLOAT) or LA20_0 == INT or LA20_0 == ML_STRING or LA20_0 == REGEX or (STRING <= LA20_0 <= TRUE)):
                    s = 1

                elif (LA20_0 == 65):
                    s = 2

                elif (LA20_0 == ID):
                    s = 3

                elif (LA20_0 == CLASS_ID):
                    s = 4

                elif (LA20_0 == 84) and (self.synpred9_impera()):
                    s = 5

                 
                input.seek(index20_0)

                if s >= 0:
                    return s
            elif s == 1: 
                LA20_3 = input.LA(1)

                 
                index20_3 = input.index()
                input.rewind()

                s = -1
                if (LA20_3 == 57):
                    s = 6

                elif (LA20_3 == 50) and (self.synpred8_impera()):
                    s = 7

                elif (LA20_3 == 55):
                    s = 8

                elif (LA20_3 == EOF or LA20_3 == CLASS_ID or LA20_3 == ID or LA20_3 == ML_STRING or (51 <= LA20_3 <= 52) or LA20_3 == 66 or (69 <= LA20_3 <= 70) or (72 <= LA20_3 <= 74) or (76 <= LA20_3 <= 77) or LA20_3 == 81):
                    s = 9

                elif (LA20_3 == 85):
                    s = 10

                 
                input.seek(index20_3)

                if s >= 0:
                    return s
            elif s == 2: 
                LA20_13 = input.LA(1)

                 
                index20_13 = input.index()
                input.rewind()

                s = -1
                if (LA20_13 == 57):
                    s = 6

                elif (LA20_13 == 50) and (self.synpred8_impera()):
                    s = 7

                elif (LA20_13 == 55):
                    s = 8

                elif (LA20_13 == EOF or LA20_13 == CLASS_ID or LA20_13 == ID or LA20_13 == ML_STRING or (51 <= LA20_13 <= 52) or LA20_13 == 66 or (69 <= LA20_13 <= 70) or (72 <= LA20_13 <= 74) or (76 <= LA20_13 <= 77) or LA20_13 == 81):
                    s = 9

                elif (LA20_13 == 85):
                    s = 10

                 
                input.seek(index20_13)

                if s >= 0:
                    return s

            if self._state.backtracking > 0:
                raise BacktrackingFailed

            nvae = NoViableAltException(self_.getDescription(), 20, _s, input)
            self_.error(nvae)
            raise nvae

    # lookup tables for DFA #27

    DFA27_eot = DFA.unpack(
        "\6\uffff"
        )

    DFA27_eof = DFA.unpack(
        "\6\uffff"
        )

    DFA27_min = DFA.unpack(
        "\1\10\1\33\1\uffff\1\10\1\uffff\1\33"
        )

    DFA27_max = DFA.unpack(
        "\1\33\1\71\1\uffff\1\33\1\uffff\1\71"
        )

    DFA27_accept = DFA.unpack(
        "\2\uffff\1\2\1\uffff\1\1\1\uffff"
        )

    DFA27_special = DFA.unpack(
        "\6\uffff"
        )


    DFA27_transition = [
        DFA.unpack("\1\2\22\uffff\1\1"),
        DFA.unpack("\1\4\35\uffff\1\3"),
        DFA.unpack(""),
        DFA.unpack("\1\2\22\uffff\1\5"),
        DFA.unpack(""),
        DFA.unpack("\1\4\35\uffff\1\3")
    ]

    # class definition for DFA #27

    class DFA27(DFA):
        pass


    # lookup tables for DFA #38

    DFA38_eot = DFA.unpack(
        "\5\uffff"
        )

    DFA38_eof = DFA.unpack(
        "\5\uffff"
        )

    DFA38_min = DFA.unpack(
        "\1\10\1\67\1\uffff\1\10\1\uffff"
        )

    DFA38_max = DFA.unpack(
        "\1\33\1\125\1\uffff\1\33\1\uffff"
        )

    DFA38_accept = DFA.unpack(
        "\2\uffff\1\1\1\uffff\1\2"
        )

    DFA38_special = DFA.unpack(
        "\5\uffff"
        )


    DFA38_transition = [
        DFA.unpack("\1\2\22\uffff\1\1"),
        DFA.unpack("\1\4\1\uffff\1\3\33\uffff\1\4"),
        DFA.unpack(""),
        DFA.unpack("\1\2\22\uffff\1\1"),
        DFA.unpack("")
    ]

    # class definition for DFA #38

    class DFA38(DFA):
        pass


    # lookup tables for DFA #40

    DFA40_eot = DFA.unpack(
        "\15\uffff"
        )

    DFA40_eof = DFA.unpack(
        "\1\uffff\1\6\1\12\10\uffff\2\6"
        )

    DFA40_min = DFA.unpack(
        "\3\10\1\uffff\1\10\1\33\5\uffff\2\10"
        )

    DFA40_max = DFA.unpack(
        "\1\55\2\126\1\uffff\2\33\5\uffff\2\126"
        )

    DFA40_accept = DFA.unpack(
        "\3\uffff\1\5\2\uffff\1\1\1\2\1\3\1\4\1\6\2\uffff"
        )

    DFA40_special = DFA.unpack(
        "\15\uffff"
        )


    DFA40_transition = [
        DFA.unpack("\1\2\15\uffff\2\3\3\uffff\1\1\2\uffff\1\3\3\uffff\1\3"
        "\7\uffff\1\3\1\uffff\2\3"),
        DFA.unpack("\1\6\22\uffff\1\6\6\uffff\1\6\16\uffff\1\6\1\7\1\6\3"
        "\uffff\1\5\1\uffff\1\4\1\6\1\uffff\1\6\1\uffff\3\6\2\uffff\1\6\2"
        "\uffff\1\6\1\uffff\6\6\2\uffff\2\6\3\uffff\1\10\1\6"),
        DFA.unpack("\1\12\22\uffff\1\12\6\uffff\1\12\16\uffff\1\12\1\uffff"
        "\1\12\6\uffff\1\12\1\uffff\1\12\1\uffff\3\12\1\11\1\uffff\1\12\2"
        "\uffff\1\12\1\uffff\6\12\2\uffff\2\12\3\uffff\1\10\1\12"),
        DFA.unpack(""),
        DFA.unpack("\1\2\22\uffff\1\13"),
        DFA.unpack("\1\14"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\6\22\uffff\1\6\6\uffff\1\6\16\uffff\1\6\1\7\1\6\3"
        "\uffff\1\5\1\uffff\1\4\1\6\1\uffff\1\6\1\uffff\3\6\2\uffff\1\6\2"
        "\uffff\1\6\1\uffff\6\6\2\uffff\2\6\3\uffff\1\10\1\6"),
        DFA.unpack("\1\6\22\uffff\1\6\6\uffff\1\6\16\uffff\1\6\1\uffff\1"
        "\6\3\uffff\1\5\2\uffff\1\6\1\uffff\1\6\1\uffff\3\6\2\uffff\1\6\2"
        "\uffff\1\6\1\uffff\6\6\2\uffff\2\6\3\uffff\1\10\1\6")
    ]

    # class definition for DFA #40

    class DFA40(DFA):
        pass


 

    FOLLOW_def_statement_in_main172 = frozenset([1, 8, 27, 34, 70, 72, 73, 74, 76, 77, 81])
    FOLLOW_top_statement_in_main176 = frozenset([1, 8, 27, 34, 70, 72, 73, 74, 76, 77, 81])
    FOLLOW_ML_STRING_in_main180 = frozenset([1, 8, 27, 34, 70, 72, 73, 74, 76, 77, 81])
    FOLLOW_typedef_in_def_statement208 = frozenset([1])
    FOLLOW_entity_def_in_def_statement212 = frozenset([1])
    FOLLOW_implementation_def_in_def_statement216 = frozenset([1])
    FOLLOW_relation_in_def_statement220 = frozenset([1])
    FOLLOW_index_in_def_statement224 = frozenset([1])
    FOLLOW_implement_def_in_def_statement228 = frozenset([1])
    FOLLOW_77_in_index240 = frozenset([8, 27])
    FOLLOW_class_ref_in_index242 = frozenset([50])
    FOLLOW_50_in_index244 = frozenset([27])
    FOLLOW_ID_in_index246 = frozenset([51, 52])
    FOLLOW_52_in_index249 = frozenset([27])
    FOLLOW_ID_in_index251 = frozenset([51, 52])
    FOLLOW_51_in_index255 = frozenset([1])
    FOLLOW_anon_ctor_in_rhs291 = frozenset([1])
    FOLLOW_operand_in_rhs296 = frozenset([1])
    FOLLOW_76_in_top_statement309 = frozenset([27])
    FOLLOW_ns_ref_in_top_statement311 = frozenset([1])
    FOLLOW_72_in_top_statement331 = frozenset([27])
    FOLLOW_ID_in_top_statement333 = frozenset([75])
    FOLLOW_75_in_top_statement335 = frozenset([8, 27])
    FOLLOW_variable_in_top_statement338 = frozenset([56])
    FOLLOW_class_ref_in_top_statement342 = frozenset([56])
    FOLLOW_implementation_in_top_statement346 = frozenset([1])
    FOLLOW_variable_in_top_statement367 = frozenset([61])
    FOLLOW_61_in_top_statement369 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 65, 84])
    FOLLOW_rhs_in_top_statement371 = frozenset([1])
    FOLLOW_anon_ctor_in_top_statement394 = frozenset([1])
    FOLLOW_function_call_in_top_statement407 = frozenset([1])
    FOLLOW_method_call_in_top_statement412 = frozenset([1])
    FOLLOW_constructor_in_anon_ctor424 = frozenset([1, 56])
    FOLLOW_implementation_in_anon_ctor426 = frozenset([1])
    FOLLOW_constructor_in_lambda_ctor450 = frozenset([1])
    FOLLOW_ID_in_lambda_func470 = frozenset([85])
    FOLLOW_85_in_lambda_func472 = frozenset([8, 27])
    FOLLOW_function_call_in_lambda_func475 = frozenset([1])
    FOLLOW_method_call_in_lambda_func479 = frozenset([1])
    FOLLOW_lambda_ctor_in_lambda_func483 = frozenset([1])
    FOLLOW_74_in_implementation_def512 = frozenset([27])
    FOLLOW_ID_in_implementation_def514 = frozenset([56, 72])
    FOLLOW_72_in_implementation_def517 = frozenset([8, 27])
    FOLLOW_class_ref_in_implementation_def519 = frozenset([56])
    FOLLOW_implementation_in_implementation_def523 = frozenset([1])
    FOLLOW_73_in_implement_def548 = frozenset([8, 27])
    FOLLOW_class_ref_in_implement_def550 = frozenset([82])
    FOLLOW_82_in_implement_def552 = frozenset([27])
    FOLLOW_ns_ref_in_implement_def554 = frozenset([1, 52, 83])
    FOLLOW_52_in_implement_def557 = frozenset([27])
    FOLLOW_ns_ref_in_implement_def559 = frozenset([1, 52, 83])
    FOLLOW_83_in_implement_def564 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 50])
    FOLLOW_expression_in_implement_def566 = frozenset([1])
    FOLLOW_56_in_implementation598 = frozenset([8, 27, 34, 69, 72, 76])
    FOLLOW_ML_STRING_in_implementation600 = frozenset([8, 27, 69, 72, 76])
    FOLLOW_statement_in_implementation603 = frozenset([8, 27, 69, 72, 76])
    FOLLOW_69_in_implementation606 = frozenset([1])
    FOLLOW_top_statement_in_statement626 = frozenset([1])
    FOLLOW_ID_in_parameter646 = frozenset([61])
    FOLLOW_61_in_parameter648 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 65, 84])
    FOLLOW_operand_in_parameter650 = frozenset([1])
    FOLLOW_class_ref_in_constructor671 = frozenset([50])
    FOLLOW_50_in_constructor673 = frozenset([27, 51])
    FOLLOW_param_list_in_constructor675 = frozenset([51])
    FOLLOW_51_in_constructor678 = frozenset([1])
    FOLLOW_parameter_in_param_list703 = frozenset([1, 52])
    FOLLOW_52_in_param_list706 = frozenset([27])
    FOLLOW_parameter_in_param_list708 = frozenset([1, 52])
    FOLLOW_52_in_param_list712 = frozenset([1])
    FOLLOW_81_in_typedef733 = frozenset([27])
    FOLLOW_ID_in_typedef735 = frozenset([68])
    FOLLOW_68_in_typedef737 = frozenset([27])
    FOLLOW_ns_ref_in_typedef739 = frozenset([78])
    FOLLOW_78_in_typedef741 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 50])
    FOLLOW_REGEX_in_typedef744 = frozenset([1])
    FOLLOW_expression_in_typedef748 = frozenset([1])
    FOLLOW_81_in_typedef770 = frozenset([8])
    FOLLOW_CLASS_ID_in_typedef772 = frozenset([68])
    FOLLOW_68_in_typedef774 = frozenset([8, 27])
    FOLLOW_constructor_in_typedef776 = frozenset([1])
    FOLLOW_INT_in_multiplicity_body804 = frozenset([1])
    FOLLOW_INT_in_multiplicity_body825 = frozenset([56])
    FOLLOW_56_in_multiplicity_body827 = frozenset([1])
    FOLLOW_INT_in_multiplicity_body852 = frozenset([56])
    FOLLOW_56_in_multiplicity_body854 = frozenset([30])
    FOLLOW_INT_in_multiplicity_body856 = frozenset([1])
    FOLLOW_56_in_multiplicity_body879 = frozenset([30])
    FOLLOW_INT_in_multiplicity_body881 = frozenset([1])
    FOLLOW_65_in_multiplicity903 = frozenset([30, 56])
    FOLLOW_multiplicity_body_in_multiplicity905 = frozenset([66])
    FOLLOW_66_in_multiplicity907 = frozenset([1])
    FOLLOW_class_ref_in_relation_end922 = frozenset([27])
    FOLLOW_ID_in_relation_end924 = frozenset([1])
    FOLLOW_relation_end_in_relation965 = frozenset([65])
    FOLLOW_multiplicity_in_relation969 = frozenset([53, 54, 59])
    FOLLOW_relation_link_in_relation972 = frozenset([65])
    FOLLOW_multiplicity_in_relation977 = frozenset([8, 27])
    FOLLOW_relation_end_in_relation981 = frozenset([1])
    FOLLOW_constant_in_operand1024 = frozenset([1])
    FOLLOW_list_def_in_operand1029 = frozenset([1])
    FOLLOW_index_lookup_in_operand1034 = frozenset([1])
    FOLLOW_function_call_in_operand1047 = frozenset([1])
    FOLLOW_class_ref_in_operand1052 = frozenset([1])
    FOLLOW_variable_in_operand1057 = frozenset([1])
    FOLLOW_method_call_in_operand1062 = frozenset([1])
    FOLLOW_84_in_operand1073 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 50])
    FOLLOW_expression_in_operand1075 = frozenset([86])
    FOLLOW_86_in_operand1077 = frozenset([1])
    FOLLOW_65_in_list_def1143 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 65, 84])
    FOLLOW_operand_in_list_def1145 = frozenset([52, 66])
    FOLLOW_52_in_list_def1148 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 65, 84])
    FOLLOW_operand_in_list_def1150 = frozenset([52, 66])
    FOLLOW_52_in_list_def1154 = frozenset([66])
    FOLLOW_66_in_list_def1157 = frozenset([1])
    FOLLOW_param_list_in_index_arg1178 = frozenset([1])
    FOLLOW_class_ref_in_index_lookup1191 = frozenset([65])
    FOLLOW_65_in_index_lookup1193 = frozenset([27])
    FOLLOW_index_arg_in_index_lookup1195 = frozenset([66])
    FOLLOW_66_in_index_lookup1197 = frozenset([1])
    FOLLOW_70_in_entity_def1219 = frozenset([8])
    FOLLOW_CLASS_ID_in_entity_def1221 = frozenset([56, 71])
    FOLLOW_71_in_entity_def1224 = frozenset([8, 27])
    FOLLOW_class_ref_in_entity_def1226 = frozenset([52, 56])
    FOLLOW_52_in_entity_def1229 = frozenset([8, 27])
    FOLLOW_class_ref_in_entity_def1231 = frozenset([52, 56])
    FOLLOW_56_in_entity_def1238 = frozenset([8, 27, 34, 69])
    FOLLOW_ML_STRING_in_entity_def1240 = frozenset([8, 27, 69])
    FOLLOW_entity_body_in_entity_def1244 = frozenset([8, 27, 69])
    FOLLOW_69_in_entity_def1248 = frozenset([1])
    FOLLOW_ns_ref_in_type1290 = frozenset([1])
    FOLLOW_class_ref_in_type1294 = frozenset([1])
    FOLLOW_type_in_entity_body1305 = frozenset([27])
    FOLLOW_ID_in_entity_body1307 = frozenset([1, 61])
    FOLLOW_61_in_entity_body1310 = frozenset([22, 23, 30, 34, 42, 44, 45])
    FOLLOW_constant_in_entity_body1312 = frozenset([1])
    FOLLOW_ID_in_ns_ref1339 = frozenset([1, 57])
    FOLLOW_57_in_ns_ref1342 = frozenset([27])
    FOLLOW_ID_in_ns_ref1344 = frozenset([1, 57])
    FOLLOW_ID_in_class_ref1373 = frozenset([57])
    FOLLOW_57_in_class_ref1375 = frozenset([8, 27])
    FOLLOW_CLASS_ID_in_class_ref1379 = frozenset([1])
    FOLLOW_ID_in_variable1413 = frozenset([57])
    FOLLOW_57_in_variable1415 = frozenset([27])
    FOLLOW_ID_in_variable1421 = frozenset([1, 55])
    FOLLOW_55_in_variable1424 = frozenset([27])
    FOLLOW_ID_in_variable1428 = frozenset([1, 55])
    FOLLOW_operand_in_arg_list1467 = frozenset([1, 52])
    FOLLOW_52_in_arg_list1470 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 65, 84])
    FOLLOW_operand_in_arg_list1472 = frozenset([1, 52])
    FOLLOW_52_in_arg_list1476 = frozenset([1])
    FOLLOW_ns_ref_in_function_call1498 = frozenset([50])
    FOLLOW_50_in_function_call1500 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 51, 65, 84])
    FOLLOW_call_arg_in_function_call1502 = frozenset([51])
    FOLLOW_51_in_function_call1505 = frozenset([1])
    FOLLOW_arg_list_in_call_arg1533 = frozenset([1])
    FOLLOW_85_in_method_pipe1544 = frozenset([27])
    FOLLOW_ns_ref_in_method_pipe1546 = frozenset([1, 50])
    FOLLOW_50_in_method_pipe1549 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 51, 65, 84])
    FOLLOW_call_arg_in_method_pipe1551 = frozenset([51])
    FOLLOW_51_in_method_pipe1554 = frozenset([1])
    FOLLOW_class_ref_in_method_call1583 = frozenset([85])
    FOLLOW_variable_in_method_call1589 = frozenset([85])
    FOLLOW_method_pipe_in_method_call1593 = frozenset([1, 85])
    FOLLOW_79_in_un_op1623 = frozenset([1])
    FOLLOW_variable_in_cmp_oper1667 = frozenset([1])
    FOLLOW_function_call_in_cmp_oper1671 = frozenset([1])
    FOLLOW_method_call_in_cmp_oper1675 = frozenset([1])
    FOLLOW_index_lookup_in_cmp_oper1679 = frozenset([1])
    FOLLOW_constant_in_cmp_oper1683 = frozenset([1])
    FOLLOW_class_ref_in_cmp_oper1687 = frozenset([1])
    FOLLOW_cmp_oper_in_cmp1708 = frozenset([75])
    FOLLOW_75_in_cmp1710 = frozenset([27, 65])
    FOLLOW_in_oper_in_cmp1712 = frozenset([1])
    FOLLOW_cmp_oper_in_cmp1737 = frozenset([49, 58, 60, 62, 63, 64])
    FOLLOW_cmp_op_in_cmp1739 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45])
    FOLLOW_cmp_oper_in_cmp1741 = frozenset([1])
    FOLLOW_function_call_in_cmp1757 = frozenset([1])
    FOLLOW_list_def_in_in_oper1793 = frozenset([1])
    FOLLOW_variable_in_in_oper1797 = frozenset([1])
    FOLLOW_cmp_in_log_oper1810 = frozenset([1])
    FOLLOW_TRUE_in_log_oper1814 = frozenset([1])
    FOLLOW_FALSE_in_log_oper1818 = frozenset([1])
    FOLLOW_log_oper_in_log_expr1839 = frozenset([67, 80])
    FOLLOW_log_op_in_log_expr1841 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45])
    FOLLOW_log_expr_in_log_expr1843 = frozenset([1])
    FOLLOW_log_oper_in_log_expr1860 = frozenset([1])
    FOLLOW_50_in_expression1872 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 50])
    FOLLOW_expression_in_expression1874 = frozenset([51])
    FOLLOW_51_in_expression1876 = frozenset([1, 67, 80])
    FOLLOW_log_op_in_expression1879 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 50])
    FOLLOW_expression_in_expression1881 = frozenset([1])
    FOLLOW_log_expr_in_expression1908 = frozenset([67, 80])
    FOLLOW_log_op_in_expression1910 = frozenset([50])
    FOLLOW_50_in_expression1912 = frozenset([8, 22, 23, 27, 30, 34, 42, 44, 45, 50])
    FOLLOW_expression_in_expression1914 = frozenset([51])
    FOLLOW_51_in_expression1916 = frozenset([1])
    FOLLOW_log_expr_in_expression1933 = frozenset([1])
    FOLLOW_class_ref_in_synpred1_impera284 = frozenset([50])
    FOLLOW_50_in_synpred1_impera286 = frozenset([1])
    FOLLOW_72_in_synpred2_impera326 = frozenset([1])
    FOLLOW_class_ref_in_synpred3_impera387 = frozenset([50])
    FOLLOW_50_in_synpred3_impera389 = frozenset([1])
    FOLLOW_INT_in_synpred4_impera799 = frozenset([1])
    FOLLOW_INT_in_synpred5_impera818 = frozenset([56])
    FOLLOW_56_in_synpred5_impera820 = frozenset([1])
    FOLLOW_INT_in_synpred6_impera843 = frozenset([56])
    FOLLOW_56_in_synpred6_impera845 = frozenset([30])
    FOLLOW_INT_in_synpred6_impera847 = frozenset([1])
    FOLLOW_56_in_synpred7_impera872 = frozenset([30])
    FOLLOW_INT_in_synpred7_impera874 = frozenset([1])
    FOLLOW_ns_ref_in_synpred8_impera1040 = frozenset([50])
    FOLLOW_50_in_synpred8_impera1042 = frozenset([1])
    FOLLOW_84_in_synpred9_impera1068 = frozenset([1])
    FOLLOW_cmp_oper_in_synpred10_impera1701 = frozenset([75])
    FOLLOW_75_in_synpred10_impera1703 = frozenset([1])
    FOLLOW_cmp_oper_in_synpred11_impera1730 = frozenset([49, 58, 60, 62, 63, 64])
    FOLLOW_cmp_op_in_synpred11_impera1732 = frozenset([1])
    FOLLOW_log_oper_in_synpred12_impera1832 = frozenset([67, 80])
    FOLLOW_log_op_in_synpred12_impera1834 = frozenset([1])
    FOLLOW_log_expr_in_synpred13_impera1901 = frozenset([67, 80])
    FOLLOW_log_op_in_synpred13_impera1903 = frozenset([1])



def main(argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    from antlr3.main import ParserMain
    main = ParserMain("imperaLexer", imperaParser)

    main.stdin = stdin
    main.stdout = stdout
    main.stderr = stderr
    main.execute(argv)



if __name__ == '__main__':
    main(sys.argv)
