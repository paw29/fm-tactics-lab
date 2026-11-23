"""Research instruction sweep (optimal-formation/engine/fm_instructions.py) on the FM 4-1-2-3 (three strikers),
winner of the exploitability ranking + databallpy cross-check (exploit.py, crosscheck.py).
Base geometry = FM slots at the model's reference-library depths (geo_score.place), same both phases.
  py f4123_instructions.py > f4123_instructions.txt"""
import os, sys
sys.path.insert(0, r'C:\Users\pawan\optimal-formation\engine')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fm_instructions as fi
import geo_score

SHAPE = 'DR-DCR-DCL-DL-DMC-AMR-AML-STR-ST-STL'.split('-')   # slots 0-9, keeper = 10
fi.BASE = geo_score.shape_tensor(SHAPE, SHAPE)
fi.IP, fi.OOP = fi.BASE[0], fi.BASE[1]
fi.G = {   # script's group names; for this shape they mean:
    "back three (CBs + half-back)": [1, 2, 4],     # DCR, DCL, DMC (build-up base)
    "central midfielders": [4],                    # DMC, the only central midfielder (playmaker zone)
    "wing-backs": [0, 3],                          # DR, DL (full-backs)
    "inside forwards": [5, 6],                     # AMR, AML (flank forwards: overlap/underlap partner)
    "striker (DLF)": [8],                          # ST
    "inner strikers": [7, 9],                      # STR, STL
}
fi.BACK4 = [0, 1, 2, 3]
fi.REST_OOP = [4, 5, 6, 7, 8, 9]
fi.BASE_SCORE = fi.score(fi.BASE)
print('4-1-2-3 geometry (m):', [(round(float(x), 1), round(float(y), 1)) for x, y in fi.BASE[1]])
fi.main()
