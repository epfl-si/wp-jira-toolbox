
import settings
from jira import JIRA
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, select_autoescape, FileSystemLoader



def get_sites_deployed_in_QA_2018() -> list:
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    sites = jira.search_issues('project = WP2018 AND status = "Instance Vide Prod18 A notifier" AND cf[10903] != "Pas de notif."', maxResults=100)
    return sites


def transition_site(key: str, new_status: str, site_name, site) -> None:
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


def notify_webmasters(key: str, site_name: str, webmasters: str, wordpress_url: str, QA18_url:str, url_ventilation: str, QA_source: str, fin_url: str) -> None:
    # time to buid the mails
    jinja_env = Environment(
        loader=FileSystemLoader("{}/templates/".format(os.path.dirname(os.path.dirname(__file__)))),
        autoescape=select_autoescape('html', 'xml'),
        trim_blocks=True,
        lstrip_blocks=True)

    jinja_template = jinja_env.get_template("20190606_notify_WM_vide_prod_2018.py.html")

    # Send the mail
    for webmaster in webmasters.split("|"):
        msgSubject = "[{0}] Votre site vide a été créé dans l’arborescence www.epfl.ch – Your empty has been created in the www.epfl.ch tree".format(
            site_name)
        msgBody = jinja_template.render(site_name=site_name, webmasters=", ".join(webmasters.split("|")),
                                        WordPress_url=wordpress_url, QA18_url=QA18_url,
                                        url_ventilee=url_ventilation, QA_source=QA_source, fin_url=fin_url)
        send_message(webmaster, msgSubject, msgBody)

    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    comment = "{}: Notified '{}' that a empty site has been created".format(site_name, webmasters)
    jira.add_comment(key, comment)


def vide_prod():
    sites = get_sites_deployed_in_QA_2018()
    for site in sites:
        site_key = site.key
        site_name = site.fields.summary

        webmasters = site.fields.customfield_10403
        wordpress_url = site.fields.customfield_10501
        QA18_url = site.fields.customfield_10908
        url_ventilation = site.fields.customfield_10900
        QA_source = site.fields.customfield_10902  # tells if copy or empty site

        notify_webmasters(site_key, site_name, webmasters, wordpress_url, QA18_url, url_ventilation, str(QA_source), str(url_ventilation)[-1])
        transition_site(site_key, "A adapter prod18", site_name, site)


if __name__ == "__main__":
    vide_prod()


