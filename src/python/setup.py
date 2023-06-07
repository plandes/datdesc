from pathlib import Path
from zensols.pybuild import SetupUtil

su = SetupUtil(
    setup_path=Path(__file__).parent.absolute(),
    name="zensols.datdesc",
    package_names=['zensols', 'resources'],
    package_data={'': ['*.conf', '*.json', '*.yml']},
    description='Generate Latex tables in a .sty file from CSV files',
    user='plandes',
    project='datdesc',
    keywords=['tooling'],
).setup()
