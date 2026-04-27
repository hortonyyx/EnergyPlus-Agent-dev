"""Convert geometry-phase YAML to IDF with the four mandatory fix patches.

Usage:
    python Tool_scripts/export_idf.py <case_dir>

Reads:  <case_dir>/output/<case_name>.yaml      (case_name = basename(<case_dir>))
Writes: <case_dir>/output/<case_name>.idf

Patches applied (all idempotent; required even when only geometry was authored):
    0. Pre-inject placeholder Constructions (Default_Ext_Wall / Default_Int_Wall /
       Default_Window) before `convert_all` - FenestrationConverter strictly requires
       Construction Default_Window to exist in the IDF; without this all
       `create_fenestration_surface` rows are silently dropped. Geometry-phase YAML
       does not author Constructions, so we inject minimal stubs (dummy NoMass
       material) here. MEP phase overwrites them with real layered constructions.
    1. RunPeriod None fields           - YAML schema emits a default RunPeriod
                                         with None fields that break IDF save.
    2. Building.Minimum_Number_of_Warmup_Days >= 1
                                       - default 0 makes EnergyPlus refuse to run.
    3. BuildingSurface:Detailed `Surface` -> `Adiabatic + Default_Int_Wall`
                                       - geometry phase already writes Adiabatic
                                         on shared walls, so this is a no-op safety
                                         net for any leftover surface-matched walls.
    4. Schedule:Compact None fields    - drop trailing None fields that break save;
                                         no-op in geometry phase (no Schedule:Compact).

Run from repo root so the IDD relative path resolves.
"""

from __future__ import annotations

import sys
from pathlib import Path

from src.converter_manager import ConverterManager
from src.validator.data_model import BaseSchema

IDD_PATH = Path("data/dependencies/Energy+.idd")
PLACEHOLDER_CONSTRUCTIONS = ("Default_Ext_Wall", "Default_Int_Wall", "Default_Window")
PLACEHOLDER_MATERIAL = "Default_Placeholder_Material"


def _inject_placeholder_constructions(idf) -> None:
    """Add a dummy NoMass material + 3 stub Constructions if absent.

    FenestrationConverter raises when a referenced Construction is missing,
    losing every window in geometry-only YAML. Stubs let the converter pass;
    the MEP phase overwrites them with real layered Constructions.
    """
    if idf.getobject("MATERIAL:NOMASS", PLACEHOLDER_MATERIAL) is None:
        idf.newidfobject(
            "MATERIAL:NOMASS",
            Name=PLACEHOLDER_MATERIAL,
            Roughness="MediumRough",
            Thermal_Resistance=0.1,
            Thermal_Absorptance=0.9,
            Solar_Absorptance=0.7,
            Visible_Absorptance=0.7,
        )
    for cname in PLACEHOLDER_CONSTRUCTIONS:
        if idf.getobject("CONSTRUCTION", cname) is None:
            idf.newidfobject(
                "CONSTRUCTION",
                Name=cname,
                Outside_Layer=PLACEHOLDER_MATERIAL,
            )


def export_idf(case_dir: Path) -> Path:
    case_dir = case_dir.resolve()
    case_name = case_dir.name
    yaml_path = case_dir / "output" / f"{case_name}.yaml"
    idf_path = case_dir / "output" / f"{case_name}.idf"

    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML not found: {yaml_path}")
    if not IDD_PATH.exists():
        raise FileNotFoundError(
            f"IDD not found at {IDD_PATH}. Run from repo root."
        )

    BaseSchema.set_idf(IDD_PATH)
    mgr = ConverterManager(yaml_path)
    _inject_placeholder_constructions(mgr._idf)
    mgr.convert_all()

    rp = mgr._idf.idfobjects["RUNPERIOD"][0]
    rp.Day_of_Week_for_Start_Day = "Sunday"
    rp.Use_Weather_File_Holidays_and_Special_Days = "Yes"
    rp.Use_Weather_File_Daylight_Saving_Period = "Yes"
    rp.Apply_Weekend_Holiday_Rule = "No"
    rp.Use_Weather_File_Rain_Indicators = "Yes"
    rp.Use_Weather_File_Snow_Indicators = "Yes"
    rp.Begin_Year = 2024
    rp.End_Year = 2024

    mgr._idf.idfobjects["BUILDING"][0].Minimum_Number_of_Warmup_Days = 1

    for surf in mgr._idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
        if surf.Outside_Boundary_Condition == "Surface":
            surf.Outside_Boundary_Condition = "Adiabatic"
            surf.Outside_Boundary_Condition_Object = ""
            surf.Sun_Exposure = "NoSun"
            surf.Wind_Exposure = "NoWind"
            surf.Construction_Name = "Default_Int_Wall"

    for sch in mgr._idf.idfobjects["SCHEDULE:COMPACT"]:
        for i in range(1, 100):
            field = f"Field_{i}"
            if hasattr(sch, field) and getattr(sch, field) is None:
                try:
                    delattr(sch, field)
                except Exception:
                    pass

    mgr.save_idf(idf_path)
    return idf_path


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python Tool_scripts/export_idf.py <case_dir>", file=sys.stderr)
        sys.exit(2)
    out = export_idf(Path(sys.argv[1]))
    print(f"IDF saved: {out}")


if __name__ == "__main__":
    main()
