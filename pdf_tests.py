from fpdf import FPDF
pdf = FPDF(orientation='P', unit='mm', format='A4')
pdf.add_page()
pdf.set_font("Arial", size=12, style="B")
pdf.cell(200, 10, txt="Привет", ln=1, align="C")
pdf.output("simple_demo.pdf")
