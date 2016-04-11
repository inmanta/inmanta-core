// Generated from /home/wouter/inc/impera/src/impera/parser/inmanta.g4 by ANTLR 4.1
import org.antlr.v4.runtime.misc.NotNull;
import org.antlr.v4.runtime.tree.ParseTreeListener;

/**
 * This interface defines a complete listener for a parse tree produced by
 * {@link inmantaParser}.
 */
public interface inmantaListener extends ParseTreeListener {
	/**
	 * Enter a parse tree produced by {@link inmantaParser#STATEMENT}.
	 * @param ctx the parse tree
	 */
	void enterSTATEMENT(@NotNull inmantaParser.STATEMENTContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#STATEMENT}.
	 * @param ctx the parse tree
	 */
	void exitSTATEMENT(@NotNull inmantaParser.STATEMENTContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#multiplicity}.
	 * @param ctx the parse tree
	 */
	void enterMultiplicity(@NotNull inmantaParser.MultiplicityContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#multiplicity}.
	 * @param ctx the parse tree
	 */
	void exitMultiplicity(@NotNull inmantaParser.MultiplicityContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#CALL}.
	 * @param ctx the parse tree
	 */
	void enterCALL(@NotNull inmantaParser.CALLContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#CALL}.
	 * @param ctx the parse tree
	 */
	void exitCALL(@NotNull inmantaParser.CALLContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#relation_end}.
	 * @param ctx the parse tree
	 */
	void enterRelation_end(@NotNull inmantaParser.Relation_endContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#relation_end}.
	 * @param ctx the parse tree
	 */
	void exitRelation_end(@NotNull inmantaParser.Relation_endContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#CONSTRUCT}.
	 * @param ctx the parse tree
	 */
	void enterCONSTRUCT(@NotNull inmantaParser.CONSTRUCTContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#CONSTRUCT}.
	 * @param ctx the parse tree
	 */
	void exitCONSTRUCT(@NotNull inmantaParser.CONSTRUCTContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#constant}.
	 * @param ctx the parse tree
	 */
	void enterConstant(@NotNull inmantaParser.ConstantContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#constant}.
	 * @param ctx the parse tree
	 */
	void exitConstant(@NotNull inmantaParser.ConstantContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#cmp}.
	 * @param ctx the parse tree
	 */
	void enterCmp(@NotNull inmantaParser.CmpContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#cmp}.
	 * @param ctx the parse tree
	 */
	void exitCmp(@NotNull inmantaParser.CmpContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#VAR_REF}.
	 * @param ctx the parse tree
	 */
	void enterVAR_REF(@NotNull inmantaParser.VAR_REFContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#VAR_REF}.
	 * @param ctx the parse tree
	 */
	void exitVAR_REF(@NotNull inmantaParser.VAR_REFContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#main}.
	 * @param ctx the parse tree
	 */
	void enterMain(@NotNull inmantaParser.MainContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#main}.
	 * @param ctx the parse tree
	 */
	void exitMain(@NotNull inmantaParser.MainContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#index_arg}.
	 * @param ctx the parse tree
	 */
	void enterIndex_arg(@NotNull inmantaParser.Index_argContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#index_arg}.
	 * @param ctx the parse tree
	 */
	void exitIndex_arg(@NotNull inmantaParser.Index_argContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#ASSIGN}.
	 * @param ctx the parse tree
	 */
	void enterASSIGN(@NotNull inmantaParser.ASSIGNContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#ASSIGN}.
	 * @param ctx the parse tree
	 */
	void exitASSIGN(@NotNull inmantaParser.ASSIGNContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#relation_link}.
	 * @param ctx the parse tree
	 */
	void enterRelation_link(@NotNull inmantaParser.Relation_linkContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#relation_link}.
	 * @param ctx the parse tree
	 */
	void exitRelation_link(@NotNull inmantaParser.Relation_linkContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#log_expr}.
	 * @param ctx the parse tree
	 */
	void enterLog_expr(@NotNull inmantaParser.Log_exprContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#log_expr}.
	 * @param ctx the parse tree
	 */
	void exitLog_expr(@NotNull inmantaParser.Log_exprContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#UPPER}.
	 * @param ctx the parse tree
	 */
	void enterUPPER(@NotNull inmantaParser.UPPERContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#UPPER}.
	 * @param ctx the parse tree
	 */
	void exitUPPER(@NotNull inmantaParser.UPPERContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#statement}.
	 * @param ctx the parse tree
	 */
	void enterStatement(@NotNull inmantaParser.StatementContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#statement}.
	 * @param ctx the parse tree
	 */
	void exitStatement(@NotNull inmantaParser.StatementContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#DEF_ENTITY}.
	 * @param ctx the parse tree
	 */
	void enterDEF_ENTITY(@NotNull inmantaParser.DEF_ENTITYContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#DEF_ENTITY}.
	 * @param ctx the parse tree
	 */
	void exitDEF_ENTITY(@NotNull inmantaParser.DEF_ENTITYContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#INDEX}.
	 * @param ctx the parse tree
	 */
	void enterINDEX(@NotNull inmantaParser.INDEXContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#INDEX}.
	 * @param ctx the parse tree
	 */
	void exitINDEX(@NotNull inmantaParser.INDEXContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#CLASS_REF}.
	 * @param ctx the parse tree
	 */
	void enterCLASS_REF(@NotNull inmantaParser.CLASS_REFContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#CLASS_REF}.
	 * @param ctx the parse tree
	 */
	void exitCLASS_REF(@NotNull inmantaParser.CLASS_REFContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#list_def}.
	 * @param ctx the parse tree
	 */
	void enterList_def(@NotNull inmantaParser.List_defContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#list_def}.
	 * @param ctx the parse tree
	 */
	void exitList_def(@NotNull inmantaParser.List_defContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#cmp_op}.
	 * @param ctx the parse tree
	 */
	void enterCmp_op(@NotNull inmantaParser.Cmp_opContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#cmp_op}.
	 * @param ctx the parse tree
	 */
	void exitCmp_op(@NotNull inmantaParser.Cmp_opContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#DEF_IMPLEMENT}.
	 * @param ctx the parse tree
	 */
	void enterDEF_IMPLEMENT(@NotNull inmantaParser.DEF_IMPLEMENTContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#DEF_IMPLEMENT}.
	 * @param ctx the parse tree
	 */
	void exitDEF_IMPLEMENT(@NotNull inmantaParser.DEF_IMPLEMENTContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#un_op}.
	 * @param ctx the parse tree
	 */
	void enterUn_op(@NotNull inmantaParser.Un_opContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#un_op}.
	 * @param ctx the parse tree
	 */
	void exitUn_op(@NotNull inmantaParser.Un_opContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#expression}.
	 * @param ctx the parse tree
	 */
	void enterExpression(@NotNull inmantaParser.ExpressionContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#expression}.
	 * @param ctx the parse tree
	 */
	void exitExpression(@NotNull inmantaParser.ExpressionContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#DEF_TYPE}.
	 * @param ctx the parse tree
	 */
	void enterDEF_TYPE(@NotNull inmantaParser.DEF_TYPEContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#DEF_TYPE}.
	 * @param ctx the parse tree
	 */
	void exitDEF_TYPE(@NotNull inmantaParser.DEF_TYPEContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#implementation}.
	 * @param ctx the parse tree
	 */
	void enterImplementation(@NotNull inmantaParser.ImplementationContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#implementation}.
	 * @param ctx the parse tree
	 */
	void exitImplementation(@NotNull inmantaParser.ImplementationContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#FIXED}.
	 * @param ctx the parse tree
	 */
	void enterFIXED(@NotNull inmantaParser.FIXEDContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#FIXED}.
	 * @param ctx the parse tree
	 */
	void exitFIXED(@NotNull inmantaParser.FIXEDContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#def_statement}.
	 * @param ctx the parse tree
	 */
	void enterDef_statement(@NotNull inmantaParser.Def_statementContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#def_statement}.
	 * @param ctx the parse tree
	 */
	void exitDef_statement(@NotNull inmantaParser.Def_statementContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#log_op}.
	 * @param ctx the parse tree
	 */
	void enterLog_op(@NotNull inmantaParser.Log_opContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#log_op}.
	 * @param ctx the parse tree
	 */
	void exitLog_op(@NotNull inmantaParser.Log_opContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#log_oper}.
	 * @param ctx the parse tree
	 */
	void enterLog_oper(@NotNull inmantaParser.Log_operContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#log_oper}.
	 * @param ctx the parse tree
	 */
	void exitLog_oper(@NotNull inmantaParser.Log_operContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#top_statement}.
	 * @param ctx the parse tree
	 */
	void enterTop_statement(@NotNull inmantaParser.Top_statementContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#top_statement}.
	 * @param ctx the parse tree
	 */
	void exitTop_statement(@NotNull inmantaParser.Top_statementContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#param_list}.
	 * @param ctx the parse tree
	 */
	void enterParam_list(@NotNull inmantaParser.Param_listContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#param_list}.
	 * @param ctx the parse tree
	 */
	void exitParam_list(@NotNull inmantaParser.Param_listContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#HASH}.
	 * @param ctx the parse tree
	 */
	void enterHASH(@NotNull inmantaParser.HASHContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#HASH}.
	 * @param ctx the parse tree
	 */
	void exitHASH(@NotNull inmantaParser.HASHContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#call}.
	 * @param ctx the parse tree
	 */
	void enterCall(@NotNull inmantaParser.CallContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#call}.
	 * @param ctx the parse tree
	 */
	void exitCall(@NotNull inmantaParser.CallContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#REF}.
	 * @param ctx the parse tree
	 */
	void enterREF(@NotNull inmantaParser.REFContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#REF}.
	 * @param ctx the parse tree
	 */
	void exitREF(@NotNull inmantaParser.REFContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#LOWER}.
	 * @param ctx the parse tree
	 */
	void enterLOWER(@NotNull inmantaParser.LOWERContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#LOWER}.
	 * @param ctx the parse tree
	 */
	void exitLOWER(@NotNull inmantaParser.LOWERContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#DEF_DEFAULT}.
	 * @param ctx the parse tree
	 */
	void enterDEF_DEFAULT(@NotNull inmantaParser.DEF_DEFAULTContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#DEF_DEFAULT}.
	 * @param ctx the parse tree
	 */
	void exitDEF_DEFAULT(@NotNull inmantaParser.DEF_DEFAULTContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#in_oper}.
	 * @param ctx the parse tree
	 */
	void enterIn_oper(@NotNull inmantaParser.In_operContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#in_oper}.
	 * @param ctx the parse tree
	 */
	void exitIn_oper(@NotNull inmantaParser.In_operContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#LIST}.
	 * @param ctx the parse tree
	 */
	void enterLIST(@NotNull inmantaParser.LISTContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#LIST}.
	 * @param ctx the parse tree
	 */
	void exitLIST(@NotNull inmantaParser.LISTContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#DEF_IMPLEMENTATION}.
	 * @param ctx the parse tree
	 */
	void enterDEF_IMPLEMENTATION(@NotNull inmantaParser.DEF_IMPLEMENTATIONContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#DEF_IMPLEMENTATION}.
	 * @param ctx the parse tree
	 */
	void exitDEF_IMPLEMENTATION(@NotNull inmantaParser.DEF_IMPLEMENTATIONContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#DEF_RELATION}.
	 * @param ctx the parse tree
	 */
	void enterDEF_RELATION(@NotNull inmantaParser.DEF_RELATIONContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#DEF_RELATION}.
	 * @param ctx the parse tree
	 */
	void exitDEF_RELATION(@NotNull inmantaParser.DEF_RELATIONContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#operand}.
	 * @param ctx the parse tree
	 */
	void enterOperand(@NotNull inmantaParser.OperandContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#operand}.
	 * @param ctx the parse tree
	 */
	void exitOperand(@NotNull inmantaParser.OperandContext ctx);

	/**
	 * Enter a parse tree produced by {@link inmantaParser#RANGE}.
	 * @param ctx the parse tree
	 */
	void enterRANGE(@NotNull inmantaParser.RANGEContext ctx);
	/**
	 * Exit a parse tree produced by {@link inmantaParser#RANGE}.
	 * @param ctx the parse tree
	 */
	void exitRANGE(@NotNull inmantaParser.RANGEContext ctx);
}