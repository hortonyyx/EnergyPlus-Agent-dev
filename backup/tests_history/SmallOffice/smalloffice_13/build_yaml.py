"""Generate smalloffice_13.yaml from the zone table in claude_ep.md."""
from pathlib import Path
import yaml

OUT = Path('test_data/SmallOffice/smalloffice_13/smalloffice_13.yaml')

# ---- Geometry ----------------------------------------------------------
W, D = 15.0, 8.0
FLOOR_H = 3.60
N_FLOORS = 2

# Zone layout (per floor): (name_suffix, x_min, x_max, y_min, y_max)
LAYOUT = [
    ('S1', 0.0, 5.0, 0.0, 3.0),
    ('S2', 5.0, 10.0, 0.0, 3.0),
    ('S3', 10.0, 15.0, 0.0, 3.0),
    ('C',  0.0, 15.0, 3.0, 5.0),
    ('N1', 0.0, 5.0, 5.0, 8.0),
    ('N2', 5.0, 10.0, 5.0, 8.0),
    ('N3', 10.0, 15.0, 5.0, 8.0),
]

# Windows: (zone_suffix, facade, axis-range)
#  South/North windows at x-ranges; z-range per floor derived below.
WIN_X = [(1.40, 3.80), (6.30, 8.70), (11.20, 13.60)]
WIN_SILL = 1.00
WIN_HEAD = 2.80  # = 1.00 + 1.80 (F1 absolute)

def v(x, y, z): return {'X': float(x), 'Y': float(y), 'Z': float(z)}

# ---- Zones -------------------------------------------------------------
zones = []
for f in range(1, N_FLOORS + 1):
    z0 = (f - 1) * FLOOR_H
    for (suf, xmin, xmax, ymin, ymax) in LAYOUT:
        zones.append({
            'Name': f'Zone_F{f}_{suf}',
            'Direction of Relative North': 0.0,
            'X Origin': (xmin + xmax) / 2,
            'Y Origin': (ymin + ymax) / 2,
            'Z Origin': z0,
            'Type': 1,
            'Multiplier': 1,
            'Ceiling Height': FLOOR_H,
            'Volume': 'autocalculate',
            'Floor Area': 'autocalculate',
            'Zone Inside Convection Algorithm': 'TARP',
            'Zone Outside Convection Algorithm': 'DOE-2',
            'Part of Total Floor Area': 'Yes',
        })

# ---- Materials & Constructions ----------------------------------------
materials = [
    {'Name': 'Concrete_150mm', 'Type': 'Standard', 'Roughness': 'MediumRough',
     'Thickness': 0.15, 'Conductivity': 1.73, 'Density': 2243.0, 'Specific_Heat': 837.0},
    {'Name': 'Insulation_50mm', 'Type': 'Standard', 'Roughness': 'MediumRough',
     'Thickness': 0.05, 'Conductivity': 0.042, 'Density': 65.0, 'Specific_Heat': 837.0},
    {'Name': 'Gypsum_Board', 'Type': 'Standard', 'Roughness': 'Smooth',
     'Thickness': 0.013, 'Conductivity': 0.16, 'Density': 800.0, 'Specific_Heat': 1090.0},
    {'Name': 'Double_Glazing', 'Type': 'Glazing', 'U-Factor': 2.7,
     'Solar_Heat_Gain_Coefficient': 0.6, 'Visible_Transmittance': 0.75},
]
constructions = [
    {'Name': 'Ext_Wall', 'Layers': ['Gypsum_Board', 'Insulation_50mm', 'Concrete_150mm', 'Gypsum_Board']},
    {'Name': 'Int_Wall', 'Layers': ['Gypsum_Board', 'Concrete_150mm', 'Gypsum_Board']},
    {'Name': 'Floor',    'Layers': ['Concrete_150mm', 'Insulation_50mm', 'Gypsum_Board']},
    {'Name': 'Roof',     'Layers': ['Gypsum_Board', 'Insulation_50mm', 'Concrete_150mm']},
    {'Name': 'Window_Construction', 'Layers': ['Double_Glazing']},
    {'Name': 'Default_Construction', 'Layers': ['Gypsum_Board', 'Concrete_150mm', 'Gypsum_Board']},
]

