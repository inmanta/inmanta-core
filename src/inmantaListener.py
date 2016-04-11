# Generated from inmanta.g4 by ANTLR 4.5.3
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .inmantaParser import inmantaParser
else:
    from inmantaParser import inmantaParser

# This class defines a complete listener for a parse tree produced by inmantaParser.
class inmantaListener(ParseTreeListener):

    # Enter a parse tree produced by inmantaParser#main.
    def enterMain(self, ctx:inmantaParser.MainContext):
        pass

    # Exit a parse tree produced by inmantaParser#main.
    def exitMain(self, ctx:inmantaParser.MainContext):
        pass


    # Enter a parse tree produced by inmantaParser#def_statement.
    def enterDef_statement(self, ctx:inmantaParser.Def_statementContext):
        pass

    # Exit a parse tree produced by inmantaParser#def_statement.
    def exitDef_statement(self, ctx:inmantaParser.Def_statementContext):
        pass


    # Enter a parse tree produced by inmantaParser#DEF_TYPE.
    def enterDEF_TYPE(self, ctx:inmantaParser.DEF_TYPEContext):
        pass

    # Exit a parse tree produced by inmantaParser#DEF_TYPE.
    def exitDEF_TYPE(self, ctx:inmantaParser.DEF_TYPEContext):
        pass


    # Enter a parse tree produced by inmantaParser#DEF_DEFAULT.
    def enterDEF_DEFAULT(self, ctx:inmantaParser.DEF_DEFAULTContext):
        pass

    # Exit a parse tree produced by inmantaParser#DEF_DEFAULT.
    def exitDEF_DEFAULT(self, ctx:inmantaParser.DEF_DEFAULTContext):
        pass


    # Enter a parse tree produced by inmantaParser#DEF_ENTITY.
    def enterDEF_ENTITY(self, ctx:inmantaParser.DEF_ENTITYContext):
        pass

    # Exit a parse tree produced by inmantaParser#DEF_ENTITY.
    def exitDEF_ENTITY(self, ctx:inmantaParser.DEF_ENTITYContext):
        pass


    # Enter a parse tree produced by inmantaParser#DEF_IMPLEMENTATION.
    def enterDEF_IMPLEMENTATION(self, ctx:inmantaParser.DEF_IMPLEMENTATIONContext):
        pass

    # Exit a parse tree produced by inmantaParser#DEF_IMPLEMENTATION.
    def exitDEF_IMPLEMENTATION(self, ctx:inmantaParser.DEF_IMPLEMENTATIONContext):
        pass


    # Enter a parse tree produced by inmantaParser#INDEX.
    def enterINDEX(self, ctx:inmantaParser.INDEXContext):
        pass

    # Exit a parse tree produced by inmantaParser#INDEX.
    def exitINDEX(self, ctx:inmantaParser.INDEXContext):
        pass


    # Enter a parse tree produced by inmantaParser#DEF_IMPLEMENT.
    def enterDEF_IMPLEMENT(self, ctx:inmantaParser.DEF_IMPLEMENTContext):
        pass

    # Exit a parse tree produced by inmantaParser#DEF_IMPLEMENT.
    def exitDEF_IMPLEMENT(self, ctx:inmantaParser.DEF_IMPLEMENTContext):
        pass


    # Enter a parse tree produced by inmantaParser#relation_end.
    def enterRelation_end(self, ctx:inmantaParser.Relation_endContext):
        pass

    # Exit a parse tree produced by inmantaParser#relation_end.
    def exitRelation_end(self, ctx:inmantaParser.Relation_endContext):
        pass


    # Enter a parse tree produced by inmantaParser#relation_link.
    def enterRelation_link(self, ctx:inmantaParser.Relation_linkContext):
        pass

    # Exit a parse tree produced by inmantaParser#relation_link.
    def exitRelation_link(self, ctx:inmantaParser.Relation_linkContext):
        pass


    # Enter a parse tree produced by inmantaParser#FIXED.
    def enterFIXED(self, ctx:inmantaParser.FIXEDContext):
        pass

    # Exit a parse tree produced by inmantaParser#FIXED.
    def exitFIXED(self, ctx:inmantaParser.FIXEDContext):
        pass


    # Enter a parse tree produced by inmantaParser#LOWER.
    def enterLOWER(self, ctx:inmantaParser.LOWERContext):
        pass

    # Exit a parse tree produced by inmantaParser#LOWER.
    def exitLOWER(self, ctx:inmantaParser.LOWERContext):
        pass


    # Enter a parse tree produced by inmantaParser#RANGE.
    def enterRANGE(self, ctx:inmantaParser.RANGEContext):
        pass

    # Exit a parse tree produced by inmantaParser#RANGE.
    def exitRANGE(self, ctx:inmantaParser.RANGEContext):
        pass


    # Enter a parse tree produced by inmantaParser#UPPER.
    def enterUPPER(self, ctx:inmantaParser.UPPERContext):
        pass

    # Exit a parse tree produced by inmantaParser#UPPER.
    def exitUPPER(self, ctx:inmantaParser.UPPERContext):
        pass


    # Enter a parse tree produced by inmantaParser#multiplicity.
    def enterMultiplicity(self, ctx:inmantaParser.MultiplicityContext):
        pass

    # Exit a parse tree produced by inmantaParser#multiplicity.
    def exitMultiplicity(self, ctx:inmantaParser.MultiplicityContext):
        pass


    # Enter a parse tree produced by inmantaParser#DEF_RELATION.
    def enterDEF_RELATION(self, ctx:inmantaParser.DEF_RELATIONContext):
        pass

    # Exit a parse tree produced by inmantaParser#DEF_RELATION.
    def exitDEF_RELATION(self, ctx:inmantaParser.DEF_RELATIONContext):
        pass


    # Enter a parse tree produced by inmantaParser#top_statement.
    def enterTop_statement(self, ctx:inmantaParser.Top_statementContext):
        pass

    # Exit a parse tree produced by inmantaParser#top_statement.
    def exitTop_statement(self, ctx:inmantaParser.Top_statementContext):
        pass


    # Enter a parse tree produced by inmantaParser#implementation.
    def enterImplementation(self, ctx:inmantaParser.ImplementationContext):
        pass

    # Exit a parse tree produced by inmantaParser#implementation.
    def exitImplementation(self, ctx:inmantaParser.ImplementationContext):
        pass


    # Enter a parse tree produced by inmantaParser#statement.
    def enterStatement(self, ctx:inmantaParser.StatementContext):
        pass

    # Exit a parse tree produced by inmantaParser#statement.
    def exitStatement(self, ctx:inmantaParser.StatementContext):
        pass


    # Enter a parse tree produced by inmantaParser#ASSIGN.
    def enterASSIGN(self, ctx:inmantaParser.ASSIGNContext):
        pass

    # Exit a parse tree produced by inmantaParser#ASSIGN.
    def exitASSIGN(self, ctx:inmantaParser.ASSIGNContext):
        pass


    # Enter a parse tree produced by inmantaParser#CONSTRUCT.
    def enterCONSTRUCT(self, ctx:inmantaParser.CONSTRUCTContext):
        pass

    # Exit a parse tree produced by inmantaParser#CONSTRUCT.
    def exitCONSTRUCT(self, ctx:inmantaParser.CONSTRUCTContext):
        pass


    # Enter a parse tree produced by inmantaParser#param_list.
    def enterParam_list(self, ctx:inmantaParser.Param_listContext):
        pass

    # Exit a parse tree produced by inmantaParser#param_list.
    def exitParam_list(self, ctx:inmantaParser.Param_listContext):
        pass


    # Enter a parse tree produced by inmantaParser#operand.
    def enterOperand(self, ctx:inmantaParser.OperandContext):
        pass

    # Exit a parse tree produced by inmantaParser#operand.
    def exitOperand(self, ctx:inmantaParser.OperandContext):
        pass


    # Enter a parse tree produced by inmantaParser#constant.
    def enterConstant(self, ctx:inmantaParser.ConstantContext):
        pass

    # Exit a parse tree produced by inmantaParser#constant.
    def exitConstant(self, ctx:inmantaParser.ConstantContext):
        pass


    # Enter a parse tree produced by inmantaParser#list_def.
    def enterList_def(self, ctx:inmantaParser.List_defContext):
        pass

    # Exit a parse tree produced by inmantaParser#list_def.
    def exitList_def(self, ctx:inmantaParser.List_defContext):
        pass


    # Enter a parse tree produced by inmantaParser#index_arg.
    def enterIndex_arg(self, ctx:inmantaParser.Index_argContext):
        pass

    # Exit a parse tree produced by inmantaParser#index_arg.
    def exitIndex_arg(self, ctx:inmantaParser.Index_argContext):
        pass


    # Enter a parse tree produced by inmantaParser#HASH.
    def enterHASH(self, ctx:inmantaParser.HASHContext):
        pass

    # Exit a parse tree produced by inmantaParser#HASH.
    def exitHASH(self, ctx:inmantaParser.HASHContext):
        pass


    # Enter a parse tree produced by inmantaParser#STATEMENT.
    def enterSTATEMENT(self, ctx:inmantaParser.STATEMENTContext):
        pass

    # Exit a parse tree produced by inmantaParser#STATEMENT.
    def exitSTATEMENT(self, ctx:inmantaParser.STATEMENTContext):
        pass


    # Enter a parse tree produced by inmantaParser#REF.
    def enterREF(self, ctx:inmantaParser.REFContext):
        pass

    # Exit a parse tree produced by inmantaParser#REF.
    def exitREF(self, ctx:inmantaParser.REFContext):
        pass


    # Enter a parse tree produced by inmantaParser#CLASS_REF.
    def enterCLASS_REF(self, ctx:inmantaParser.CLASS_REFContext):
        pass

    # Exit a parse tree produced by inmantaParser#CLASS_REF.
    def exitCLASS_REF(self, ctx:inmantaParser.CLASS_REFContext):
        pass


    # Enter a parse tree produced by inmantaParser#VAR_REF.
    def enterVAR_REF(self, ctx:inmantaParser.VAR_REFContext):
        pass

    # Exit a parse tree produced by inmantaParser#VAR_REF.
    def exitVAR_REF(self, ctx:inmantaParser.VAR_REFContext):
        pass


    # Enter a parse tree produced by inmantaParser#LIST.
    def enterLIST(self, ctx:inmantaParser.LISTContext):
        pass

    # Exit a parse tree produced by inmantaParser#LIST.
    def exitLIST(self, ctx:inmantaParser.LISTContext):
        pass


    # Enter a parse tree produced by inmantaParser#call.
    def enterCall(self, ctx:inmantaParser.CallContext):
        pass

    # Exit a parse tree produced by inmantaParser#call.
    def exitCall(self, ctx:inmantaParser.CallContext):
        pass


    # Enter a parse tree produced by inmantaParser#CALL.
    def enterCALL(self, ctx:inmantaParser.CALLContext):
        pass

    # Exit a parse tree produced by inmantaParser#CALL.
    def exitCALL(self, ctx:inmantaParser.CALLContext):
        pass


    # Enter a parse tree produced by inmantaParser#un_op.
    def enterUn_op(self, ctx:inmantaParser.Un_opContext):
        pass

    # Exit a parse tree produced by inmantaParser#un_op.
    def exitUn_op(self, ctx:inmantaParser.Un_opContext):
        pass


    # Enter a parse tree produced by inmantaParser#cmp_op.
    def enterCmp_op(self, ctx:inmantaParser.Cmp_opContext):
        pass

    # Exit a parse tree produced by inmantaParser#cmp_op.
    def exitCmp_op(self, ctx:inmantaParser.Cmp_opContext):
        pass


    # Enter a parse tree produced by inmantaParser#cmp.
    def enterCmp(self, ctx:inmantaParser.CmpContext):
        pass

    # Exit a parse tree produced by inmantaParser#cmp.
    def exitCmp(self, ctx:inmantaParser.CmpContext):
        pass


    # Enter a parse tree produced by inmantaParser#log_op.
    def enterLog_op(self, ctx:inmantaParser.Log_opContext):
        pass

    # Exit a parse tree produced by inmantaParser#log_op.
    def exitLog_op(self, ctx:inmantaParser.Log_opContext):
        pass


    # Enter a parse tree produced by inmantaParser#in_oper.
    def enterIn_oper(self, ctx:inmantaParser.In_operContext):
        pass

    # Exit a parse tree produced by inmantaParser#in_oper.
    def exitIn_oper(self, ctx:inmantaParser.In_operContext):
        pass


    # Enter a parse tree produced by inmantaParser#log_oper.
    def enterLog_oper(self, ctx:inmantaParser.Log_operContext):
        pass

    # Exit a parse tree produced by inmantaParser#log_oper.
    def exitLog_oper(self, ctx:inmantaParser.Log_operContext):
        pass


    # Enter a parse tree produced by inmantaParser#log_expr.
    def enterLog_expr(self, ctx:inmantaParser.Log_exprContext):
        pass

    # Exit a parse tree produced by inmantaParser#log_expr.
    def exitLog_expr(self, ctx:inmantaParser.Log_exprContext):
        pass


    # Enter a parse tree produced by inmantaParser#expression.
    def enterExpression(self, ctx:inmantaParser.ExpressionContext):
        pass

    # Exit a parse tree produced by inmantaParser#expression.
    def exitExpression(self, ctx:inmantaParser.ExpressionContext):
        pass


