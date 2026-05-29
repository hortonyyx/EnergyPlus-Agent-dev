import time
from pathlib import Path

from src.converter_manager import ConverterManager
from src.mcp.interface import ToolResponse
from src.mcp.state import ConfigState
from src.runner.runner import EnergyPlusRunner
from src.utils.logging import get_logger
from src.validator.interzone import (
    audit_interzone_surface_pairs,
    validate_interzone_surface_pairs,
)

logger = get_logger(__name__)


def _check_interzone_pairs(manager: ConverterManager) -> list[str]:
    """Deterministic InterZone surface-pair gate on the assembled IDF.

    Run after `convert_all()` and before EnergyPlus so a missing / non-
    reciprocal / degenerate pair fails fast with a precise message instead of a
    late EP fatal or a silent wrong-physics pass. See
    src/validator/interzone.py and the 2026-05-28 InterZone review.

    Reads the live `manager._idf` (read-only); the `manager.idf` property
    deep-copies an IDF backed by a StringIO that may already be closed.
    """
    idf = manager._idf
    audit = audit_interzone_surface_pairs(idf)
    logger.info("InterZone surface-pair audit: {}", audit)
    issues = validate_interzone_surface_pairs(idf)
    if issues:
        logger.error(
            "InterZone surface-pair validation found {} issue(s):", len(issues)
        )
        for issue in issues:
            logger.error("  - {}", issue)
    return issues