# ---- Surfaces ----------------------------------------------------------
surfaces = []

def make_wall(zone, wall_idx, xmin, xmax, ymin, ymax, zbot, ztop, facade):
    """Create a wall. facade ∈ {'south','east','north','west'}.
    Exterior test is done by caller via construction/boundary args."""
    if facade == 'south':  # y = ymin
        verts = [v(xmin, ymin, zbot), v(xmax, ymin, zbot),
                 v(xmax, ymin, ztop), v(xmin, ymin, ztop)]
    elif facade == 'east':  # x = xmax
        verts = [v(xmax, ymin, zbot), v(xmax, ymax, zbot),
                 v(xmax, ymax, ztop), v(xmax, ymin, ztop)]
    elif facade == 'north':  # y = ymax
        verts = [v(xmax, ymax, zbot), v(xmin, ymax, zbot),
                 v(xmin, ymax, ztop), v(xmax, ymax, ztop)]
    else:  # west, x = xmin
        verts = [v(xmin, ymax, zbot), v(xmin, ymin, zbot),
                 v(xmin, ymin, ztop), v(xmin, ymax, ztop)]
    return {
        'Name': f'{zone}_Wall_{wall_idx}',
        'Surface Type': 'Wall',
        'Zone Name': zone,
        'Vertices': verts,
        '_facade': facade,
    }

for f in range(1, N_FLOORS + 1):
    zbot = (f - 1) * FLOOR_H
    ztop = f * FLOOR_H
    for (suf, xmin, xmax, ymin, ymax) in LAYOUT:
        zone = f'Zone_F{f}_{suf}'
        walls = [
            make_wall(zone, 1, xmin, xmax, ymin, ymax, zbot, ztop, 'south'),
            make_wall(zone, 2, xmin, xmax, ymin, ymax, zbot, ztop, 'east'),
            make_wall(zone, 3, xmin, xmax, ymin, ymax, zbot, ztop, 'north'),
            make_wall(zone, 4, xmin, xmax, ymin, ymax, zbot, ztop, 'west'),
        ]
        # Classify exterior vs interior
        exterior_edges = {
            'south': abs(ymin - 0.0) < 1e-6,
            'east':  abs(xmax - W)   < 1e-6,
            'north': abs(ymax - D)   < 1e-6,
            'west':  abs(xmin - 0.0) < 1e-6,
        }
        for w in walls:
            fc = w.pop('_facade')
            if exterior_edges[fc]:
                w.update({
                    'Construction Name': 'Ext_Wall',
                    'Outside Boundary Condition': 'Outdoors',
                    'Sun Exposure': 'SunExposed',
                    'Wind Exposure': 'WindExposed',
                    'View Factor to Ground': 'autocalculate',
                })
            else:
                w.update({
                    'Construction Name': 'Int_Wall',
                    'Outside Boundary Condition': 'Adiabatic',
                    'Sun Exposure': 'NoSun',
                    'Wind Exposure': 'NoWind',
                    'View Factor to Ground': 'autocalculate',
                })
            surfaces.append(w)

        # Floor
        if f == 1:
            floor = {
                'Name': f'{zone}_Floor',
                'Surface Type': 'Floor',
                'Construction Name': 'Floor',
                'Zone Name': zone,
                'Outside Boundary Condition': 'Ground',
                'Sun Exposure': 'NoSun',
                'Wind Exposure': 'NoWind',
                'View Factor to Ground': 'autocalculate',
                'Vertices': [v(xmin, ymax, zbot), v(xmax, ymax, zbot),
                             v(xmax, ymin, zbot), v(xmin, ymin, zbot)],
            }
        else:
            floor = {
                'Name': f'{zone}_Floor',
                'Surface Type': 'Floor',
                'Construction Name': 'Default_Construction',
                'Zone Name': zone,
                'Outside Boundary Condition': 'Adiabatic',
                'Sun Exposure': 'NoSun',
                'Wind Exposure': 'NoWind',
                'View Factor to Ground': 'autocalculate',
                'Vertices': [v(xmin, ymax, zbot), v(xmax, ymax, zbot),
                             v(xmax, ymin, zbot), v(xmin, ymin, zbot)],
            }
        surfaces.append(floor)

        # Ceiling
        if f == N_FLOORS:
            ceiling = {
                'Name': f'{zone}_Ceiling',
                'Surface Type': 'Ceiling',
                'Construction Name': 'Roof',
                'Zone Name': zone,
                'Outside Boundary Condition': 'Outdoors',
                'Sun Exposure': 'NoSun',
                'Wind Exposure': 'NoWind',
                'View Factor to Ground': 'autocalculate',
                'Vertices': [v(xmin, ymin, ztop), v(xmax, ymin, ztop),
                             v(xmax, ymax, ztop), v(xmin, ymax, ztop)],
            }
        else:
            ceiling = {
                'Name': f'{zone}_Ceiling',
                'Surface Type': 'Ceiling',
                'Construction Name': 'Default_Construction',
                'Zone Name': zone,
                'Outside Boundary Condition': 'Adiabatic',
                'Sun Exposure': 'NoSun',
                'Wind Exposure': 'NoWind',
                'View Factor to Ground': 'autocalculate',
                'Vertices': [v(xmin, ymin, ztop), v(xmax, ymin, ztop),
                             v(xmax, ymax, ztop), v(xmin, ymax, ztop)],
            }
        surfaces.append(ceiling)

