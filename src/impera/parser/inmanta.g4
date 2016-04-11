/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */

grammar inmanta;

options {
//    language=Python3;
}

main
	: (def_statement | top_statement | ML_STRING)*
	;

def_statement
	: typedef | entity_def | implementation_def | relation | index | implement_def
	;

typedef
	: 'typedef' ID 'as' ns_ref 'matching' (REGEX | expression) #DEF_TYPE
	| 'typedef' CLASS_ID 'as' constructor #DEF_DEFAULT
	;
        
entity_def
	: ('entity' CLASS_ID ('extends' class_ref (',' class_ref)*)?) ':' ML_STRING? (entity_body)* 'end' 
		#DEF_ENTITY
    ; 

implementation_def
	: 'implementation' ID ('for' class_ref)? implementation #DEF_IMPLEMENTATION
	;
        
index
	: 'index' class_ref '(' ID (',' ID)* ')' #INDEX
	;

// implement File using PosixFile, LinuxFile when os is "redhat"
implement_def
	: 'implement' class_ref 'using' ns_ref (',' ns_ref)* ('when' expression)? #DEF_IMPLEMENT
	;


// relation	
relation_end
	: class_ref ID 
	;
	
relation_link
	: '<-' | '->' | '--'
	;
	
multiplicity_body
	: INT #FIXED
	| INT ':' #LOWER
	| INT ':' INT #RANGE
	| ':' INT  #UPPER
	;

multiplicity
	: '[' multiplicity_body ']'
	;
        
relation
	: (left_end=relation_end left_m=multiplicity) relation_link (right_m=multiplicity right_end=relation_end) #DEF_RELATION
	;

        
        
top_statement
	// plugin function, method call, assignemnt or construction -> start with var
	: 'for' ID 'in' variable implementation
	| variable '=' operand 
	| call
	;

implementation
	: ':' ML_STRING? statement* 'end'
	;

statement
	: top_statement 
	;
	
parameter
	: ID '=' operand #ASSIGN
	;

constructor
	: class_ref '(' param_list? ')'#CONSTRUCT 
    ;

param_list
	:	parameter (',' parameter)* ','?
	;


operand	
	: constant
	| list_def
	| index_lookup
	| call
	| variable
    // builtin_func method_Call list_def
    ;

constant
	: TRUE | FALSE | STRING | INT | FLOAT | REGEX | ML_STRING
	;
    
list_def
	: '[' operand (',' operand)* ','? ']'
	;
	
index_arg
	: param_list
	;

index_lookup
	// also parse variables with this rule
	: class_ref '[' index_arg ']' #HASH
	;

entity_body
	: ns_ref ID ('=' constant)? #STATEMENT
	;

ns_ref
	: ID ('::' ID)* #REF
	;
	
class_ref
    : (ns+=ID '::')* CLASS_ID #CLASS_REF
    ;
	
variable
	: (ns+=ID '::')* var=ID ('.' attr+=ID)* #VAR_REF
	;
	
arg_list
	: operand (',' operand)* ','? #LIST
	;

call
        : function_call
        | constructor
        ;
	
function_call
	: ns_ref '(' arg_list? ')' #CALL
	;
un_op
	: 'not'
	;
	
cmp_op
	: '==' | '!=' | '<=' | '>=' | '<' | '>'
	;
	
cmp	
	: operand 'in' in_oper
	| operand cmp_op operand
	| function_call 
	;
	
log_op
	: 'and' | 'or'
	;
	
in_oper
	: list_def | variable
	;	
	
log_oper
	: cmp | TRUE | FALSE
	;
	
log_expr
//	: left=log_oper (log_op^ right=log_oper)*
	: log_oper log_op log_expr
	| log_oper
	;
	
expression
	: '(' expression ')' (log_op expression)?
	| log_expr log_op '(' expression ')'
	| log_expr
	;
        
TRUE
	:	'true'
	;

FALSE
	:	'false'
	;

ID	:	('a'..'z'| '_') ('a'..'z'|'A'..'Z'|'0'..'9'|'_'|'-')*
    ;
    
CLASS_ID
	: 	('A'..'Z') ('a'..'z'|'A'..'Z'|'0'..'9'|'_'|'-')*
    ;    

INT :	'0'..'9' '0'..'9'*
    ;

FLOAT
    :   '0'..'9' ('0'..'9')* '.' ('0'..'9')* EXPONENT?
    |   '.' ('0'..'9')+ EXPONENT?
    |   ('0'..'9') ('0'..'9')* EXPONENT
    ;

COMMENT1
    :   ('//' ~('\n'|'\r')* '\r'? '\n' 
        |	'#' ~('\n'|'\r')* '\r'? '\n' 
        |   '/*' .*? '*/'
        ) -> skip
    ;

WS  :   ( ' '
        | '\t'
        | '\r'
        | '\n'
        ) -> skip
    ;
   
ML_STRING
    :   '"""' .*? '"""'
    ;

STRING
    :  	'"' ( ESC_SEQ | ~('\\'|'"') )* '"'
    ;
    
REGEX
	:	'/' (~('/'))* '/'
	;

fragment
EXPONENT : ('e'|'E') ('+'|'-')? ('0'..'9')+ ;

fragment
HEX_DIGIT : ('0'..'9'|'a'..'f'|'A'..'F') ;

fragment
ESC_SEQ
    :   '\\' ('b'|'t'|'n'|'f'|'r'|'\"'|'\''|'\\')
    |   UNICODE_ESC
    |   OCTAL_ESC
    ;

fragment
OCTAL_ESC
    :   '\\' ('0'..'3') ('0'..'7') ('0'..'7')
    |   '\\' ('0'..'7') ('0'..'7')
    |   '\\' ('0'..'7')
    ;

fragment
UNICODE_ESC
    :   '\\' 'u' HEX_DIGIT HEX_DIGIT HEX_DIGIT HEX_DIGIT
    ;