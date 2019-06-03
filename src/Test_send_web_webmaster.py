from jira import JIRA
import settings
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, select_autoescape, FileSystemLoader


def get_sites_deployed_in_QA() -> list:
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    sites = jira.search_issues('project = WPFEEDBACK AND status = "déployé en QA" AND site = "theos"', maxResults=10000)
    return sites


def transition_site(key: str, new_status: str) -> None:
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))

    transitions = jira.transitions(key)
    for t in transitions:
        if t['name'] == new_status:
            comment = "{}: Applied transition '{}'".format(site_name, new_status)
            print(comment)
            jira.transition_issue(issue=site, transition=t['id'])
            jira.add_comment(key, comment)
            break


def send_message(to: str, subject: str, message: str) -> None:
    me = settings.SMTP_FROM
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = me
    if settings.SMTP_DRYRUN:
        msg['To'] = me
        recipients = [me]
    else:
        msg['To'] = to
        recipients = [to, me]

    text = "Your mail client does not support HTML emails."

    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(message, 'html')

    msg.attach(part1)
    msg.attach(part2)

    smtp = smtplib.SMTP(settings.SMTP_SERVER)
    smtp.connect(settings.SMTP_SERVER)
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()
    smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
    smtp.send_message(msg, me, recipients)
    smtp.quit()


def notify_webmasters(key: str, site_name: str, unit: str, webmasters: str, WordPress_url: str) -> None:
    # time to buid the mails
    jinja_env = Environment(
        loader=FileSystemLoader("{}/templates/".format(os.path.dirname(os.path.dirname(__file__)))),
        autoescape=select_autoescape('html', 'xml'),
        trim_blocks=True,
        lstrip_blocks=True)

    jinja_template = jinja_env.get_template("20180508_WM_deployment_notification.html")

    # Send the mail
    for webmaster in webmasters.split("|"):
        msgSubject = "[WWP] [{0}] Le site '{0}' a été (re)déployé / The '{0}' site has been (re)deployed".format(
            site_name)
        msgBody = jinja_template.render(site_name=site_name, unit=unit, webmasters=", ".join(webmasters.split("|")),
                                        WordPress_url=WordPress_url)
        send_message(webmaster, msgSubject, msgBody)


if __name__ == "__main__":
    notify_webmasters('dcsl', 'nom_du_site', 'IDEVING', 'luc.venries@epfl.ch', 'https://migration-wp.epfl.ch/dcls')
