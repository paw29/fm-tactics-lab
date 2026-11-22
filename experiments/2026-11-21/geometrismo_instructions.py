"""Run the research's own instruction sweep (optimal-formation/engine/fm_instructions.py) on Geometrismo (3-2-5 / 4-1-4-1).
Base geometry = FM slots placed with the model's reference-library depths (geo_score.place), same both phases.
  py diamond_instructions.py > diamond_instructions.txt"""
import os, sys
import torch
sys.path.insert(0, r'C:\Users\pawan\optimal-formation\engine')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fm_instructions as fi
import geo_score

IPS = 'DR-DCR-DCL-DL-DMC-MCL-MCR-AMR-AML-ST'.split('-')   # Geometrismo in possession (WBs, HB, IFs, CF)
OOPS = 'DR-DCR-DCL-DL-DMC-MCL-MCR-MR-ML-ST'.split('-')   # Geometrismo out of possession 4-1-4-1
fi.BASE = geo_score.shape_tensor(IPS, OOPS)
fi.IP, fi.OOP = fi.BASE[0], fi.BASE[1]
# group keys are the script's names; for the diamond they mean:
fi.G = {
    "back three (CBs + half-back)": [1, 2, 4],     # DCR, DCL, HB
    "central midfielders": [5, 6],                 # MCL, MCR
    "wing-backs": [0, 3],                          # DR, DL wing-backs
    "inside forwards": [7, 8],                     # AMR, AML inside forwards
    "striker (DLF)": [9],                          # ST
}
fi.BACK4 = [0, 1, 2, 3]
fi.REST_OOP = [4, 5, 6, 7, 8, 9]
fi.BASE_SCORE = fi.score(fi.BASE)
print('Geometrismo geometry (m):', [(round(float(x), 1), round(float(y), 1)) for x, y in fi.BASE[1]])
fi.main()
