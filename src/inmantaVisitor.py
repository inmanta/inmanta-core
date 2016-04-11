# Generated from inmanta.g4 by ANTLR 4.5.3
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .inmantaParser import inmantaParser
else:
    from inmantaParser import inmantaParser

# This class defines a complete generic visitor for a parse tree produced by inmantaParser.

class inmantaVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by inmantaParser#main.
    def visitMain(self, ctx:inmantaParser.MainContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#def_statement.
    def visitDef_statement(self, ctx:inmantaParser.Def_statementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#DEF_TYPE.
    def visitDEF_TYPE(self, ctx:inmantaParser.DEF_TYPEContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#DEF_DEFAULT.
    def visitDEF_DEFAULT(self, ctx:inmantaParser.DEF_DEFAULTContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#DEF_ENTITY.
    def visitDEF_ENTITY(self, ctx:inmantaParser.DEF_ENTITYContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#DEF_IMPLEMENTATION.
    def visitDEF_IMPLEMENTATION(self, ctx:inmantaParser.DEF_IMPLEMENTATIONContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#INDEX.
    def visitINDEX(self, ctx:inmantaParser.INDEXContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#DEF_IMPLEMENT.
    def visitDEF_IMPLEMENT(self, ctx:inmantaParser.DEF_IMPLEMENTContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#relation_end.
    def visitRelation_end(self, ctx:inmantaParser.Relation_endContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#relation_link.
    def visitRelation_link(self, ctx:inmantaParser.Relation_linkContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#FIXED.
    def visitFIXED(self, ctx:inmantaParser.FIXEDContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#LOWER.
    def visitLOWER(self, ctx:inmantaParser.LOWERContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#RANGE.
    def visitRANGE(self, ctx:inmantaParser.RANGEContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#UPPER.
    def visitUPPER(self, ctx:inmantaParser.UPPERContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#multiplicity.
    def visitMultiplicity(self, ctx:inmantaParser.MultiplicityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#DEF_RELATION.
    def visitDEF_RELATION(self, ctx:inmantaParser.DEF_RELATIONContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#top_statement.
    def visitTop_statement(self, ctx:inmantaParser.Top_statementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#implementation.
    def visitImplementation(self, ctx:inmantaParser.ImplementationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#statement.
    def visitStatement(self, ctx:inmantaParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#ASSIGN.
    def visitASSIGN(self, ctx:inmantaParser.ASSIGNContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#CONSTRUCT.
    def visitCONSTRUCT(self, ctx:inmantaParser.CONSTRUCTContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#param_list.
    def visitParam_list(self, ctx:inmantaParser.Param_listContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#operand.
    def visitOperand(self, ctx:inmantaParser.OperandContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#constant.
    def visitConstant(self, ctx:inmantaParser.ConstantContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#list_def.
    def visitList_def(self, ctx:inmantaParser.List_defContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#index_arg.
    def visitIndex_arg(self, ctx:inmantaParser.Index_argContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#HASH.
    def visitHASH(self, ctx:inmantaParser.HASHContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#STATEMENT.
    def visitSTATEMENT(self, ctx:inmantaParser.STATEMENTContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#REF.
    def visitREF(self, ctx:inmantaParser.REFContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#CLASS_REF.
    def visitCLASS_REF(self, ctx:inmantaParser.CLASS_REFContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#VAR_REF.
    def visitVAR_REF(self, ctx:inmantaParser.VAR_REFContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#LIST.
    def visitLIST(self, ctx:inmantaParser.LISTContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#call.
    def visitCall(self, ctx:inmantaParser.CallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#CALL.
    def visitCALL(self, ctx:inmantaParser.CALLContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#un_op.
    def visitUn_op(self, ctx:inmantaParser.Un_opContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#cmp_op.
    def visitCmp_op(self, ctx:inmantaParser.Cmp_opContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#cmp.
    def visitCmp(self, ctx:inmantaParser.CmpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#log_op.
    def visitLog_op(self, ctx:inmantaParser.Log_opContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#in_oper.
    def visitIn_oper(self, ctx:inmantaParser.In_operContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#log_oper.
    def visitLog_oper(self, ctx:inmantaParser.Log_operContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#log_expr.
    def visitLog_expr(self, ctx:inmantaParser.Log_exprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by inmantaParser#expression.
    def visitExpression(self, ctx:inmantaParser.ExpressionContext):
        return self.visitChildren(ctx)



del inmantaParser