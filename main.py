import os
import logging
import smtplib
from flask import Flask, render_template, request
from supabase import create_client, Client
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


SUPABASE_URL = os.environ.get('SUPABASE_URL') 
SUPABASE_API_KEY = os.environ.get('SUPABASE_API_KEY') 
EMAIL_USER = os.environ.get('SMTP_USER')  # المستخدم المخزن في secrets
EMAIL_PASS = os.environ.get('SMTP_PASSWORD')  # كلمة المرور المخزنة في secrets
EMAIL_HOST = 'smtp-mail.outlook.com'  # خادم SMTP الخاص بـ Hotmail/Outlook
EMAIL_PORT = 587  # المنفذ المستخدم

# إعدادات الاتصال بـ Supabase

# استدعاء القيم من الـ Secrets
app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/procurement')
def procurement():
    return render_template('procurement.html')


@app.route('/procurement/mr-details')
def mr_details():
    return render_template('mr_details.html')


@app.route('/procurement/rfq')
def rfq():
    return render_template('rfq.html')


@app.route('/procurement/search')
def search():
    return render_template('search.html')


@app.route('/customs')
def customs():
    return render_template('customs.html')


@app.route('/inventory')
def inventory():
    return render_template('inventory.html')


@app.route('/reports')
def reports():
    try:
        procurement_data = supabase.table("procurement").select(
            "*").execute().data
        inventory_data = supabase.table("inventory").select("*").execute().data
        customs_data = supabase.table("customs").select("*").execute().data
    except Exception as e:
        logging.error(f"An error occurred while fetching reports data: {e}")
        return f"An error occurred while fetching reports data: {e}", 500

    return render_template('reports.html',
                           procurement_data=procurement_data,
                           inventory_data=inventory_data,
                           customs_data=customs_data)


@app.route('/submit-mr-details', methods=['POST'])
def submit_mr_details():
    data = {
        "mr_no": request.form.get('mr_no'),
        "po_no": request.form.get('po_no'),
        "cd_no": request.form.get('cd_no'),
        "specs": request.form.get('specs'),
        "est_value": request.form.get('est_value'),
        "vendor_name": request.form.get('vendor_name'),
        "actual_value": request.form.get('actual_value'),
        "delivery_time": request.form.get('delivery_time'),
        "delivery_location": request.form.get('delivery_location'),
        "eta": request.form.get('eta'),
        "payment": request.form.get('payment'),
        "closed": request.form.get('closed')
    }

    required_fields = ["mr_no", "po_no", "specs"]
    for field in required_fields:
        if not data.get(field):
            return f"Error: '{field}' is required and cannot be empty.", 400

    try:
        response = supabase.table("procurement").insert(data).execute()
        return f"MR Details submitted successfully for MR No.: {data['mr_no']}"
    except Exception as e:
        logging.error(f"An error occurred while submitting MR details: {e}")
        return f"An error occurred while submitting MR details: {e}", 500


@app.route('/submit-rfq', methods=['POST'])
def submit_rfq():
                    rfq_no = request.form.get('rfq_no')
                    rfq_date = request.form.get('rfq_date')
                    list_name = request.form.get('list_name')
                    item_no = request.form.getlist('item_no[]')
                    specification = request.form.getlist('specification[]')
                    quantity = request.form.getlist('quantity[]')

                    # التحقق من المدخلات الأساسية
                    if not rfq_no or not rfq_date or not list_name:
                        return "خطأ: RFQ No، Date، و List Name مطلوبون.", 400

                    try:
                        # إدخال بيانات الـ RFQ في Supabase
                        for i in range(len(item_no)):
                            supabase.table("rfq").insert({
                                "rfq_no": rfq_no,
                                "rfq_date": rfq_date,
                                "list_name": list_name,
                                "item_no": item_no[i],
                                "specification": specification[i],
                                "quantity": quantity[i]
                            }).execute()

                        # جلب معلومات الموردين بناءً على list_name
                        suppliers = supabase.table("list_name").select("supplier_name, supplier_email").eq("list_name", list_name).execute().data

                        # التحقق من وجود الموردين
                        if not suppliers:
                            return f"لم يتم العثور على موردين مرتبطين بـ list_name: {list_name}", 404

                        # إرسال الإيميل لكل مورد
                        for supplier in suppliers:
                            email_result = send_email(rfq_no, rfq_date, supplier['supplier_email'])
                            if email_result != "Success":
                                return f"حدث خطأ أثناء إرسال الإيميل إلى {supplier['supplier_email']}: {email_result}", 500

                        return "تم إرسال RFQ وإرسال الإيميلات بنجاح."

                    except Exception as e:
                        logging.error(f"Error in RFQ submission: {e}")
                        return f"Error: {str(e)}", 500


