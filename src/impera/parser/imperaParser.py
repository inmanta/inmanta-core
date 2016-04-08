# @PydevCodeAnalysisIgnore
# $ANTLR 3.5.2 impera.g 2016-04-08 15:45:48

import sys
from antlr3 import *

from antlr3.tree import *




# for convenience in actions
HIDDEN = BaseRecognizer.HIDDEN

# token types
EOF=-1
T__46=46
T__47=47
T__48=48
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
ASSIGN=4
ATTR=5
CALL=6
CLASS_ID=7
CLASS_REF=8
COMMENT=9
CONSTRUCT=10
DEF_DEFAULT=11
DEF_ENTITY=12
DEF_IMPLEMENT=13
DEF_IMPLEMENTATION=14
DEF_RELATION=15
DEF_TYPE=16
ENUM=17
ESC_SEQ=18
EXPONENT=19
FALSE=20
FLOAT=21
FOR=22
HASH=23
HEX_DIGIT=24
ID=25
INCLUDE=26
INDEX=27
INT=28
LAMBDA=29
LIST=30
ML_STRING=31
MULT=32
NONE=33
NS=34
OCTAL_ESC=35
OP=36
ORPHAN=37
REF=38
REGEX=39
STATEMENT=40
STRING=41
TRUE=42
UNICODE_ESC=43
VAR_REF=44
WS=45

# token names
tokenNamesMap = {
    0: "<invalid>", 1: "<EOR>", 2: "<DOWN>", 3: "<UP>",
    -1: "EOF", 46: "T__46", 47: "T__47", 48: "T__48", 49: "T__49", 50: "T__50", 
    51: "T__51", 52: "T__52", 53: "T__53", 54: "T__54", 55: "T__55", 56: "T__56", 
    57: "T__57", 58: "T__58", 59: "T__59", 60: "T__60", 61: "T__61", 62: "T__62", 
    63: "T__63", 64: "T__64", 65: "T__65", 66: "T__66", 67: "T__67", 68: "T__68", 
    69: "T__69", 70: "T__70", 71: "T__71", 72: "T__72", 73: "T__73", 74: "T__74", 
    75: "T__75", 76: "T__76", 77: "T__77", 78: "T__78", 79: "T__79", 4: "ASSIGN", 
    5: "ATTR", 6: "CALL", 7: "CLASS_ID", 8: "CLASS_REF", 9: "COMMENT", 10: "CONSTRUCT", 
    11: "DEF_DEFAULT", 12: "DEF_ENTITY", 13: "DEF_IMPLEMENT", 14: "DEF_IMPLEMENTATION", 
    15: "DEF_RELATION", 16: "DEF_TYPE", 17: "ENUM", 18: "ESC_SEQ", 19: "EXPONENT", 
    20: "FALSE", 21: "FLOAT", 22: "FOR", 23: "HASH", 24: "HEX_DIGIT", 25: "ID", 
    26: "INCLUDE", 27: "INDEX", 28: "INT", 29: "LAMBDA", 30: "LIST", 31: "ML_STRING", 
    32: "MULT", 33: "NONE", 34: "NS", 35: "OCTAL_ESC", 36: "OP", 37: "ORPHAN", 
    38: "REF", 39: "REGEX", 40: "STATEMENT", 41: "STRING", 42: "TRUE", 43: "UNICODE_ESC", 
    44: "VAR_REF", 45: "WS"
}
Token.registerTokenNamesMap(tokenNamesMap)

