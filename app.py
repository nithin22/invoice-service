from flask import Flask, request, jsonify, Response
import json
import asyncio
from jinja2 import Template
import os
import base64
import io
from datetime import datetime
from playwright.async_api import async_playwright
import nest_asyncio
import qrcode
from PIL import Image

# Enable nested event loops (needed for Flask + asyncio)
nest_asyncio.apply()

app = Flask(__name__)

# Updated HTML template for Invoice
INVOICE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ invoice_type | default("Invoice Template") }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: Arial, sans-serif;
            font-size: 10px;
            line-height: 1.2;
            color: #000;
        }

        .invoice-container {
            width: 210mm;
            min-height: 297mm;
            margin: 0 auto;
            padding: 10mm;
            background: white;
        }

        .header-section {
            border: 1px solid #000;
            margin-bottom: 5px;
        }

        .company-info {
            display: flex;
            justify-content: space-between;
            padding: 5px;
            border-bottom: 1px solid #000;
        }

        .company-left {
            flex: 1;
        }

        .company-right {
            flex: 1;
            text-align: right;
        }

        .invoice-header {
            text-align: center;
            background: #f0f0f0;
            padding: 5px;
            font-weight: bold;
            font-size: 14px;
            border-bottom: 1px solid #000;
            color: #d63384;
        }

        /* E-Invoice and E-Way Bill specific styles */
        .einvoice-info, .ewaybill-info {
            background: #e7f3ff;
            border: 1px solid #0066cc;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }

        .ewaybill-info {
            background: #fff3e0;
            border-color: #ff9800;
        }

        .irn-section, .ewb-section {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .irn-details, .ewb-details {
            flex: 2;
        }

        .qr-code-section {
            flex: 1;
            text-align: center;
        }

        .qr-code-image {
            max-width: 120px;
            max-height: 120px;
            border: 1px solid #ccc;
        }

        .compliance-note {
            font-size: 8px;
            color: #666;
            font-style: italic;
            margin-top: 5px;
        }

        .transport-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
        }

        .transport-section {
            padding: 8px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
        }

        .transport-title {
            font-weight: bold;
            color: #495057;
            margin-bottom: 5px;
        }

        .transport-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 2px;
            font-size: 8px;
        }

        .status-generated {
            background: #d4edda;
            color: #155724;
        }

        .status-pending {
            background: #fff3cd;
            color: #856404;
        }

        .status-failed {
            background: #f8d7da;
            color: #721c24;
        }

        .ewaybill-status {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 8px;
            font-weight: bold;
        }

        /* Rest of existing styles remain the same */
        .billing-section {
            display: flex;
            padding: 5px;
        }

        .from-section, .to-section {
            flex: 1;
            padding: 0 10px;
        }

        .from-section {
            border-right: 1px solid #000;
        }

        .section-title {
            font-weight: bold;
            margin-bottom: 5px;
        }

        .info-row {
            margin-bottom: 2px;
            display: flex;
        }

        .info-label {
            font-weight: bold;
            min-width: 80px;
        }

        .products-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: 8px;
        }

        .products-table th,
        .products-table td {
            border: 1px solid #000;
            padding: 3px;
            text-align: center;
            vertical-align: top;
        }

        .products-table th {
            background: #f0f0f0;
            font-weight: bold;
            font-size: 7px;
        }

        .product-name {
            text-align: left !important;
            font-size: 7px;
        }

        .total-row {
            font-weight: bold;
            background: #f9f9f9;
        }

        .tax-summary {
            margin: 10px 0;
            border: 1px solid #000;
        }

        .tax-header {
            background: #f0f0f0;
            padding: 5px;
            font-weight: bold;
            text-align: center;
        }

        .tax-details {
            display: flex;
        }

        .tax-left {
            flex: 2;
            padding: 5px;
            border-right: 1px solid #000;
        }

        .tax-right {
            flex: 1;
            padding: 5px;
        }

        .tax-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 2px;
        }

        .amount-words {
            margin: 10px 0;
            padding: 5px;
            border: 1px solid #000;
        }

        .footer-section {
            margin-top: 20px;
            border-top: 1px solid #000;
            padding-top: 10px;
        }

        .footer-info {
            font-size: 9px;
            margin-bottom: 5px;
        }

        .signature-section {
            text-align: right;
            margin-top: 20px;
        }

        .net-receivable {
            font-weight: bold;
            font-size: 12px;
        }

        @media print {
            .invoice-container {
                width: 100%;
                margin: 0;
                padding: 5mm;
            }
        }
    </style>
