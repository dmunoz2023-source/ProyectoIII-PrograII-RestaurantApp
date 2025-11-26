from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

def generate_menu_pdf(available_items: list) -> tuple[bool, str]:
    """
    Genera un PDF con la lista de menús recibida.
    Recibe: available_items (Lista de objetos MenuItemModel)
    """
    filepath = "carta.pdf"
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Título y Fecha
    title_style = styles['Title']
    title_style.textColor = colors.HexColor('#262433')
    story.append(Paragraph("<b>Restaurante - Carta de la Casa</b>", title_style))
    story.append(Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(Spacer(1, 20))

    # Preparar datos de la tabla
    table_data = [["Menú", "Precio"]] # Encabezados

    if not available_items:
        story.append(Paragraph("No hay menús disponibles para la venta en este momento.", styles['Normal']))
    else:
        # Ordenar alfabéticamente por nombre
        items_sorted = sorted(available_items, key=lambda x: x.name)
        
        for item in items_sorted:
            # item es una instancia de MenuItemModel, tiene .name y .price
            table_data.append([item.name, f"${item.price:,.0f}"])

    # Si hay datos (más allá del encabezado), creamos la tabla
    if len(table_data) > 1:
        table = Table(table_data, colWidths=[300, 100])
        
        # Estilos de la tabla
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')), # Encabezado Azul
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F3F4F6')), # Filas gris claro
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'), # Precio a la derecha
        ])
        
        table.setStyle(style)
        story.append(table)

    try:
        doc.build(story)
        return True, filepath
    except Exception as e:
        return False, f"Error al generar el PDF: {e}"