# token names
tokenNames = [
    "<invalid>", "<EOR>", "<DOWN>", "<UP>",
    "ASSIGN", "ATTR", "CALL", "CLASS_ID", "CLASS_REF", "COMMENT", "CONSTRUCT", 
    "DEF_DEFAULT", "DEF_ENTITY", "DEF_IMPLEMENT", "DEF_IMPLEMENTATION", 
    "DEF_RELATION", "DEF_TYPE", "ENUM", "ESC_SEQ", "EXPONENT", "FALSE", 
    "FLOAT", "FOR", "HASH", "HEX_DIGIT", "ID", "INCLUDE", "INDEX", "INT", 
    "LAMBDA", "LIST", "ML_STRING", "MULT", "NONE", "NS", "OCTAL_ESC", "OP", 
    "ORPHAN", "REF", "REGEX", "STATEMENT", "STRING", "TRUE", "UNICODE_ESC", 
    "VAR_REF", "WS", "'!='", "'('", "')'", "','", "'--'", "'->'", "'.'", 
    "':'", "'::'", "'<'", "'<-'", "'<='", "'='", "'=='", "'>'", "'>='", 
    "'['", "']'", "'and'", "'as'", "'end'", "'entity'", "'extends'", "'for'", 
    "'implement'", "'implementation'", "'in'", "'index'", "'matching'", 
    "'not'", "'or'", "'typedef'", "'using'", "'when'"
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

        self.dfa14 = self.DFA14(
            self, 14,
            eot = self.DFA14_eot,
            eof = self.DFA14_eof,
            min = self.DFA14_min,
            max = self.DFA14_max,
            accept = self.DFA14_accept,
            special = self.DFA14_special,
            transition = self.DFA14_transition
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

        self.dfa30 = self.DFA30(
            self, 30,
            eot = self.DFA30_eot,
            eof = self.DFA30_eof,
            min = self.DFA30_min,
            max = self.DFA30_max,
            accept = self.DFA30_accept,
            special = self.DFA30_special,
            transition = self.DFA30_transition
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
    # impera.g:38:1: main : ( def_statement | top_statement | ML_STRING )* -> ^( LIST ( def_statement )* ( top_statement )* ( ML_STRING )* ) ;
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
                # impera.g:39:2: ( ( def_statement | top_statement | ML_STRING )* -> ^( LIST ( def_statement )* ( top_statement )* ( ML_STRING )* ) )
                # impera.g:39:4: ( def_statement | top_statement | ML_STRING )*
                pass 
                # impera.g:39:4: ( def_statement | top_statement | ML_STRING )*
                while True: #loop1
                    alt1 = 4
                    alt1 = self.dfa1.predict(self.input)
                    if alt1 == 1:
                        # impera.g:39:5: def_statement
                        pass 
                        self._state.following.append(self.FOLLOW_def_statement_in_main153)
                        def_statement1 = self.def_statement()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_def_statement.add(def_statement1.tree)



                    elif alt1 == 2:
                        # impera.g:39:21: top_statement
                        pass 
                        self._state.following.append(self.FOLLOW_top_statement_in_main157)
                        top_statement2 = self.top_statement()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_top_statement.add(top_statement2.tree)



                    elif alt1 == 3:
                        # impera.g:39:37: ML_STRING
                        pass 
                        ML_STRING3 = self.match(self.input, ML_STRING, self.FOLLOW_ML_STRING_in_main161) 
                        if self._state.backtracking == 0:
                            stream_ML_STRING.add(ML_STRING3)



                    else:
                        break #loop1


                # AST Rewrite
                # elements: def_statement, ML_STRING, top_statement
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
                    # 39:49: -> ^( LIST ( def_statement )* ( top_statement )* ( ML_STRING )* )
                    # impera.g:39:52: ^( LIST ( def_statement )* ( top_statement )* ( ML_STRING )* )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_1)

                    # impera.g:39:59: ( def_statement )*
                    while stream_def_statement.hasNext():
                        self._adaptor.addChild(root_1, stream_def_statement.nextTree())


                    stream_def_statement.reset();

                    # impera.g:39:74: ( top_statement )*
                    while stream_top_statement.hasNext():
                        self._adaptor.addChild(root_1, stream_top_statement.nextTree())


                    stream_top_statement.reset();

                    # impera.g:39:89: ( ML_STRING )*
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "main"


    class def_statement_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "def_statement"
    # impera.g:42:1: def_statement : ( typedef | entity_def | implementation_def | relation | index | implement_def );
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
                # impera.g:43:2: ( typedef | entity_def | implementation_def | relation | index | implement_def )
                alt2 = 6
                LA2 = self.input.LA(1)
                if LA2 in {77}:
                    alt2 = 1
                elif LA2 in {67}:
                    alt2 = 2
                elif LA2 in {71}:
                    alt2 = 3
                elif LA2 in {CLASS_ID, ID}:
                    alt2 = 4
                elif LA2 in {73}:
                    alt2 = 5
                elif LA2 in {70}:
                    alt2 = 6
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 2, 0, self.input)

                    raise nvae


                if alt2 == 1:
                    # impera.g:43:4: typedef
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_typedef_in_def_statement189)
                    typedef4 = self.typedef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, typedef4.tree)



                elif alt2 == 2:
                    # impera.g:43:14: entity_def
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_entity_def_in_def_statement193)
                    entity_def5 = self.entity_def()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, entity_def5.tree)



                elif alt2 == 3:
                    # impera.g:43:27: implementation_def
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_implementation_def_in_def_statement197)
                    implementation_def6 = self.implementation_def()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, implementation_def6.tree)



                elif alt2 == 4:
                    # impera.g:43:48: relation
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_relation_in_def_statement201)
                    relation7 = self.relation()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, relation7.tree)



                elif alt2 == 5:
                    # impera.g:43:59: index
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_index_in_def_statement205)
                    index8 = self.index()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, index8.tree)



                elif alt2 == 6:
                    # impera.g:43:67: implement_def
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_implement_def_in_def_statement209)
                    implement_def9 = self.implement_def()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, implement_def9.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



            except RecognitionException as re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "def_statement"


    class typedef_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "typedef"
    # impera.g:46:1: typedef : ( 'typedef' ID 'as' ns_ref 'matching' ( REGEX | expression ) -> ^( DEF_TYPE ID ns_ref ( expression )? ( REGEX )? ) | 'typedef' CLASS_ID 'as' constructor -> ^( DEF_DEFAULT CLASS_ID constructor ) );
    def typedef(self, ):
        retval = self.typedef_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal10 = None
        ID11 = None
        string_literal12 = None
        string_literal14 = None
        REGEX15 = None
        string_literal17 = None
        CLASS_ID18 = None
        string_literal19 = None
        ns_ref13 = None
        expression16 = None
        constructor20 = None

        string_literal10_tree = None
        ID11_tree = None
        string_literal12_tree = None
        string_literal14_tree = None
        REGEX15_tree = None
        string_literal17_tree = None
        CLASS_ID18_tree = None
        string_literal19_tree = None
        stream_77 = RewriteRuleTokenStream(self._adaptor, "token 77")
        stream_REGEX = RewriteRuleTokenStream(self._adaptor, "token REGEX")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_74 = RewriteRuleTokenStream(self._adaptor, "token 74")
        stream_CLASS_ID = RewriteRuleTokenStream(self._adaptor, "token CLASS_ID")
        stream_65 = RewriteRuleTokenStream(self._adaptor, "token 65")
        stream_expression = RewriteRuleSubtreeStream(self._adaptor, "rule expression")
        stream_constructor = RewriteRuleSubtreeStream(self._adaptor, "rule constructor")
        stream_ns_ref = RewriteRuleSubtreeStream(self._adaptor, "rule ns_ref")
        try:
            try:
                # impera.g:47:2: ( 'typedef' ID 'as' ns_ref 'matching' ( REGEX | expression ) -> ^( DEF_TYPE ID ns_ref ( expression )? ( REGEX )? ) | 'typedef' CLASS_ID 'as' constructor -> ^( DEF_DEFAULT CLASS_ID constructor ) )
                alt4 = 2
                LA4_0 = self.input.LA(1)

                if (LA4_0 == 77) :
                    LA4_1 = self.input.LA(2)

                    if (LA4_1 == ID) :
                        alt4 = 1
                    elif (LA4_1 == CLASS_ID) :
                        alt4 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 4, 1, self.input)

                        raise nvae


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 4, 0, self.input)

                    raise nvae


                if alt4 == 1:
                    # impera.g:47:4: 'typedef' ID 'as' ns_ref 'matching' ( REGEX | expression )
                    pass 
                    string_literal10 = self.match(self.input, 77, self.FOLLOW_77_in_typedef220) 
                    if self._state.backtracking == 0:
                        stream_77.add(string_literal10)


                    ID11 = self.match(self.input, ID, self.FOLLOW_ID_in_typedef222) 
                    if self._state.backtracking == 0:
                        stream_ID.add(ID11)


                    string_literal12 = self.match(self.input, 65, self.FOLLOW_65_in_typedef224) 
                    if self._state.backtracking == 0:
                        stream_65.add(string_literal12)


                    self._state.following.append(self.FOLLOW_ns_ref_in_typedef226)
                    ns_ref13 = self.ns_ref()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_ns_ref.add(ns_ref13.tree)


                    string_literal14 = self.match(self.input, 74, self.FOLLOW_74_in_typedef228) 
                    if self._state.backtracking == 0:
                        stream_74.add(string_literal14)


                    # impera.g:47:40: ( REGEX | expression )
                    alt3 = 2
                    LA3_0 = self.input.LA(1)

                    if (LA3_0 == REGEX) :
                        LA3_1 = self.input.LA(2)

                        if (LA3_1 in {EOF, CLASS_ID, ID, ML_STRING, 67, 69, 70, 71, 73, 77}) :
                            alt3 = 1
                        elif (LA3_1 in {46, 55, 57, 59, 60, 61, 72}) :
                            alt3 = 2
                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed


                            nvae = NoViableAltException("", 3, 1, self.input)

                            raise nvae


                    elif (LA3_0 in {CLASS_ID, FALSE, FLOAT, ID, INT, ML_STRING, STRING, TRUE, 47, 62}) :
                        alt3 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 3, 0, self.input)

                        raise nvae


                    if alt3 == 1:
                        # impera.g:47:41: REGEX
                        pass 
                        REGEX15 = self.match(self.input, REGEX, self.FOLLOW_REGEX_in_typedef231) 
                        if self._state.backtracking == 0:
                            stream_REGEX.add(REGEX15)



                    elif alt3 == 2:
                        # impera.g:47:49: expression
                        pass 
                        self._state.following.append(self.FOLLOW_expression_in_typedef235)
                        expression16 = self.expression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_expression.add(expression16.tree)





                    # AST Rewrite
                    # elements: ID, ns_ref, REGEX, expression
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
                        # 47:61: -> ^( DEF_TYPE ID ns_ref ( expression )? ( REGEX )? )
                        # impera.g:47:64: ^( DEF_TYPE ID ns_ref ( expression )? ( REGEX )? )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(DEF_TYPE, "DEF_TYPE")
                        , root_1)

                        self._adaptor.addChild(root_1, 
                        stream_ID.nextNode()
                        )

                        self._adaptor.addChild(root_1, stream_ns_ref.nextTree())

                        # impera.g:47:85: ( expression )?
                        if stream_expression.hasNext():
                            self._adaptor.addChild(root_1, stream_expression.nextTree())


                        stream_expression.reset();

                        # impera.g:47:97: ( REGEX )?
                        if stream_REGEX.hasNext():
                            self._adaptor.addChild(root_1, 
                            stream_REGEX.nextNode()
                            )


                        stream_REGEX.reset();

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt4 == 2:
                    # impera.g:48:4: 'typedef' CLASS_ID 'as' constructor
                    pass 
                    string_literal17 = self.match(self.input, 77, self.FOLLOW_77_in_typedef257) 
                    if self._state.backtracking == 0:
                        stream_77.add(string_literal17)


                    CLASS_ID18 = self.match(self.input, CLASS_ID, self.FOLLOW_CLASS_ID_in_typedef259) 
                    if self._state.backtracking == 0:
                        stream_CLASS_ID.add(CLASS_ID18)


                    string_literal19 = self.match(self.input, 65, self.FOLLOW_65_in_typedef261) 
                    if self._state.backtracking == 0:
                        stream_65.add(string_literal19)


                    self._state.following.append(self.FOLLOW_constructor_in_typedef263)
                    constructor20 = self.constructor()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_constructor.add(constructor20.tree)


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
                        # 48:40: -> ^( DEF_DEFAULT CLASS_ID constructor )
                        # impera.g:48:43: ^( DEF_DEFAULT CLASS_ID constructor )
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "typedef"


    class entity_def_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "entity_def"
    # impera.g:51:1: entity_def : ( 'entity' CLASS_ID ( 'extends' class_ref ( ',' class_ref )* )? ) ':' ( ML_STRING )? ( entity_body )* 'end' -> ^( DEF_ENTITY CLASS_ID ^( LIST ( class_ref )* ) ^( LIST ( entity_body )* ) ( ML_STRING )? ) ;
    def entity_def(self, ):
        retval = self.entity_def_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal21 = None
        CLASS_ID22 = None
        string_literal23 = None
        char_literal25 = None
        char_literal27 = None
        ML_STRING28 = None
        string_literal30 = None
        class_ref24 = None
        class_ref26 = None
        entity_body29 = None

        string_literal21_tree = None
        CLASS_ID22_tree = None
        string_literal23_tree = None
        char_literal25_tree = None
        char_literal27_tree = None
        ML_STRING28_tree = None
        string_literal30_tree = None
        stream_66 = RewriteRuleTokenStream(self._adaptor, "token 66")
        stream_67 = RewriteRuleTokenStream(self._adaptor, "token 67")
        stream_68 = RewriteRuleTokenStream(self._adaptor, "token 68")
        stream_49 = RewriteRuleTokenStream(self._adaptor, "token 49")
        stream_ML_STRING = RewriteRuleTokenStream(self._adaptor, "token ML_STRING")
        stream_53 = RewriteRuleTokenStream(self._adaptor, "token 53")
        stream_CLASS_ID = RewriteRuleTokenStream(self._adaptor, "token CLASS_ID")
        stream_entity_body = RewriteRuleSubtreeStream(self._adaptor, "rule entity_body")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        try:
            try:
                # impera.g:52:2: ( ( 'entity' CLASS_ID ( 'extends' class_ref ( ',' class_ref )* )? ) ':' ( ML_STRING )? ( entity_body )* 'end' -> ^( DEF_ENTITY CLASS_ID ^( LIST ( class_ref )* ) ^( LIST ( entity_body )* ) ( ML_STRING )? ) )
                # impera.g:52:4: ( 'entity' CLASS_ID ( 'extends' class_ref ( ',' class_ref )* )? ) ':' ( ML_STRING )? ( entity_body )* 'end'
                pass 
                # impera.g:52:4: ( 'entity' CLASS_ID ( 'extends' class_ref ( ',' class_ref )* )? )
                # impera.g:52:5: 'entity' CLASS_ID ( 'extends' class_ref ( ',' class_ref )* )?
                pass 
                string_literal21 = self.match(self.input, 67, self.FOLLOW_67_in_entity_def293) 
                if self._state.backtracking == 0:
                    stream_67.add(string_literal21)


                CLASS_ID22 = self.match(self.input, CLASS_ID, self.FOLLOW_CLASS_ID_in_entity_def295) 
                if self._state.backtracking == 0:
                    stream_CLASS_ID.add(CLASS_ID22)


                # impera.g:52:23: ( 'extends' class_ref ( ',' class_ref )* )?
                alt6 = 2
                LA6_0 = self.input.LA(1)

                if (LA6_0 == 68) :
                    alt6 = 1
                if alt6 == 1:
                    # impera.g:52:24: 'extends' class_ref ( ',' class_ref )*
                    pass 
                    string_literal23 = self.match(self.input, 68, self.FOLLOW_68_in_entity_def298) 
                    if self._state.backtracking == 0:
                        stream_68.add(string_literal23)


                    self._state.following.append(self.FOLLOW_class_ref_in_entity_def300)
                    class_ref24 = self.class_ref()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_class_ref.add(class_ref24.tree)


                    # impera.g:52:44: ( ',' class_ref )*
                    while True: #loop5
                        alt5 = 2
                        LA5_0 = self.input.LA(1)

                        if (LA5_0 == 49) :
                            alt5 = 1


                        if alt5 == 1:
                            # impera.g:52:45: ',' class_ref
                            pass 
                            char_literal25 = self.match(self.input, 49, self.FOLLOW_49_in_entity_def303) 
                            if self._state.backtracking == 0:
                                stream_49.add(char_literal25)


                            self._state.following.append(self.FOLLOW_class_ref_in_entity_def305)
                            class_ref26 = self.class_ref()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                stream_class_ref.add(class_ref26.tree)



                        else:
                            break #loop5








                char_literal27 = self.match(self.input, 53, self.FOLLOW_53_in_entity_def312) 
                if self._state.backtracking == 0:
                    stream_53.add(char_literal27)


                # impera.g:52:68: ( ML_STRING )?
                alt7 = 2
                LA7_0 = self.input.LA(1)

                if (LA7_0 == ML_STRING) :
                    alt7 = 1
                if alt7 == 1:
                    # impera.g:52:68: ML_STRING
                    pass 
                    ML_STRING28 = self.match(self.input, ML_STRING, self.FOLLOW_ML_STRING_in_entity_def314) 
                    if self._state.backtracking == 0:
                        stream_ML_STRING.add(ML_STRING28)





                # impera.g:52:79: ( entity_body )*
                while True: #loop8
                    alt8 = 2
                    LA8_0 = self.input.LA(1)

                    if (LA8_0 == ID) :
                        alt8 = 1


                    if alt8 == 1:
                        # impera.g:52:80: entity_body
                        pass 
                        self._state.following.append(self.FOLLOW_entity_body_in_entity_def318)
                        entity_body29 = self.entity_body()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_entity_body.add(entity_body29.tree)



                    else:
                        break #loop8


                string_literal30 = self.match(self.input, 66, self.FOLLOW_66_in_entity_def322) 
                if self._state.backtracking == 0:
                    stream_66.add(string_literal30)


                # AST Rewrite
                # elements: entity_body, ML_STRING, CLASS_ID, class_ref
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
                    # 53:3: -> ^( DEF_ENTITY CLASS_ID ^( LIST ( class_ref )* ) ^( LIST ( entity_body )* ) ( ML_STRING )? )
                    # impera.g:53:6: ^( DEF_ENTITY CLASS_ID ^( LIST ( class_ref )* ) ^( LIST ( entity_body )* ) ( ML_STRING )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(DEF_ENTITY, "DEF_ENTITY")
                    , root_1)

                    self._adaptor.addChild(root_1, 
                    stream_CLASS_ID.nextNode()
                    )

                    # impera.g:53:28: ^( LIST ( class_ref )* )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_2)

                    # impera.g:53:35: ( class_ref )*
                    while stream_class_ref.hasNext():
                        self._adaptor.addChild(root_2, stream_class_ref.nextTree())


                    stream_class_ref.reset();

                    self._adaptor.addChild(root_1, root_2)

                    # impera.g:53:47: ^( LIST ( entity_body )* )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_2)

                    # impera.g:53:54: ( entity_body )*
                    while stream_entity_body.hasNext():
                        self._adaptor.addChild(root_2, stream_entity_body.nextTree())


                    stream_entity_body.reset();

                    self._adaptor.addChild(root_1, root_2)

                    # impera.g:53:68: ( ML_STRING )?
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "entity_def"


    class implementation_def_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "implementation_def"
    # impera.g:56:1: implementation_def : 'implementation' ID ( 'for' class_ref )? implementation -> ^( DEF_IMPLEMENTATION ID implementation ( class_ref )? ) ;
    def implementation_def(self, ):
        retval = self.implementation_def_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal31 = None
        ID32 = None
        string_literal33 = None
        class_ref34 = None
        implementation35 = None

        string_literal31_tree = None
        ID32_tree = None
        string_literal33_tree = None
        stream_69 = RewriteRuleTokenStream(self._adaptor, "token 69")
        stream_71 = RewriteRuleTokenStream(self._adaptor, "token 71")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_implementation = RewriteRuleSubtreeStream(self._adaptor, "rule implementation")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        try:
            try:
                # impera.g:57:2: ( 'implementation' ID ( 'for' class_ref )? implementation -> ^( DEF_IMPLEMENTATION ID implementation ( class_ref )? ) )
                # impera.g:57:4: 'implementation' ID ( 'for' class_ref )? implementation
                pass 
                string_literal31 = self.match(self.input, 71, self.FOLLOW_71_in_implementation_def365) 
                if self._state.backtracking == 0:
                    stream_71.add(string_literal31)


                ID32 = self.match(self.input, ID, self.FOLLOW_ID_in_implementation_def367) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID32)


                # impera.g:57:24: ( 'for' class_ref )?
                alt9 = 2
                LA9_0 = self.input.LA(1)

                if (LA9_0 == 69) :
                    alt9 = 1
                if alt9 == 1:
                    # impera.g:57:25: 'for' class_ref
                    pass 
                    string_literal33 = self.match(self.input, 69, self.FOLLOW_69_in_implementation_def370) 
                    if self._state.backtracking == 0:
                        stream_69.add(string_literal33)


                    self._state.following.append(self.FOLLOW_class_ref_in_implementation_def372)
                    class_ref34 = self.class_ref()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_class_ref.add(class_ref34.tree)





                self._state.following.append(self.FOLLOW_implementation_in_implementation_def376)
                implementation35 = self.implementation()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_implementation.add(implementation35.tree)


                # AST Rewrite
                # elements: class_ref, implementation, ID
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
                    # 57:58: -> ^( DEF_IMPLEMENTATION ID implementation ( class_ref )? )
                    # impera.g:57:61: ^( DEF_IMPLEMENTATION ID implementation ( class_ref )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(DEF_IMPLEMENTATION, "DEF_IMPLEMENTATION")
                    , root_1)

                    self._adaptor.addChild(root_1, 
                    stream_ID.nextNode()
                    )

                    self._adaptor.addChild(root_1, stream_implementation.nextTree())

                    # impera.g:57:100: ( class_ref )?
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "implementation_def"


    class index_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "index"
    # impera.g:60:1: index : 'index' class_ref '(' ID ( ',' ID )* ')' -> ^( INDEX class_ref ^( LIST ( ID )+ ) ) ;
    def index(self, ):
        retval = self.index_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal36 = None
        char_literal38 = None
        ID39 = None
        char_literal40 = None
        ID41 = None
        char_literal42 = None
        class_ref37 = None

        string_literal36_tree = None
        char_literal38_tree = None
        ID39_tree = None
        char_literal40_tree = None
        ID41_tree = None
        char_literal42_tree = None
        stream_47 = RewriteRuleTokenStream(self._adaptor, "token 47")
        stream_48 = RewriteRuleTokenStream(self._adaptor, "token 48")
        stream_49 = RewriteRuleTokenStream(self._adaptor, "token 49")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_73 = RewriteRuleTokenStream(self._adaptor, "token 73")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        try:
            try:
                # impera.g:61:2: ( 'index' class_ref '(' ID ( ',' ID )* ')' -> ^( INDEX class_ref ^( LIST ( ID )+ ) ) )
                # impera.g:61:4: 'index' class_ref '(' ID ( ',' ID )* ')'
                pass 
                string_literal36 = self.match(self.input, 73, self.FOLLOW_73_in_index408) 
                if self._state.backtracking == 0:
                    stream_73.add(string_literal36)


                self._state.following.append(self.FOLLOW_class_ref_in_index410)
                class_ref37 = self.class_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_class_ref.add(class_ref37.tree)


                char_literal38 = self.match(self.input, 47, self.FOLLOW_47_in_index412) 
                if self._state.backtracking == 0:
                    stream_47.add(char_literal38)


                ID39 = self.match(self.input, ID, self.FOLLOW_ID_in_index414) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID39)


                # impera.g:61:29: ( ',' ID )*
                while True: #loop10
                    alt10 = 2
                    LA10_0 = self.input.LA(1)

                    if (LA10_0 == 49) :
                        alt10 = 1


                    if alt10 == 1:
                        # impera.g:61:30: ',' ID
                        pass 
                        char_literal40 = self.match(self.input, 49, self.FOLLOW_49_in_index417) 
                        if self._state.backtracking == 0:
                            stream_49.add(char_literal40)


                        ID41 = self.match(self.input, ID, self.FOLLOW_ID_in_index419) 
                        if self._state.backtracking == 0:
                            stream_ID.add(ID41)



                    else:
                        break #loop10


                char_literal42 = self.match(self.input, 48, self.FOLLOW_48_in_index423) 
                if self._state.backtracking == 0:
                    stream_48.add(char_literal42)


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
                    # 61:43: -> ^( INDEX class_ref ^( LIST ( ID )+ ) )
                    # impera.g:61:46: ^( INDEX class_ref ^( LIST ( ID )+ ) )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(INDEX, "INDEX")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_class_ref.nextTree())

                    # impera.g:61:64: ^( LIST ( ID )+ )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_2)

                    # impera.g:61:71: ( ID )+
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "index"


    class implement_def_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "implement_def"
    # impera.g:65:1: implement_def : 'implement' class_ref 'using' ns_ref ( ',' ns_ref )* ( 'when' expression )? -> ^( DEF_IMPLEMENT class_ref ^( LIST ( ns_ref )+ ) ( expression )? ) ;
    def implement_def(self, ):
        retval = self.implement_def_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal43 = None
        string_literal45 = None
        char_literal47 = None
        string_literal49 = None
        class_ref44 = None
        ns_ref46 = None
        ns_ref48 = None
        expression50 = None

        string_literal43_tree = None
        string_literal45_tree = None
        char_literal47_tree = None
        string_literal49_tree = None
        stream_78 = RewriteRuleTokenStream(self._adaptor, "token 78")
        stream_79 = RewriteRuleTokenStream(self._adaptor, "token 79")
        stream_49 = RewriteRuleTokenStream(self._adaptor, "token 49")
        stream_70 = RewriteRuleTokenStream(self._adaptor, "token 70")
        stream_expression = RewriteRuleSubtreeStream(self._adaptor, "rule expression")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        stream_ns_ref = RewriteRuleSubtreeStream(self._adaptor, "rule ns_ref")
        try:
            try:
                # impera.g:66:2: ( 'implement' class_ref 'using' ns_ref ( ',' ns_ref )* ( 'when' expression )? -> ^( DEF_IMPLEMENT class_ref ^( LIST ( ns_ref )+ ) ( expression )? ) )
                # impera.g:66:4: 'implement' class_ref 'using' ns_ref ( ',' ns_ref )* ( 'when' expression )?
                pass 
                string_literal43 = self.match(self.input, 70, self.FOLLOW_70_in_implement_def450) 
                if self._state.backtracking == 0:
                    stream_70.add(string_literal43)


                self._state.following.append(self.FOLLOW_class_ref_in_implement_def452)
                class_ref44 = self.class_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_class_ref.add(class_ref44.tree)


                string_literal45 = self.match(self.input, 78, self.FOLLOW_78_in_implement_def454) 
                if self._state.backtracking == 0:
                    stream_78.add(string_literal45)


                self._state.following.append(self.FOLLOW_ns_ref_in_implement_def456)
                ns_ref46 = self.ns_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_ns_ref.add(ns_ref46.tree)


                # impera.g:66:41: ( ',' ns_ref )*
                while True: #loop11
                    alt11 = 2
                    LA11_0 = self.input.LA(1)

                    if (LA11_0 == 49) :
                        alt11 = 1


                    if alt11 == 1:
                        # impera.g:66:42: ',' ns_ref
                        pass 
                        char_literal47 = self.match(self.input, 49, self.FOLLOW_49_in_implement_def459) 
                        if self._state.backtracking == 0:
                            stream_49.add(char_literal47)


                        self._state.following.append(self.FOLLOW_ns_ref_in_implement_def461)
                        ns_ref48 = self.ns_ref()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_ns_ref.add(ns_ref48.tree)



                    else:
                        break #loop11


                # impera.g:66:55: ( 'when' expression )?
                alt12 = 2
                LA12_0 = self.input.LA(1)

                if (LA12_0 == 79) :
                    alt12 = 1
                if alt12 == 1:
                    # impera.g:66:56: 'when' expression
                    pass 
                    string_literal49 = self.match(self.input, 79, self.FOLLOW_79_in_implement_def466) 
                    if self._state.backtracking == 0:
                        stream_79.add(string_literal49)


                    self._state.following.append(self.FOLLOW_expression_in_implement_def468)
                    expression50 = self.expression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_expression.add(expression50.tree)





                # AST Rewrite
                # elements: ns_ref, expression, class_ref
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
                    # 66:76: -> ^( DEF_IMPLEMENT class_ref ^( LIST ( ns_ref )+ ) ( expression )? )
                    # impera.g:66:79: ^( DEF_IMPLEMENT class_ref ^( LIST ( ns_ref )+ ) ( expression )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(DEF_IMPLEMENT, "DEF_IMPLEMENT")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_class_ref.nextTree())

                    # impera.g:66:105: ^( LIST ( ns_ref )+ )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_2)

                    # impera.g:66:112: ( ns_ref )+
                    if not (stream_ns_ref.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_ns_ref.hasNext():
                        self._adaptor.addChild(root_2, stream_ns_ref.nextTree())


                    stream_ns_ref.reset()

                    self._adaptor.addChild(root_1, root_2)

                    # impera.g:66:121: ( expression )?
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "implement_def"


    class relation_end_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "relation_end"
    # impera.g:71:1: relation_end : class_ref ID -> class_ref ID ;
    def relation_end(self, ):
        retval = self.relation_end_return()
        retval.start = self.input.LT(1)


        root_0 = None

        ID52 = None
        class_ref51 = None

        ID52_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        try:
            try:
                # impera.g:72:2: ( class_ref ID -> class_ref ID )
                # impera.g:72:4: class_ref ID
                pass 
                self._state.following.append(self.FOLLOW_class_ref_in_relation_end501)
                class_ref51 = self.class_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_class_ref.add(class_ref51.tree)


                ID52 = self.match(self.input, ID, self.FOLLOW_ID_in_relation_end503) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID52)


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
                    # 72:17: -> class_ref ID
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "relation_end"


    class relation_link_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "relation_link"
    # impera.g:75:1: relation_link : ( '<-' | '->' | '--' );
    def relation_link(self, ):
        retval = self.relation_link_return()
        retval.start = self.input.LT(1)


        root_0 = None

        set53 = None

        set53_tree = None

        try:
            try:
                # impera.g:76:2: ( '<-' | '->' | '--' )
                # impera.g:
                pass 
                root_0 = self._adaptor.nil()


                set53 = self.input.LT(1)

                if self.input.LA(1) in {50, 51, 56}:
                    self.input.consume()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set53))

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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "relation_link"


    class multiplicity_body_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "multiplicity_body"
    # impera.g:79:1: multiplicity_body : ( ( INT )=> INT -> ^( MULT INT ) | ( INT ':' )=> INT ':' -> ^( MULT INT NONE ) | ( INT ':' INT )=> INT ':' INT -> ^( MULT INT INT ) | ( ':' INT )=> ':' INT -> ^( MULT NONE INT ) );
    def multiplicity_body(self, ):
        retval = self.multiplicity_body_return()
        retval.start = self.input.LT(1)


        root_0 = None

        INT54 = None
        INT55 = None
        char_literal56 = None
        INT57 = None
        char_literal58 = None
        INT59 = None
        char_literal60 = None
        INT61 = None

        INT54_tree = None
        INT55_tree = None
        char_literal56_tree = None
        INT57_tree = None
        char_literal58_tree = None
        INT59_tree = None
        char_literal60_tree = None
        INT61_tree = None
        stream_INT = RewriteRuleTokenStream(self._adaptor, "token INT")
        stream_53 = RewriteRuleTokenStream(self._adaptor, "token 53")

        try:
            try:
                # impera.g:80:2: ( ( INT )=> INT -> ^( MULT INT ) | ( INT ':' )=> INT ':' -> ^( MULT INT NONE ) | ( INT ':' INT )=> INT ':' INT -> ^( MULT INT INT ) | ( ':' INT )=> ':' INT -> ^( MULT NONE INT ) )
                alt13 = 4
                LA13_0 = self.input.LA(1)

                if (LA13_0 == INT) :
                    LA13_1 = self.input.LA(2)

                    if (LA13_1 == 53) :
                        LA13_3 = self.input.LA(3)

                        if (LA13_3 == INT) and (self.synpred3_impera()):
                            alt13 = 3
                        elif (LA13_3 == 63) and (self.synpred2_impera()):
                            alt13 = 2
                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed


                            nvae = NoViableAltException("", 13, 3, self.input)

                            raise nvae


                    elif (LA13_1 == 63) and (self.synpred1_impera()):
                        alt13 = 1
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 13, 1, self.input)

                        raise nvae


                elif (LA13_0 == 53) and (self.synpred4_impera()):
                    alt13 = 4
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 13, 0, self.input)

                    raise nvae


                if alt13 == 1:
                    # impera.g:80:4: ( INT )=> INT
                    pass 
                    INT54 = self.match(self.input, INT, self.FOLLOW_INT_in_multiplicity_body547) 
                    if self._state.backtracking == 0:
                        stream_INT.add(INT54)


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
                        # 80:17: -> ^( MULT INT )
                        # impera.g:80:20: ^( MULT INT )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(MULT, "MULT")
                        , root_1)

                        self._adaptor.addChild(root_1, 
                        stream_INT.nextNode()
                        )

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt13 == 2:
                    # impera.g:81:4: ( INT ':' )=> INT ':'
                    pass 
                    INT55 = self.match(self.input, INT, self.FOLLOW_INT_in_multiplicity_body568) 
                    if self._state.backtracking == 0:
                        stream_INT.add(INT55)


                    char_literal56 = self.match(self.input, 53, self.FOLLOW_53_in_multiplicity_body570) 
                    if self._state.backtracking == 0:
                        stream_53.add(char_literal56)


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
                        # 81:25: -> ^( MULT INT NONE )
                        # impera.g:81:28: ^( MULT INT NONE )
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




                elif alt13 == 3:
                    # impera.g:82:4: ( INT ':' INT )=> INT ':' INT
                    pass 
                    INT57 = self.match(self.input, INT, self.FOLLOW_INT_in_multiplicity_body595) 
                    if self._state.backtracking == 0:
                        stream_INT.add(INT57)


                    char_literal58 = self.match(self.input, 53, self.FOLLOW_53_in_multiplicity_body597) 
                    if self._state.backtracking == 0:
                        stream_53.add(char_literal58)


                    INT59 = self.match(self.input, INT, self.FOLLOW_INT_in_multiplicity_body599) 
                    if self._state.backtracking == 0:
                        stream_INT.add(INT59)


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
                        # 82:33: -> ^( MULT INT INT )
                        # impera.g:82:36: ^( MULT INT INT )
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




                elif alt13 == 4:
                    # impera.g:83:4: ( ':' INT )=> ':' INT
                    pass 
                    char_literal60 = self.match(self.input, 53, self.FOLLOW_53_in_multiplicity_body622) 
                    if self._state.backtracking == 0:
                        stream_53.add(char_literal60)


                    INT61 = self.match(self.input, INT, self.FOLLOW_INT_in_multiplicity_body624) 
                    if self._state.backtracking == 0:
                        stream_INT.add(INT61)


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
                        # 83:25: -> ^( MULT NONE INT )
                        # impera.g:83:28: ^( MULT NONE INT )
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "multiplicity_body"


    class multiplicity_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "multiplicity"
    # impera.g:86:1: multiplicity : '[' multiplicity_body ']' -> multiplicity_body ;
    def multiplicity(self, ):
        retval = self.multiplicity_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal62 = None
        char_literal64 = None
        multiplicity_body63 = None

        char_literal62_tree = None
        char_literal64_tree = None
        stream_62 = RewriteRuleTokenStream(self._adaptor, "token 62")
        stream_63 = RewriteRuleTokenStream(self._adaptor, "token 63")
        stream_multiplicity_body = RewriteRuleSubtreeStream(self._adaptor, "rule multiplicity_body")
        try:
            try:
                # impera.g:87:2: ( '[' multiplicity_body ']' -> multiplicity_body )
                # impera.g:87:4: '[' multiplicity_body ']'
                pass 
                char_literal62 = self.match(self.input, 62, self.FOLLOW_62_in_multiplicity645) 
                if self._state.backtracking == 0:
                    stream_62.add(char_literal62)


                self._state.following.append(self.FOLLOW_multiplicity_body_in_multiplicity647)
                multiplicity_body63 = self.multiplicity_body()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_multiplicity_body.add(multiplicity_body63.tree)


                char_literal64 = self.match(self.input, 63, self.FOLLOW_63_in_multiplicity649) 
                if self._state.backtracking == 0:
                    stream_63.add(char_literal64)


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
                    # 87:30: -> multiplicity_body
                    self._adaptor.addChild(root_0, stream_multiplicity_body.nextTree())




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



            except RecognitionException as re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "multiplicity"


    class relation_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "relation"
    # impera.g:90:1: relation : (left_end= relation_end left_m= multiplicity ) relation_link (right_m= multiplicity right_end= relation_end ) -> ^( DEF_RELATION relation_link ^( LIST $left_end $left_m) ^( LIST $right_end $right_m) ) ;
    def relation(self, ):
        retval = self.relation_return()
        retval.start = self.input.LT(1)


        root_0 = None

        left_end = None
        left_m = None
        right_m = None
        right_end = None
        relation_link65 = None

        stream_multiplicity = RewriteRuleSubtreeStream(self._adaptor, "rule multiplicity")
        stream_relation_end = RewriteRuleSubtreeStream(self._adaptor, "rule relation_end")
        stream_relation_link = RewriteRuleSubtreeStream(self._adaptor, "rule relation_link")
        try:
            try:
                # impera.g:91:2: ( (left_end= relation_end left_m= multiplicity ) relation_link (right_m= multiplicity right_end= relation_end ) -> ^( DEF_RELATION relation_link ^( LIST $left_end $left_m) ^( LIST $right_end $right_m) ) )
                # impera.g:91:4: (left_end= relation_end left_m= multiplicity ) relation_link (right_m= multiplicity right_end= relation_end )
                pass 
                # impera.g:91:4: (left_end= relation_end left_m= multiplicity )
                # impera.g:91:5: left_end= relation_end left_m= multiplicity
                pass 
                self._state.following.append(self.FOLLOW_relation_end_in_relation675)
                left_end = self.relation_end()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_relation_end.add(left_end.tree)


                self._state.following.append(self.FOLLOW_multiplicity_in_relation679)
                left_m = self.multiplicity()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_multiplicity.add(left_m.tree)





                self._state.following.append(self.FOLLOW_relation_link_in_relation682)
                relation_link65 = self.relation_link()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_relation_link.add(relation_link65.tree)


                # impera.g:91:62: (right_m= multiplicity right_end= relation_end )
                # impera.g:91:63: right_m= multiplicity right_end= relation_end
                pass 
                self._state.following.append(self.FOLLOW_multiplicity_in_relation687)
                right_m = self.multiplicity()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_multiplicity.add(right_m.tree)


                self._state.following.append(self.FOLLOW_relation_end_in_relation691)
                right_end = self.relation_end()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_relation_end.add(right_end.tree)





                # AST Rewrite
                # elements: left_m, right_end, right_m, relation_link, left_end
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
                    # 91:108: -> ^( DEF_RELATION relation_link ^( LIST $left_end $left_m) ^( LIST $right_end $right_m) )
                    # impera.g:92:3: ^( DEF_RELATION relation_link ^( LIST $left_end $left_m) ^( LIST $right_end $right_m) )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(DEF_RELATION, "DEF_RELATION")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_relation_link.nextTree())

                    # impera.g:92:32: ^( LIST $left_end $left_m)
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_2)

                    self._adaptor.addChild(root_2, stream_left_end.nextTree())

                    self._adaptor.addChild(root_2, stream_left_m.nextTree())

                    self._adaptor.addChild(root_1, root_2)

                    # impera.g:92:58: ^( LIST $right_end $right_m)
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "relation"


    class top_statement_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "top_statement"
    # impera.g:97:1: top_statement : ( ( 'for' )=> 'for' ID 'in' variable implementation -> ^( FOR ID ( variable )? implementation ) | variable '=' operand -> ^( ASSIGN variable operand ) | call );
    def top_statement(self, ):
        retval = self.top_statement_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal66 = None
        ID67 = None
        string_literal68 = None
        char_literal72 = None
        variable69 = None
        implementation70 = None
        variable71 = None
        operand73 = None
        call74 = None

        string_literal66_tree = None
        ID67_tree = None
        string_literal68_tree = None
        char_literal72_tree = None
        stream_69 = RewriteRuleTokenStream(self._adaptor, "token 69")
        stream_58 = RewriteRuleTokenStream(self._adaptor, "token 58")
        stream_72 = RewriteRuleTokenStream(self._adaptor, "token 72")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_implementation = RewriteRuleSubtreeStream(self._adaptor, "rule implementation")
        stream_variable = RewriteRuleSubtreeStream(self._adaptor, "rule variable")
        stream_operand = RewriteRuleSubtreeStream(self._adaptor, "rule operand")
        try:
            try:
                # impera.g:99:2: ( ( 'for' )=> 'for' ID 'in' variable implementation -> ^( FOR ID ( variable )? implementation ) | variable '=' operand -> ^( ASSIGN variable operand ) | call )
                alt14 = 3
                alt14 = self.dfa14.predict(self.input)
                if alt14 == 1:
                    # impera.g:99:4: ( 'for' )=> 'for' ID 'in' variable implementation
                    pass 
                    string_literal66 = self.match(self.input, 69, self.FOLLOW_69_in_top_statement759) 
                    if self._state.backtracking == 0:
                        stream_69.add(string_literal66)


                    ID67 = self.match(self.input, ID, self.FOLLOW_ID_in_top_statement761) 
                    if self._state.backtracking == 0:
                        stream_ID.add(ID67)


                    string_literal68 = self.match(self.input, 72, self.FOLLOW_72_in_top_statement763) 
                    if self._state.backtracking == 0:
                        stream_72.add(string_literal68)


                    self._state.following.append(self.FOLLOW_variable_in_top_statement765)
                    variable69 = self.variable()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_variable.add(variable69.tree)


                    self._state.following.append(self.FOLLOW_implementation_in_top_statement767)
                    implementation70 = self.implementation()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_implementation.add(implementation70.tree)


                    # AST Rewrite
                    # elements: implementation, ID, variable
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
                        # 99:53: -> ^( FOR ID ( variable )? implementation )
                        # impera.g:99:56: ^( FOR ID ( variable )? implementation )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(FOR, "FOR")
                        , root_1)

                        self._adaptor.addChild(root_1, 
                        stream_ID.nextNode()
                        )

                        # impera.g:99:65: ( variable )?
                        if stream_variable.hasNext():
                            self._adaptor.addChild(root_1, stream_variable.nextTree())


                        stream_variable.reset();

                        self._adaptor.addChild(root_1, stream_implementation.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt14 == 2:
                    # impera.g:100:4: variable '=' operand
                    pass 
                    self._state.following.append(self.FOLLOW_variable_in_top_statement785)
                    variable71 = self.variable()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_variable.add(variable71.tree)


                    char_literal72 = self.match(self.input, 58, self.FOLLOW_58_in_top_statement787) 
                    if self._state.backtracking == 0:
                        stream_58.add(char_literal72)


                    self._state.following.append(self.FOLLOW_operand_in_top_statement789)
                    operand73 = self.operand()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_operand.add(operand73.tree)


                    # AST Rewrite
                    # elements: variable, operand
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
                        # 100:25: -> ^( ASSIGN variable operand )
                        # impera.g:100:28: ^( ASSIGN variable operand )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(ASSIGN, "ASSIGN")
                        , root_1)

                        self._adaptor.addChild(root_1, stream_variable.nextTree())

                        self._adaptor.addChild(root_1, stream_operand.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt14 == 3:
                    # impera.g:101:4: call
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_call_in_top_statement804)
                    call74 = self.call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, call74.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



            except RecognitionException as re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "top_statement"


    class implementation_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "implementation"
    # impera.g:104:1: implementation : ':' ( ML_STRING )? ( statement )* 'end' -> ^( LIST ( statement )* ) ;
    def implementation(self, ):
        retval = self.implementation_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal75 = None
        ML_STRING76 = None
        string_literal78 = None
        statement77 = None

        char_literal75_tree = None
        ML_STRING76_tree = None
        string_literal78_tree = None
        stream_66 = RewriteRuleTokenStream(self._adaptor, "token 66")
        stream_ML_STRING = RewriteRuleTokenStream(self._adaptor, "token ML_STRING")
        stream_53 = RewriteRuleTokenStream(self._adaptor, "token 53")
        stream_statement = RewriteRuleSubtreeStream(self._adaptor, "rule statement")
        try:
            try:
                # impera.g:105:2: ( ':' ( ML_STRING )? ( statement )* 'end' -> ^( LIST ( statement )* ) )
                # impera.g:105:4: ':' ( ML_STRING )? ( statement )* 'end'
                pass 
                char_literal75 = self.match(self.input, 53, self.FOLLOW_53_in_implementation815) 
                if self._state.backtracking == 0:
                    stream_53.add(char_literal75)


                # impera.g:105:8: ( ML_STRING )?
                alt15 = 2
                LA15_0 = self.input.LA(1)

                if (LA15_0 == ML_STRING) :
                    alt15 = 1
                if alt15 == 1:
                    # impera.g:105:8: ML_STRING
                    pass 
                    ML_STRING76 = self.match(self.input, ML_STRING, self.FOLLOW_ML_STRING_in_implementation817) 
                    if self._state.backtracking == 0:
                        stream_ML_STRING.add(ML_STRING76)





                # impera.g:105:19: ( statement )*
                while True: #loop16
                    alt16 = 2
                    LA16_0 = self.input.LA(1)

                    if (LA16_0 in {CLASS_ID, ID, 69}) :
                        alt16 = 1


                    if alt16 == 1:
                        # impera.g:105:19: statement
                        pass 
                        self._state.following.append(self.FOLLOW_statement_in_implementation820)
                        statement77 = self.statement()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_statement.add(statement77.tree)



                    else:
                        break #loop16


                string_literal78 = self.match(self.input, 66, self.FOLLOW_66_in_implementation823) 
                if self._state.backtracking == 0:
                    stream_66.add(string_literal78)


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
                    # 105:36: -> ^( LIST ( statement )* )
                    # impera.g:105:39: ^( LIST ( statement )* )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_1)

                    # impera.g:105:46: ( statement )*
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "implementation"


    class statement_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "statement"
    # impera.g:108:1: statement : top_statement -> ^( STATEMENT top_statement ) ;
    def statement(self, ):
        retval = self.statement_return()
        retval.start = self.input.LT(1)


        root_0 = None

        top_statement79 = None

        stream_top_statement = RewriteRuleSubtreeStream(self._adaptor, "rule top_statement")
        try:
            try:
                # impera.g:109:2: ( top_statement -> ^( STATEMENT top_statement ) )
                # impera.g:109:4: top_statement
                pass 
                self._state.following.append(self.FOLLOW_top_statement_in_statement843)
                top_statement79 = self.top_statement()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_top_statement.add(top_statement79.tree)


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
                    # 109:18: -> ^( STATEMENT top_statement )
                    # impera.g:109:21: ^( STATEMENT top_statement )
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "statement"


    class parameter_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "parameter"
    # impera.g:112:1: parameter : ID '=' operand -> ^( ASSIGN ID operand ) ;
    def parameter(self, ):
        retval = self.parameter_return()
        retval.start = self.input.LT(1)


        root_0 = None

        ID80 = None
        char_literal81 = None
        operand82 = None

        ID80_tree = None
        char_literal81_tree = None
        stream_58 = RewriteRuleTokenStream(self._adaptor, "token 58")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_operand = RewriteRuleSubtreeStream(self._adaptor, "rule operand")
        try:
            try:
                # impera.g:113:2: ( ID '=' operand -> ^( ASSIGN ID operand ) )
                # impera.g:113:4: ID '=' operand
                pass 
                ID80 = self.match(self.input, ID, self.FOLLOW_ID_in_parameter863) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID80)


                char_literal81 = self.match(self.input, 58, self.FOLLOW_58_in_parameter865) 
                if self._state.backtracking == 0:
                    stream_58.add(char_literal81)


                self._state.following.append(self.FOLLOW_operand_in_parameter867)
                operand82 = self.operand()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_operand.add(operand82.tree)


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
                    # 113:19: -> ^( ASSIGN ID operand )
                    # impera.g:113:22: ^( ASSIGN ID operand )
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "parameter"


    class constructor_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "constructor"
    # impera.g:116:1: constructor : class_ref '(' ( param_list )? ')' -> ^( CONSTRUCT class_ref ( param_list )? ) ;
    def constructor(self, ):
        retval = self.constructor_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal84 = None
        char_literal86 = None
        class_ref83 = None
        param_list85 = None

        char_literal84_tree = None
        char_literal86_tree = None
        stream_47 = RewriteRuleTokenStream(self._adaptor, "token 47")
        stream_48 = RewriteRuleTokenStream(self._adaptor, "token 48")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        stream_param_list = RewriteRuleSubtreeStream(self._adaptor, "rule param_list")
        try:
            try:
                # impera.g:117:2: ( class_ref '(' ( param_list )? ')' -> ^( CONSTRUCT class_ref ( param_list )? ) )
                # impera.g:117:4: class_ref '(' ( param_list )? ')'
                pass 
                self._state.following.append(self.FOLLOW_class_ref_in_constructor888)
                class_ref83 = self.class_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_class_ref.add(class_ref83.tree)


                char_literal84 = self.match(self.input, 47, self.FOLLOW_47_in_constructor890) 
                if self._state.backtracking == 0:
                    stream_47.add(char_literal84)


                # impera.g:117:18: ( param_list )?
                alt17 = 2
                LA17_0 = self.input.LA(1)

                if (LA17_0 == ID) :
                    alt17 = 1
                if alt17 == 1:
                    # impera.g:117:18: param_list
                    pass 
                    self._state.following.append(self.FOLLOW_param_list_in_constructor892)
                    param_list85 = self.param_list()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_param_list.add(param_list85.tree)





                char_literal86 = self.match(self.input, 48, self.FOLLOW_48_in_constructor895) 
                if self._state.backtracking == 0:
                    stream_48.add(char_literal86)


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
                    # 117:34: -> ^( CONSTRUCT class_ref ( param_list )? )
                    # impera.g:117:37: ^( CONSTRUCT class_ref ( param_list )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(CONSTRUCT, "CONSTRUCT")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_class_ref.nextTree())

                    # impera.g:117:59: ( param_list )?
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "constructor"


    class param_list_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "param_list"
    # impera.g:120:1: param_list : parameter ( ',' parameter )* ( ',' )? -> ^( LIST ( parameter )+ ) ;
    def param_list(self, ):
        retval = self.param_list_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal88 = None
        char_literal90 = None
        parameter87 = None
        parameter89 = None

        char_literal88_tree = None
        char_literal90_tree = None
        stream_49 = RewriteRuleTokenStream(self._adaptor, "token 49")
        stream_parameter = RewriteRuleSubtreeStream(self._adaptor, "rule parameter")
        try:
            try:
                # impera.g:121:2: ( parameter ( ',' parameter )* ( ',' )? -> ^( LIST ( parameter )+ ) )
                # impera.g:121:4: parameter ( ',' parameter )* ( ',' )?
                pass 
                self._state.following.append(self.FOLLOW_parameter_in_param_list920)
                parameter87 = self.parameter()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_parameter.add(parameter87.tree)


                # impera.g:121:14: ( ',' parameter )*
                while True: #loop18
                    alt18 = 2
                    LA18_0 = self.input.LA(1)

                    if (LA18_0 == 49) :
                        LA18_1 = self.input.LA(2)

                        if (LA18_1 == ID) :
                            alt18 = 1




                    if alt18 == 1:
                        # impera.g:121:15: ',' parameter
                        pass 
                        char_literal88 = self.match(self.input, 49, self.FOLLOW_49_in_param_list923) 
                        if self._state.backtracking == 0:
                            stream_49.add(char_literal88)


                        self._state.following.append(self.FOLLOW_parameter_in_param_list925)
                        parameter89 = self.parameter()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_parameter.add(parameter89.tree)



                    else:
                        break #loop18


                # impera.g:121:31: ( ',' )?
                alt19 = 2
                LA19_0 = self.input.LA(1)

                if (LA19_0 == 49) :
                    alt19 = 1
                if alt19 == 1:
                    # impera.g:121:31: ','
                    pass 
                    char_literal90 = self.match(self.input, 49, self.FOLLOW_49_in_param_list929) 
                    if self._state.backtracking == 0:
                        stream_49.add(char_literal90)





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
                    # 121:36: -> ^( LIST ( parameter )+ )
                    # impera.g:121:39: ^( LIST ( parameter )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_1)

                    # impera.g:121:46: ( parameter )+
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "param_list"


    class operand_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "operand"
    # impera.g:125:1: operand : ( constant | list_def | index_lookup | call | variable );
    def operand(self, ):
        retval = self.operand_return()
        retval.start = self.input.LT(1)


        root_0 = None

        constant91 = None
        list_def92 = None
        index_lookup93 = None
        call94 = None
        variable95 = None


        try:
            try:
                # impera.g:126:2: ( constant | list_def | index_lookup | call | variable )
                alt20 = 5
                alt20 = self.dfa20.predict(self.input)
                if alt20 == 1:
                    # impera.g:126:4: constant
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_constant_in_operand952)
                    constant91 = self.constant()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, constant91.tree)



                elif alt20 == 2:
                    # impera.g:127:4: list_def
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_list_def_in_operand957)
                    list_def92 = self.list_def()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, list_def92.tree)



                elif alt20 == 3:
                    # impera.g:128:4: index_lookup
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_index_lookup_in_operand962)
                    index_lookup93 = self.index_lookup()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, index_lookup93.tree)



                elif alt20 == 4:
                    # impera.g:129:4: call
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_call_in_operand967)
                    call94 = self.call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, call94.tree)



                elif alt20 == 5:
                    # impera.g:130:4: variable
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_variable_in_operand972)
                    variable95 = self.variable()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, variable95.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



            except RecognitionException as re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "operand"


    class constant_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "constant"
    # impera.g:134:1: constant : ( TRUE | FALSE | STRING | INT | FLOAT | REGEX | ML_STRING );
    def constant(self, ):
        retval = self.constant_return()
        retval.start = self.input.LT(1)


        root_0 = None

        set96 = None

        set96_tree = None

        try:
            try:
                # impera.g:135:2: ( TRUE | FALSE | STRING | INT | FLOAT | REGEX | ML_STRING )
                # impera.g:
                pass 
                root_0 = self._adaptor.nil()


                set96 = self.input.LT(1)

                if self.input.LA(1) in {FALSE, FLOAT, INT, ML_STRING, REGEX, STRING, TRUE}:
                    self.input.consume()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set96))

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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "constant"


    class list_def_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "list_def"
    # impera.g:138:1: list_def : '[' operand ( ',' operand )* ( ',' )? ']' -> ^( LIST ( operand )+ ) ;
    def list_def(self, ):
        retval = self.list_def_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal97 = None
        char_literal99 = None
        char_literal101 = None
        char_literal102 = None
        operand98 = None
        operand100 = None

        char_literal97_tree = None
        char_literal99_tree = None
        char_literal101_tree = None
        char_literal102_tree = None
        stream_49 = RewriteRuleTokenStream(self._adaptor, "token 49")
        stream_62 = RewriteRuleTokenStream(self._adaptor, "token 62")
        stream_63 = RewriteRuleTokenStream(self._adaptor, "token 63")
        stream_operand = RewriteRuleSubtreeStream(self._adaptor, "rule operand")
        try:
            try:
                # impera.g:139:2: ( '[' operand ( ',' operand )* ( ',' )? ']' -> ^( LIST ( operand )+ ) )
                # impera.g:139:4: '[' operand ( ',' operand )* ( ',' )? ']'
                pass 
                char_literal97 = self.match(self.input, 62, self.FOLLOW_62_in_list_def1030) 
                if self._state.backtracking == 0:
                    stream_62.add(char_literal97)


                self._state.following.append(self.FOLLOW_operand_in_list_def1032)
                operand98 = self.operand()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_operand.add(operand98.tree)


                # impera.g:139:16: ( ',' operand )*
                while True: #loop21
                    alt21 = 2
                    LA21_0 = self.input.LA(1)

                    if (LA21_0 == 49) :
                        LA21_1 = self.input.LA(2)

                        if (LA21_1 in {CLASS_ID, FALSE, FLOAT, ID, INT, ML_STRING, REGEX, STRING, TRUE, 62}) :
                            alt21 = 1




                    if alt21 == 1:
                        # impera.g:139:17: ',' operand
                        pass 
                        char_literal99 = self.match(self.input, 49, self.FOLLOW_49_in_list_def1035) 
                        if self._state.backtracking == 0:
                            stream_49.add(char_literal99)


                        self._state.following.append(self.FOLLOW_operand_in_list_def1037)
                        operand100 = self.operand()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_operand.add(operand100.tree)



                    else:
                        break #loop21


                # impera.g:139:31: ( ',' )?
                alt22 = 2
                LA22_0 = self.input.LA(1)

                if (LA22_0 == 49) :
                    alt22 = 1
                if alt22 == 1:
                    # impera.g:139:31: ','
                    pass 
                    char_literal101 = self.match(self.input, 49, self.FOLLOW_49_in_list_def1041) 
                    if self._state.backtracking == 0:
                        stream_49.add(char_literal101)





                char_literal102 = self.match(self.input, 63, self.FOLLOW_63_in_list_def1044) 
                if self._state.backtracking == 0:
                    stream_63.add(char_literal102)


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
                    # 139:40: -> ^( LIST ( operand )+ )
                    # impera.g:139:43: ^( LIST ( operand )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_1)

                    # impera.g:139:50: ( operand )+
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "list_def"


    class index_arg_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "index_arg"
    # impera.g:142:1: index_arg : param_list ;
    def index_arg(self, ):
        retval = self.index_arg_return()
        retval.start = self.input.LT(1)


        root_0 = None

        param_list103 = None


        try:
            try:
                # impera.g:143:2: ( param_list )
                # impera.g:143:4: param_list
                pass 
                root_0 = self._adaptor.nil()


                self._state.following.append(self.FOLLOW_param_list_in_index_arg1065)
                param_list103 = self.param_list()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, param_list103.tree)




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



            except RecognitionException as re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "index_arg"


    class index_lookup_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "index_lookup"
    # impera.g:146:1: index_lookup : class_ref '[' index_arg ']' -> ^( HASH class_ref index_arg ) ;
    def index_lookup(self, ):
        retval = self.index_lookup_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal105 = None
        char_literal107 = None
        class_ref104 = None
        index_arg106 = None

        char_literal105_tree = None
        char_literal107_tree = None
        stream_62 = RewriteRuleTokenStream(self._adaptor, "token 62")
        stream_63 = RewriteRuleTokenStream(self._adaptor, "token 63")
        stream_index_arg = RewriteRuleSubtreeStream(self._adaptor, "rule index_arg")
        stream_class_ref = RewriteRuleSubtreeStream(self._adaptor, "rule class_ref")
        try:
            try:
                # impera.g:148:2: ( class_ref '[' index_arg ']' -> ^( HASH class_ref index_arg ) )
                # impera.g:148:4: class_ref '[' index_arg ']'
                pass 
                self._state.following.append(self.FOLLOW_class_ref_in_index_lookup1078)
                class_ref104 = self.class_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_class_ref.add(class_ref104.tree)


                char_literal105 = self.match(self.input, 62, self.FOLLOW_62_in_index_lookup1080) 
                if self._state.backtracking == 0:
                    stream_62.add(char_literal105)


                self._state.following.append(self.FOLLOW_index_arg_in_index_lookup1082)
                index_arg106 = self.index_arg()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_index_arg.add(index_arg106.tree)


                char_literal107 = self.match(self.input, 63, self.FOLLOW_63_in_index_lookup1084) 
                if self._state.backtracking == 0:
                    stream_63.add(char_literal107)


                # AST Rewrite
                # elements: index_arg, class_ref
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
                    # 148:32: -> ^( HASH class_ref index_arg )
                    # impera.g:148:35: ^( HASH class_ref index_arg )
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "index_lookup"


    class entity_body_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "entity_body"
    # impera.g:151:1: entity_body : ns_ref ID ( '=' constant )? -> ^( STATEMENT ns_ref ID ( constant )? ) ;
    def entity_body(self, ):
        retval = self.entity_body_return()
        retval.start = self.input.LT(1)


        root_0 = None

        ID109 = None
        char_literal110 = None
        ns_ref108 = None
        constant111 = None

        ID109_tree = None
        char_literal110_tree = None
        stream_58 = RewriteRuleTokenStream(self._adaptor, "token 58")
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_constant = RewriteRuleSubtreeStream(self._adaptor, "rule constant")
        stream_ns_ref = RewriteRuleSubtreeStream(self._adaptor, "rule ns_ref")
        try:
            try:
                # impera.g:152:2: ( ns_ref ID ( '=' constant )? -> ^( STATEMENT ns_ref ID ( constant )? ) )
                # impera.g:152:4: ns_ref ID ( '=' constant )?
                pass 
                self._state.following.append(self.FOLLOW_ns_ref_in_entity_body1105)
                ns_ref108 = self.ns_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_ns_ref.add(ns_ref108.tree)


                ID109 = self.match(self.input, ID, self.FOLLOW_ID_in_entity_body1107) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID109)


                # impera.g:152:14: ( '=' constant )?
                alt23 = 2
                LA23_0 = self.input.LA(1)

                if (LA23_0 == 58) :
                    alt23 = 1
                if alt23 == 1:
                    # impera.g:152:15: '=' constant
                    pass 
                    char_literal110 = self.match(self.input, 58, self.FOLLOW_58_in_entity_body1110) 
                    if self._state.backtracking == 0:
                        stream_58.add(char_literal110)


                    self._state.following.append(self.FOLLOW_constant_in_entity_body1112)
                    constant111 = self.constant()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_constant.add(constant111.tree)





                # AST Rewrite
                # elements: constant, ns_ref, ID
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
                    # 152:30: -> ^( STATEMENT ns_ref ID ( constant )? )
                    # impera.g:152:33: ^( STATEMENT ns_ref ID ( constant )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(STATEMENT, "STATEMENT")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_ns_ref.nextTree())

                    self._adaptor.addChild(root_1, 
                    stream_ID.nextNode()
                    )

                    # impera.g:152:55: ( constant )?
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "entity_body"


    class ns_ref_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "ns_ref"
    # impera.g:155:1: ns_ref : ID ( '::' ID )* -> ^( REF ( ID )+ ) ;
    def ns_ref(self, ):
        retval = self.ns_ref_return()
        retval.start = self.input.LT(1)


        root_0 = None

        ID112 = None
        string_literal113 = None
        ID114 = None

        ID112_tree = None
        string_literal113_tree = None
        ID114_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_54 = RewriteRuleTokenStream(self._adaptor, "token 54")

        try:
            try:
                # impera.g:156:2: ( ID ( '::' ID )* -> ^( REF ( ID )+ ) )
                # impera.g:156:4: ID ( '::' ID )*
                pass 
                ID112 = self.match(self.input, ID, self.FOLLOW_ID_in_ns_ref1139) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID112)


                # impera.g:156:7: ( '::' ID )*
                while True: #loop24
                    alt24 = 2
                    LA24_0 = self.input.LA(1)

                    if (LA24_0 == 54) :
                        alt24 = 1


                    if alt24 == 1:
                        # impera.g:156:8: '::' ID
                        pass 
                        string_literal113 = self.match(self.input, 54, self.FOLLOW_54_in_ns_ref1142) 
                        if self._state.backtracking == 0:
                            stream_54.add(string_literal113)


                        ID114 = self.match(self.input, ID, self.FOLLOW_ID_in_ns_ref1144) 
                        if self._state.backtracking == 0:
                            stream_ID.add(ID114)



                    else:
                        break #loop24


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
                    # 156:18: -> ^( REF ( ID )+ )
                    # impera.g:156:21: ^( REF ( ID )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(REF, "REF")
                    , root_1)

                    # impera.g:156:27: ( ID )+
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "ns_ref"


    class class_ref_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "class_ref"
    # impera.g:159:1: class_ref : (ns+= ID '::' )* CLASS_ID -> ^( CLASS_REF ^( NS ( $ns)* ) CLASS_ID ) ;
    def class_ref(self, ):
        retval = self.class_ref_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal115 = None
        CLASS_ID116 = None
        ns = None
        list_ns = None

        string_literal115_tree = None
        CLASS_ID116_tree = None
        ns_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_CLASS_ID = RewriteRuleTokenStream(self._adaptor, "token CLASS_ID")
        stream_54 = RewriteRuleTokenStream(self._adaptor, "token 54")

        try:
            try:
                # impera.g:160:5: ( (ns+= ID '::' )* CLASS_ID -> ^( CLASS_REF ^( NS ( $ns)* ) CLASS_ID ) )
                # impera.g:160:7: (ns+= ID '::' )* CLASS_ID
                pass 
                # impera.g:160:7: (ns+= ID '::' )*
                while True: #loop25
                    alt25 = 2
                    LA25_0 = self.input.LA(1)

                    if (LA25_0 == ID) :
                        alt25 = 1


                    if alt25 == 1:
                        # impera.g:160:8: ns+= ID '::'
                        pass 
                        ns = self.match(self.input, ID, self.FOLLOW_ID_in_class_ref1173) 
                        if self._state.backtracking == 0:
                            stream_ID.add(ns)

                        if list_ns is None:
                            list_ns = []
                        list_ns.append(ns)


                        string_literal115 = self.match(self.input, 54, self.FOLLOW_54_in_class_ref1175) 
                        if self._state.backtracking == 0:
                            stream_54.add(string_literal115)



                    else:
                        break #loop25


                CLASS_ID116 = self.match(self.input, CLASS_ID, self.FOLLOW_CLASS_ID_in_class_ref1179) 
                if self._state.backtracking == 0:
                    stream_CLASS_ID.add(CLASS_ID116)


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
                    # 160:31: -> ^( CLASS_REF ^( NS ( $ns)* ) CLASS_ID )
                    # impera.g:160:34: ^( CLASS_REF ^( NS ( $ns)* ) CLASS_ID )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(CLASS_REF, "CLASS_REF")
                    , root_1)

                    # impera.g:160:46: ^( NS ( $ns)* )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(NS, "NS")
                    , root_2)

                    # impera.g:160:52: ( $ns)*
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "class_ref"


    class variable_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "variable"
    # impera.g:163:1: variable : (ns+= ID '::' )* var= ID ( '.' attr+= ID )* -> ^( VAR_REF ^( NS ( $ns)* ) $var ^( ATTR ( $attr)* ) ) ;
    def variable(self, ):
        retval = self.variable_return()
        retval.start = self.input.LT(1)


        root_0 = None

        var = None
        string_literal117 = None
        char_literal118 = None
        ns = None
        attr = None
        list_ns = None
        list_attr = None

        var_tree = None
        string_literal117_tree = None
        char_literal118_tree = None
        ns_tree = None
        attr_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")
        stream_52 = RewriteRuleTokenStream(self._adaptor, "token 52")
        stream_54 = RewriteRuleTokenStream(self._adaptor, "token 54")

        try:
            try:
                # impera.g:164:2: ( (ns+= ID '::' )* var= ID ( '.' attr+= ID )* -> ^( VAR_REF ^( NS ( $ns)* ) $var ^( ATTR ( $attr)* ) ) )
                # impera.g:164:4: (ns+= ID '::' )* var= ID ( '.' attr+= ID )*
                pass 
                # impera.g:164:4: (ns+= ID '::' )*
                while True: #loop26
                    alt26 = 2
                    LA26_0 = self.input.LA(1)

                    if (LA26_0 == ID) :
                        LA26_1 = self.input.LA(2)

                        if (LA26_1 == 54) :
                            alt26 = 1




                    if alt26 == 1:
                        # impera.g:164:5: ns+= ID '::'
                        pass 
                        ns = self.match(self.input, ID, self.FOLLOW_ID_in_variable1213) 
                        if self._state.backtracking == 0:
                            stream_ID.add(ns)

                        if list_ns is None:
                            list_ns = []
                        list_ns.append(ns)


                        string_literal117 = self.match(self.input, 54, self.FOLLOW_54_in_variable1215) 
                        if self._state.backtracking == 0:
                            stream_54.add(string_literal117)



                    else:
                        break #loop26


                var = self.match(self.input, ID, self.FOLLOW_ID_in_variable1221) 
                if self._state.backtracking == 0:
                    stream_ID.add(var)


                # impera.g:164:26: ( '.' attr+= ID )*
                while True: #loop27
                    alt27 = 2
                    LA27_0 = self.input.LA(1)

                    if (LA27_0 == 52) :
                        alt27 = 1


                    if alt27 == 1:
                        # impera.g:164:27: '.' attr+= ID
                        pass 
                        char_literal118 = self.match(self.input, 52, self.FOLLOW_52_in_variable1224) 
                        if self._state.backtracking == 0:
                            stream_52.add(char_literal118)


                        attr = self.match(self.input, ID, self.FOLLOW_ID_in_variable1228) 
                        if self._state.backtracking == 0:
                            stream_ID.add(attr)

                        if list_attr is None:
                            list_attr = []
                        list_attr.append(attr)



                    else:
                        break #loop27


                # AST Rewrite
                # elements: attr, var, ns
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
                    # 164:42: -> ^( VAR_REF ^( NS ( $ns)* ) $var ^( ATTR ( $attr)* ) )
                    # impera.g:164:45: ^( VAR_REF ^( NS ( $ns)* ) $var ^( ATTR ( $attr)* ) )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(VAR_REF, "VAR_REF")
                    , root_1)

                    # impera.g:164:55: ^( NS ( $ns)* )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(NS, "NS")
                    , root_2)

                    # impera.g:164:61: ( $ns)*
                    while stream_ns.hasNext():
                        self._adaptor.addChild(root_2, stream_ns.nextNode())


                    stream_ns.reset();

                    self._adaptor.addChild(root_1, root_2)

                    self._adaptor.addChild(root_1, stream_var.nextNode())

                    # impera.g:164:71: ^( ATTR ( $attr)* )
                    root_2 = self._adaptor.nil()
                    root_2 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(ATTR, "ATTR")
                    , root_2)

                    # impera.g:164:79: ( $attr)*
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "variable"


    class arg_list_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "arg_list"
    # impera.g:167:1: arg_list : operand ( ',' operand )* ( ',' )? -> ^( LIST ( operand )+ ) ;
    def arg_list(self, ):
        retval = self.arg_list_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal120 = None
        char_literal122 = None
        operand119 = None
        operand121 = None

        char_literal120_tree = None
        char_literal122_tree = None
        stream_49 = RewriteRuleTokenStream(self._adaptor, "token 49")
        stream_operand = RewriteRuleSubtreeStream(self._adaptor, "rule operand")
        try:
            try:
                # impera.g:168:2: ( operand ( ',' operand )* ( ',' )? -> ^( LIST ( operand )+ ) )
                # impera.g:168:4: operand ( ',' operand )* ( ',' )?
                pass 
                self._state.following.append(self.FOLLOW_operand_in_arg_list1267)
                operand119 = self.operand()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_operand.add(operand119.tree)


                # impera.g:168:12: ( ',' operand )*
                while True: #loop28
                    alt28 = 2
                    LA28_0 = self.input.LA(1)

                    if (LA28_0 == 49) :
                        LA28_1 = self.input.LA(2)

                        if (LA28_1 in {CLASS_ID, FALSE, FLOAT, ID, INT, ML_STRING, REGEX, STRING, TRUE, 62}) :
                            alt28 = 1




                    if alt28 == 1:
                        # impera.g:168:13: ',' operand
                        pass 
                        char_literal120 = self.match(self.input, 49, self.FOLLOW_49_in_arg_list1270) 
                        if self._state.backtracking == 0:
                            stream_49.add(char_literal120)


                        self._state.following.append(self.FOLLOW_operand_in_arg_list1272)
                        operand121 = self.operand()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_operand.add(operand121.tree)



                    else:
                        break #loop28


                # impera.g:168:27: ( ',' )?
                alt29 = 2
                LA29_0 = self.input.LA(1)

                if (LA29_0 == 49) :
                    alt29 = 1
                if alt29 == 1:
                    # impera.g:168:27: ','
                    pass 
                    char_literal122 = self.match(self.input, 49, self.FOLLOW_49_in_arg_list1276) 
                    if self._state.backtracking == 0:
                        stream_49.add(char_literal122)





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
                    # 168:32: -> ^( LIST ( operand )+ )
                    # impera.g:168:35: ^( LIST ( operand )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(LIST, "LIST")
                    , root_1)

                    # impera.g:168:42: ( operand )+
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "arg_list"


    class call_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "call"
    # impera.g:171:1: call : ( ( ns_ref '(' )=> function_call | ( class_ref '(' )=> constructor );
    def call(self, ):
        retval = self.call_return()
        retval.start = self.input.LT(1)


        root_0 = None

        function_call123 = None
        constructor124 = None


        try:
            try:
                # impera.g:172:9: ( ( ns_ref '(' )=> function_call | ( class_ref '(' )=> constructor )
                alt30 = 2
                alt30 = self.dfa30.predict(self.input)
                if alt30 == 1:
                    # impera.g:172:11: ( ns_ref '(' )=> function_call
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_function_call_in_call1312)
                    function_call123 = self.function_call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, function_call123.tree)



                elif alt30 == 2:
                    # impera.g:173:11: ( class_ref '(' )=> constructor
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_constructor_in_call1333)
                    constructor124 = self.constructor()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, constructor124.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



            except RecognitionException as re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "call"


    class function_call_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "function_call"
    # impera.g:176:1: function_call : ns_ref '(' ( arg_list )? ')' -> ^( CALL ns_ref ( arg_list )? ) ;
    def function_call(self, ):
        retval = self.function_call_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal126 = None
        char_literal128 = None
        ns_ref125 = None
        arg_list127 = None

        char_literal126_tree = None
        char_literal128_tree = None
        stream_47 = RewriteRuleTokenStream(self._adaptor, "token 47")
        stream_48 = RewriteRuleTokenStream(self._adaptor, "token 48")
        stream_ns_ref = RewriteRuleSubtreeStream(self._adaptor, "rule ns_ref")
        stream_arg_list = RewriteRuleSubtreeStream(self._adaptor, "rule arg_list")
        try:
            try:
                # impera.g:177:2: ( ns_ref '(' ( arg_list )? ')' -> ^( CALL ns_ref ( arg_list )? ) )
                # impera.g:177:4: ns_ref '(' ( arg_list )? ')'
                pass 
                self._state.following.append(self.FOLLOW_ns_ref_in_function_call1352)
                ns_ref125 = self.ns_ref()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_ns_ref.add(ns_ref125.tree)


                char_literal126 = self.match(self.input, 47, self.FOLLOW_47_in_function_call1354) 
                if self._state.backtracking == 0:
                    stream_47.add(char_literal126)


                # impera.g:177:15: ( arg_list )?
                alt31 = 2
                LA31_0 = self.input.LA(1)

                if (LA31_0 in {CLASS_ID, FALSE, FLOAT, ID, INT, ML_STRING, REGEX, STRING, TRUE, 62}) :
                    alt31 = 1
                if alt31 == 1:
                    # impera.g:177:15: arg_list
                    pass 
                    self._state.following.append(self.FOLLOW_arg_list_in_function_call1356)
                    arg_list127 = self.arg_list()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_arg_list.add(arg_list127.tree)





                char_literal128 = self.match(self.input, 48, self.FOLLOW_48_in_function_call1359) 
                if self._state.backtracking == 0:
                    stream_48.add(char_literal128)


                # AST Rewrite
                # elements: arg_list, ns_ref
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
                    # 177:29: -> ^( CALL ns_ref ( arg_list )? )
                    # impera.g:177:32: ^( CALL ns_ref ( arg_list )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(
                    self._adaptor.createFromType(CALL, "CALL")
                    , root_1)

                    self._adaptor.addChild(root_1, stream_ns_ref.nextTree())

                    # impera.g:177:46: ( arg_list )?
                    if stream_arg_list.hasNext():
                        self._adaptor.addChild(root_1, stream_arg_list.nextTree())


                    stream_arg_list.reset();

                    self._adaptor.addChild(root_0, root_1)




                    retval.tree = root_0





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



            except RecognitionException as re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "function_call"


    class un_op_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "un_op"
    # impera.g:179:1: un_op : 'not' ;
    def un_op(self, ):
        retval = self.un_op_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal129 = None

        string_literal129_tree = None

        try:
            try:
                # impera.g:180:2: ( 'not' )
                # impera.g:180:4: 'not'
                pass 
                root_0 = self._adaptor.nil()


                string_literal129 = self.match(self.input, 75, self.FOLLOW_75_in_un_op1380)
                if self._state.backtracking == 0:
                    string_literal129_tree = self._adaptor.createWithPayload(string_literal129)
                    self._adaptor.addChild(root_0, string_literal129_tree)





                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



            except RecognitionException as re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "un_op"


    class cmp_op_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "cmp_op"
    # impera.g:183:1: cmp_op : ( '==' | '!=' | '<=' | '>=' | '<' | '>' );
    def cmp_op(self, ):
        retval = self.cmp_op_return()
        retval.start = self.input.LT(1)


        root_0 = None

        set130 = None

        set130_tree = None

        try:
            try:
                # impera.g:184:2: ( '==' | '!=' | '<=' | '>=' | '<' | '>' )
                # impera.g:
                pass 
                root_0 = self._adaptor.nil()


                set130 = self.input.LT(1)

                if self.input.LA(1) in {46, 55, 57, 59, 60, 61}:
                    self.input.consume()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set130))

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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "cmp_op"


    class cmp_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "cmp"
    # impera.g:187:1: cmp : ( ( operand 'in' )=> operand 'in' in_oper -> ^( OP 'in' operand in_oper ) | ( operand cmp_op )=> operand cmp_op operand -> ^( OP cmp_op ( operand )+ ) | function_call -> ^( OP function_call ) );
    def cmp(self, ):
        retval = self.cmp_return()
        retval.start = self.input.LT(1)


        root_0 = None

        string_literal132 = None
        operand131 = None
        in_oper133 = None
        operand134 = None
        cmp_op135 = None
        operand136 = None
        function_call137 = None

        string_literal132_tree = None
        stream_72 = RewriteRuleTokenStream(self._adaptor, "token 72")
        stream_function_call = RewriteRuleSubtreeStream(self._adaptor, "rule function_call")
        stream_in_oper = RewriteRuleSubtreeStream(self._adaptor, "rule in_oper")
        stream_operand = RewriteRuleSubtreeStream(self._adaptor, "rule operand")
        stream_cmp_op = RewriteRuleSubtreeStream(self._adaptor, "rule cmp_op")
        try:
            try:
                # impera.g:188:2: ( ( operand 'in' )=> operand 'in' in_oper -> ^( OP 'in' operand in_oper ) | ( operand cmp_op )=> operand cmp_op operand -> ^( OP cmp_op ( operand )+ ) | function_call -> ^( OP function_call ) )
                alt32 = 3
                LA32 = self.input.LA(1)
                if LA32 in {FALSE, FLOAT, INT, ML_STRING, REGEX, STRING, TRUE}:
                    LA32_1 = self.input.LA(2)

                    if (self.synpred8_impera()) :
                        alt32 = 1
                    elif (self.synpred9_impera()) :
                        alt32 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 32, 1, self.input)

                        raise nvae


                elif LA32 in {62}:
                    LA32_2 = self.input.LA(2)

                    if (self.synpred8_impera()) :
                        alt32 = 1
                    elif (self.synpred9_impera()) :
                        alt32 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 32, 2, self.input)

                        raise nvae


                elif LA32 in {ID}:
                    LA32_3 = self.input.LA(2)

                    if (self.synpred8_impera()) :
                        alt32 = 1
                    elif (self.synpred9_impera()) :
                        alt32 = 2
                    elif (True) :
                        alt32 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 32, 3, self.input)

                        raise nvae


                elif LA32 in {CLASS_ID}:
                    LA32_4 = self.input.LA(2)

                    if (self.synpred8_impera()) :
                        alt32 = 1
                    elif (self.synpred9_impera()) :
                        alt32 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 32, 4, self.input)

                        raise nvae


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 32, 0, self.input)

                    raise nvae


                if alt32 == 1:
                    # impera.g:188:4: ( operand 'in' )=> operand 'in' in_oper
                    pass 
                    self._state.following.append(self.FOLLOW_operand_in_cmp1433)
                    operand131 = self.operand()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_operand.add(operand131.tree)


                    string_literal132 = self.match(self.input, 72, self.FOLLOW_72_in_cmp1435) 
                    if self._state.backtracking == 0:
                        stream_72.add(string_literal132)


                    self._state.following.append(self.FOLLOW_in_oper_in_cmp1437)
                    in_oper133 = self.in_oper()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_in_oper.add(in_oper133.tree)


                    # AST Rewrite
                    # elements: operand, 72, in_oper
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
                        # 188:43: -> ^( OP 'in' operand in_oper )
                        # impera.g:188:46: ^( OP 'in' operand in_oper )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(OP, "OP")
                        , root_1)

                        self._adaptor.addChild(root_1, 
                        stream_72.nextNode()
                        )

                        self._adaptor.addChild(root_1, stream_operand.nextTree())

                        self._adaptor.addChild(root_1, stream_in_oper.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt32 == 2:
                    # impera.g:189:4: ( operand cmp_op )=> operand cmp_op operand
                    pass 
                    self._state.following.append(self.FOLLOW_operand_in_cmp1462)
                    operand134 = self.operand()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_operand.add(operand134.tree)


                    self._state.following.append(self.FOLLOW_cmp_op_in_cmp1464)
                    cmp_op135 = self.cmp_op()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_cmp_op.add(cmp_op135.tree)


                    self._state.following.append(self.FOLLOW_operand_in_cmp1466)
                    operand136 = self.operand()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_operand.add(operand136.tree)


                    # AST Rewrite
                    # elements: operand, cmp_op
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
                        # 189:47: -> ^( OP cmp_op ( operand )+ )
                        # impera.g:189:50: ^( OP cmp_op ( operand )+ )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(OP, "OP")
                        , root_1)

                        self._adaptor.addChild(root_1, stream_cmp_op.nextTree())

                        # impera.g:189:62: ( operand )+
                        if not (stream_operand.hasNext()):
                            raise RewriteEarlyExitException()

                        while stream_operand.hasNext():
                            self._adaptor.addChild(root_1, stream_operand.nextTree())


                        stream_operand.reset()

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt32 == 3:
                    # impera.g:190:4: function_call
                    pass 
                    self._state.following.append(self.FOLLOW_function_call_in_cmp1482)
                    function_call137 = self.function_call()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_function_call.add(function_call137.tree)


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
                        # 190:18: -> ^( OP function_call )
                        # impera.g:190:21: ^( OP function_call )
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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "cmp"


    class log_op_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "log_op"
    # impera.g:193:1: log_op : ( 'and' | 'or' );
    def log_op(self, ):
        retval = self.log_op_return()
        retval.start = self.input.LT(1)


        root_0 = None

        set138 = None

        set138_tree = None

        try:
            try:
                # impera.g:194:2: ( 'and' | 'or' )
                # impera.g:
                pass 
                root_0 = self._adaptor.nil()


                set138 = self.input.LT(1)

                if self.input.LA(1) in {64, 76}:
                    self.input.consume()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set138))

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
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "log_op"


    class in_oper_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "in_oper"
    # impera.g:197:1: in_oper : ( list_def | variable );
    def in_oper(self, ):
        retval = self.in_oper_return()
        retval.start = self.input.LT(1)


        root_0 = None

        list_def139 = None
        variable140 = None


        try:
            try:
                # impera.g:198:2: ( list_def | variable )
                alt33 = 2
                LA33_0 = self.input.LA(1)

                if (LA33_0 == 62) :
                    alt33 = 1
                elif (LA33_0 == ID) :
                    alt33 = 2
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 33, 0, self.input)

                    raise nvae


                if alt33 == 1:
                    # impera.g:198:4: list_def
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_list_def_in_in_oper1518)
                    list_def139 = self.list_def()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, list_def139.tree)



                elif alt33 == 2:
                    # impera.g:198:15: variable
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_variable_in_in_oper1522)
                    variable140 = self.variable()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, variable140.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



            except RecognitionException as re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "in_oper"


    class log_oper_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "log_oper"
    # impera.g:201:1: log_oper : ( cmp | TRUE | FALSE );
    def log_oper(self, ):
        retval = self.log_oper_return()
        retval.start = self.input.LT(1)


        root_0 = None

        TRUE142 = None
        FALSE143 = None
        cmp141 = None

        TRUE142_tree = None
        FALSE143_tree = None

        try:
            try:
                # impera.g:202:2: ( cmp | TRUE | FALSE )
                alt34 = 3
                LA34 = self.input.LA(1)
                if LA34 in {TRUE}:
                    LA34_1 = self.input.LA(2)

                    if (LA34_1 in {46, 55, 57, 59, 60, 61, 72}) :
                        alt34 = 1
                    elif (LA34_1 in {EOF, CLASS_ID, ID, ML_STRING, 48, 64, 67, 69, 70, 71, 73, 76, 77}) :
                        alt34 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 34, 1, self.input)

                        raise nvae


                elif LA34 in {CLASS_ID, FLOAT, ID, INT, ML_STRING, REGEX, STRING, 62}:
                    alt34 = 1
                elif LA34 in {FALSE}:
                    LA34_3 = self.input.LA(2)

                    if (LA34_3 in {46, 55, 57, 59, 60, 61, 72}) :
                        alt34 = 1
                    elif (LA34_3 in {EOF, CLASS_ID, ID, ML_STRING, 48, 64, 67, 69, 70, 71, 73, 76, 77}) :
                        alt34 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 34, 3, self.input)

                        raise nvae


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 34, 0, self.input)

                    raise nvae


                if alt34 == 1:
                    # impera.g:202:4: cmp
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_cmp_in_log_oper1535)
                    cmp141 = self.cmp()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, cmp141.tree)



                elif alt34 == 2:
                    # impera.g:202:10: TRUE
                    pass 
                    root_0 = self._adaptor.nil()


                    TRUE142 = self.match(self.input, TRUE, self.FOLLOW_TRUE_in_log_oper1539)
                    if self._state.backtracking == 0:
                        TRUE142_tree = self._adaptor.createWithPayload(TRUE142)
                        self._adaptor.addChild(root_0, TRUE142_tree)




                elif alt34 == 3:
                    # impera.g:202:17: FALSE
                    pass 
                    root_0 = self._adaptor.nil()


                    FALSE143 = self.match(self.input, FALSE, self.FOLLOW_FALSE_in_log_oper1543)
                    if self._state.backtracking == 0:
                        FALSE143_tree = self._adaptor.createWithPayload(FALSE143)
                        self._adaptor.addChild(root_0, FALSE143_tree)




                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



            except RecognitionException as re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "log_oper"


    class log_expr_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "log_expr"
    # impera.g:205:1: log_expr : ( ( log_oper log_op )=> log_oper log_op log_expr -> ^( OP log_op log_oper log_expr ) | log_oper );
    def log_expr(self, ):
        retval = self.log_expr_return()
        retval.start = self.input.LT(1)


        root_0 = None

        log_oper144 = None
        log_op145 = None
        log_expr146 = None
        log_oper147 = None

        stream_log_expr = RewriteRuleSubtreeStream(self._adaptor, "rule log_expr")
        stream_log_op = RewriteRuleSubtreeStream(self._adaptor, "rule log_op")
        stream_log_oper = RewriteRuleSubtreeStream(self._adaptor, "rule log_oper")
        try:
            try:
                # impera.g:207:2: ( ( log_oper log_op )=> log_oper log_op log_expr -> ^( OP log_op log_oper log_expr ) | log_oper )
                alt35 = 2
                LA35 = self.input.LA(1)
                if LA35 in {TRUE}:
                    LA35_1 = self.input.LA(2)

                    if (self.synpred10_impera()) :
                        alt35 = 1
                    elif (True) :
                        alt35 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 35, 1, self.input)

                        raise nvae


                elif LA35 in {62}:
                    LA35_2 = self.input.LA(2)

                    if (self.synpred10_impera()) :
                        alt35 = 1
                    elif (True) :
                        alt35 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 35, 2, self.input)

                        raise nvae


                elif LA35 in {ID}:
                    LA35_3 = self.input.LA(2)

                    if (self.synpred10_impera()) :
                        alt35 = 1
                    elif (True) :
                        alt35 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 35, 3, self.input)

                        raise nvae


                elif LA35 in {CLASS_ID}:
                    LA35_4 = self.input.LA(2)

                    if (self.synpred10_impera()) :
                        alt35 = 1
                    elif (True) :
                        alt35 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 35, 4, self.input)

                        raise nvae


                elif LA35 in {FALSE}:
                    LA35_5 = self.input.LA(2)

                    if (self.synpred10_impera()) :
                        alt35 = 1
                    elif (True) :
                        alt35 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 35, 5, self.input)

                        raise nvae


                elif LA35 in {FLOAT, INT, ML_STRING, REGEX, STRING}:
                    LA35_6 = self.input.LA(2)

                    if (self.synpred10_impera()) :
                        alt35 = 1
                    elif (True) :
                        alt35 = 2
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 35, 6, self.input)

                        raise nvae


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 35, 0, self.input)

                    raise nvae


                if alt35 == 1:
                    # impera.g:207:4: ( log_oper log_op )=> log_oper log_op log_expr
                    pass 
                    self._state.following.append(self.FOLLOW_log_oper_in_log_expr1564)
                    log_oper144 = self.log_oper()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_log_oper.add(log_oper144.tree)


                    self._state.following.append(self.FOLLOW_log_op_in_log_expr1566)
                    log_op145 = self.log_op()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_log_op.add(log_op145.tree)


                    self._state.following.append(self.FOLLOW_log_expr_in_log_expr1568)
                    log_expr146 = self.log_expr()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_log_expr.add(log_expr146.tree)


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
                        # 207:50: -> ^( OP log_op log_oper log_expr )
                        # impera.g:207:53: ^( OP log_op log_oper log_expr )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(OP, "OP")
                        , root_1)

                        self._adaptor.addChild(root_1, stream_log_op.nextTree())

                        self._adaptor.addChild(root_1, stream_log_oper.nextTree())

                        self._adaptor.addChild(root_1, stream_log_expr.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt35 == 2:
                    # impera.g:208:4: log_oper
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_log_oper_in_log_expr1585)
                    log_oper147 = self.log_oper()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, log_oper147.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



            except RecognitionException as re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "log_expr"


    class expression_return(ParserRuleReturnScope):
        def __init__(self):
            super().__init__()

            self.tree = None





    # $ANTLR start "expression"
    # impera.g:211:1: expression : ( '(' expression ')' ( log_op expression )? -> ^( OP ( log_op )? ( expression )+ ) | ( log_expr log_op )=> log_expr log_op '(' expression ')' -> ^( OP log_op log_expr expression ) | log_expr );
    def expression(self, ):
        retval = self.expression_return()
        retval.start = self.input.LT(1)


        root_0 = None

        char_literal148 = None
        char_literal150 = None
        char_literal155 = None
        char_literal157 = None
        expression149 = None
        log_op151 = None
        expression152 = None
        log_expr153 = None
        log_op154 = None
        expression156 = None
        log_expr158 = None

        char_literal148_tree = None
        char_literal150_tree = None
        char_literal155_tree = None
        char_literal157_tree = None
        stream_47 = RewriteRuleTokenStream(self._adaptor, "token 47")
        stream_48 = RewriteRuleTokenStream(self._adaptor, "token 48")
        stream_log_expr = RewriteRuleSubtreeStream(self._adaptor, "rule log_expr")
        stream_expression = RewriteRuleSubtreeStream(self._adaptor, "rule expression")
        stream_log_op = RewriteRuleSubtreeStream(self._adaptor, "rule log_op")
        try:
            try:
                # impera.g:212:2: ( '(' expression ')' ( log_op expression )? -> ^( OP ( log_op )? ( expression )+ ) | ( log_expr log_op )=> log_expr log_op '(' expression ')' -> ^( OP log_op log_expr expression ) | log_expr )
                alt37 = 3
                LA37 = self.input.LA(1)
                if LA37 in {47}:
                    alt37 = 1
                elif LA37 in {TRUE}:
                    LA37_2 = self.input.LA(2)

                    if (self.synpred11_impera()) :
                        alt37 = 2
                    elif (True) :
                        alt37 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 37, 2, self.input)

                        raise nvae


                elif LA37 in {62}:
                    LA37_3 = self.input.LA(2)

                    if (self.synpred11_impera()) :
                        alt37 = 2
                    elif (True) :
                        alt37 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 37, 3, self.input)

                        raise nvae


                elif LA37 in {ID}:
                    LA37_4 = self.input.LA(2)

                    if (self.synpred11_impera()) :
                        alt37 = 2
                    elif (True) :
                        alt37 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 37, 4, self.input)

                        raise nvae


                elif LA37 in {CLASS_ID}:
                    LA37_5 = self.input.LA(2)

                    if (self.synpred11_impera()) :
                        alt37 = 2
                    elif (True) :
                        alt37 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 37, 5, self.input)

                        raise nvae


                elif LA37 in {FALSE}:
                    LA37_6 = self.input.LA(2)

                    if (self.synpred11_impera()) :
                        alt37 = 2
                    elif (True) :
                        alt37 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 37, 6, self.input)

                        raise nvae


                elif LA37 in {FLOAT, INT, ML_STRING, REGEX, STRING}:
                    LA37_7 = self.input.LA(2)

                    if (self.synpred11_impera()) :
                        alt37 = 2
                    elif (True) :
                        alt37 = 3
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed


                        nvae = NoViableAltException("", 37, 7, self.input)

                        raise nvae


                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed


                    nvae = NoViableAltException("", 37, 0, self.input)

                    raise nvae


                if alt37 == 1:
                    # impera.g:212:4: '(' expression ')' ( log_op expression )?
                    pass 
                    char_literal148 = self.match(self.input, 47, self.FOLLOW_47_in_expression1597) 
                    if self._state.backtracking == 0:
                        stream_47.add(char_literal148)


                    self._state.following.append(self.FOLLOW_expression_in_expression1599)
                    expression149 = self.expression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_expression.add(expression149.tree)


                    char_literal150 = self.match(self.input, 48, self.FOLLOW_48_in_expression1601) 
                    if self._state.backtracking == 0:
                        stream_48.add(char_literal150)


                    # impera.g:212:23: ( log_op expression )?
                    alt36 = 2
                    LA36_0 = self.input.LA(1)

                    if (LA36_0 in {64, 76}) :
                        alt36 = 1
                    if alt36 == 1:
                        # impera.g:212:24: log_op expression
                        pass 
                        self._state.following.append(self.FOLLOW_log_op_in_expression1604)
                        log_op151 = self.log_op()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_log_op.add(log_op151.tree)


                        self._state.following.append(self.FOLLOW_expression_in_expression1606)
                        expression152 = self.expression()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_expression.add(expression152.tree)





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
                        # 212:44: -> ^( OP ( log_op )? ( expression )+ )
                        # impera.g:212:47: ^( OP ( log_op )? ( expression )+ )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(OP, "OP")
                        , root_1)

                        # impera.g:212:52: ( log_op )?
                        if stream_log_op.hasNext():
                            self._adaptor.addChild(root_1, stream_log_op.nextTree())


                        stream_log_op.reset();

                        # impera.g:212:60: ( expression )+
                        if not (stream_expression.hasNext()):
                            raise RewriteEarlyExitException()

                        while stream_expression.hasNext():
                            self._adaptor.addChild(root_1, stream_expression.nextTree())


                        stream_expression.reset()

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt37 == 2:
                    # impera.g:213:4: ( log_expr log_op )=> log_expr log_op '(' expression ')'
                    pass 
                    self._state.following.append(self.FOLLOW_log_expr_in_expression1633)
                    log_expr153 = self.log_expr()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_log_expr.add(log_expr153.tree)


                    self._state.following.append(self.FOLLOW_log_op_in_expression1635)
                    log_op154 = self.log_op()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_log_op.add(log_op154.tree)


                    char_literal155 = self.match(self.input, 47, self.FOLLOW_47_in_expression1637) 
                    if self._state.backtracking == 0:
                        stream_47.add(char_literal155)


                    self._state.following.append(self.FOLLOW_expression_in_expression1639)
                    expression156 = self.expression()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_expression.add(expression156.tree)


                    char_literal157 = self.match(self.input, 48, self.FOLLOW_48_in_expression1641) 
                    if self._state.backtracking == 0:
                        stream_48.add(char_literal157)


                    # AST Rewrite
                    # elements: log_expr, log_op, expression
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
                        # 213:60: -> ^( OP log_op log_expr expression )
                        # impera.g:213:63: ^( OP log_op log_expr expression )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(
                        self._adaptor.createFromType(OP, "OP")
                        , root_1)

                        self._adaptor.addChild(root_1, stream_log_op.nextTree())

                        self._adaptor.addChild(root_1, stream_log_expr.nextTree())

                        self._adaptor.addChild(root_1, stream_expression.nextTree())

                        self._adaptor.addChild(root_0, root_1)




                        retval.tree = root_0




                elif alt37 == 3:
                    # impera.g:214:4: log_expr
                    pass 
                    root_0 = self._adaptor.nil()


                    self._state.following.append(self.FOLLOW_log_expr_in_expression1658)
                    log_expr158 = self.log_expr()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, log_expr158.tree)



                retval.stop = self.input.LT(-1)


                if self._state.backtracking == 0:
                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)



            except RecognitionException as re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)

        finally:
            pass
        return retval

    # $ANTLR end "expression"

    # $ANTLR start "synpred1_impera"
    def synpred1_impera_fragment(self, ):
        # impera.g:80:4: ( INT )
        # impera.g:80:5: INT
        pass 
        root_0 = self._adaptor.nil()


        self.match(self.input, INT, self.FOLLOW_INT_in_synpred1_impera542)




    # $ANTLR end "synpred1_impera"



    # $ANTLR start "synpred2_impera"
    def synpred2_impera_fragment(self, ):
        # impera.g:81:4: ( INT ':' )
        # impera.g:81:5: INT ':'
        pass 
        root_0 = self._adaptor.nil()


        self.match(self.input, INT, self.FOLLOW_INT_in_synpred2_impera561)


        self.match(self.input, 53, self.FOLLOW_53_in_synpred2_impera563)




    # $ANTLR end "synpred2_impera"



    # $ANTLR start "synpred3_impera"
    def synpred3_impera_fragment(self, ):
        # impera.g:82:4: ( INT ':' INT )
        # impera.g:82:5: INT ':' INT
        pass 
        root_0 = self._adaptor.nil()


        self.match(self.input, INT, self.FOLLOW_INT_in_synpred3_impera586)


        self.match(self.input, 53, self.FOLLOW_53_in_synpred3_impera588)


        self.match(self.input, INT, self.FOLLOW_INT_in_synpred3_impera590)




    # $ANTLR end "synpred3_impera"



    # $ANTLR start "synpred4_impera"
    def synpred4_impera_fragment(self, ):
        # impera.g:83:4: ( ':' INT )
        # impera.g:83:5: ':' INT
        pass 
        root_0 = self._adaptor.nil()


        self.match(self.input, 53, self.FOLLOW_53_in_synpred4_impera615)


        self.match(self.input, INT, self.FOLLOW_INT_in_synpred4_impera617)




    # $ANTLR end "synpred4_impera"



    # $ANTLR start "synpred5_impera"
    def synpred5_impera_fragment(self, ):
        # impera.g:99:4: ( 'for' )
        # impera.g:99:5: 'for'
        pass 
        root_0 = self._adaptor.nil()


        self.match(self.input, 69, self.FOLLOW_69_in_synpred5_impera754)




    # $ANTLR end "synpred5_impera"



    # $ANTLR start "synpred6_impera"
    def synpred6_impera_fragment(self, ):
        # impera.g:172:11: ( ns_ref '(' )
        # impera.g:172:12: ns_ref '('
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_ns_ref_in_synpred6_impera1305)
        self.ns_ref()

        self._state.following.pop()


        self.match(self.input, 47, self.FOLLOW_47_in_synpred6_impera1307)




    # $ANTLR end "synpred6_impera"



    # $ANTLR start "synpred7_impera"
    def synpred7_impera_fragment(self, ):
        # impera.g:173:11: ( class_ref '(' )
        # impera.g:173:12: class_ref '('
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_class_ref_in_synpred7_impera1325)
        self.class_ref()

        self._state.following.pop()


        self.match(self.input, 47, self.FOLLOW_47_in_synpred7_impera1327)




    # $ANTLR end "synpred7_impera"



    # $ANTLR start "synpred8_impera"
    def synpred8_impera_fragment(self, ):
        # impera.g:188:4: ( operand 'in' )
        # impera.g:188:5: operand 'in'
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_operand_in_synpred8_impera1426)
        self.operand()

        self._state.following.pop()


        self.match(self.input, 72, self.FOLLOW_72_in_synpred8_impera1428)




    # $ANTLR end "synpred8_impera"



    # $ANTLR start "synpred9_impera"
    def synpred9_impera_fragment(self, ):
        # impera.g:189:4: ( operand cmp_op )
        # impera.g:189:5: operand cmp_op
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_operand_in_synpred9_impera1455)
        self.operand()

        self._state.following.pop()


        self._state.following.append(self.FOLLOW_cmp_op_in_synpred9_impera1457)
        self.cmp_op()

        self._state.following.pop()




    # $ANTLR end "synpred9_impera"



    # $ANTLR start "synpred10_impera"
    def synpred10_impera_fragment(self, ):
        # impera.g:207:4: ( log_oper log_op )
        # impera.g:207:5: log_oper log_op
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_log_oper_in_synpred10_impera1557)
        self.log_oper()

        self._state.following.pop()


        self._state.following.append(self.FOLLOW_log_op_in_synpred10_impera1559)
        self.log_op()

        self._state.following.pop()




    # $ANTLR end "synpred10_impera"



    # $ANTLR start "synpred11_impera"
    def synpred11_impera_fragment(self, ):
        # impera.g:213:4: ( log_expr log_op )
        # impera.g:213:5: log_expr log_op
        pass 
        root_0 = self._adaptor.nil()


        self._state.following.append(self.FOLLOW_log_expr_in_synpred11_impera1626)
        self.log_expr()

        self._state.following.pop()


        self._state.following.append(self.FOLLOW_log_op_in_synpred11_impera1628)
        self.log_op()

        self._state.following.pop()




    # $ANTLR end "synpred11_impera"




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
        "\1\7\2\uffff\1\57\1\31\2\uffff\1\7\1\57"
        )

    DFA1_max = DFA.unpack(
        "\1\115\2\uffff\1\72\1\57\2\uffff\1\31\1\72"
        )

    DFA1_accept = DFA.unpack(
        "\1\uffff\1\4\1\1\2\uffff\1\2\1\3\2\uffff"
        )

    DFA1_special = DFA.unpack(
        "\11\uffff"
        )


    DFA1_transition = [
        DFA.unpack("\1\4\21\uffff\1\3\5\uffff\1\6\43\uffff\1\2\1\uffff\1"
        "\5\2\2\1\uffff\1\2\3\uffff\1\2"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\5\4\uffff\1\5\1\uffff\1\7\3\uffff\1\5"),
        DFA.unpack("\1\2\25\uffff\1\5"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\4\21\uffff\1\10"),
        DFA.unpack("\1\5\4\uffff\1\5\1\uffff\1\7\3\uffff\1\5")
    ]

    # class definition for DFA #1

    class DFA1(DFA):
        pass


    # lookup tables for DFA #14

    DFA14_eot = DFA.unpack(
        "\7\uffff"
        )

    DFA14_eof = DFA.unpack(
        "\7\uffff"
        )

    DFA14_min = DFA.unpack(
        "\1\7\1\uffff\1\57\1\uffff\1\7\1\uffff\1\57"
        )

    DFA14_max = DFA.unpack(
        "\1\105\1\uffff\1\72\1\uffff\1\31\1\uffff\1\72"
        )

    DFA14_accept = DFA.unpack(
        "\1\uffff\1\1\1\uffff\1\3\1\uffff\1\2\1\uffff"
        )

    DFA14_special = DFA.unpack(
        "\1\0\6\uffff"
        )


    DFA14_transition = [
        DFA.unpack("\1\3\21\uffff\1\2\53\uffff\1\1"),
        DFA.unpack(""),
        DFA.unpack("\1\3\4\uffff\1\5\1\uffff\1\4\3\uffff\1\5"),
        DFA.unpack(""),
        DFA.unpack("\1\3\21\uffff\1\6"),
        DFA.unpack(""),
        DFA.unpack("\1\3\4\uffff\1\5\1\uffff\1\4\3\uffff\1\5")
    ]

    # class definition for DFA #14

    class DFA14(DFA):
        pass


        def specialStateTransition(self_, s, input):
            # convince pylint that my self_ magic is ok ;)
            # pylint: disable-msg=E0213

            # pretend we are a member of the recognizer
            # thus semantic predicates can be evaluated
            self = self_.recognizer

            _s = s

            if s == 0: 
                LA14_0 = input.LA(1)

                 
                index14_0 = input.index()
                input.rewind()

                s = -1
                if (LA14_0 == 69) and (self.synpred5_impera()):
                    s = 1

                elif (LA14_0 == ID):
                    s = 2

                elif (LA14_0 == CLASS_ID):
                    s = 3

                 
                input.seek(index14_0)

                if s >= 0:
                    return s

            if self._state.backtracking > 0:
                raise BacktrackingFailed

            nvae = NoViableAltException(self_.getDescription(), 14, _s, input)
            self_.error(nvae)
            raise nvae

    # lookup tables for DFA #20

    DFA20_eot = DFA.unpack(
        "\12\uffff"
        )

    DFA20_eof = DFA.unpack(
        "\3\uffff\1\7\5\uffff\1\7"
        )

    DFA20_min = DFA.unpack(
        "\1\7\2\uffff\1\7\1\57\1\7\3\uffff\1\7"
        )

    DFA20_max = DFA.unpack(
        "\1\76\2\uffff\1\115\1\76\1\31\3\uffff\1\115"
        )

    DFA20_accept = DFA.unpack(
        "\1\uffff\1\1\1\2\3\uffff\1\4\1\5\1\3\1\uffff"
        )

    DFA20_special = DFA.unpack(
        "\12\uffff"
        )


    DFA20_transition = [
        DFA.unpack("\1\4\14\uffff\2\1\3\uffff\1\3\2\uffff\1\1\2\uffff\1\1"
        "\7\uffff\1\1\1\uffff\2\1\23\uffff\1\2"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\7\21\uffff\1\7\5\uffff\1\7\16\uffff\1\7\1\6\2\7\2"
        "\uffff\1\7\1\uffff\1\5\1\7\1\uffff\1\7\1\uffff\3\7\1\uffff\2\7\1"
        "\uffff\2\7\1\uffff\5\7\2\uffff\2\7"),
        DFA.unpack("\1\6\16\uffff\1\10"),
        DFA.unpack("\1\4\21\uffff\1\11"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\7\21\uffff\1\7\5\uffff\1\7\16\uffff\1\7\1\6\2\7\2"
        "\uffff\1\7\1\uffff\1\5\1\7\1\uffff\1\7\1\uffff\3\7\1\uffff\2\7\1"
        "\uffff\2\7\1\uffff\5\7\2\uffff\2\7")
    ]

    # class definition for DFA #20

    class DFA20(DFA):
        pass


    # lookup tables for DFA #30

    DFA30_eot = DFA.unpack(
        "\6\uffff"
        )

    DFA30_eof = DFA.unpack(
        "\6\uffff"
        )

    DFA30_min = DFA.unpack(
        "\1\7\1\57\1\uffff\1\7\1\uffff\1\57"
        )

    DFA30_max = DFA.unpack(
        "\1\31\1\66\1\uffff\1\31\1\uffff\1\66"
        )

    DFA30_accept = DFA.unpack(
        "\2\uffff\1\2\1\uffff\1\1\1\uffff"
        )

    DFA30_special = DFA.unpack(
        "\1\2\1\0\1\uffff\1\1\1\uffff\1\3"
        )


    DFA30_transition = [
        DFA.unpack("\1\2\21\uffff\1\1"),
        DFA.unpack("\1\4\6\uffff\1\3"),
        DFA.unpack(""),
        DFA.unpack("\1\2\21\uffff\1\5"),
        DFA.unpack(""),
        DFA.unpack("\1\4\6\uffff\1\3")
    ]

    # class definition for DFA #30

    class DFA30(DFA):
        pass


        def specialStateTransition(self_, s, input):
            # convince pylint that my self_ magic is ok ;)
            # pylint: disable-msg=E0213

            # pretend we are a member of the recognizer
            # thus semantic predicates can be evaluated
            self = self_.recognizer

            _s = s

            if s == 0: 
                LA30_1 = input.LA(1)

                 
                index30_1 = input.index()
                input.rewind()

                s = -1
                if (LA30_1 == 54):
                    s = 3

                elif (LA30_1 == 47) and (self.synpred6_impera()):
                    s = 4

                 
                input.seek(index30_1)

                if s >= 0:
                    return s
            elif s == 1: 
                LA30_3 = input.LA(1)

                 
                index30_3 = input.index()
                input.rewind()

                s = -1
                if (LA30_3 == ID):
                    s = 5

                elif (LA30_3 == CLASS_ID) and (self.synpred7_impera()):
                    s = 2

                 
                input.seek(index30_3)

                if s >= 0:
                    return s
            elif s == 2: 
                LA30_0 = input.LA(1)

                 
                index30_0 = input.index()
                input.rewind()

                s = -1
                if (LA30_0 == ID):
                    s = 1

                elif (LA30_0 == CLASS_ID) and (self.synpred7_impera()):
                    s = 2

                 
                input.seek(index30_0)

                if s >= 0:
                    return s
            elif s == 3: 
                LA30_5 = input.LA(1)

                 
                index30_5 = input.index()
                input.rewind()

                s = -1
                if (LA30_5 == 54):
                    s = 3

                elif (LA30_5 == 47) and (self.synpred6_impera()):
                    s = 4

                 
                input.seek(index30_5)

                if s >= 0:
                    return s

            if self._state.backtracking > 0:
                raise BacktrackingFailed

            nvae = NoViableAltException(self_.getDescription(), 30, _s, input)
            self_.error(nvae)
            raise nvae

 

    FOLLOW_def_statement_in_main153 = frozenset([1, 7, 25, 31, 67, 69, 70, 71, 73, 77])
    FOLLOW_top_statement_in_main157 = frozenset([1, 7, 25, 31, 67, 69, 70, 71, 73, 77])
    FOLLOW_ML_STRING_in_main161 = frozenset([1, 7, 25, 31, 67, 69, 70, 71, 73, 77])
    FOLLOW_typedef_in_def_statement189 = frozenset([1])
    FOLLOW_entity_def_in_def_statement193 = frozenset([1])
    FOLLOW_implementation_def_in_def_statement197 = frozenset([1])
    FOLLOW_relation_in_def_statement201 = frozenset([1])
    FOLLOW_index_in_def_statement205 = frozenset([1])
    FOLLOW_implement_def_in_def_statement209 = frozenset([1])
    FOLLOW_77_in_typedef220 = frozenset([25])
    FOLLOW_ID_in_typedef222 = frozenset([65])
    FOLLOW_65_in_typedef224 = frozenset([25])
    FOLLOW_ns_ref_in_typedef226 = frozenset([74])
    FOLLOW_74_in_typedef228 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 47, 62])
    FOLLOW_REGEX_in_typedef231 = frozenset([1])
    FOLLOW_expression_in_typedef235 = frozenset([1])
    FOLLOW_77_in_typedef257 = frozenset([7])
    FOLLOW_CLASS_ID_in_typedef259 = frozenset([65])
    FOLLOW_65_in_typedef261 = frozenset([7, 25])
    FOLLOW_constructor_in_typedef263 = frozenset([1])
    FOLLOW_67_in_entity_def293 = frozenset([7])
    FOLLOW_CLASS_ID_in_entity_def295 = frozenset([53, 68])
    FOLLOW_68_in_entity_def298 = frozenset([7, 25])
    FOLLOW_class_ref_in_entity_def300 = frozenset([49, 53])
    FOLLOW_49_in_entity_def303 = frozenset([7, 25])
    FOLLOW_class_ref_in_entity_def305 = frozenset([49, 53])
    FOLLOW_53_in_entity_def312 = frozenset([25, 31, 66])
    FOLLOW_ML_STRING_in_entity_def314 = frozenset([25, 66])
    FOLLOW_entity_body_in_entity_def318 = frozenset([25, 66])
    FOLLOW_66_in_entity_def322 = frozenset([1])
    FOLLOW_71_in_implementation_def365 = frozenset([25])
    FOLLOW_ID_in_implementation_def367 = frozenset([53, 69])
    FOLLOW_69_in_implementation_def370 = frozenset([7, 25])
    FOLLOW_class_ref_in_implementation_def372 = frozenset([53])
    FOLLOW_implementation_in_implementation_def376 = frozenset([1])
    FOLLOW_73_in_index408 = frozenset([7, 25])
    FOLLOW_class_ref_in_index410 = frozenset([47])
    FOLLOW_47_in_index412 = frozenset([25])
    FOLLOW_ID_in_index414 = frozenset([48, 49])
    FOLLOW_49_in_index417 = frozenset([25])
    FOLLOW_ID_in_index419 = frozenset([48, 49])
    FOLLOW_48_in_index423 = frozenset([1])
    FOLLOW_70_in_implement_def450 = frozenset([7, 25])
    FOLLOW_class_ref_in_implement_def452 = frozenset([78])
    FOLLOW_78_in_implement_def454 = frozenset([25])
    FOLLOW_ns_ref_in_implement_def456 = frozenset([1, 49, 79])
    FOLLOW_49_in_implement_def459 = frozenset([25])
    FOLLOW_ns_ref_in_implement_def461 = frozenset([1, 49, 79])
    FOLLOW_79_in_implement_def466 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 47, 62])
    FOLLOW_expression_in_implement_def468 = frozenset([1])
    FOLLOW_class_ref_in_relation_end501 = frozenset([25])
    FOLLOW_ID_in_relation_end503 = frozenset([1])
    FOLLOW_INT_in_multiplicity_body547 = frozenset([1])
    FOLLOW_INT_in_multiplicity_body568 = frozenset([53])
    FOLLOW_53_in_multiplicity_body570 = frozenset([1])
    FOLLOW_INT_in_multiplicity_body595 = frozenset([53])
    FOLLOW_53_in_multiplicity_body597 = frozenset([28])
    FOLLOW_INT_in_multiplicity_body599 = frozenset([1])
    FOLLOW_53_in_multiplicity_body622 = frozenset([28])
    FOLLOW_INT_in_multiplicity_body624 = frozenset([1])
    FOLLOW_62_in_multiplicity645 = frozenset([28, 53])
    FOLLOW_multiplicity_body_in_multiplicity647 = frozenset([63])
    FOLLOW_63_in_multiplicity649 = frozenset([1])
    FOLLOW_relation_end_in_relation675 = frozenset([62])
    FOLLOW_multiplicity_in_relation679 = frozenset([50, 51, 56])
    FOLLOW_relation_link_in_relation682 = frozenset([62])
    FOLLOW_multiplicity_in_relation687 = frozenset([7, 25])
    FOLLOW_relation_end_in_relation691 = frozenset([1])
    FOLLOW_69_in_top_statement759 = frozenset([25])
    FOLLOW_ID_in_top_statement761 = frozenset([72])
    FOLLOW_72_in_top_statement763 = frozenset([25])
    FOLLOW_variable_in_top_statement765 = frozenset([53])
    FOLLOW_implementation_in_top_statement767 = frozenset([1])
    FOLLOW_variable_in_top_statement785 = frozenset([58])
    FOLLOW_58_in_top_statement787 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 62])
    FOLLOW_operand_in_top_statement789 = frozenset([1])
    FOLLOW_call_in_top_statement804 = frozenset([1])
    FOLLOW_53_in_implementation815 = frozenset([7, 25, 31, 66, 69])
    FOLLOW_ML_STRING_in_implementation817 = frozenset([7, 25, 66, 69])
    FOLLOW_statement_in_implementation820 = frozenset([7, 25, 66, 69])
    FOLLOW_66_in_implementation823 = frozenset([1])
    FOLLOW_top_statement_in_statement843 = frozenset([1])
    FOLLOW_ID_in_parameter863 = frozenset([58])
    FOLLOW_58_in_parameter865 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 62])
    FOLLOW_operand_in_parameter867 = frozenset([1])
    FOLLOW_class_ref_in_constructor888 = frozenset([47])
    FOLLOW_47_in_constructor890 = frozenset([25, 48])
    FOLLOW_param_list_in_constructor892 = frozenset([48])
    FOLLOW_48_in_constructor895 = frozenset([1])
    FOLLOW_parameter_in_param_list920 = frozenset([1, 49])
    FOLLOW_49_in_param_list923 = frozenset([25])
    FOLLOW_parameter_in_param_list925 = frozenset([1, 49])
    FOLLOW_49_in_param_list929 = frozenset([1])
    FOLLOW_constant_in_operand952 = frozenset([1])
    FOLLOW_list_def_in_operand957 = frozenset([1])
    FOLLOW_index_lookup_in_operand962 = frozenset([1])
    FOLLOW_call_in_operand967 = frozenset([1])
    FOLLOW_variable_in_operand972 = frozenset([1])
    FOLLOW_62_in_list_def1030 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 62])
    FOLLOW_operand_in_list_def1032 = frozenset([49, 63])
    FOLLOW_49_in_list_def1035 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 62])
    FOLLOW_operand_in_list_def1037 = frozenset([49, 63])
    FOLLOW_49_in_list_def1041 = frozenset([63])
    FOLLOW_63_in_list_def1044 = frozenset([1])
    FOLLOW_param_list_in_index_arg1065 = frozenset([1])
    FOLLOW_class_ref_in_index_lookup1078 = frozenset([62])
    FOLLOW_62_in_index_lookup1080 = frozenset([25])
    FOLLOW_index_arg_in_index_lookup1082 = frozenset([63])
    FOLLOW_63_in_index_lookup1084 = frozenset([1])
    FOLLOW_ns_ref_in_entity_body1105 = frozenset([25])
    FOLLOW_ID_in_entity_body1107 = frozenset([1, 58])
    FOLLOW_58_in_entity_body1110 = frozenset([20, 21, 28, 31, 39, 41, 42])
    FOLLOW_constant_in_entity_body1112 = frozenset([1])
    FOLLOW_ID_in_ns_ref1139 = frozenset([1, 54])
    FOLLOW_54_in_ns_ref1142 = frozenset([25])
    FOLLOW_ID_in_ns_ref1144 = frozenset([1, 54])
    FOLLOW_ID_in_class_ref1173 = frozenset([54])
    FOLLOW_54_in_class_ref1175 = frozenset([7, 25])
    FOLLOW_CLASS_ID_in_class_ref1179 = frozenset([1])
    FOLLOW_ID_in_variable1213 = frozenset([54])
    FOLLOW_54_in_variable1215 = frozenset([25])
    FOLLOW_ID_in_variable1221 = frozenset([1, 52])
    FOLLOW_52_in_variable1224 = frozenset([25])
    FOLLOW_ID_in_variable1228 = frozenset([1, 52])
    FOLLOW_operand_in_arg_list1267 = frozenset([1, 49])
    FOLLOW_49_in_arg_list1270 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 62])
    FOLLOW_operand_in_arg_list1272 = frozenset([1, 49])
    FOLLOW_49_in_arg_list1276 = frozenset([1])
    FOLLOW_function_call_in_call1312 = frozenset([1])
    FOLLOW_constructor_in_call1333 = frozenset([1])
    FOLLOW_ns_ref_in_function_call1352 = frozenset([47])
    FOLLOW_47_in_function_call1354 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 48, 62])
    FOLLOW_arg_list_in_function_call1356 = frozenset([48])
    FOLLOW_48_in_function_call1359 = frozenset([1])
    FOLLOW_75_in_un_op1380 = frozenset([1])
    FOLLOW_operand_in_cmp1433 = frozenset([72])
    FOLLOW_72_in_cmp1435 = frozenset([25, 62])
    FOLLOW_in_oper_in_cmp1437 = frozenset([1])
    FOLLOW_operand_in_cmp1462 = frozenset([46, 55, 57, 59, 60, 61])
    FOLLOW_cmp_op_in_cmp1464 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 62])
    FOLLOW_operand_in_cmp1466 = frozenset([1])
    FOLLOW_function_call_in_cmp1482 = frozenset([1])
    FOLLOW_list_def_in_in_oper1518 = frozenset([1])
    FOLLOW_variable_in_in_oper1522 = frozenset([1])
    FOLLOW_cmp_in_log_oper1535 = frozenset([1])
    FOLLOW_TRUE_in_log_oper1539 = frozenset([1])
    FOLLOW_FALSE_in_log_oper1543 = frozenset([1])
    FOLLOW_log_oper_in_log_expr1564 = frozenset([64, 76])
    FOLLOW_log_op_in_log_expr1566 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 62])
    FOLLOW_log_expr_in_log_expr1568 = frozenset([1])
    FOLLOW_log_oper_in_log_expr1585 = frozenset([1])
    FOLLOW_47_in_expression1597 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 47, 62])
    FOLLOW_expression_in_expression1599 = frozenset([48])
    FOLLOW_48_in_expression1601 = frozenset([1, 64, 76])
    FOLLOW_log_op_in_expression1604 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 47, 62])
    FOLLOW_expression_in_expression1606 = frozenset([1])
    FOLLOW_log_expr_in_expression1633 = frozenset([64, 76])
    FOLLOW_log_op_in_expression1635 = frozenset([47])
    FOLLOW_47_in_expression1637 = frozenset([7, 20, 21, 25, 28, 31, 39, 41, 42, 47, 62])
    FOLLOW_expression_in_expression1639 = frozenset([48])
    FOLLOW_48_in_expression1641 = frozenset([1])
    FOLLOW_log_expr_in_expression1658 = frozenset([1])
    FOLLOW_INT_in_synpred1_impera542 = frozenset([1])
    FOLLOW_INT_in_synpred2_impera561 = frozenset([53])
    FOLLOW_53_in_synpred2_impera563 = frozenset([1])
    FOLLOW_INT_in_synpred3_impera586 = frozenset([53])
    FOLLOW_53_in_synpred3_impera588 = frozenset([28])
    FOLLOW_INT_in_synpred3_impera590 = frozenset([1])
    FOLLOW_53_in_synpred4_impera615 = frozenset([28])
    FOLLOW_INT_in_synpred4_impera617 = frozenset([1])
    FOLLOW_69_in_synpred5_impera754 = frozenset([1])
    FOLLOW_ns_ref_in_synpred6_impera1305 = frozenset([47])
    FOLLOW_47_in_synpred6_impera1307 = frozenset([1])
    FOLLOW_class_ref_in_synpred7_impera1325 = frozenset([47])
    FOLLOW_47_in_synpred7_impera1327 = frozenset([1])
    FOLLOW_operand_in_synpred8_impera1426 = frozenset([72])
    FOLLOW_72_in_synpred8_impera1428 = frozenset([1])
    FOLLOW_operand_in_synpred9_impera1455 = frozenset([46, 55, 57, 59, 60, 61])
    FOLLOW_cmp_op_in_synpred9_impera1457 = frozenset([1])
    FOLLOW_log_oper_in_synpred10_impera1557 = frozenset([64, 76])
    FOLLOW_log_op_in_synpred10_impera1559 = frozenset([1])
    FOLLOW_log_expr_in_synpred11_impera1626 = frozenset([64, 76])
    FOLLOW_log_op_in_synpred11_impera1628 = frozenset([1])



def main(argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    from antlr3.main import ParserMain
    main = ParserMain("imperaLexer", imperaParser)

    main.stdin = stdin
    main.stdout = stdout
    main.stderr = stderr
    main.execute(argv)



if __name__ == '__main__':
    main(sys.argv)
