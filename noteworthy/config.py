from pathlib import Path
BASE_DIR = Path(__file__).parent.parent.resolve()
BUILD_DIR = BASE_DIR / 'templates/build'
OUTPUT_FILE = BASE_DIR / 'output.pdf'
RENDERER_FILE = BASE_DIR / 'templates/parser.typ'
SYSTEM_CONFIG_DIR = BASE_DIR / 'templates/systemconfig'
SETTINGS_FILE = SYSTEM_CONFIG_DIR / 'build_settings.json'
INDEXIGNORE_FILE = SYSTEM_CONFIG_DIR / '.indexignore'
METADATA_FILE = BASE_DIR / 'config/metadata.json'
CONSTANTS_FILE = BASE_DIR / 'config/constants.json'
HIERARCHY_FILE = BASE_DIR / 'config/hierarchy.json'
PREFACE_FILE = BASE_DIR / 'config/preface.typ'
SNIPPETS_FILE = BASE_DIR / 'config/snippets.typ'
SCHEMES_DIR = BASE_DIR / 'config/schemes'
SETUP_FILE = BASE_DIR / 'templates/setup.typ'

LOGO = ['         ,--. ', "       ,--.'| ", '   ,--,:  : | ', ",`--.'`|  ' : ", '|   :  :  | | ', ':   |   \\ | : ', "|   : '  '; | ", "'   ' ;.    ; ", '|   | | \\   | ', "'   : |  ; .' ", "|   | '`--'   ", "'   : |       ", ";   |.'       ", "'---'         "]
HAPPY_FACE = ['    __  ', ' _  \\ \\ ', '(_)  | |', '     | |', ' _   | |', '(_)  | |', '    /_/ ']
HMM_FACE = ['     _ ', ' _  | |', '(_) | |', '    | |', ' _  | |', '(_) | |', '    |_|']
SAD_FACE = ['       __', '  _   / /', ' (_) | | ', '     | | ', '  _  | | ', ' (_) | | ', '      \\_\\']