grammar impera;

options {
//    language=Python3;
    output=AST;
    ASTLabelType=CommonTree;
}

tokens {
	NONE;
	DEF_ENTITY;
	DEF_IMPLEMENTATION;
	DEF_RELATION;
	DEF_TYPE;
	DEF_DEFAULT;
	DEF_IMPLEMENT;
	LIST;
	STATEMENT;
	ASSIGN;
	CONSTRUCT;
	CLASS_REF;
	REF;
	VAR_REF;
	ATTR;
	NS;
	CALL;
	MULT;
	HASH;
	OP;
	INCLUDE;
	LAMBDA;
	ORPHAN;
	FOR;
	ENUM;
	INDEX;
}

main
	: (def_statement | top_statement | ML_STRING)* -> ^(LIST def_statement* top_statement* ML_STRING*)
	;

def_statement
	: typedef | entity_def | implementation_def | relation | index | implement_def
	;

typedef
	: 'typedef' ID 'as' ns_ref 'matching' (REGEX | expression) -> ^(DEF_TYPE ID ns_ref expression? REGEX?)
	| 'typedef' CLASS_ID 'as' constructor -> ^(DEF_DEFAULT CLASS_ID constructor)
	;
        
entity_def
	: ('entity' CLASS_ID ('extends' class_ref (',' class_ref)*)?) ':' ML_STRING? (entity_body)* 'end' 
		-> ^(DEF_ENTITY CLASS_ID ^(LIST class_ref*) ^(LIST entity_body*) ML_STRING?)
    ; 

implementation_def
	: 'implementation' ID ('for' class_ref)? implementation -> ^(DEF_IMPLEMENTATION ID implementation class_ref?)
	;
        
index
	: 'index' class_ref '(' ID (',' ID)* ')' -> ^(INDEX class_ref ^(LIST ID+))
	;

// implement File using PosixFile, LinuxFile when os is "redhat"
implement_def
	: 'implement' class_ref 'using' ns_ref (',' ns_ref)* ('when' expression)? -> ^(DEF_IMPLEMENT class_ref ^(LIST ns_ref+) expression?)
	;


// relation	
relation_end
	: class_ref ID -> class_ref ID
	;
	
relation_link
	: '<-' | '->' | '--'
	;
	
multiplicity_body
	: (INT) => INT -> ^(MULT INT)
	| (INT ':') => INT ':' -> ^(MULT INT NONE)
	| (INT ':' INT) => INT ':' INT -> ^(MULT INT INT)
	| (':' INT) => ':' INT -> ^(MULT NONE INT)
	;

multiplicity
	: '[' multiplicity_body ']' -> multiplicity_body
	;
        
relation
	: (left_end=relation_end left_m=multiplicity) relation_link (right_m=multiplicity right_end=relation_end) ->
		^(DEF_RELATION relation_link ^(LIST $left_end $left_m) ^(LIST $right_end $right_m))
	;

        
        
top_statement
	// plugin function, method call, assignemnt or construction -> start with var
	: ('for') => 'for' ID 'in' variable implementation -> ^(FOR ID variable? implementation)
	| variable '=' operand -> ^(ASSIGN variable operand)
	| call
	;

implementation
	: ':' ML_STRING? statement* 'end' -> ^(LIST statement*)
	;

statement
	: top_statement -> ^(STATEMENT top_statement)
	;
	
parameter
	: ID '=' operand -> ^(ASSIGN ID operand)
	;

constructor
	: class_ref '(' param_list? ')' -> ^(CONSTRUCT class_ref param_list?)
    ;

param_list
	:	parameter (',' parameter)* ','? -> ^(LIST parameter+)
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
	: '[' operand (',' operand)* ','? ']' -> ^(LIST operand+)
	;
	
index_arg
	: param_list
	;

index_lookup
	// also parse variables with this rule
	: class_ref '[' index_arg ']' -> ^(HASH class_ref index_arg)
	;

entity_body
	: ns_ref ID ('=' constant)? -> ^(STATEMENT ns_ref ID constant?) 
	;

ns_ref
	: ID ('::' ID)* -> ^(REF ID+)
	;
	
class_ref
    : (ns+=ID '::')* CLASS_ID -> ^(CLASS_REF ^(NS $ns*) CLASS_ID)
    ;
	
variable
	: (ns+=ID '::')* var=ID ('.' attr+=ID)* -> ^(VAR_REF ^(NS $ns*) $var ^(ATTR $attr*))
	;
	
arg_list
	: operand (',' operand)* ','? -> ^(LIST operand+)
	;

call
        : (ns_ref '(') => function_call
        | (class_ref '(') =>  constructor
        ;
	
function_call
	: ns_ref '(' arg_list? ')' -> ^(CALL ns_ref arg_list?)
	;
un_op
	: 'not'
	;
	
cmp_op
	: '==' | '!=' | '<=' | '>=' | '<' | '>'
	;
	
cmp	
	: (operand 'in') => operand 'in' in_oper -> ^(OP 'in' operand in_oper)
	| (operand cmp_op) => operand cmp_op operand -> ^(OP cmp_op operand+)
	| function_call -> ^(OP function_call)
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
	: (log_oper log_op) => log_oper log_op log_expr -> ^(OP log_op log_oper log_expr)
	| log_oper
	;
	
expression
	: '(' expression ')' (log_op expression)? -> ^(OP log_op? expression+)
	| (log_expr log_op) => log_expr log_op '(' expression ')' -> ^(OP log_op log_expr expression)
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

INT :	'0'..'9'+
    ;

FLOAT
    :   ('0'..'9')+ '.' ('0'..'9')* EXPONENT?
    |   '.' ('0'..'9')+ EXPONENT?
    |   ('0'..'9')+ EXPONENT
    ;

COMMENT
    :   '//' ~('\n'|'\r')* '\r'? '\n' {$channel=HIDDEN;}
    |	'#' ~('\n'|'\r')* '\r'? '\n' {$channel=HIDDEN;}
    |   '/*' ( options {greedy=false;} : . )* '*/' {$channel=HIDDEN;}
    ;

WS  :   ( ' '
        | '\t'
        | '\r'
        | '\n'
        ) {$channel=HIDDEN;}
    ;
   
ML_STRING
    :   '"""' (options {greedy=false;} : .)* '"""'
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
