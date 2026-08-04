from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("invoice.pdf", pagesize=letter)
c.drawString(50, 750, "INVOICE")
c.drawString(50, 700, "Vendor: ABC Company")
c.drawString(50, 680, "Date: 08/04/2026")
c.drawString(50, 660, "Invoice #: 12345")
c.drawString(50, 640, "Item: Service")
c.drawString(50, 620, "Amount: $100.00")
c.save()
print("invoice.pdf created!")