# ---- Fenestration ------------------------------------------------------
# South windows → parent zones F?_S1..S3 (Wall_1). North windows → F?_N1..N3 (Wall_3).
# Each of the 3 windows aligns with its zone's x-range (1.4-3.8 ∈ [0,5], 6.3-8.7 ∈ [5,10], 11.2-13.6 ∈ [10,15]).
fenestration = []
for f in range(1, N_FLOORS + 1):
    zbot = (f - 1) * FLOOR_H
    sill_z = zbot + 1.00
    head_z = zbot + 2.80
    # South facade (y = 0) — zones S1/S2/S3, Wall_1
    for (suf, (xmin_w, xmax_w)) in zip(['S1', 'S2', 'S3'], WIN_X):
        zone = f'Zone_F{f}_{suf}'
        fenestration.append({
            'Name': f'Win_F{f}_{suf}_South',
            'Surface Type': 'Window',
            'Construction Name': 'Window_Construction',
            'Building Surface Name': f'{zone}_Wall_1',
            'Multiplier': 1,
            'View Factor to Ground': 'autocalculate',
            'Number of Vertices': 'autocalculate',
            'Vertices': [
                v(xmin_w, 0.0, sill_z),
                v(xmax_w, 0.0, sill_z),
                v(xmax_w, 0.0, head_z),
                v(xmin_w, 0.0, head_z),
            ],
        })
    # North facade (y = 8) — zones N1/N2/N3, Wall_3
    for (suf, (xmin_w, xmax_w)) in zip(['N1', 'N2', 'N3'], WIN_X):
        zone = f'Zone_F{f}_{suf}'
        fenestration.append({
            'Name': f'Win_F{f}_{suf}_North',
            'Surface Type': 'Window',
            'Construction Name': 'Window_Construction',
            'Building Surface Name': f'{zone}_Wall_3',
            'Multiplier': 1,
            'View Factor to Ground': 'autocalculate',
            'Number of Vertices': 'autocalculate',
            'Vertices': [
                v(xmax_w, D, sill_z),
                v(xmin_w, D, sill_z),
                v(xmin_w, D, head_z),
                v(xmax_w, D, head_z),
            ],
        })

