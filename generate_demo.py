from pathlib import Path
import json
from src.field import package,synthetic_tile
root=Path(__file__).resolve().parent
out=root/'demo-field'
field,anchor=package([synthetic_tile(22,10,38),synthetic_tile(22,10,39),synthetic_tile(91,19,19),synthetic_tile(91,19,20),synthetic_tile(91,20,19)],out)
(root/'trust-anchor-demo.json').write_text(json.dumps(anchor,indent=2)+'\n')
print('Synthetic field:',out,'root:',anchor['field_root'])