def send_email(rfq_no, rfq_date, to_email):
                    try:
                        msg = MIMEMultipart()
                        msg['From'] = EMAIL_USER
                        msg['To'] = to_email
                        msg['Subject'] = f"RFQ {rfq_no} - {rfq_date}"

                        body = f"""
                        Dear Supplier,

                        Please find the RFQ details below:
                        RFQ No: {rfq_no}
                        Date: {rfq_date}

                        Please respond with your quotation.

                        Best regards,
                        Procurement Team
                        """
                        msg.attach(MIMEText(body, 'plain'))

                        # إرسال البريد الإلكتروني باستخدام SMTP
                        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
                            server.starttls()  # تأمين الاتصال
                            server.login(EMAIL_USER, EMAIL_PASS)  # تسجيل الدخول باستخدام البيانات المخزنة في secrets
                            server.sendmail(EMAIL_USER, to_email, msg.as_string())  # إرسال الإيميل

                        logging.info(f"Email sent to {to_email}")
                        return "Success"

                    except Exception as e:
                        logging.error(f"An error occurred while sending email to {to_email}: {e}")
                        return str(e)



@app.route('/search-results', methods=['GET'])
def search_results():
    mr_no = request.args.get('mr_no')
    po_no = request.args.get('po_no')

    try:
        if mr_no:
            response = supabase.table("procurement").select("*").eq(
                "mr_no", mr_no).execute()
        elif po_no:
            response = supabase.table("procurement").select("*").eq(
                "po_no", po_no).execute()
        else:
            return "No results found. Please enter MR No. or P.O. No.", 400
    except Exception as e:
        logging.error(f"An error occurred while searching: {e}")
        return f"An error occurred while searching: {e}", 500

    return render_template('search_results.html', results=response.data)


@app.route('/submit-customs', methods=['POST'])
def submit_customs():
    data = {
        "customs_declaration_number":
        request.form.get('customs_declaration_number'),
        "purchase_order_number":
        request.form.get('purchase_order_number'),
        "amount":
        request.form.get('amount'),
        "vendor_name":
        request.form.get('vendor_name'),
        "shipping_method":
        request.form.get('shipping_method'),
        "bill_of_lading_number":
        request.form.get('bill_of_lading_number'),
        "full_specification":
        request.form.get('full_specification'),
        "quantities":
        request.form.get('quantities'),
        "accounted_for_whom":
        request.form.get('accounted_for_whom')
    }

    required_fields = ["customs_declaration_number"]
    for field in required_fields:
        if not data.get(field):
            return f"Error: '{field}' is required and cannot be empty.", 400

    try:
        response = supabase.table("customs").insert(data).execute()
        return f"Customs data submitted successfully for Customs Declaration Number: {data['customs_declaration_number']}"
    except Exception as e:
        logging.error(f"An error occurred while submitting customs data: {e}")
        return f"An error occurred while submitting customs data: {e}", 500


@app.route('/customs_reports')
def customs_reports():
    try:
        customs_data = supabase.table('customs').select("*").execute().data
    except Exception as e:
        logging.error(
            f"An error occurred while fetching customs reports data: {e}")
        return f"An error occurred while fetching customs reports data: {e}", 500

    return render_template('customs_reports.html', customs_data=customs_data)


@app.route('/submit-inventory', methods=['POST'])
def submit_inventory():
    data = {
        "specification": request.form.get('specification'),
        "est_value": request.form.get('est_value'),
        "last_purchase_date": request.form.get('last_purchase_date'),
        "quantities": request.form.get('quantities'),
        "min_value": request.form.get('min_value'),
        "max_value": request.form.get('max_value')
    }

    required_fields = ["specification", "est_value"]
    for field in required_fields:
        if not data.get(field):
            return f"Error: '{field}' is required and cannot be empty.", 400

    try:
        response = supabase.table("inventory").insert(data).execute()
        return f"Inventory data submitted successfully for specification: {data['specification']}"
    except Exception as e:
        logging.error(
            f"An error occurred while submitting inventory data: {e}")
        return f"An error occurred while submitting inventory data: {e}", 500


@app.route('/procurement/employees/<employee_name>', methods=['GET', 'POST'])
def employee_details(employee_name):
    if request.method == 'POST':
        data = {
            "mr_no": request.form.get('mr_no'),
            "description": request.form.get('description'),
            "est_value": request.form.get('est_value'),
            "status": request.form.get('status'),
            "employee_name": employee_name
        }
        try:
            response = supabase.table("employee_data").insert(data).execute()
        except Exception as e:
            logging.error(
                f"An error occurred while submitting employee data: {e}")
            return f"An error occurred while submitting employee data: {e}", 500

    try:
        employee_data = supabase.table("employee_data").select("*").eq(
            "employee_name", employee_name).execute().data
    except Exception as e:
        logging.error(f"An error occurred while fetching employee data: {e}")
        return f"An error occurred while fetching employee data: {e}", 500

    return render_template('employee_details.html',
                           employee_name=employee_name,
                           employee_data=employee_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