</head>
<body>
    <div class="invoice-container">
        <!-- Header Section -->
        <div class="header-section">
            <div class="company-info">
                <div class="company-left">
                    <div><strong>From:</strong> {{ company_name }}</div>
                    <div>{{ company_address }}</div>
                    <div>{{ company_city }}</div>
                </div>
                <div class="company-right">
                    <div><strong>Inv No:</strong> {{ invoice_number }}</div>
                    <div><strong>Invoice Date:</strong> {{ invoice_date }}</div>
                    <div><strong>GSTIN No:</strong> {{ company_gstin }}</div>
                    {% if document_type %}
                    <div style="color: #d63384;"><strong>{{ document_type }}</strong></div>
                    {% endif %}
                </div>
            </div>
            
            <div class="invoice-header">{{ invoice_type | default("TAX INVOICE") }}</div>
            
            <!-- E-Invoice Information Section -->
            {% if is_einvoice %}
            <div class="einvoice-info">
                <div class="irn-section">
                    <div class="irn-details">
                        <div><strong>IRN:</strong> {{ irn_number }}</div>
                        {% if ack_no %}
                        <div><strong>Ack No:</strong> {{ ack_no }}</div>
                        {% endif %}
                        {% if ack_date %}
                        <div><strong>Ack Date:</strong> {{ ack_date }}</div>
                        {% endif %}
                        <div>
                            <span class="einvoice-status status-{{ einvoice_status.lower() }}">
                                {{ einvoice_status }}
                            </span>
                        </div>
                        {% if government_portal %}
                        <div style="font-size: 8px; color: #666;">
                            Verify at: {{ government_portal }}
                        </div>
                        {% endif %}
                    </div>
                    {% if show_qr_code and qr_code_base64 %}
                    <div class="qr-code-section">
                        <img src="data:image/png;base64,{{ qr_code_base64 }}" 
                             alt="E-Invoice QR Code" 
                             class="qr-code-image" />
                        <div style="font-size: 7px; margin-top: 2px;">Scan QR for verification</div>
                    </div>
                    {% endif %}
                </div>
                {% if einvoice_compliance_note %}
                <div class="compliance-note">{{ einvoice_compliance_note }}</div>
                {% endif %}
            </div>
            {% endif %}

            <!-- E-Way Bill Information Section -->
            {% if is_ewaybill %}
            <div class="ewaybill-info">
                <div class="ewb-section">
                    <div class="ewb-details">
                        <div><strong>E-Way Bill No:</strong> {{ ewb_number }}</div>
                        {% if ewb_date %}
                        <div><strong>EWB Date:</strong> {{ ewb_date }}</div>
                        {% endif %}
                        {% if ewb_valid_until %}
                        <div><strong>Valid Until:</strong> {{ ewb_valid_until }}</div>
                        {% endif %}
                        <div>
                            <span class="ewaybill-status status-{{ ewaybill_status.lower() }}">
                                {{ ewaybill_status }}
                            </span>
                        </div>
                        {% if government_portal %}
                        <div style="font-size: 8px; color: #666;">
                            Verify at: https://ewaybillgst.gov.in
                        </div>
                        {% endif %}
                    </div>
                </div>

                <!-- Transport Details -->
                {% if transporter_name or vehicle_number %}
                <div class="transport-details">
                    <div class="transport-section">
                        <div class="transport-title">Transport Information</div>
                        {% if transporter_name %}
                        <div class="transport-row">
                            <span>Transporter:</span>
                            <span>{{ transporter_name }}</span>
                        </div>
                        {% endif %}
                        {% if transporter_id %}
                        <div class="transport-row">
                            <span>Transporter ID:</span>
                            <span>{{ transporter_id }}</span>
                        </div>
                        {% endif %}
                        {% if vehicle_number %}
                        <div class="transport-row">
                            <span>Vehicle No:</span>
                            <span>{{ vehicle_number }}</span>
                        </div>
                        {% endif %}
                        {% if driver_name %}
                        <div class="transport-row">
                            <span>Driver:</span>
                            <span>{{ driver_name }}</span>
                        </div>
                        {% endif %}
                        {% if driver_mobile %}
                        <div class="transport-row">
                            <span>Driver Mobile:</span>
                            <span>{{ driver_mobile }}</span>
                        </div>
                        {% endif %}
                    </div>

                    <div class="transport-section">
                        <div class="transport-title">Route Information</div>
                        {% if from_place %}
                        <div class="transport-row">
                            <span>From:</span>
                            <span>{{ from_place }} ({{ from_pincode }})</span>
                        </div>
                        {% endif %}
                        {% if to_place %}
                        <div class="transport-row">
                            <span>To:</span>
                            <span>{{ to_place }} ({{ to_pincode }})</span>
                        </div>
                        {% endif %}
                        {% if transport_distance %}
                        <div class="transport-row">
                            <span>Distance:</span>
                            <span>{{ transport_distance }} KM</span>
                        </div>
                        {% endif %}
                        {% if transport_mode %}
                        <div class="transport-row">
                            <span>Mode:</span>
                            <span>{{ transport_mode }}</span>
                        </div>
                        {% endif %}
                        {% if has_extensions and extension_count %}
                        <div class="transport-row">
                            <span>Extensions:</span>
                            <span>{{ extension_count }}</span>
                        </div>
                        {% endif %}
                    </div>
                </div>
                {% endif %}

                {% if ewaybill_compliance_note %}
                <div class="compliance-note">{{ ewaybill_compliance_note }}</div>
                {% endif %}
            </div>
            {% endif %}
            
            <div class="billing-section">
                <div class="from-section">
                    <div class="section-title">SM Name: {{ sm_name }}</div>
                    <div class="info-row">
                        <span class="info-label">Beat Name:</span>
                        <span>{{ beat_name }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Contact No:</span>
                        <span>{{ sm_contact }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">SM MobNo:</span>
                        <span>{{ sm_mobile }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">PAN:</span>
                        <span>{{ company_pan }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">FSSAI Lic No:</span>
                        <span>{{ company_fssai }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">GST State:</span>
                        <span>{{ company_gst_state }}, State Code: {{ company_state_code }}</span>
                    </div>
                </div>
                
                <div class="to-section">
                    <div class="section-title">To:</div>
                    <div><strong>{{ customer_name }}</strong></div>
                    <div>{{ customer_address }}</div>
                    <div class="info-row">
                        <span class="info-label">Cmp Retailer Code:</span>
                        <span>{{ retailer_code }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">PO/SO ref. no:</span>
                        <span>{{ po_so_ref }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">PAN:</span>
                        <span>{{ customer_pan }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">GSTIN No:</span>
                        <span>{{ customer_gstin }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Payment Mode:</span>
                        <span>{{ payment_mode }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Contact No:</span>
                        <span>{{ customer_contact }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Drug License No:</span>
                        <span>{{ drug_license }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">FSSAI Lic No:</span>
                        <span>{{ customer_fssai }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">GST State:</span>
                        <span>{{ customer_gst_state }}, State Code: {{ customer_state_code }}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Vehicle:</span>
                        <span>{{ vehicle }}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Products Table -->
        <table class="products-table">
            <thead>
                <tr>
                    <th rowspan="2">S.</th>
                    <th rowspan="2">HSN Code</th>
                    <th rowspan="2">Product Name</th>
                    <th rowspan="2">MRP</th>
                    <th rowspan="2">Cs</th>
                    <th rowspan="2">Qty</th>
                    <th rowspan="2">Free</th>
                    <th rowspan="2">Upc</th>
                    <th rowspan="2">Gross Rate</th>
                    <th rowspan="2">Total</th>
                    <th rowspan="2">Pri Disc</th>
                    <th rowspan="2">Sec Disc</th>
                    <th rowspan="2">LnD Disc</th>
                    <th rowspan="2">Taxable Amt</th>
                    <th colspan="2">CGST/IGST</th>
                    <th colspan="2">SGST</th>
                    <th rowspan="2">Net Rate</th>
                    <th rowspan="2">Net Value</th>
                </tr>
                <tr>
                    <th>Rate</th>
                    <th>Amt</th>
                    <th>Rate</th>
                    <th>Amt</th>
                </tr>
            </thead>
            <tbody>
                {% for product in products %}
                <tr>
                    <td>{{ product.serial_no }}</td>
                    <td>{{ product.hsn_code }}</td>
                    <td class="product-name">{{ product.product_name }}</td>
                    <td>{{ product.mrp }}</td>
                    <td>{{ product.cs }}</td>
                    <td>{{ product.qty }}</td>
                    <td>{{ product.free }}</td>
                    <td>{{ product.upc }}</td>
                    <td>{{ product.gross_rate }}</td>
                    <td>{{ product.total }}</td>
                    <td>{{ product.pri_disc }}</td>
                    <td>{{ product.sec_disc }}</td>
                    <td>{{ product.lnd_disc }}</td>
                    <td>{{ product.taxable_amt }}</td>
                    <td>{{ product.cgst_rate }}</td>
                    <td>{{ product.cgst_amt }}</td>
                    <td>{{ product.sgst_rate }}</td>
                    <td>{{ product.sgst_amt }}</td>
                    <td>{{ product.net_rate }}</td>
                    <td>{{ product.net_value }}</td>
                </tr>
                {% endfor %}
                
                <tr class="total-row">
                    <td colspan="4"><strong>No.of Items sold: {{ total_items }}</strong></td>
                    <td><strong>{{ total_cs }}</strong></td>
                    <td><strong>{{ total_qty }}</strong></td>
                    <td><strong>{{ total_free }}</strong></td>
                    <td></td>
                    <td></td>
                    <td><strong>{{ grand_total }}</strong></td>
                    <td><strong>{{ total_pri_disc }}</strong></td>
                    <td><strong>{{ total_sec_disc }}</strong></td>
                    <td><strong>{{ total_lnd_disc }}</strong></td>
                    <td><strong>{{ total_taxable_amt }}</strong></td>
                    <td></td>
                    <td><strong>{{ total_cgst_amt }}</strong></td>
                    <td></td>
                    <td><strong>{{ total_sgst_amt }}</strong></td>
                    <td></td>
                    <td><strong>{{ grand_total }}</strong></td>
                </tr>
            </tbody>
        </table>

        <!-- Tax Summary -->
        <div class="tax-summary">
            <div class="tax-header">
                <strong>Taxable CGST/IGST CGST/IGST Pre Tax Scheme Amt: {{ pre_tax_scheme_amt }}</strong><br>
                <strong>% Amt SGST% SGST Amt</strong><br>
                <strong>Net Amount: {{ net_amount }}</strong>
            </div>
            
            <div class="tax-details">
                <div class="tax-left">
                    {% for slab in tax_slabs %}
                    <div class="tax-row">
                        <span>{{ slab.taxable_amount }}</span>
                        <span>{{ slab.cgst_rate }}</span>
                        <span>{{ slab.cgst_amount }}</span>
                        <span>{{ slab.sgst_rate }}</span>
                        <span>{{ slab.sgst_amount }}</span>
                    </div>
                    {% endfor %}
                    
                    <div class="tax-row">
                        <span><strong>Total</strong></span>
                        <span><strong>Tot CGST</strong></span>
                        <span><strong>{{ total_cgst }}</strong></span>
                        <span><strong>Tot SGST</strong></span>
                        <span><strong>{{ total_sgst }}</strong></span>
                    </div>
                </div>
                
                <div class="tax-right">
                    <div class="tax-row">
                        <span>Cash Disc Deducted Above:</span>
                        <span>{{ cash_disc_deducted }}</span>
                    </div>
                    <div class="tax-row">
                        <span>TCS Tax Amt:</span>
                        <span>{{ tcs_tax_amt }}</span>
                    </div>
                    <div class="tax-row">
                        <span>Credit Adj.:</span>
                        <span>{{ credit_adj }}</span>
                    </div>
                    <div class="tax-row">
                        <span>Round Off:</span>
                        <span>{{ round_off }}</span>
                    </div>
                    <div class="tax-row net-receivable">
                        <span><strong>Net Receivable:</strong></span>
                        <span><strong>{{ net_receivable }}</strong></span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Amount in Words -->
        <div class="amount-words">
            <strong>Amount In Words:</strong><br>
            {{ amount_in_words }}
        </div>

        <!-- Footer -->
        <div class="footer-section">
            <div class="footer-info">
                <strong>For: {{ company_name }}</strong>
            </div>
            
            <div class="footer-info">
                E. & O.E. Declaration: Whether the tax is payable on reverse charge basis: {{ reverse_charge_basis }}
            </div>
            
            <div class="footer-info">
                Kindly note, any product of {{ return_policy_note }}
            </div>
            
            <div class="footer-info">
                Subject to {{ jurisdiction }} Jurisdiction only <strong>Ac No. {{ bank_account_no }} - {{ bank_name }} - IFSC CODE {{ bank_ifsc }}</strong>
            </div>
            
            <div class="signature-section">
                <strong>Authorised Signature</strong>
            </div>
        </div>
    </div>
</body>
</html>
"""

class InvoiceGenerator:
    def __init__(self):
        self.template = Template(INVOICE_TEMPLATE)
    
    def generate_qr_code(self, qr_data):
        """Generate QR code image and return base64 encoded string"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=4,
                border=1,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffered = io.BytesIO()
            qr_img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return img_base64
        except Exception as e:
            print(f"Error generating QR code: {str(e)}")
            return None
    
    def generate_html(self, invoice_data):
        """Generate HTML invoice from JSON data with QR code support"""
        try:
            # Generate QR code if data is provided
            if invoice_data.get('show_qr_code') and invoice_data.get('qr_code_data'):
                qr_base64 = self.generate_qr_code(invoice_data['qr_code_data'])
                if qr_base64:
                    invoice_data['qr_code_base64'] = qr_base64
                else:
                    invoice_data['show_qr_code'] = False
            
            html_content = self.template.render(**invoice_data)
            return html_content
        except Exception as e:
            raise Exception(f"Error generating HTML: {str(e)}")
    
    async def generate_pdf_async(self, invoice_data):
        """Generate PDF invoice using Playwright"""
        try:
            html_content = self.generate_html(invoice_data)
            
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                
                # Set the HTML content
                await page.set_content(html_content, wait_until="networkidle")
                
                # Generate PDF with proper options
                pdf_bytes = await page.pdf(
                    format='A4',
                    margin={
                        'top': '0.3in',
                        'right': '0.3in',
                        'bottom': '0.3in',
                        'left': '0.3in'
                    },
                    print_background=True
                )
                
                await browser.close()
                return pdf_bytes
                
        except Exception as e:
            raise Exception(f"Error generating PDF: {str(e)}")
    
    def generate_pdf(self, invoice_data):
        """Synchronous wrapper for PDF generation"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.generate_pdf_async(invoice_data))
        finally:
            loop.close()

    def validate_invoice_data(self, data):
        """Validate required fields in invoice data"""
        required_fields = [
            'invoice_number', 'invoice_date', 'company_name', 
            'customer_name', 'products', 'net_receivable'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate products array
        if not isinstance(data['products'], list) or len(data['products']) == 0:
            raise ValueError("Products must be a non-empty array")
        
        return True

    def validate_ewaybill_data(self, data):
        """Validate required fields for E-Way Bill"""
        required_fields = [
            'invoice_number', 'invoice_date', 'company_name', 
            'customer_name', 'products', 'net_receivable',
            'ewb_number'  # E-Way Bill specific
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required fields for E-Way Bill: {', '.join(missing_fields)}")
        
        # Validate products array
        if not isinstance(data['products'], list) or len(data['products']) == 0:
            raise ValueError("Products must be a non-empty array")
        
        return True

# Initialize the invoice generator
invoice_generator = InvoiceGenerator()

@app.route('/generate-invoice', methods=['POST'])
def generate_invoice():
    """API endpoint to generate regular invoice"""
    try:
        # Get JSON data from request
        invoice_data = request.get_json()
        
        if not invoice_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate the data
        invoice_generator.validate_invoice_data(invoice_data)
        
        # Get output format (html or pdf)
        output_format = request.args.get('format', 'html').lower()
        
        if output_format == 'pdf':
            # Generate PDF
            pdf_bytes = invoice_generator.generate_pdf(invoice_data)
            
            # Create response
            response = Response(pdf_bytes, mimetype='application/pdf')
            response.headers['Content-Disposition'] = f'attachment; filename=invoice_{invoice_data["invoice_number"]}.pdf'
            return response
        
        else:
            # Generate HTML
            html_content = invoice_generator.generate_html(invoice_data)
            return html_content, 200, {'Content-Type': 'text/html'}
            
    except ValueError as e:
        return jsonify({'error': f'Validation error: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/generate-ewaybill', methods=['POST'])
def generate_ewaybill():
    """API endpoint to generate E-Way Bill with transport details"""
    try:
        # Get JSON data from request
        ewaybill_data = request.get_json()
        
        if not ewaybill_data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Set E-Way Bill specific flags
        ewaybill_data['is_ewaybill'] = True
        ewaybill_data['invoice_type'] = ewaybill_data.get('invoice_type', 'TAX INVOICE WITH E-WAY BILL')
        ewaybill_data['document_type'] = ewaybill_data.get('document_type', 'ORIGINAL FOR CONSIGNEE')
        
        # Validate the data
        invoice_generator.validate_ewaybill_data(ewaybill_data)
        
        # Get output format (html or pdf)
        output_format = request.args.get('format', 'html').lower()
        
        if output_format == 'pdf':
            # Generate PDF
            pdf_bytes = invoice_generator.generate_pdf(ewaybill_data)
            
            # Create response
            response = Response(pdf_bytes, mimetype='application/pdf')
            response.headers['Content-Disposition'] = f'attachment; filename=ewaybill_{ewaybill_data["ewb_number"]}.pdf'
            return response
        
        else:
            # Generate HTML
            html_content = invoice_generator.generate_html(ewaybill_data)
            return html_content, 200, {'Content-Type': 'text/html'}
            
    except ValueError as e:
        return jsonify({'error': f'Validation error: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/template-schema', methods=['GET'])
def get_template_schema():
    """Get the JSON schema for invoice template"""
    schema = {
        "invoice_number": "string - Invoice number",
        "invoice_date": "string - Invoice date (DD/MM/YYYY)",
        "invoice_type": "string - Type of invoice (default: TAX INVOICE)",
        "document_type": "string - Document type (e.g., ORIGINAL FOR RECIPIENT)",
        
        # E-Invoice specific fields
        "is_einvoice": "boolean - Whether this is an E-Invoice",
        "irn_number": "string - IRN number for E-Invoice",
        "ack_no": "string - Acknowledgement number",
        "ack_date": "string - Acknowledgement date",
        "einvoice_status": "string - E-Invoice status (GENERATED, PENDING, FAILED)",
        "show_qr_code": "boolean - Whether to show QR code",
        "qr_code_data": "string - QR code data content",
        "government_portal": "string - Government portal URL",
        "einvoice_compliance_note": "string - Compliance note for E-Invoice",
        "signed_invoice_available": "boolean - Whether signed invoice is available",
        
        # E-Way Bill specific fields
        "is_ewaybill": "boolean - Whether this is an E-Way Bill",
        "ewb_number": "string - E-Way Bill number",
        "ewb_date": "string - E-Way Bill generation date",
        "ewb_valid_until": "string - E-Way Bill validity date",
        "ewaybill_status": "string - E-Way Bill status (GENERATED, PENDING, FAILED)",
        "ewaybill_compliance_note": "string - Compliance note for E-Way Bill",
        
        # Transport details for E-Way Bill
        "transporter_name": "string - Transporter name",
        "transporter_id": "string - Transporter ID/GSTIN",
        "vehicle_number": "string - Vehicle registration number",
        "driver_name": "string - Driver name",
        "driver_mobile": "string - Driver mobile number",
        "transport_distance": "string - Transport distance in KM",
        "transport_mode": "string - Mode of transport (Road/Rail/Air/Ship)",
        "from_place": "string - Origin place",
        "from_pincode": "string - Origin pincode",
        "from_state_code": "string - Origin state code",
        "to_place": "string - Destination place",
        "to_pincode": "string - Destination pincode",
        "to_state_code": "string - Destination state code",
        "has_extensions": "boolean - Whether E-Way Bill has extensions",
        "extension_count": "number - Number of extensions applied",
        
        # Company and customer details
        "company_name": "string - Company name",
        "company_address": "string - Company address",
        "company_city": "string - Company city",
        "company_gstin": "string - Company GSTIN",
        "company_pan": "string - Company PAN",
        "company_fssai": "string - Company FSSAI license",
        "company_gst_state": "string - Company GST state",
        "company_state_code": "string - Company state code",
        "sm_name": "string - Sales manager name",
        "beat_name": "string - Beat name",
        "sm_contact": "string - Sales manager contact",
        "sm_mobile": "string - Sales manager mobile",
        "customer_name": "string - Customer name",
        "customer_address": "string - Customer address",
        "retailer_code": "string - Retailer code",
        "po_so_ref": "string - PO/SO reference",
        "customer_pan": "string - Customer PAN",
        "customer_gstin": "string - Customer GSTIN",
        "payment_mode": "string - Payment mode",
        "customer_contact": "string - Customer contact",
        "drug_license": "string - Drug license number",
        "customer_fssai": "string - Customer FSSAI",
        "customer_gst_state": "string - Customer GST state",
        "customer_state_code": "string - Customer state code",
        "vehicle": "string - Vehicle information",
        
        # Product details
        "products": [
            {
                "serial_no": "number - Serial number",
                "hsn_code": "string - HSN code",
                "product_name": "string - Product name",
                "mrp": "string - MRP",
                "cs": "string - Cases",
                "qty": "string - Quantity",
                "free": "string - Free quantity",
                "upc": "string - UPC",
                "gross_rate": "string - Gross rate",
                "total": "string - Total amount",
                "pri_disc": "string - Primary discount",
                "sec_disc": "string - Secondary discount",
                "lnd_disc": "string - L&D discount",
                "taxable_amt": "string - Taxable amount",
                "cgst_rate": "string - CGST rate",
                "cgst_amt": "string - CGST amount",
                "sgst_rate": "string - SGST rate",
                "sgst_amt": "string - SGST amount",
                "net_rate": "string - Net rate",
                "net_value": "string - Net value"
            }
        ],
        
        # Summary totals
        "total_items": "string - Total number of items",
        "total_cs": "string - Total cases",
        "total_qty": "string - Total quantity",
        "total_free": "string - Total free quantity",
        "grand_total": "string - Grand total",
        "total_pri_disc": "string - Total primary discount",
        "total_sec_disc": "string - Total secondary discount",
        "total_lnd_disc": "string - Total L&D discount",
        "total_taxable_amt": "string - Total taxable amount",
        "total_cgst_amt": "string - Total CGST amount",
        "total_sgst_amt": "string - Total SGST amount",
        
        # Tax summary
        "tax_slabs": [
            {
                "taxable_amount": "string - Taxable amount for this slab",
                "cgst_rate": "string - CGST rate",
                "cgst_amount": "string - CGST amount",
                "sgst_rate": "string - SGST rate",
                "sgst_amount": "string - SGST amount"
            }
        ],
        
        # Financial summary
        "pre_tax_scheme_amt": "string - Pre-tax scheme amount",
        "net_amount": "string - Net amount",
        "total_cgst": "string - Total CGST",
        "total_sgst": "string - Total SGST",
        "cash_disc_deducted": "string - Cash discount deducted",
        "tcs_tax_amt": "string - TCS tax amount",
        "credit_adj": "string - Credit adjustment",
        "round_off": "string - Round off amount",
        "net_receivable": "string - Net receivable amount",
        "amount_in_words": "string - Amount in words",
        
        # Footer details
        "reverse_charge_basis": "string - Reverse charge basis (Yes/No)",
        "return_policy_note": "string - Return policy note",
        "jurisdiction": "string - Jurisdiction",
        "bank_account_no": "string - Bank account number",
        "bank_name": "string - Bank name",
        "bank_ifsc": "string - Bank IFSC code"
    }
    
    return jsonify(schema)

@app.route('/ewaybill-schema', methods=['GET'])
def get_ewaybill_schema():
    """Get specific schema for E-Way Bill with transport details"""
    schema = {
        "required_fields": [
            "invoice_number",
            "invoice_date", 
            "company_name",
            "customer_name",
            "products",
            "net_receivable",
            "ewb_number"
        ],
        "ewaybill_specific": {
            "ewb_number": "string - E-Way Bill number (required)",
            "ewb_date": "string - E-Way Bill generation date",
            "ewb_valid_until": "string - E-Way Bill validity end date/time",
            "ewaybill_status": "string - Status: GENERATED/PENDING/FAILED",
            "transporter_name": "string - Name of the transporter",
            "transporter_id": "string - Transporter GSTIN or ID",
            "vehicle_number": "string - Vehicle registration number",
            "driver_name": "string - Driver's name",
            "driver_mobile": "string - Driver's mobile number",
            "transport_distance": "string - Distance in kilometers",
            "transport_mode": "string - Road/Rail/Air/Ship",
            "from_place": "string - Origin city/place",
            "from_pincode": "string - Origin pincode",
            "from_state_code": "string - Origin state code",
            "to_place": "string - Destination city/place", 
            "to_pincode": "string - Destination pincode",
            "to_state_code": "string - Destination state code",
            "has_extensions": "boolean - Whether validity was extended",
            "extension_count": "number - Number of extensions applied"
        },
        "automatic_fields": {
            "is_ewaybill": "boolean - Automatically set to true",
            "invoice_type": "string - Automatically set to 'TAX INVOICE WITH E-WAY BILL'",
            "document_type": "string - Automatically set to 'ORIGINAL FOR CONSIGNEE'",
            "ewaybill_compliance_note": "string - Auto-generated compliance text"
        }
    }
    
    return jsonify(schema)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8088)