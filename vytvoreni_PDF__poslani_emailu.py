import subprocess
import os
from datetime import datetime

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

##########################################################################################################
########################################## Vytvoření PDF #################################################
##########################################################################################################
def process_images_and_create_report():
    try:
        current_date = datetime.now().strftime('%Y-%m-%d')

        # resizing images
        subprocess.run('for img in *.png; do convert "$img" -resize 50% "$img"; done', shell=True)

        # reating montage files
        subprocess.run('montage obr_zakl1.png obr_zakl2.png '
                        'obr_0_0.png obr_1_0.png '
                        'obr_0_1.png obr_nevim.png '
                        'obr_0_2.png obr_1_2.png '
                        'obr_0_3.png obr_1_3.png '
                        'obr_0_4.png obr_1_4.png '
                        'obr_0_5.png obr_1_5.png '
                        'obr_0_6.png obr_1_6.png '
                        'obr_0_7.png obr_1_7.png '
                        'obr_19.png obr_20.png '
                        'obr_0_8.png obr_1_8.png '
                        'obr_21.png '
                        '-tile 2x4 -geometry +0+0 montage_output.png', shell=True)

        # montage to PDF
        subprocess.run(f'for img in montage_output-*.png; do base_name=$(basename "$img" .png); '
                       f'convert "$img" -gravity South -pointsize 24 -annotate +0+10 "{current_date}" '
                       f'"$base_name.pdf"; done', shell=True)

        # merging PDFs
        subprocess.run(f'pdfunite montage_output-*.pdf covid_report.pdf', shell=True)

        # odstranění "neziouborů"
        subprocess.run('rm montage_output-*.pdf *.png', shell=True)

        print("PDF was created")
    except:
        print("Problem")


##########################################################################################################š
######################### Poslání emailu ##################################################################
##########################################################################################################

def send_email_with_pdf(sender_email, sender_password, receiver_email, subject, body, pdf_file):
    # Create a multipart message
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = receiver_email
    message['Subject'] = subject

    # Attach the email body
    message.attach(MIMEText(body, 'plain'))

    # Open the PDF file in binary mode
    with open(pdf_file, "rb") as attachment:
        # Create a MIMEBase object and attach the file to it
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    # Encode the attachment in base64
    encoders.encode_base64(part)

    # Add header to the attachment
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {os.path.basename(pdf_file)}",
    )

    # Attach the PDF file to the email
    message.attach(part)

    # Connect to the email server and send the email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)  # Use Gmail's SMTP server (adjust if using another service)
        server.starttls()  # Secure the connection
        server.login(sender_email, sender_password)  # Log in to the email account
        text = message.as_string()
        server.sendmail(sender_email, receiver_email, text)  # Send the email
        print(f"Email sent to {receiver_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit()
