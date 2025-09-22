"""
Read results from a directory of .stix files
"""

import os

from bolus.toolbox.results import results_from_dir

if __name__ == "__main__":
    directory = input("Voer het pad naar map met .stix-bestanden in en druk op enter "
                      "(laat leeg voor gebruik van de standaardmap): ")

    if directory == "":
        directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Uitvoer")

    print("Exporteren naar D-Stability Rekenresultaten.xlsx...")
    results_from_dir(
        directory=directory,
        output_path=os.path.join(directory, "D-Stability Rekenresultaten.xlsx")
    )
    print("Afgerond")
