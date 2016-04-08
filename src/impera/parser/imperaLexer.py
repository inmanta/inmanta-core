# @PydevCodeAnalysisIgnore
# $ANTLR 3.5.2 impera.g 2016-04-08 15:45:49

import sys
from antlr3 import *



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

class imperaLexer(Lexer):

    grammarFileName = "impera.g"
    api_version = 1

    def __init__(self, input=None, state=None):
        if state is None:
            state = RecognizerSharedState()
        super().__init__(input, state)

        self.delegates = []

        self.dfa10 = self.DFA10(
            self, 10,
            eot = self.DFA10_eot,
            eof = self.DFA10_eof,
            min = self.DFA10_min,
            max = self.DFA10_max,
            accept = self.DFA10_accept,
            special = self.DFA10_special,
            transition = self.DFA10_transition
            )

        self.dfa24 = self.DFA24(
            self, 24,
            eot = self.DFA24_eot,
            eof = self.DFA24_eof,
            min = self.DFA24_min,
            max = self.DFA24_max,
            accept = self.DFA24_accept,
            special = self.DFA24_special,
            transition = self.DFA24_transition
            )






    # $ANTLR start "T__46"
    def mT__46(self, ):
        try:
            _type = T__46
            _channel = DEFAULT_CHANNEL

            # impera.g:7:7: ( '!=' )
            # impera.g:7:9: '!='
            pass 
            self.match("!=")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__46"



    # $ANTLR start "T__47"
    def mT__47(self, ):
        try:
            _type = T__47
            _channel = DEFAULT_CHANNEL

            # impera.g:8:7: ( '(' )
            # impera.g:8:9: '('
            pass 
            self.match(40)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__47"



    # $ANTLR start "T__48"
    def mT__48(self, ):
        try:
            _type = T__48
            _channel = DEFAULT_CHANNEL

            # impera.g:9:7: ( ')' )
            # impera.g:9:9: ')'
            pass 
            self.match(41)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__48"



    # $ANTLR start "T__49"
    def mT__49(self, ):
        try:
            _type = T__49
            _channel = DEFAULT_CHANNEL

            # impera.g:10:7: ( ',' )
            # impera.g:10:9: ','
            pass 
            self.match(44)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__49"



    # $ANTLR start "T__50"
    def mT__50(self, ):
        try:
            _type = T__50
            _channel = DEFAULT_CHANNEL

            # impera.g:11:7: ( '--' )
            # impera.g:11:9: '--'
            pass 
            self.match("--")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__50"



    # $ANTLR start "T__51"
    def mT__51(self, ):
        try:
            _type = T__51
            _channel = DEFAULT_CHANNEL

            # impera.g:12:7: ( '->' )
            # impera.g:12:9: '->'
            pass 
            self.match("->")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__51"



    # $ANTLR start "T__52"
    def mT__52(self, ):
        try:
            _type = T__52
            _channel = DEFAULT_CHANNEL

            # impera.g:13:7: ( '.' )
            # impera.g:13:9: '.'
            pass 
            self.match(46)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__52"



    # $ANTLR start "T__53"
    def mT__53(self, ):
        try:
            _type = T__53
            _channel = DEFAULT_CHANNEL

            # impera.g:14:7: ( ':' )
            # impera.g:14:9: ':'
            pass 
            self.match(58)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__53"



    # $ANTLR start "T__54"
    def mT__54(self, ):
        try:
            _type = T__54
            _channel = DEFAULT_CHANNEL

            # impera.g:15:7: ( '::' )
            # impera.g:15:9: '::'
            pass 
            self.match("::")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__54"



    # $ANTLR start "T__55"
    def mT__55(self, ):
        try:
            _type = T__55
            _channel = DEFAULT_CHANNEL

            # impera.g:16:7: ( '<' )
            # impera.g:16:9: '<'
            pass 
            self.match(60)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__55"



    # $ANTLR start "T__56"
    def mT__56(self, ):
        try:
            _type = T__56
            _channel = DEFAULT_CHANNEL

            # impera.g:17:7: ( '<-' )
            # impera.g:17:9: '<-'
            pass 
            self.match("<-")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__56"



    # $ANTLR start "T__57"
    def mT__57(self, ):
        try:
            _type = T__57
            _channel = DEFAULT_CHANNEL

            # impera.g:18:7: ( '<=' )
            # impera.g:18:9: '<='
            pass 
            self.match("<=")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__57"



    # $ANTLR start "T__58"
    def mT__58(self, ):
        try:
            _type = T__58
            _channel = DEFAULT_CHANNEL

            # impera.g:19:7: ( '=' )
            # impera.g:19:9: '='
            pass 
            self.match(61)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__58"



    # $ANTLR start "T__59"
    def mT__59(self, ):
        try:
            _type = T__59
            _channel = DEFAULT_CHANNEL

            # impera.g:20:7: ( '==' )
            # impera.g:20:9: '=='
            pass 
            self.match("==")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__59"



    # $ANTLR start "T__60"
    def mT__60(self, ):
        try:
            _type = T__60
            _channel = DEFAULT_CHANNEL

            # impera.g:21:7: ( '>' )
            # impera.g:21:9: '>'
            pass 
            self.match(62)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__60"



    # $ANTLR start "T__61"
    def mT__61(self, ):
        try:
            _type = T__61
            _channel = DEFAULT_CHANNEL

            # impera.g:22:7: ( '>=' )
            # impera.g:22:9: '>='
            pass 
            self.match(">=")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__61"



    # $ANTLR start "T__62"
    def mT__62(self, ):
        try:
            _type = T__62
            _channel = DEFAULT_CHANNEL

            # impera.g:23:7: ( '[' )
            # impera.g:23:9: '['
            pass 
            self.match(91)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__62"



    # $ANTLR start "T__63"
    def mT__63(self, ):
        try:
            _type = T__63
            _channel = DEFAULT_CHANNEL

            # impera.g:24:7: ( ']' )
            # impera.g:24:9: ']'
            pass 
            self.match(93)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__63"



    # $ANTLR start "T__64"
    def mT__64(self, ):
        try:
            _type = T__64
            _channel = DEFAULT_CHANNEL

            # impera.g:25:7: ( 'and' )
            # impera.g:25:9: 'and'
            pass 
            self.match("and")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__64"



    # $ANTLR start "T__65"
    def mT__65(self, ):
        try:
            _type = T__65
            _channel = DEFAULT_CHANNEL

            # impera.g:26:7: ( 'as' )
            # impera.g:26:9: 'as'
            pass 
            self.match("as")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__65"



    # $ANTLR start "T__66"
    def mT__66(self, ):
        try:
            _type = T__66
            _channel = DEFAULT_CHANNEL

            # impera.g:27:7: ( 'end' )
            # impera.g:27:9: 'end'
            pass 
            self.match("end")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__66"



    # $ANTLR start "T__67"
    def mT__67(self, ):
        try:
            _type = T__67
            _channel = DEFAULT_CHANNEL

            # impera.g:28:7: ( 'entity' )
            # impera.g:28:9: 'entity'
            pass 
            self.match("entity")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__67"



    # $ANTLR start "T__68"
    def mT__68(self, ):
        try:
            _type = T__68
            _channel = DEFAULT_CHANNEL

            # impera.g:29:7: ( 'extends' )
            # impera.g:29:9: 'extends'
            pass 
            self.match("extends")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__68"



    # $ANTLR start "T__69"
    def mT__69(self, ):
        try:
            _type = T__69
            _channel = DEFAULT_CHANNEL

            # impera.g:30:7: ( 'for' )
            # impera.g:30:9: 'for'
            pass 
            self.match("for")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__69"



    # $ANTLR start "T__70"
    def mT__70(self, ):
        try:
            _type = T__70
            _channel = DEFAULT_CHANNEL

            # impera.g:31:7: ( 'implement' )
            # impera.g:31:9: 'implement'
            pass 
            self.match("implement")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__70"



    # $ANTLR start "T__71"
    def mT__71(self, ):
        try:
            _type = T__71
            _channel = DEFAULT_CHANNEL

            # impera.g:32:7: ( 'implementation' )
            # impera.g:32:9: 'implementation'
            pass 
            self.match("implementation")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__71"



    # $ANTLR start "T__72"
    def mT__72(self, ):
        try:
            _type = T__72
            _channel = DEFAULT_CHANNEL

            # impera.g:33:7: ( 'in' )
            # impera.g:33:9: 'in'
            pass 
            self.match("in")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__72"



    # $ANTLR start "T__73"
    def mT__73(self, ):
        try:
            _type = T__73
            _channel = DEFAULT_CHANNEL

            # impera.g:34:7: ( 'index' )
            # impera.g:34:9: 'index'
            pass 
            self.match("index")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__73"



    # $ANTLR start "T__74"
    def mT__74(self, ):
        try:
            _type = T__74
            _channel = DEFAULT_CHANNEL

            # impera.g:35:7: ( 'matching' )
            # impera.g:35:9: 'matching'
            pass 
            self.match("matching")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__74"



    # $ANTLR start "T__75"
    def mT__75(self, ):
        try:
            _type = T__75
            _channel = DEFAULT_CHANNEL

            # impera.g:36:7: ( 'not' )
            # impera.g:36:9: 'not'
            pass 
            self.match("not")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__75"



    # $ANTLR start "T__76"
    def mT__76(self, ):
        try:
            _type = T__76
            _channel = DEFAULT_CHANNEL

            # impera.g:37:7: ( 'or' )
            # impera.g:37:9: 'or'
            pass 
            self.match("or")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__76"



    # $ANTLR start "T__77"
    def mT__77(self, ):
        try:
            _type = T__77
            _channel = DEFAULT_CHANNEL

            # impera.g:38:7: ( 'typedef' )
            # impera.g:38:9: 'typedef'
            pass 
            self.match("typedef")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__77"



    # $ANTLR start "T__78"
    def mT__78(self, ):
        try:
            _type = T__78
            _channel = DEFAULT_CHANNEL

            # impera.g:39:7: ( 'using' )
            # impera.g:39:9: 'using'
            pass 
            self.match("using")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__78"



    # $ANTLR start "T__79"
    def mT__79(self, ):
        try:
            _type = T__79
            _channel = DEFAULT_CHANNEL

            # impera.g:40:7: ( 'when' )
            # impera.g:40:9: 'when'
            pass 
            self.match("when")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "T__79"



    # $ANTLR start "TRUE"
    def mTRUE(self, ):
        try:
            _type = TRUE
            _channel = DEFAULT_CHANNEL

            # impera.g:218:2: ( 'true' )
            # impera.g:218:4: 'true'
            pass 
            self.match("true")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "TRUE"



    # $ANTLR start "FALSE"
    def mFALSE(self, ):
        try:
            _type = FALSE
            _channel = DEFAULT_CHANNEL

            # impera.g:222:2: ( 'false' )
            # impera.g:222:4: 'false'
            pass 
            self.match("false")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "FALSE"



    # $ANTLR start "ID"
    def mID(self, ):
        try:
            _type = ID
            _channel = DEFAULT_CHANNEL

            # impera.g:225:4: ( ( 'a' .. 'z' | '_' ) ( 'a' .. 'z' | 'A' .. 'Z' | '0' .. '9' | '_' | '-' )* )
            # impera.g:225:6: ( 'a' .. 'z' | '_' ) ( 'a' .. 'z' | 'A' .. 'Z' | '0' .. '9' | '_' | '-' )*
            pass 
            if (97 <= self.input.LA(1) <= 122) or self.input.LA(1) in {95}:
                self.input.consume()
            else:
                mse = MismatchedSetException(None, self.input)
                self.recover(mse)
                raise mse



            # impera.g:225:22: ( 'a' .. 'z' | 'A' .. 'Z' | '0' .. '9' | '_' | '-' )*
            while True: #loop1
                alt1 = 2
                LA1_0 = self.input.LA(1)

                if ((48 <= LA1_0 <= 57) or (65 <= LA1_0 <= 90) or (97 <= LA1_0 <= 122) or LA1_0 in {45, 95}) :
                    alt1 = 1


                if alt1 == 1:
                    # impera.g:
                    pass 
                    if (48 <= self.input.LA(1) <= 57) or (65 <= self.input.LA(1) <= 90) or (97 <= self.input.LA(1) <= 122) or self.input.LA(1) in {45, 95}:
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse




                else:
                    break #loop1




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "ID"



    # $ANTLR start "CLASS_ID"
    def mCLASS_ID(self, ):
        try:
            _type = CLASS_ID
            _channel = DEFAULT_CHANNEL

            # impera.g:229:2: ( ( 'A' .. 'Z' ) ( 'a' .. 'z' | 'A' .. 'Z' | '0' .. '9' | '_' | '-' )* )
            # impera.g:229:5: ( 'A' .. 'Z' ) ( 'a' .. 'z' | 'A' .. 'Z' | '0' .. '9' | '_' | '-' )*
            pass 
            if (65 <= self.input.LA(1) <= 90) or self.input.LA(1) in {}:
                self.input.consume()
            else:
                mse = MismatchedSetException(None, self.input)
                self.recover(mse)
                raise mse



            # impera.g:229:16: ( 'a' .. 'z' | 'A' .. 'Z' | '0' .. '9' | '_' | '-' )*
            while True: #loop2
                alt2 = 2
                LA2_0 = self.input.LA(1)

                if ((48 <= LA2_0 <= 57) or (65 <= LA2_0 <= 90) or (97 <= LA2_0 <= 122) or LA2_0 in {45, 95}) :
                    alt2 = 1


                if alt2 == 1:
                    # impera.g:
                    pass 
                    if (48 <= self.input.LA(1) <= 57) or (65 <= self.input.LA(1) <= 90) or (97 <= self.input.LA(1) <= 122) or self.input.LA(1) in {45, 95}:
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse




                else:
                    break #loop2




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "CLASS_ID"



    # $ANTLR start "INT"
    def mINT(self, ):
        try:
            _type = INT
            _channel = DEFAULT_CHANNEL

            # impera.g:232:5: ( ( '0' .. '9' )+ )
            # impera.g:232:7: ( '0' .. '9' )+
            pass 
            # impera.g:232:7: ( '0' .. '9' )+
            cnt3 = 0
            while True: #loop3
                alt3 = 2
                LA3_0 = self.input.LA(1)

                if ((48 <= LA3_0 <= 57) or LA3_0 in {}) :
                    alt3 = 1


                if alt3 == 1:
                    # impera.g:
                    pass 
                    if (48 <= self.input.LA(1) <= 57) or self.input.LA(1) in {}:
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse




                else:
                    if cnt3 >= 1:
                        break #loop3

                    eee = EarlyExitException(3, self.input)
                    raise eee

                cnt3 += 1




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "INT"



    # $ANTLR start "FLOAT"
    def mFLOAT(self, ):
        try:
            _type = FLOAT
            _channel = DEFAULT_CHANNEL

            # impera.g:236:5: ( ( '0' .. '9' )+ '.' ( '0' .. '9' )* ( EXPONENT )? | '.' ( '0' .. '9' )+ ( EXPONENT )? | ( '0' .. '9' )+ EXPONENT )
            alt10 = 3
            alt10 = self.dfa10.predict(self.input)
            if alt10 == 1:
                # impera.g:236:9: ( '0' .. '9' )+ '.' ( '0' .. '9' )* ( EXPONENT )?
                pass 
                # impera.g:236:9: ( '0' .. '9' )+
                cnt4 = 0
                while True: #loop4
                    alt4 = 2
                    LA4_0 = self.input.LA(1)

                    if ((48 <= LA4_0 <= 57) or LA4_0 in {}) :
                        alt4 = 1


                    if alt4 == 1:
                        # impera.g:
                        pass 
                        if (48 <= self.input.LA(1) <= 57) or self.input.LA(1) in {}:
                            self.input.consume()
                        else:
                            mse = MismatchedSetException(None, self.input)
                            self.recover(mse)
                            raise mse




                    else:
                        if cnt4 >= 1:
                            break #loop4

                        eee = EarlyExitException(4, self.input)
                        raise eee

                    cnt4 += 1


                self.match(46)

                # impera.g:236:25: ( '0' .. '9' )*
                while True: #loop5
                    alt5 = 2
                    LA5_0 = self.input.LA(1)

                    if ((48 <= LA5_0 <= 57) or LA5_0 in {}) :
                        alt5 = 1


                    if alt5 == 1:
                        # impera.g:
                        pass 
                        if (48 <= self.input.LA(1) <= 57) or self.input.LA(1) in {}:
                            self.input.consume()
                        else:
                            mse = MismatchedSetException(None, self.input)
                            self.recover(mse)
                            raise mse




                    else:
                        break #loop5


                # impera.g:236:37: ( EXPONENT )?
                alt6 = 2
                LA6_0 = self.input.LA(1)

                if (LA6_0 in {69, 101}) :
                    alt6 = 1
                if alt6 == 1:
                    # impera.g:236:37: EXPONENT
                    pass 
                    self.mEXPONENT()






            elif alt10 == 2:
                # impera.g:237:9: '.' ( '0' .. '9' )+ ( EXPONENT )?
                pass 
                self.match(46)

                # impera.g:237:13: ( '0' .. '9' )+
                cnt7 = 0
                while True: #loop7
                    alt7 = 2
                    LA7_0 = self.input.LA(1)

                    if ((48 <= LA7_0 <= 57) or LA7_0 in {}) :
                        alt7 = 1


                    if alt7 == 1:
                        # impera.g:
                        pass 
                        if (48 <= self.input.LA(1) <= 57) or self.input.LA(1) in {}:
                            self.input.consume()
                        else:
                            mse = MismatchedSetException(None, self.input)
                            self.recover(mse)
                            raise mse




                    else:
                        if cnt7 >= 1:
                            break #loop7

                        eee = EarlyExitException(7, self.input)
                        raise eee

                    cnt7 += 1


                # impera.g:237:25: ( EXPONENT )?
                alt8 = 2
                LA8_0 = self.input.LA(1)

                if (LA8_0 in {69, 101}) :
                    alt8 = 1
                if alt8 == 1:
                    # impera.g:237:25: EXPONENT
                    pass 
                    self.mEXPONENT()






            elif alt10 == 3:
                # impera.g:238:9: ( '0' .. '9' )+ EXPONENT
                pass 
                # impera.g:238:9: ( '0' .. '9' )+
                cnt9 = 0
                while True: #loop9
                    alt9 = 2
                    LA9_0 = self.input.LA(1)

                    if ((48 <= LA9_0 <= 57) or LA9_0 in {}) :
                        alt9 = 1


                    if alt9 == 1:
                        # impera.g:
                        pass 
                        if (48 <= self.input.LA(1) <= 57) or self.input.LA(1) in {}:
                            self.input.consume()
                        else:
                            mse = MismatchedSetException(None, self.input)
                            self.recover(mse)
                            raise mse




                    else:
                        if cnt9 >= 1:
                            break #loop9

                        eee = EarlyExitException(9, self.input)
                        raise eee

                    cnt9 += 1


                self.mEXPONENT()



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "FLOAT"



    # $ANTLR start "COMMENT"
    def mCOMMENT(self, ):
        try:
            _type = COMMENT
            _channel = DEFAULT_CHANNEL

            # impera.g:242:5: ( '//' (~ ( '\\n' | '\\r' ) )* ( '\\r' )? '\\n' | '#' (~ ( '\\n' | '\\r' ) )* ( '\\r' )? '\\n' | '/*' ( options {greedy=false; } : . )* '*/' )
            alt16 = 3
            LA16_0 = self.input.LA(1)

            if (LA16_0 == 47) :
                LA16_1 = self.input.LA(2)

                if (LA16_1 == 47) :
                    alt16 = 1
                elif (LA16_1 == 42) :
                    alt16 = 3
                else:
                    nvae = NoViableAltException("", 16, 1, self.input)

                    raise nvae


            elif (LA16_0 == 35) :
                alt16 = 2
            else:
                nvae = NoViableAltException("", 16, 0, self.input)

                raise nvae


            if alt16 == 1:
                # impera.g:242:9: '//' (~ ( '\\n' | '\\r' ) )* ( '\\r' )? '\\n'
                pass 
                self.match("//")


                # impera.g:242:14: (~ ( '\\n' | '\\r' ) )*
                while True: #loop11
                    alt11 = 2
                    LA11_0 = self.input.LA(1)

                    if ((0 <= LA11_0 <= 9) or (14 <= LA11_0 <= 65535) or LA11_0 in {11, 12}) :
                        alt11 = 1


                    if alt11 == 1:
                        # impera.g:
                        pass 
                        if (0 <= self.input.LA(1) <= 9) or (14 <= self.input.LA(1) <= 65535) or self.input.LA(1) in {11, 12}:
                            self.input.consume()
                        else:
                            mse = MismatchedSetException(None, self.input)
                            self.recover(mse)
                            raise mse




                    else:
                        break #loop11


                # impera.g:242:28: ( '\\r' )?
                alt12 = 2
                LA12_0 = self.input.LA(1)

                if (LA12_0 == 13) :
                    alt12 = 1
                if alt12 == 1:
                    # impera.g:242:28: '\\r'
                    pass 
                    self.match(13)




                self.match(10)

                #action start
                _channel=HIDDEN;
                #action end



            elif alt16 == 2:
                # impera.g:243:7: '#' (~ ( '\\n' | '\\r' ) )* ( '\\r' )? '\\n'
                pass 
                self.match(35)

                # impera.g:243:11: (~ ( '\\n' | '\\r' ) )*
                while True: #loop13
                    alt13 = 2
                    LA13_0 = self.input.LA(1)

                    if ((0 <= LA13_0 <= 9) or (14 <= LA13_0 <= 65535) or LA13_0 in {11, 12}) :
                        alt13 = 1


                    if alt13 == 1:
                        # impera.g:
                        pass 
                        if (0 <= self.input.LA(1) <= 9) or (14 <= self.input.LA(1) <= 65535) or self.input.LA(1) in {11, 12}:
                            self.input.consume()
                        else:
                            mse = MismatchedSetException(None, self.input)
                            self.recover(mse)
                            raise mse




                    else:
                        break #loop13


                # impera.g:243:25: ( '\\r' )?
                alt14 = 2
                LA14_0 = self.input.LA(1)

                if (LA14_0 == 13) :
                    alt14 = 1
                if alt14 == 1:
                    # impera.g:243:25: '\\r'
                    pass 
                    self.match(13)




                self.match(10)

                #action start
                _channel=HIDDEN;
                #action end



            elif alt16 == 3:
                # impera.g:244:9: '/*' ( options {greedy=false; } : . )* '*/'
                pass 
                self.match("/*")


                # impera.g:244:14: ( options {greedy=false; } : . )*
                while True: #loop15
                    alt15 = 2
                    LA15_0 = self.input.LA(1)

                    if (LA15_0 == 42) :
                        LA15_1 = self.input.LA(2)

                        if (LA15_1 == 47) :
                            alt15 = 2
                        elif ((0 <= LA15_1 <= 46) or (48 <= LA15_1 <= 65535) or LA15_1 in {}) :
                            alt15 = 1


                    elif ((0 <= LA15_0 <= 41) or (43 <= LA15_0 <= 65535) or LA15_0 in {}) :
                        alt15 = 1


                    if alt15 == 1:
                        # impera.g:244:42: .
                        pass 
                        self.matchAny()


                    else:
                        break #loop15


                self.match("*/")


                #action start
                _channel=HIDDEN;
                #action end



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "COMMENT"



    # $ANTLR start "WS"
    def mWS(self, ):
        try:
            _type = WS
            _channel = DEFAULT_CHANNEL

            # impera.g:247:5: ( ( ' ' | '\\t' | '\\r' | '\\n' ) )
            # impera.g:247:9: ( ' ' | '\\t' | '\\r' | '\\n' )
            pass 
            if self.input.LA(1) in {9, 10, 13, 32}:
                self.input.consume()
            else:
                mse = MismatchedSetException(None, self.input)
                self.recover(mse)
                raise mse



            #action start
            _channel=HIDDEN;
            #action end




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "WS"



    # $ANTLR start "ML_STRING"
    def mML_STRING(self, ):
        try:
            _type = ML_STRING
            _channel = DEFAULT_CHANNEL

            # impera.g:255:5: ( '\"\"\"' ( options {greedy=false; } : . )* '\"\"\"' )
            # impera.g:255:9: '\"\"\"' ( options {greedy=false; } : . )* '\"\"\"'
            pass 
            self.match("\"\"\"")


            # impera.g:255:15: ( options {greedy=false; } : . )*
            while True: #loop17
                alt17 = 2
                LA17_0 = self.input.LA(1)

                if (LA17_0 == 34) :
                    LA17_1 = self.input.LA(2)

                    if (LA17_1 == 34) :
                        LA17_3 = self.input.LA(3)

                        if (LA17_3 == 34) :
                            alt17 = 2
                        elif ((0 <= LA17_3 <= 33) or (35 <= LA17_3 <= 65535) or LA17_3 in {}) :
                            alt17 = 1


                    elif ((0 <= LA17_1 <= 33) or (35 <= LA17_1 <= 65535) or LA17_1 in {}) :
                        alt17 = 1


                elif ((0 <= LA17_0 <= 33) or (35 <= LA17_0 <= 65535) or LA17_0 in {}) :
                    alt17 = 1


                if alt17 == 1:
                    # impera.g:255:42: .
                    pass 
                    self.matchAny()


                else:
                    break #loop17


            self.match("\"\"\"")




            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "ML_STRING"



    # $ANTLR start "STRING"
    def mSTRING(self, ):
        try:
            _type = STRING
            _channel = DEFAULT_CHANNEL

            # impera.g:259:5: ( '\"' ( ESC_SEQ |~ ( '\\\\' | '\"' ) )* '\"' )
            # impera.g:259:9: '\"' ( ESC_SEQ |~ ( '\\\\' | '\"' ) )* '\"'
            pass 
            self.match(34)

            # impera.g:259:13: ( ESC_SEQ |~ ( '\\\\' | '\"' ) )*
            while True: #loop18
                alt18 = 3
                LA18_0 = self.input.LA(1)

                if (LA18_0 == 92) :
                    alt18 = 1
                elif ((0 <= LA18_0 <= 33) or (35 <= LA18_0 <= 91) or (93 <= LA18_0 <= 65535) or LA18_0 in {}) :
                    alt18 = 2


                if alt18 == 1:
                    # impera.g:259:15: ESC_SEQ
                    pass 
                    self.mESC_SEQ()



                elif alt18 == 2:
                    # impera.g:259:25: ~ ( '\\\\' | '\"' )
                    pass 
                    if (0 <= self.input.LA(1) <= 33) or (35 <= self.input.LA(1) <= 91) or (93 <= self.input.LA(1) <= 65535) or self.input.LA(1) in {}:
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse




                else:
                    break #loop18


            self.match(34)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "STRING"



    # $ANTLR start "REGEX"
    def mREGEX(self, ):
        try:
            _type = REGEX
            _channel = DEFAULT_CHANNEL

            # impera.g:263:2: ( '/' (~ ( '/' ) )* '/' )
            # impera.g:263:4: '/' (~ ( '/' ) )* '/'
            pass 
            self.match(47)

            # impera.g:263:8: (~ ( '/' ) )*
            while True: #loop19
                alt19 = 2
                LA19_0 = self.input.LA(1)

                if ((0 <= LA19_0 <= 46) or (48 <= LA19_0 <= 65535) or LA19_0 in {}) :
                    alt19 = 1


                if alt19 == 1:
                    # impera.g:
                    pass 
                    if (0 <= self.input.LA(1) <= 46) or (48 <= self.input.LA(1) <= 65535) or self.input.LA(1) in {}:
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse




                else:
                    break #loop19


            self.match(47)



            self._state.type = _type
            self._state.channel = _channel
        finally:
            pass

    # $ANTLR end "REGEX"



    # $ANTLR start "EXPONENT"
    def mEXPONENT(self, ):
        try:
            # impera.g:268:10: ( ( 'e' | 'E' ) ( '+' | '-' )? ( '0' .. '9' )+ )
            # impera.g:268:12: ( 'e' | 'E' ) ( '+' | '-' )? ( '0' .. '9' )+
            pass 
            if self.input.LA(1) in {69, 101}:
                self.input.consume()
            else:
                mse = MismatchedSetException(None, self.input)
                self.recover(mse)
                raise mse



            # impera.g:268:22: ( '+' | '-' )?
            alt20 = 2
            LA20_0 = self.input.LA(1)

            if (LA20_0 in {43, 45}) :
                alt20 = 1
            if alt20 == 1:
                # impera.g:
                pass 
                if self.input.LA(1) in {43, 45}:
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse






            # impera.g:268:33: ( '0' .. '9' )+
            cnt21 = 0
            while True: #loop21
                alt21 = 2
                LA21_0 = self.input.LA(1)

                if ((48 <= LA21_0 <= 57) or LA21_0 in {}) :
                    alt21 = 1


                if alt21 == 1:
                    # impera.g:
                    pass 
                    if (48 <= self.input.LA(1) <= 57) or self.input.LA(1) in {}:
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse




                else:
                    if cnt21 >= 1:
                        break #loop21

                    eee = EarlyExitException(21, self.input)
                    raise eee

                cnt21 += 1





        finally:
            pass

    # $ANTLR end "EXPONENT"



    # $ANTLR start "HEX_DIGIT"
    def mHEX_DIGIT(self, ):
        try:
            # impera.g:271:11: ( ( '0' .. '9' | 'a' .. 'f' | 'A' .. 'F' ) )
            # impera.g:
            pass 
            if (48 <= self.input.LA(1) <= 57) or (65 <= self.input.LA(1) <= 70) or (97 <= self.input.LA(1) <= 102) or self.input.LA(1) in {}:
                self.input.consume()
            else:
                mse = MismatchedSetException(None, self.input)
                self.recover(mse)
                raise mse






        finally:
            pass

    # $ANTLR end "HEX_DIGIT"



    # $ANTLR start "ESC_SEQ"
    def mESC_SEQ(self, ):
        try:
            # impera.g:275:5: ( '\\\\' ( 'b' | 't' | 'n' | 'f' | 'r' | '\\\"' | '\\'' | '\\\\' ) | UNICODE_ESC | OCTAL_ESC )
            alt22 = 3
            LA22_0 = self.input.LA(1)

            if (LA22_0 == 92) :
                LA22 = self.input.LA(2)
                if LA22 in {34, 39, 92, 98, 102, 110, 114, 116}:
                    alt22 = 1
                elif LA22 in {117}:
                    alt22 = 2
                elif LA22 in {48, 49, 50, 51, 52, 53, 54, 55}:
                    alt22 = 3
                else:
                    nvae = NoViableAltException("", 22, 1, self.input)

                    raise nvae


            else:
                nvae = NoViableAltException("", 22, 0, self.input)

                raise nvae


            if alt22 == 1:
                # impera.g:275:9: '\\\\' ( 'b' | 't' | 'n' | 'f' | 'r' | '\\\"' | '\\'' | '\\\\' )
                pass 
                self.match(92)

                if self.input.LA(1) in {34, 39, 92, 98, 102, 110, 114, 116}:
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse




            elif alt22 == 2:
                # impera.g:276:9: UNICODE_ESC
                pass 
                self.mUNICODE_ESC()



            elif alt22 == 3:
                # impera.g:277:9: OCTAL_ESC
                pass 
                self.mOCTAL_ESC()




        finally:
            pass

    # $ANTLR end "ESC_SEQ"



    # $ANTLR start "OCTAL_ESC"
    def mOCTAL_ESC(self, ):
        try:
            # impera.g:282:5: ( '\\\\' ( '0' .. '3' ) ( '0' .. '7' ) ( '0' .. '7' ) | '\\\\' ( '0' .. '7' ) ( '0' .. '7' ) | '\\\\' ( '0' .. '7' ) )
            alt23 = 3
            LA23_0 = self.input.LA(1)

            if (LA23_0 == 92) :
                LA23_1 = self.input.LA(2)

                if (LA23_1 in {48, 49, 50, 51}) :
                    LA23_2 = self.input.LA(3)

                    if ((48 <= LA23_2 <= 55) or LA23_2 in {}) :
                        LA23_4 = self.input.LA(4)

                        if ((48 <= LA23_4 <= 55) or LA23_4 in {}) :
                            alt23 = 1
                        else:
                            alt23 = 2

                    else:
                        alt23 = 3

                elif (LA23_1 in {52, 53, 54, 55}) :
                    LA23_3 = self.input.LA(3)

                    if ((48 <= LA23_3 <= 55) or LA23_3 in {}) :
                        alt23 = 2
                    else:
                        alt23 = 3

                else:
                    nvae = NoViableAltException("", 23, 1, self.input)

                    raise nvae


            else:
                nvae = NoViableAltException("", 23, 0, self.input)

                raise nvae


            if alt23 == 1:
                # impera.g:282:9: '\\\\' ( '0' .. '3' ) ( '0' .. '7' ) ( '0' .. '7' )
                pass 
                self.match(92)

                if self.input.LA(1) in {48, 49, 50, 51}:
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse



                if (48 <= self.input.LA(1) <= 55) or self.input.LA(1) in {}:
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse



                if (48 <= self.input.LA(1) <= 55) or self.input.LA(1) in {}:
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse




            elif alt23 == 2:
                # impera.g:283:9: '\\\\' ( '0' .. '7' ) ( '0' .. '7' )
                pass 
                self.match(92)

                if (48 <= self.input.LA(1) <= 55) or self.input.LA(1) in {}:
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse



                if (48 <= self.input.LA(1) <= 55) or self.input.LA(1) in {}:
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse




            elif alt23 == 3:
                # impera.g:284:9: '\\\\' ( '0' .. '7' )
                pass 
                self.match(92)

                if (48 <= self.input.LA(1) <= 55) or self.input.LA(1) in {}:
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse





        finally:
            pass

    # $ANTLR end "OCTAL_ESC"



    # $ANTLR start "UNICODE_ESC"
    def mUNICODE_ESC(self, ):
        try:
            # impera.g:289:5: ( '\\\\' 'u' HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT )
            # impera.g:289:9: '\\\\' 'u' HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT
            pass 
            self.match(92)

            self.match(117)

            self.mHEX_DIGIT()


            self.mHEX_DIGIT()


            self.mHEX_DIGIT()


            self.mHEX_DIGIT()





        finally:
            pass

    # $ANTLR end "UNICODE_ESC"



    def mTokens(self):
        # impera.g:1:8: ( T__46 | T__47 | T__48 | T__49 | T__50 | T__51 | T__52 | T__53 | T__54 | T__55 | T__56 | T__57 | T__58 | T__59 | T__60 | T__61 | T__62 | T__63 | T__64 | T__65 | T__66 | T__67 | T__68 | T__69 | T__70 | T__71 | T__72 | T__73 | T__74 | T__75 | T__76 | T__77 | T__78 | T__79 | TRUE | FALSE | ID | CLASS_ID | INT | FLOAT | COMMENT | WS | ML_STRING | STRING | REGEX )
        alt24 = 45
        alt24 = self.dfa24.predict(self.input)
        if alt24 == 1:
            # impera.g:1:10: T__46
            pass 
            self.mT__46()



        elif alt24 == 2:
            # impera.g:1:16: T__47
            pass 
            self.mT__47()



        elif alt24 == 3:
            # impera.g:1:22: T__48
            pass 
            self.mT__48()



        elif alt24 == 4:
            # impera.g:1:28: T__49
            pass 
            self.mT__49()



        elif alt24 == 5:
            # impera.g:1:34: T__50
            pass 
            self.mT__50()



        elif alt24 == 6:
            # impera.g:1:40: T__51
            pass 
            self.mT__51()



        elif alt24 == 7:
            # impera.g:1:46: T__52
            pass 
            self.mT__52()



        elif alt24 == 8:
            # impera.g:1:52: T__53
            pass 
            self.mT__53()



        elif alt24 == 9:
            # impera.g:1:58: T__54
            pass 
            self.mT__54()



        elif alt24 == 10:
            # impera.g:1:64: T__55
            pass 
            self.mT__55()



        elif alt24 == 11:
            # impera.g:1:70: T__56
            pass 
            self.mT__56()



        elif alt24 == 12:
            # impera.g:1:76: T__57
            pass 
            self.mT__57()



        elif alt24 == 13:
            # impera.g:1:82: T__58
            pass 
            self.mT__58()



        elif alt24 == 14:
            # impera.g:1:88: T__59
            pass 
            self.mT__59()



        elif alt24 == 15:
            # impera.g:1:94: T__60
            pass 
            self.mT__60()



        elif alt24 == 16:
            # impera.g:1:100: T__61
            pass 
            self.mT__61()



        elif alt24 == 17:
            # impera.g:1:106: T__62
            pass 
            self.mT__62()



        elif alt24 == 18:
            # impera.g:1:112: T__63
            pass 
            self.mT__63()



        elif alt24 == 19:
            # impera.g:1:118: T__64
            pass 
            self.mT__64()



        elif alt24 == 20:
            # impera.g:1:124: T__65
            pass 
            self.mT__65()



        elif alt24 == 21:
            # impera.g:1:130: T__66
            pass 
            self.mT__66()



        elif alt24 == 22:
            # impera.g:1:136: T__67
            pass 
            self.mT__67()



        elif alt24 == 23:
            # impera.g:1:142: T__68
            pass 
            self.mT__68()



        elif alt24 == 24:
            # impera.g:1:148: T__69
            pass 
            self.mT__69()



        elif alt24 == 25:
            # impera.g:1:154: T__70
            pass 
            self.mT__70()



        elif alt24 == 26:
            # impera.g:1:160: T__71
            pass 
            self.mT__71()



        elif alt24 == 27:
            # impera.g:1:166: T__72
            pass 
            self.mT__72()



        elif alt24 == 28:
            # impera.g:1:172: T__73
            pass 
            self.mT__73()



        elif alt24 == 29:
            # impera.g:1:178: T__74
            pass 
            self.mT__74()



        elif alt24 == 30:
            # impera.g:1:184: T__75
            pass 
            self.mT__75()



        elif alt24 == 31:
            # impera.g:1:190: T__76
            pass 
            self.mT__76()



        elif alt24 == 32:
            # impera.g:1:196: T__77
            pass 
            self.mT__77()



        elif alt24 == 33:
            # impera.g:1:202: T__78
            pass 
            self.mT__78()



        elif alt24 == 34:
            # impera.g:1:208: T__79
            pass 
            self.mT__79()



        elif alt24 == 35:
            # impera.g:1:214: TRUE
            pass 
            self.mTRUE()



        elif alt24 == 36:
            # impera.g:1:219: FALSE
            pass 
            self.mFALSE()



        elif alt24 == 37:
            # impera.g:1:225: ID
            pass 
            self.mID()



        elif alt24 == 38:
            # impera.g:1:228: CLASS_ID
            pass 
            self.mCLASS_ID()



        elif alt24 == 39:
            # impera.g:1:237: INT
            pass 
            self.mINT()



        elif alt24 == 40:
            # impera.g:1:241: FLOAT
            pass 
            self.mFLOAT()



        elif alt24 == 41:
            # impera.g:1:247: COMMENT
            pass 
            self.mCOMMENT()



        elif alt24 == 42:
            # impera.g:1:255: WS
            pass 
            self.mWS()



        elif alt24 == 43:
            # impera.g:1:258: ML_STRING
            pass 
            self.mML_STRING()



        elif alt24 == 44:
            # impera.g:1:268: STRING
            pass 
            self.mSTRING()



        elif alt24 == 45:
            # impera.g:1:275: REGEX
            pass 
            self.mREGEX()








    # lookup tables for DFA #10

    DFA10_eot = DFA.unpack(
        "\5\uffff"
        )

    DFA10_eof = DFA.unpack(
        "\5\uffff"
        )

    DFA10_min = DFA.unpack(
        "\2\56\3\uffff"
        )

    DFA10_max = DFA.unpack(
        "\1\71\1\145\3\uffff"
        )

    DFA10_accept = DFA.unpack(
        "\2\uffff\1\2\1\1\1\3"
        )

    DFA10_special = DFA.unpack(
        "\5\uffff"
        )


    DFA10_transition = [
        DFA.unpack("\1\2\1\uffff\12\1"),
        DFA.unpack("\1\3\1\uffff\12\1\13\uffff\1\4\37\uffff\1\4"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("")
    ]

    # class definition for DFA #10

    class DFA10(DFA):
        pass


    # lookup tables for DFA #24

    DFA24_eot = DFA.unpack(
        "\6\uffff\1\40\1\43\1\46\1\50\1\52\2\uffff\12\27\2\uffff\1\72\21"
        "\uffff\1\27\1\101\5\27\1\111\2\27\1\114\4\27\1\uffff\1\75\2\uffff"
        "\1\77\1\uffff\1\125\1\uffff\1\126\2\27\1\131\3\27\1\uffff\1\27\1"
        "\136\1\uffff\4\27\1\uffff\1\75\4\uffff\2\27\1\uffff\4\27\1\uffff"
        "\1\27\1\153\1\27\1\155\1\uffff\2\27\1\160\1\27\1\162\2\27\1\uffff"
        "\1\165\1\uffff\1\166\1\27\1\uffff\1\27\1\uffff\2\27\2\uffff\1\173"
        "\2\27\1\176\1\uffff\1\27\1\u0080\1\uffff\1\u0082\1\uffff\1\27\1"
        "\uffff\3\27\1\u0087\1\uffff"
        )

    DFA24_eof = DFA.unpack(
        "\u0088\uffff"
        )

    DFA24_min = DFA.unpack(
        "\1\11\4\uffff\1\55\1\60\1\72\1\55\2\75\2\uffff\2\156\1\141\1\155"
        "\1\141\1\157\2\162\1\163\1\150\2\uffff\1\56\1\0\2\uffff\1\0\15\uffff"
        "\1\144\1\55\1\144\1\164\1\162\1\154\1\160\1\55\2\164\1\55\1\160"
        "\1\165\1\151\1\145\1\uffff\2\0\1\uffff\1\42\1\uffff\1\55\1\uffff"
        "\1\55\1\151\1\145\1\55\1\163\1\154\1\145\1\uffff\1\143\1\55\1\uffff"
        "\2\145\2\156\3\0\3\uffff\1\164\1\156\1\uffff\2\145\1\170\1\150\1"
        "\uffff\1\144\1\55\1\147\1\55\1\uffff\1\171\1\144\1\55\1\155\1\55"
        "\1\151\1\145\1\uffff\1\55\1\uffff\1\55\1\163\1\uffff\1\145\1\uffff"
        "\1\156\1\146\2\uffff\1\55\1\156\1\147\1\55\1\uffff\1\164\1\55\1"
        "\uffff\1\55\1\uffff\1\164\1\uffff\1\151\1\157\1\156\1\55\1\uffff"
        )

    DFA24_max = DFA.unpack(
        "\1\172\4\uffff\1\76\1\71\1\72\3\75\2\uffff\1\163\1\170\1\157\1\156"
        "\1\141\1\157\1\162\1\171\1\163\1\150\2\uffff\1\145\1\uffff\2\uffff"
        "\1\uffff\15\uffff\1\144\1\172\2\164\1\162\1\154\1\160\1\172\2\164"
        "\1\172\1\160\1\165\1\151\1\145\1\uffff\2\uffff\1\uffff\1\42\1\uffff"
        "\1\172\1\uffff\1\172\1\151\1\145\1\172\1\163\1\154\1\145\1\uffff"
        "\1\143\1\172\1\uffff\2\145\2\156\3\uffff\3\uffff\1\164\1\156\1\uffff"
        "\2\145\1\170\1\150\1\uffff\1\144\1\172\1\147\1\172\1\uffff\1\171"
        "\1\144\1\172\1\155\1\172\1\151\1\145\1\uffff\1\172\1\uffff\1\172"
        "\1\163\1\uffff\1\145\1\uffff\1\156\1\146\2\uffff\1\172\1\156\1\147"
        "\1\172\1\uffff\1\164\1\172\1\uffff\1\172\1\uffff\1\164\1\uffff\1"
        "\151\1\157\1\156\1\172\1\uffff"
        )

    DFA24_accept = DFA.unpack(
        "\1\uffff\1\1\1\2\1\3\1\4\6\uffff\1\21\1\22\12\uffff\1\45\1\46\2"
        "\uffff\1\51\1\52\1\uffff\1\5\1\6\1\7\1\50\1\11\1\10\1\13\1\14\1"
        "\12\1\16\1\15\1\20\1\17\17\uffff\1\47\2\uffff\1\55\1\uffff\1\54"
        "\1\uffff\1\24\7\uffff\1\33\2\uffff\1\37\7\uffff\1\53\1\23\1\25\2"
        "\uffff\1\30\4\uffff\1\36\4\uffff\1\51\7\uffff\1\43\1\uffff\1\42"
        "\2\uffff\1\44\1\uffff\1\34\2\uffff\1\41\1\26\4\uffff\1\27\2\uffff"
        "\1\40\1\uffff\1\35\1\uffff\1\31\4\uffff\1\32"
        )

    DFA24_special = DFA.unpack(
        "\32\uffff\1\0\2\uffff\1\4\35\uffff\1\2\1\3\24\uffff\1\5\1\1\1\6"
        "\64\uffff"
        )


    DFA24_transition = [
        DFA.unpack("\2\34\2\uffff\1\34\22\uffff\1\34\1\1\1\35\1\33\4\uffff"
        "\1\2\1\3\2\uffff\1\4\1\5\1\6\1\32\12\31\1\7\1\uffff\1\10\1\11\1"
        "\12\2\uffff\32\30\1\13\1\uffff\1\14\1\uffff\1\27\1\uffff\1\15\3"
        "\27\1\16\1\17\2\27\1\20\3\27\1\21\1\22\1\23\4\27\1\24\1\25\1\27"
        "\1\26\3\27"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\36\20\uffff\1\37"),
        DFA.unpack("\12\41"),
        DFA.unpack("\1\42"),
        DFA.unpack("\1\44\17\uffff\1\45"),
        DFA.unpack("\1\47"),
        DFA.unpack("\1\51"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\53\4\uffff\1\54"),
        DFA.unpack("\1\55\11\uffff\1\56"),
        DFA.unpack("\1\60\15\uffff\1\57"),
        DFA.unpack("\1\61\1\62"),
        DFA.unpack("\1\63"),
        DFA.unpack("\1\64"),
        DFA.unpack("\1\65"),
        DFA.unpack("\1\67\6\uffff\1\66"),
        DFA.unpack("\1\70"),
        DFA.unpack("\1\71"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\41\1\uffff\12\31\13\uffff\1\41\37\uffff\1\41"),
        DFA.unpack("\52\75\1\74\4\75\1\73\uffd0\75"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\42\77\1\76\uffdd\77"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\100"),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack("\1\102\17\uffff\1\103"),
        DFA.unpack("\1\104"),
        DFA.unpack("\1\105"),
        DFA.unpack("\1\106"),
        DFA.unpack("\1\107"),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\3\27\1\110\26\27"),
        DFA.unpack("\1\112"),
        DFA.unpack("\1\113"),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack("\1\115"),
        DFA.unpack("\1\116"),
        DFA.unpack("\1\117"),
        DFA.unpack("\1\120"),
        DFA.unpack(""),
        DFA.unpack("\0\33"),
        DFA.unpack("\52\123\1\121\4\123\1\122\uffd0\123"),
        DFA.unpack(""),
        DFA.unpack("\1\124"),
        DFA.unpack(""),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack(""),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack("\1\127"),
        DFA.unpack("\1\130"),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack("\1\132"),
        DFA.unpack("\1\133"),
        DFA.unpack("\1\134"),
        DFA.unpack(""),
        DFA.unpack("\1\135"),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack(""),
        DFA.unpack("\1\137"),
        DFA.unpack("\1\140"),
        DFA.unpack("\1\141"),
        DFA.unpack("\1\142"),
        DFA.unpack("\52\123\1\121\4\123\1\143\uffd0\123"),
        DFA.unpack("\0\33"),
        DFA.unpack("\52\123\1\121\4\123\1\122\uffd0\123"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\144"),
        DFA.unpack("\1\145"),
        DFA.unpack(""),
        DFA.unpack("\1\146"),
        DFA.unpack("\1\147"),
        DFA.unpack("\1\150"),
        DFA.unpack("\1\151"),
        DFA.unpack(""),
        DFA.unpack("\1\152"),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack("\1\154"),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack(""),
        DFA.unpack("\1\156"),
        DFA.unpack("\1\157"),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack("\1\161"),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack("\1\163"),
        DFA.unpack("\1\164"),
        DFA.unpack(""),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack(""),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack("\1\167"),
        DFA.unpack(""),
        DFA.unpack("\1\170"),
        DFA.unpack(""),
        DFA.unpack("\1\171"),
        DFA.unpack("\1\172"),
        DFA.unpack(""),
        DFA.unpack(""),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack("\1\174"),
        DFA.unpack("\1\175"),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack(""),
        DFA.unpack("\1\177"),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack(""),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\1\u0081\31\27"),
        DFA.unpack(""),
        DFA.unpack("\1\u0083"),
        DFA.unpack(""),
        DFA.unpack("\1\u0084"),
        DFA.unpack("\1\u0085"),
        DFA.unpack("\1\u0086"),
        DFA.unpack("\1\27\2\uffff\12\27\7\uffff\32\27\4\uffff\1\27\1\uffff"
        "\32\27"),
        DFA.unpack("")
    ]

    # class definition for DFA #24

    class DFA24(DFA):
        pass


        def specialStateTransition(self_, s, input):
            # convince pylint that my self_ magic is ok ;)
            # pylint: disable-msg=E0213

            # pretend we are a member of the recognizer
            # thus semantic predicates can be evaluated
            self = self_.recognizer

            _s = s

            if s == 0: 
                LA24_26 = input.LA(1)

                s = -1
                if (LA24_26 == 47):
                    s = 59

                elif (LA24_26 == 42):
                    s = 60

                elif ((0 <= LA24_26 <= 41) or (48 <= LA24_26 <= 65535) or LA24_26 in {43, 44, 45, 46}):
                    s = 61

                if s >= 0:
                    return s
            elif s == 1: 
                LA24_82 = input.LA(1)

                s = -1
                if ((0 <= LA24_82 <= 65535) or LA24_82 in {}):
                    s = 27

                else:
                    s = 61

                if s >= 0:
                    return s
            elif s == 2: 
                LA24_59 = input.LA(1)

                s = -1
                if ((0 <= LA24_59 <= 65535) or LA24_59 in {}):
                    s = 27

                else:
                    s = 61

                if s >= 0:
                    return s
            elif s == 3: 
                LA24_60 = input.LA(1)

                s = -1
                if (LA24_60 == 42):
                    s = 81

                elif (LA24_60 == 47):
                    s = 82

                elif ((0 <= LA24_60 <= 41) or (48 <= LA24_60 <= 65535) or LA24_60 in {43, 44, 45, 46}):
                    s = 83

                if s >= 0:
                    return s
            elif s == 4: 
                LA24_29 = input.LA(1)

                s = -1
                if (LA24_29 == 34):
                    s = 62

                elif ((0 <= LA24_29 <= 33) or (35 <= LA24_29 <= 65535) or LA24_29 in {}):
                    s = 63

                if s >= 0:
                    return s
            elif s == 5: 
                LA24_81 = input.LA(1)

                s = -1
                if (LA24_81 == 47):
                    s = 99

                elif (LA24_81 == 42):
                    s = 81

                elif ((0 <= LA24_81 <= 41) or (48 <= LA24_81 <= 65535) or LA24_81 in {43, 44, 45, 46}):
                    s = 83

                if s >= 0:
                    return s
            elif s == 6: 
                LA24_83 = input.LA(1)

                s = -1
                if (LA24_83 == 42):
                    s = 81

                elif (LA24_83 == 47):
                    s = 82

                elif ((0 <= LA24_83 <= 41) or (48 <= LA24_83 <= 65535) or LA24_83 in {43, 44, 45, 46}):
                    s = 83

                if s >= 0:
                    return s

            nvae = NoViableAltException(self_.getDescription(), 24, _s, input)
            self_.error(nvae)
            raise nvae

 



def main(argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    from antlr3.main import LexerMain
    main = LexerMain(imperaLexer)

    main.stdin = stdin
    main.stdout = stdout
    main.stderr = stderr
    main.execute(argv)



if __name__ == '__main__':
    main(sys.argv)
