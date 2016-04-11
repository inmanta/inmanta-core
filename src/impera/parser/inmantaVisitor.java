// Generated from /home/wouter/inc/impera/src/impera/parser/inmanta.g4 by ANTLR 4.1
import org.antlr.v4.runtime.misc.NotNull;
import org.antlr.v4.runtime.tree.ParseTreeVisitor;

/**
 * This interface defines a complete generic visitor for a parse tree produced
 * by {@link inmantaParser}.
 *
 * @param <T> The return type of the visit operation. Use {@link Void} for
 * operations with no return type.
 */
public interface inmantaVisitor<T> extends ParseTreeVisitor<T> {
	/**
	 * Visit a parse tree produced by {@link inmantaParser#STATEMENT}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitSTATEMENT(@NotNull inmantaParser.STATEMENTContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#multiplicity}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitMultiplicity(@NotNull inmantaParser.MultiplicityContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#CALL}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitCALL(@NotNull inmantaParser.CALLContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#relation_end}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitRelation_end(@NotNull inmantaParser.Relation_endContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#CONSTRUCT}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitCONSTRUCT(@NotNull inmantaParser.CONSTRUCTContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#constant}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitConstant(@NotNull inmantaParser.ConstantContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#cmp}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitCmp(@NotNull inmantaParser.CmpContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#VAR_REF}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitVAR_REF(@NotNull inmantaParser.VAR_REFContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#main}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitMain(@NotNull inmantaParser.MainContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#index_arg}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitIndex_arg(@NotNull inmantaParser.Index_argContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#ASSIGN}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitASSIGN(@NotNull inmantaParser.ASSIGNContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#relation_link}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitRelation_link(@NotNull inmantaParser.Relation_linkContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#log_expr}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitLog_expr(@NotNull inmantaParser.Log_exprContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#UPPER}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitUPPER(@NotNull inmantaParser.UPPERContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#statement}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitStatement(@NotNull inmantaParser.StatementContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#DEF_ENTITY}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitDEF_ENTITY(@NotNull inmantaParser.DEF_ENTITYContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#INDEX}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitINDEX(@NotNull inmantaParser.INDEXContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#CLASS_REF}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitCLASS_REF(@NotNull inmantaParser.CLASS_REFContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#list_def}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitList_def(@NotNull inmantaParser.List_defContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#cmp_op}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitCmp_op(@NotNull inmantaParser.Cmp_opContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#DEF_IMPLEMENT}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitDEF_IMPLEMENT(@NotNull inmantaParser.DEF_IMPLEMENTContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#un_op}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitUn_op(@NotNull inmantaParser.Un_opContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#expression}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitExpression(@NotNull inmantaParser.ExpressionContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#DEF_TYPE}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitDEF_TYPE(@NotNull inmantaParser.DEF_TYPEContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#implementation}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitImplementation(@NotNull inmantaParser.ImplementationContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#FIXED}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitFIXED(@NotNull inmantaParser.FIXEDContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#def_statement}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitDef_statement(@NotNull inmantaParser.Def_statementContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#log_op}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitLog_op(@NotNull inmantaParser.Log_opContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#log_oper}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitLog_oper(@NotNull inmantaParser.Log_operContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#top_statement}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitTop_statement(@NotNull inmantaParser.Top_statementContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#param_list}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitParam_list(@NotNull inmantaParser.Param_listContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#HASH}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitHASH(@NotNull inmantaParser.HASHContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#call}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitCall(@NotNull inmantaParser.CallContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#REF}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitREF(@NotNull inmantaParser.REFContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#LOWER}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitLOWER(@NotNull inmantaParser.LOWERContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#DEF_DEFAULT}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitDEF_DEFAULT(@NotNull inmantaParser.DEF_DEFAULTContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#in_oper}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitIn_oper(@NotNull inmantaParser.In_operContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#LIST}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitLIST(@NotNull inmantaParser.LISTContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#DEF_IMPLEMENTATION}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitDEF_IMPLEMENTATION(@NotNull inmantaParser.DEF_IMPLEMENTATIONContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#DEF_RELATION}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitDEF_RELATION(@NotNull inmantaParser.DEF_RELATIONContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#operand}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitOperand(@NotNull inmantaParser.OperandContext ctx);

	/**
	 * Visit a parse tree produced by {@link inmantaParser#RANGE}.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	T visitRANGE(@NotNull inmantaParser.RANGEContext ctx);
}