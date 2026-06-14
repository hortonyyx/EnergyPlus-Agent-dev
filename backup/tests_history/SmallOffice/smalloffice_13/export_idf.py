"""Export smalloffice_13.yaml → IDF following skills/energyplus_mcp/export_idf.md."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.validator.data_model import BaseSchema
from src.converter_manager import ConverterManager

idd_file = ROOT / 'data' / 'dependencies' / 'Energy+.idd'
BaseSchema.set_idf(idd_file)

yaml_path = ROOT / 'test_data' / 'SmallOffice' / 'smalloffice_13' / 'smalloffice_13.yaml'
output_dir = ROOT / 'test_data' / 'SmallOffice' / 'smalloffice_13' / 'output'
output_dir.mkdir(parents=True, exist_ok=True)

manager = ConverterManager(yaml_path)
manager.convert_all()

# --- Post-conversion fixes ---
rp = manager._idf.idfobjects['RUNPERIOD'][0]
rp.Day_of_Week_for_Start_Day = 'Sunday'
rp.Use_Weather_File_Holidays_and_Special_Days = 'Yes'
rp.Use_Weather_File_Daylight_Saving_Period = 'Yes'
rp.Apply_Weekend_Holiday_Rule = 'No'
rp.Use_Weather_File_Rain_Indicators = 'Yes'
rp.Use_Weather_File_Snow_Indicators = 'Yes'
rp.Begin_Year = 2024
rp.End_Year = 2024

bldg = manager._idf.idfobjects['BUILDING'][0]
bldg.Minimum_Number_of_Warmup_Days = 1

for surf in manager._idf.idfobjects['BUILDINGSURFACE:DETAILED']:
    if surf.Outside_Boundary_Condition == 'Surface':
        surf.Outside_Boundary_Condition = 'Adiabatic'
        surf.Outside_Boundary_Condition_Object = ''
        surf.Sun_Exposure = 'NoSun'
        surf.Wind_Exposure = 'NoWind'
        surf.Construction_Name = 'Int_Wall'

for sch in manager._idf.idfobjects['SCHEDULE:COMPACT']:
    for i in range(1, 100):
        field_name = f'Field_{i}'
        if hasattr(sch, field_name):
            val = getattr(sch, field_name)
            if val is None:
                try:
                    delattr(sch, field_name)
                except Exception:
                    pass

idf_path = output_dir / 'smalloffice_13.idf'
manager.save_idf(idf_path)
print('IDF saved to:', idf_path)