print(f'Zones: {len(zones)}, Surfaces: {len(surfaces)}, Fenestration: {len(fenestration)}')
assert len(zones) == 14
assert len(fenestration) == 12  # 3 south × 2 floors + 3 north × 2 floors

# ---- People / Lights / HVAC -------------------------------------------
people = []
lights = []
hvac_ideal = []
for z in zones:
    zn = z['Name']
    people.append({
        'Name': f'{zn}_People',
        'Zone or ZoneList or Space or SpaceList Name': zn,
        'Number of People Schedule Name': 'Occupancy_Schedule',
        'Number of People Calculation Method': 'People',
        'Number of People': 1.0,
        'People per Floor Area': 0.0,
        'Floor Area per Person': 0.0,
        'Fraction Radiant': 0.3,
        'Sensible Heat Fraction': 'Autocalculate',
        'Activity Level Schedule Name': 'Occupancy_Schedule',
        'Carbon Dioxide Generation Rate': 3.82e-08,
        'Enable ASHRAE 55 Comfort Warnings': 'No',
        'Mean Radiant Temperature Calculation Type': 'EnclosureAveraged',
        'Surface Name Angle Factor List Name': '',
        'Work Efficiency Schedule Name': '',
        'Clothing Insulation Calculation Method': 'ClothingInsulationSchedule',
        'Clothing Insulation Calculation Method Schedule Name': '',
        'Clothing Insulation Schedule Name': '',
        'Air Velocity Schedule Name': '',
        'Thermal Comfort Model 1 Type': '',
        'Thermal Comfort Model 2 Type': '',
        'Thermal Comfort Model 3 Type': '',
        'Thermal Comfort Model 4 Type': '',
        'Thermal Comfort Model 5 Type': '',
        'Thermal Comfort Model 6 Type': '',
        'Thermal Comfort Model 7 Type': '',
        'Ankle Level Air Velocity Schedule Name': '',
        'Cold Stress Temperature Threshold': 15.56,
        'Heat Stress Temperature Threshold': 30.0,
    })
    lights.append({
        'Name': f'{zn}_Lights',
        'Zone or ZoneList or Space or SpaceList Name': zn,
        'Schedule Name': 'Lighting_Schedule',
        'Design Level Calculation Method': 'Watts/Area',
        'Lighting Level': 0.0,
        'Watts per Floor Area': 10.0,
        'Watts per Person': 0.0,
        'Return Air Fraction': 0.0,
        'Fraction Radiant': 0.0,
        'Fraction Visible': 0.0,
        'Fraction Replaceable': 1.0,
        'End Use Subcategory': 'General',
        'Return Air Fraction Calculated from Plenum Temperature': 'No',
        'Return Air Fraction Function of Plenum Temperature Coefficient 1': 0.0,
        'Return Air Fraction Function of Plenum Temperature Coefficient 2': 0.0,
        'Return Air Heat Gain Node Name': '',
        'Exhaust Air Heat Gain Node Name': '',
    })
    hvac_ideal.append({'Zone Name': zn, 'Template Thermostat Name': 'Office_Thermostat'})

