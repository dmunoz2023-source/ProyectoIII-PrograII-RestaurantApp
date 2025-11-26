from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from src.models import OrderModel

class Receipt:
    def __init__(self, order: OrderModel):
        self.order = order
        # Generamos un nombre único para no pisar archivos si se abren varios
        self.filepath = f"boleta_{self.order.id}.pdf"

    def generate_pdf(self) -> tuple[bool, str]:
        doc = SimpleDocTemplate(self.filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Encabezado con datos reales del pedido
        client_name = self.order.client.name if self.order.client else "Cliente General"
        
        story_items_texts = [
            "<b>Boleta Restaurante</b>", 
            "<b>Razón Social del Negocio</b>",
            "<b>RUT:</b> 12345678-9", 
            "<b>Dirección:</b> Calle Falsa 123",
            f"<b>Fecha Emisión:</b> {self.order.date.strftime('%d/%m/%Y %H:%M:%S')}",
            f"<b>N° Pedido:</b> {self.order.id}",
            f"<b>Cliente:</b> {client_name}"
        ]
        
        for i, txt in enumerate(story_items_texts):
            story.append(Paragraph(txt, styles['Heading1'] if i == 0 else styles['Normal']))
        story.append(Spacer(1, 18))

        # Tabla de Detalles
        table_data = [['Cant.', 'Descripción', 'P. Unit.', 'Subtotal']]
        
        # Extraer líneas desde la relación ORM (order.details)
        for detail in self.order.details:
            name = detail.menu_item.name
            qty = detail.quantity
            price = detail.menu_item.price
            subtotal = detail.subtotal
            
            table_data.append([
                str(qty),
                name,
                f"${price:,.0f}".replace(",", "."),
                f"${subtotal:,.0f}".replace(",", ".")
            ])
        
        # Totales
        total = self.order.total
        subtotal_neto = total / 1.19
        iva_amount = total - subtotal_neto
        
        subtotal_str = f"${subtotal_neto:,.0f}".replace(",", ".")
        iva_str = f"${iva_amount:,.0f}".replace(",", ".")
        total_str = f"${total:,.0f}".replace(",", ".")

        table_data.append(["", "", "SUBTOTAL", subtotal_str])
        table_data.append(["", "", "IVA (19%)", iva_str])
        table_data.append(["", "", "TOTAL", total_str])

        # Estilos
        table = Table(table_data, colWidths=[40, 250, 80, 80])
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004D40')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (2, -3), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#4CAF50')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
        ])
        
        table.setStyle(style)
        story.append(table)
        story.append(Spacer(1, 12))
        story.append(Paragraph("Gracias por su preferencia.", styles['Italic']))

        try:
            doc.build(story)
            return True, self.filepath
        except Exception as e:
            return False, f"Error al generar el PDF: {e}"