from jira import JIRA
import settings
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, select_autoescape, FileSystemLoader


def get_sites_deployed_in_QA() -> list:
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    sites = jira.search_issues('project = WPFEEDBACK AND status = "déployé en QA"', maxResults=10000)
    return sites


def transition_site(key: str, site_name: str, new_status: str) -> None:
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
        msgSubject = "[WWP] [{0}] Le site '{0}' a été (re)déployé / The '{0}' site has been (re)deployed".format(site_name)
        msgBody = jinja_template.render(site_name=site_name, unit=unit, webmasters=", ".join(webmasters.split("|")),
                                        WordPress_url=WordPress_url)
        send_message(webmaster, msgSubject, msgBody)

    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    comment = "{}: Notified '{}' that the site has been (re)deployed".format(site_name, webmasters)
    jira.add_comment(key, comment)


def notify_wordpress_admins(key: str, site_name: str) -> None:
    """
    Notify wordpress admin about the fact that website with [UP] flag has been redeployed and ask them to do some things
    :param key: WWP-1234
    :param site_name: site name
    :return:
    """
    # time to buid the mails
    jinja_env = Environment(
        loader=FileSystemLoader("{}/templates/".format(os.path.dirname(os.path.dirname(__file__)))),
        autoescape=select_autoescape('html', 'xml'),
        trim_blocks=True,
        lstrip_blocks=True)

    jinja_template = jinja_env.get_template("20181008_Admins_UP_WD_redeployed.html")

    msgSubject = "[WWP] [{0}] Le site '{0}' a été (re)déployé - Mise à jour de ServiceNow requise".format(site_name)
    msgBody = jinja_template.render(site_name=site_name, site_key=key)
    send_message("wwp-members@groupes.epfl.ch", msgSubject, msgBody)


if __name__ == "__main__":
    sites = get_sites_deployed_in_QA()
    for site in sites:

        site_key = site.key
        site_name = site.fields.summary

        # If website is in "Update in Progress" state, we have to move it to the right column
        if site_name.startswith('[UP]'):
            print("{} is in 'Update in Progress', moving it in right column...".format(site_key))
            transition_site(site_key, site_name, "Webmaster notifié")
            transition_site(site_key, site_name, "Contient des bugs")

            notify_wordpress_admins(key=site_key, site_name=site_name.replace('[UP]', '').strip())

        else: # Website is not in "Update in Progress" state

            have_wont_do_issues = False
            # Looking for issues to see if there is "Won't Do" issues
            for issue_link in site.fields.issuelinks:
                if (hasattr(issue_link, 'outwardIssue') and issue_link.outwardIssue.fields.summary.startswith("[WD]")) or \
                        (hasattr(issue_link, 'inwardIssue') and issue_link.inwardIssue.fields.summary.startswith("[WD]")):
                    have_wont_do_issues = True
                    break

            # If site have "won't do issues", communication to WM will by manually done
            if have_wont_do_issues:
                print('{} has "Won\'t do" issue(s), moving it in right column...'.format(site_key))

                # We have to go through others column before going in "won't do" column
                transition_site(site_key, site_name, "Webmaster notifié")
                transition_site(site_key, site_name, "Contient des bugs")
                transition_site(site_key, site_name, "Won't do à communiquer au WM")

            else:
                # No won't do issues so communcation is automatic
                unit = site.fields.customfield_10404
                webmasters = site.fields.customfield_10403
                WordPress_url = site.fields.customfield_10501

                notify_webmasters(site_key, site_name, unit, webmasters, WordPress_url)
                transition_site(site_key, site_name, "Webmaster notifié")
