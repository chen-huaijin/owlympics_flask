# Send email automatically
def send_email(TEXT, TO):
    import smtplib
    user = "eceowlympics@gmail.com"
    pwd = "eceowlympicspw"
    FROM = 'eceowlympics@gmail.com'
    SUBJECT = "Username/password recovery for Rice ECE Owlympics"

    # Prepare actual message
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587) #or port 465 doesn't seem to work
        server.ehlo()
        server.starttls()
        server.login(user, pwd)
        server.sendmail(FROM, TO, message)
        #server.quit()
        server.close()
        isSent = True
    except:
        isSent = False

    return isSent
