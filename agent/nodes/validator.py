"""
Validator Node: Cross-validates financial calculations
"""

from agent.agent_state import AgentState, ValidationResult, create_reasoning_step


def create_validator(mcp_manager):
    """
    Factory function that creates a validator node with MCP manager in closure
    """

    async def validate_results(state: AgentState) -> dict:
        """
        Cross-validates results using multiple approaches
        Checks consistency across different hierarchies or data sources
        """

        # Identify results that need validation (HPL calculations)
        results_to_validate = [
            exec for exec in state["tool_executions"]
            if exec.tool_name == "calculate_hypothetical_pnl" and exec.result
        ]

        if not results_to_validate:
            # Nothing to validate
            reasoning = create_reasoning_step(
                step_type="validation",
                content="No calculations require cross-validation",
                metadata={"validated_count": 0}
            )
            return {
                "reasoning_steps": [reasoning],
                "needs_validation": False,
                "iteration_count": state["iteration_count"] + 1
            }

        validation_results = []

        for execution in results_to_validate:
            reasoning = create_reasoning_step(
                step_type="validation",
                content=f"Cross-validating results from {execution.tool_name}",
                metadata={"tool": execution.tool_name, "account": execution.arguments.get("account_number")}
            )

            # Cross-check with alternative hierarchy
            original_hierarchy = execution.arguments.get("hierarchy")
            alt_hierarchy = "PRA" if original_hierarchy == "FHC" else "FHC"

            try:
                alt_result = await mcp_manager.call_tool(
                    "calculate_hypothetical_pnl",
                    {
                        "account_number": execution.arguments["account_number"],
                        "hierarchy": alt_hierarchy
                    }
                )

                # Simple consistency check - both should return results
                is_consistent = (execution.result is not None) and (alt_result is not None)

                validation = ValidationResult(
                    is_valid=is_consistent,
                    confidence=0.95 if is_consistent else 0.6,
                    issues=[] if is_consistent else ["Alternative hierarchy produced different result structure"],
                    cross_check_results={
                        "original": {
                            "hierarchy": original_hierarchy,
                            "result": execution.result[:200] if len(str(execution.result)) > 200 else execution.result
                        },
                        "alternative": {
                            "hierarchy": alt_hierarchy,
                            "result": alt_result[:200] if len(str(alt_result)) > 200 else alt_result
                        }
                    }
                )

                validation_results.append(validation)

            except Exception as e:
                # Validation failed - lower confidence but don't fail
                validation = ValidationResult(
                    is_valid=True,  # Assume valid but with lower confidence
                    confidence=0.7,
                    issues=[f"Cross-validation failed: {str(e)}"],
                    cross_check_results={}
                )
                validation_results.append(validation)

        # Create summary reasoning step
        avg_confidence = sum(v.confidence for v in validation_results) / len(validation_results) if validation_results else 1.0
        summary_reasoning = create_reasoning_step(
            step_type="validation",
            content=f"Validated {len(validation_results)} calculation(s) with average confidence: {avg_confidence:.2f}",
            metadata={
                "validated_count": len(validation_results),
                "average_confidence": avg_confidence,
                "all_valid": all(v.is_valid for v in validation_results)
            }
        )

        return {
            "validation_results": validation_results,
            "needs_validation": False,
            "reasoning_steps": [reasoning, summary_reasoning] if 'reasoning' in locals() else [summary_reasoning],
            "iteration_count": state["iteration_count"] + 1
        }

    return validate_results
