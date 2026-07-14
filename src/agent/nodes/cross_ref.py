from src.agent.state import AgentState, AgentStateUpdate


def _output_coordinate_errors(state: AgentState) -> list[str]:
    """Run the E4 contract gate at graph repair boundaries.

    The final Workflow gate remains authoritative for the converted IDF, but
    an in-memory drift must not survive a parallel merge/checkpoint/retry only
    to be discovered at export time (E4 §5.2 call point 3, BO-CR8).
    """
    contract = state.output_coordinate_contract
    if contract is None:
        return []
    if state.output_coordinate_context is None:
        return ["output-coordinates[CONTRACT_IDENTITY]: contract has no validation context"]
    from src.validator.output_coordinates import validate_output_coordinate_contract

    return [
        f"output-coordinates[{issue.code}]: {issue.message}"
        for issue in validate_output_coordinate_contract(
            state.config_state, contract, state.output_coordinate_context,
        )
    ]


def cross_ref_foundations_node(state: AgentState) -> AgentStateUpdate:
    """Cross-ref check after phase 1 (zone + material + schedule).

    Most checks are moot at this stage (no constructions, surfaces, HVAC yet),
    but any early violation of shared identity still surfaces here.
    """
    return AgentStateUpdate(
        validation_errors=state.config_state.validate_references() + _output_coordinate_errors(state)
    )


def cross_ref_complete_node(state: AgentState) -> AgentStateUpdate:
    """Full cross-ref check after phase 3 (hvac + people + lights)."""
    return AgentStateUpdate(
        validation_errors=state.config_state.validate_references() + _output_coordinate_errors(state)
    )
