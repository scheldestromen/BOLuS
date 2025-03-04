from geolib.models.dstability import DStabilityModel
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from dstability_toolbox.dm_getter import get_soil_by_id




# Step 1: Load the D-Stability model from a .stix file
stix_file = Path(r"C:\Users\danie\Documents\Rekenmap\Berekening 1.stix")  # Replace with your .stix file path
model = DStabilityModel()
model.parse(stix_file)

# Step 2: Extract required data
# Subsoil schematization (layers and soils)
subsoil_data = []
for layer in model.datastructure.geometries[0].Layers:  # Assuming first geometry
    soil_id = get_soil_id_by_layer_id(model, layer.Id, 0, 0)
    soil_name = next((soil.Code for soil in model.soils.Soils if soil.Id == soil_id), "Unknown")
    points = [(point.X, point.Z) for point in layer.Points]
    subsoil_data.append([soil_name, str(points)])

# Slip plane results (assuming calculation has been executed)
# model.execute()  # Execute if not already done
slip_plane = model.get_result(0, 0)
slip_plane_points = [(point.X, point.Z) for point in slip_plane.Points] if slip_plane else "No slip plane found"

# Phreatic line
waternet = model.waternets[0]  # Assuming first waternet
phreatic_line_id = waternet.PhreaticLineId
phreatic_line = waternet.get_head_line(phreatic_line_id)
phreatic_points = [(point.X, point.Z) for point in phreatic_line.Points] if phreatic_line else "No phreatic line"

# Headlines (assuming these are calculation settings or metadata)
headlines = {
    "Calculation Type": "dummy value",  # model.datastructure.calculationsettings[0].Type.Name,
    "Stage": model.scenarios[0].Stages[0].Label,
    "Notes": model.scenarios[0].Stages[0].Notes or "None"
}

# Step 3: Create the PDF factsheet
pdf_file = "dstability_factsheet.pdf"
doc = SimpleDocTemplate(pdf_file, pagesize=A4)
styles = getSampleStyleSheet()
elements = []

# Title
elements.append(Paragraph("D-Stability Calculation Factsheet", styles["Heading1"]))
elements.append(Spacer(1, 12))

# Headlines
elements.append(Paragraph("Headlines", styles["Heading2"]))
headline_data = [[key, value] for key, value in headlines.items()]
elements.append(Table(headline_data, colWidths=[100, 400], style=[
    ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
]))
elements.append(Spacer(1, 12))

# Subsoil Schematization
elements.append(Paragraph("Subsoil Schematization", styles["Heading2"]))
subsoil_table = Table(subsoil_data, colWidths=[100, 80, 80, 250], style=[
    ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Header row in grey
    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),  # Center numerical columns
    ('FONTSIZE', (0, 0), (-1, -1), 10),  # Adjust font size for readability
])
elements.append(subsoil_table)
elements.append(Spacer(1, 12))

# Slip Plane Results
elements.append(Paragraph("Slip Plane Results", styles["Heading2"]))
elements.append(Paragraph(f"Points: {slip_plane_points}", styles["BodyText"]))
elements.append(Spacer(1, 12))

# Phreatic Line
elements.append(Paragraph("Phreatic Line", styles["Heading2"]))
elements.append(Paragraph(f"Points: {phreatic_points}", styles["BodyText"]))

# Build the PDF
doc.build(elements)

print(f"PDF factsheet generated: {pdf_file}")
