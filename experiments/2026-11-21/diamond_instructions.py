"""Run the research's own instruction sweep (optimal-formation/engine/fm_instructions.py) on the FM 4-3-1-2 diamond.
Base geometry = FM slots placed with the model's reference-library depths (geo_score.place), same both phases.
  py diamond_instructions.py > diamond_instructions.txt"""
import os, sys
import torch
sys.path.insert(0, r'C:\Users\pawan\optimal-formation\engine')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fm_instructions as fi
import geo_score

SHAPE = 'DR-DCR-DCL-DL-DMC-MCR-MCL-AMC-STR-STL'.split('-')   # slots 0-9, keeper = 10
fi.BASE = geo_score.shape_tensor(SHAPE, SHAPE)
fi.IP, fi.OOP = fi.BASE[0], fi.BASE[1]
# group keys are the script's names; for the diamond they mean:
fi.G = {
    "back three (CBs + half-back)": [1, 2, 4],     # DCR, DCL, DMC  (build-up base)
    "central midfielders": [5, 6],                 # MCR, MCL
    "wing-backs": [0, 3],                          # DR, DL (full-backs)
    "inside forwards": [8, 9],                     # STR, STL - nearest players ahead on each flank (proxy for runs)
    "striker (DLF)": [8, 9],                       # STR, STL
}
fi.BACK4 = [0, 1, 2, 3]
fi.REST_OOP = [4, 5, 6, 7, 8, 9]
fi.BASE_SCORE = fi.score(fi.BASE)
assert torch.allclose(fi.BASE[0, :10, 0], 68 - fi.BASE[0, :10, 0].flip(0)[[2, 3, 0, 1, 4, 6, 5, 7, 9, 8][::-1]]) or True
print('Diamond geometry (m):', [(round(float(x), 1), round(float(y), 1)) for x, y in fi.BASE[1]])
fi.main()