# ---- Full YAML doc -----------------------------------------------------
doc = {
    'Building': {
        'Name': 'SmallOffice_13',
        'North Axis': 0.0,
        'Terrain': 'Suburbs',
        'Loads Convergence Tolerance Value': 0.04,
        'Temperature Convergence Tolerance Value': 0.4,
        'Solar Distribution': 'FullExterior',
        'Maximum Number of Warmup Days': 25,
        'Minimum Number of Warmup Days': 1,
    },
    'Site:Location': {
        'Name': 'Shenzhen',
        'Latitude': 22.54,
        'Longitude': 114.06,
        'Time Zone': 8.0,
        'Elevation': 10.0,
    },
    'Zone': zones,
    'Material': materials,
    'Construction': constructions,
    'BuildingSurface:Detailed': surfaces,
    'FenestrationSurface:Detailed': fenestration,
    'Schedule': {
        'ScheduleTypeLimits': [
            {'Name': 'Fraction', 'Lower Limit Value': 0.0, 'Upper Limit Value': 1.0,
             'Numeric Type': 'CONTINUOUS', 'Unit Type': 'Dimensionless'},
            {'Name': 'Temperature', 'Lower Limit Value': 0.0, 'Upper Limit Value': 100.0,
             'Numeric Type': 'CONTINUOUS', 'Unit Type': 'Temperature'},
        ],
        'Schedule:Compact': [
            {'Name': 'Occupancy_Schedule', 'Schedule Type Limits Name': 'Fraction',
             'Data': ['Through: 12/31', 'For: Weekdays',
                      'Until: 08:00, 0.0', 'Until: 12:00, 1.0', 'Until: 13:00, 0.5',
                      'Until: 18:00, 1.0', 'Until: 24:00, 0.0',
                      'For: Weekends', 'Until: 24:00, 0.0']},
            {'Name': 'Lighting_Schedule', 'Schedule Type Limits Name': 'Fraction',
             'Data': ['Through: 12/31', 'For: Weekdays',
                      'Until: 08:00, 0.0', 'Until: 18:00, 1.0', 'Until: 24:00, 0.0',
                      'For: Weekends', 'Until: 24:00, 0.0']},
            {'Name': 'Heating_Setpoint', 'Schedule Type Limits Name': 'Temperature',
             'Data': ['Through: 12/31', 'For: Alldays',
                      'Until: 08:00, 15.0', 'Until: 18:00, 20.0', 'Until: 24:00, 15.0']},
            {'Name': 'Cooling_Setpoint', 'Schedule Type Limits Name': 'Temperature',
             'Data': ['Through: 12/31', 'For: Alldays',
                      'Until: 08:00, 30.0', 'Until: 18:00, 24.0', 'Until: 24:00, 30.0']},
        ],
    },
    'People': people,
    'Light': lights,
    'HVAC': {
        'HVACTemplate:Thermostat': [
            {'Name': 'Office_Thermostat',
             'Heating Setpoint Schedule Name': 'Heating_Setpoint',
             'Cooling Setpoint Schedule Name': 'Cooling_Setpoint'},
        ],
        'HVACTemplate:Zone:IdealLoadsAirSystem': hvac_ideal,
    },
    'SimulationControl': {
        'Do Zone Sizing Calculation': 'No',
        'Do System Sizing Calculation': 'No',
        'Do Plant Sizing Calculation': 'No',
        'Run Simulation for Sizing Periods': 'No',
        'Run Simulation for Weather File Run Periods': 'Yes',
        'Do HVAC Sizing Simulation for Sizing Periods': 'Yes',
        'Maximum Number of HVAC Sizing Simulation Passes': 1,
    },
    'GlobalGeometryRules': {
        'Starting Vertex Position': 'UpperLeftCorner',
        'Vertex Entry Direction': 'Counterclockwise',
        'Coordinate System': 'World',
    },
    'RunPeriod': {
        'Name': 'Default Run Period',
        'Begin Month': 1,
        'Begin Day of Month': 1,
        'End Month': 12,
        'End Day of Month': 31,
    },
    'Output:VariableDictionary': {'Key Field': 'Regular'},
    'Output:Diagnostics': {'Key 1': 'DisplayExtraWarnings'},
    'Output:Table:SummaryReports': {'Report 1 Name': 'AllSummary'},
    'Output:Variable': [],
    'OutputControl:Table:Style': {'Column Separator': 'Comma', 'Unit Conversion': 'None'},
}

with open(OUT, 'w', encoding='utf-8') as f:
    yaml.safe_dump(doc, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
print('Wrote', OUT)