class WorkflowTool:
    """Tool for EnergyPlus workflow operations.

    Provides high-level operations for exporting/loading YAML configurations,
    validating references, running simulations, and managing overall state.
    Unlike other tools, this does not inherit from BaseTool as it operates
    on the entire configuration rather than individual components.
    """

    def __init__(self, state: ConfigState):
        self.state = state

    def export_yaml(self, output_path: str) -> ToolResponse:
        """Export the current configuration state to a YAML file.

        Args:
            output_path: File path for the output YAML file.

        Returns:
            ToolResponse with the absolute path of the exported file.
        """
        try:
            path = Path(output_path)
            self.state.export_yaml(path)
            return ToolResponse(
                success=True,
                message=f"Exported YAML to {path}",
                data={"path": str(path.absolute())},
            )
        except Exception as e:
            logger.exception("Error exporting YAML")
            return ToolResponse(
                success=False,
                message=f"Error exporting YAML: {e!s}",
            )

    def load_yaml(self, yaml_path: str) -> ToolResponse:
        """Load a YAML configuration file and replace the current state.

        Args:
            yaml_path: Path to the YAML file to load.

        Returns:
            ToolResponse with a configuration summary after loading.
        """
        try:
            path = Path(yaml_path)
            new_state = ConfigState.load_yaml(path)
            self.state.update_from(new_state)

            summary = self.state.get_summary()
            return ToolResponse(
                success=True,
                message=f"Loaded YAML from {path}",
                data={"summary": summary.model_dump()},
            )

        except Exception as e:
            logger.exception("Error loading YAML")
            return ToolResponse(
                success=False,
                message=f"Error loading YAML: {e!s}",
            )

    def validate_config(self) -> ToolResponse:
        """Validate all cross-references in the current configuration.

        Returns:
            ToolResponse with validation result. Includes error list on failure
            or configuration summary on success.
        """
        errors = self.state.validate_references()

        if errors:
            return ToolResponse(
                success=False,
                message=f"Validation failed: {len(errors)} reference errors found.",
                data={"errors": errors},
            )

        return ToolResponse(
            success=True,
            message="Validation passed.",
            data=self.state.get_summary().model_dump(),
        )

    def export_idf_only(self, output_dir: str = "./output") -> ToolResponse:
        """Run the validate -> export YAML -> convert IDF chain WITHOUT
        invoking EnergyPlus. Used by `--no-simulate` debugging path
        (2026-05-07 added for B0' surface bug iteration).
        """
        try:
            validation = self.validate_config()
            if not validation.success:
                return ToolResponse(
                    success=False,
                    message="Validation Reference Errors, cannot export IDF.",
                    data=validation.data,
                )

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            temp_yaml = Path(output_dir) / f"temp_{timestamp}.yaml"
            temp_idf = Path(output_dir) / f"temp_{timestamp}.idf"

            self.state.export_yaml(temp_yaml)
            manager = ConverterManager(temp_yaml)
            manager.convert_all()

            pair_issues = _check_interzone_pairs(manager)
            if pair_issues:
                manager.save_idf(temp_idf)  # keep artifact for inspection
                return ToolResponse(
                    success=False,
                    message=(
                        f"InterZone surface-pair validation failed: "
                        f"{len(pair_issues)} issue(s). IDF not accepted."
                    ),
                    data={
                        "interzone_pair_issues": pair_issues,
                        "idf_path": str(temp_idf.absolute()),
                    },
                )

            manager.save_idf(temp_idf)

            logger.info("IDF exported (no simulation): {}", temp_idf)
            return ToolResponse(
                success=True,
                message="IDF exported (simulation skipped).",
                data={"idf_path": str(temp_idf.absolute()), "output_dir": output_dir},
            )
        except Exception as e:
            logger.exception("Error exporting IDF")
            return ToolResponse(
                success=False, message=f"Error exporting IDF: {e!s}"
            )

    def run_simulation(
        self, epw_path: str, output_dir: str = "./output"
    ) -> ToolResponse:
        """Run an EnergyPlus simulation with the current configuration.

        Validates references, exports to YAML, converts to IDF, and
        executes the EnergyPlus simulation.

        Args:
            epw_path: Path to the EPW weather data file.
            output_dir: Directory for simulation output files.

        Returns:
            ToolResponse with IDF path and output directory on success.
        """
        try:
            validation = self.validate_config()
            if not validation.success:
                return ToolResponse(
                    success=False,
                    message="Validation Reference Errors, cannot run simulation.",
                    data=validation.data,
                )

            output_dir_path = Path(output_dir)
            output_dir_path.mkdir(parents=True, exist_ok=True)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            temp_yaml = output_dir_path / f"temp_{timestamp}.yaml"
            temp_idf = output_dir_path / f"temp_{timestamp}.idf"

            self.state.export_yaml(temp_yaml)

            manager = ConverterManager(temp_yaml)
            manager.convert_all()

            pair_issues = _check_interzone_pairs(manager)
            if pair_issues:
                manager.save_idf(temp_idf)  # keep artifact for inspection
                return ToolResponse(
                    success=False,
                    message=(
                        f"InterZone surface-pair validation failed: "
                        f"{len(pair_issues)} issue(s). Simulation not started."
                    ),
                    data={
                        "interzone_pair_issues": pair_issues,
                        "idf_path": str(temp_idf.absolute()),
                    },
                )

            manager.save_idf(temp_idf)

            runner = EnergyPlusRunner(idf=manager.idf)
            runner.run_idf(epw_path, output_directory=output_dir_path)

            logger.info(
                "Simulation run successfully. Output directory: {}",
                output_dir_path,
            )

            return ToolResponse(
                success=True,
                message="Simulation run successfully.",
                data={
                    "idf_path": str(temp_idf.absolute()),
                    "output_dir": str(output_dir_path.absolute()),
                },
            )

        except Exception as e:
            logger.exception("Error running simulation")
            return ToolResponse(
                success=False,
                message=f"Error running simulation: {e!s}",
            )

    def get_summary(self) -> ToolResponse:
        """Get a summary of the current configuration state.

        Returns:
            ToolResponse with configuration summary data.
        """
        return ToolResponse(
            success=True,
            message="Configuration summary.",
            data=self.state.get_summary().model_dump(),
        )

    def clear_all(self) -> ToolResponse:
        """Clear all configuration state, resetting to defaults.

        Returns:
            ToolResponse confirming the state has been cleared.
        """
        self.state.clear()
        logger.info("All configuration cleared.")
        return ToolResponse(
            success=True,
            message="All configuration cleared.",
        )
