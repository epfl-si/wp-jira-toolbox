import json
import os
import re
import csv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gspread
import requests
import settings
from jinja2 import Environment, select_autoescape, FileSystemLoader
from jira import JIRA
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from site_to_check import SiteToCheck
from google_form_to_send import GoogleFormToSend


def get_list_of_Jira_sites_to_migrate() -> list:
    # boilerplate
    results = []

    # Connect to the Jira instance
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))

    # Search for the issues using JQL
    issues_in_project = jira.search_issues(settings.JIRA_JQL, maxResults=1000)

    # Loop over the issues found
    for issue in issues_in_project:
        current_result = SiteToCheck()

        current_result.jira_issue_key = issue.key
        current_result.jahia_url = issue.fields.customfield_10400
        current_result.wordpress_url = issue.fields.customfield_10501
        current_result.associated_unit = issue.fields.customfield_10404
        for person in issue.fields.customfield_10403.split('|'):
            current_result.persons_in_charge.append(person.strip())
        current_result.site_name = issue.fields.description

        results.append(current_result)

    return results


def get_metadata_information_from_truth_source() -> dict:
    # use credentials to create a client to interact with the Google Drive API
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('Jahia2WP-a52cf41bf254.json', scope)
    client = gspread.authorize(credentials)

    sheet = client.open("Jahia 2 Wordpress - Source de vérité").worksheet('Sites WP INT - Migrations')

    # Extract and print all of the values
    list_of_hashes = sheet.get_all_records()

    return_value = dict()
    for site in list_of_hashes:
        parsed_site_name = re.match('https://migration-wp\.epfl\.ch/(.*)', site['wp_site_url'], re.IGNORECASE).group(1)
        return_value[parsed_site_name] = site['unit_name']

    return return_value


def update_site_associated_unit_in_Jira(Jira_key: str, associated_unit: str) -> None:
    # Connect to the Jira instance
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))

    issues = jira.search_issues('key = {}'.format(Jira_key))

    assert issues.total == 1

    for issue in issues:
        issue.update(customfield_10404=associated_unit)


def add_comment_to_Jira_item(Jira_key: str, comment: str) -> None:
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    jira.add_comment(Jira_key, comment)


def get_Jira_issue_by_Jahia_url(Jahia_url: str) -> str:
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    issues = jira.search_issues("'URL Jahia' = '{}'".format(Jahia_url))
    assert issues.total == 1
    for issue in issues:
        return issue.key


def get_Jira_issue_by_site_name(name: str) -> str:
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    issues = jira.search_issues("project = WPFEEDBACK AND Summary ~'{}'".format(name))
    assert issues.total == 1, 'Found {} issue(s) instead of 1'.format(issues.total)
    for issue in issues:
        return issue.key


def fix_missing_associated_unit_in_Jira() -> None:
    Jira_sites_to_migrate = get_list_of_Jira_sites_to_migrate()
    sites_metadata = get_metadata_information_from_truth_source()

    for Jira_site_to_migrate in Jira_sites_to_migrate:
        if Jira_site_to_migrate.associated_unit is None:
            if Jira_site_to_migrate.site_name in sites_metadata.keys():
                print("{} -> {}".format(Jira_site_to_migrate, sites_metadata[Jira_site_to_migrate.site_name]))
                update_site_associated_unit_in_Jira(Jira_site_to_migrate.jira_issue_key,
                                                    sites_metadata[Jira_site_to_migrate.site_name])
                Jira_site_to_migrate.associated_unit = sites_metadata[Jira_site_to_migrate.site_name]
            else:
                print("{} -> {}".format(Jira_site_to_migrate, 'Not found in Google sheet'))
        else:
            print("{} -> {}".format(Jira_site_to_migrate, 'Already associated'))


def get_unit_id_selenium(unit_name: str) -> str:
    driver = webdriver.Firefox()
    driver.get('http://bottin.epfl.ch/ubrowse.action?acro={}'.format(unit_name))
    administrative_data_link = driver.find_element_by_xpath('//button[@title="Administrative datas"]')
    administrative_data_link.click()
    accreditors_link_element = driver.find_element_by_xpath(
        '//a[@title="Accreditors, roles and rights for this unit (fr)"]')
    accreditors_link = accreditors_link_element.get_attribute('href')
    unit_id = re.match('http://accred\.epfl\.ch/cgi-bin/adminsofunite\.pl\?unite=(\d*)', accreditors_link,
                       re.IGNORECASE).group(1)
    driver.close()

    return unit_id


def get_unit_id_api(unit_name: str) -> int:
    base_url = 'http://websrv.epfl.ch/cgi-bin/rwsunits/searchUnits?acro={}&app=websrv'.format(unit_name)
    headers = {'Content-Type': 'application/json'}

    response = requests.get(base_url, headers)

    if response.status_code == 200:
        json_result = json.loads(response.content.decode('utf-8'))
        return json_result['result'][0]['id']


def build_link_to_rights_check(unit_id: int) -> str:
    return "https://accred.epfl.ch/cgi-bin/adminsofunite.pl/droitdetails?unite={}&droit=103&details=consulter".format(
        unit_id)


def build_link_to_accreditors(unit_id: int) -> str:
    return "https://accred.epfl.ch/cgi-bin/adminsofunite.pl?unite={}".format(unit_id)


def send_message(to: str, message: str) -> None:
    me = settings.SMTP_FROM
    msg = MIMEMultipart('alternative')
    msg['Subject'] = settings.SMTP_MESSAGE_SUBJECT
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


def notify_webmasters(Jira_sites_to_migrate: list) -> None:
    # Build the extra info needed for the mail merge
    for Jira_site_to_migrate in Jira_sites_to_migrate:
        unit_id = get_unit_id_api(Jira_site_to_migrate.associated_unit)
        Jira_site_to_migrate.link_to_persons_having_editor_right = build_link_to_rights_check(unit_id)
        Jira_site_to_migrate.link_to_accreditors_for_the_unit = build_link_to_accreditors(unit_id)

    # time to buid the mails
    jinja_env = Environment(
        loader=FileSystemLoader("{}/templates/".format(os.path.dirname(os.path.dirname(__file__)))),
        autoescape=select_autoescape('html', 'xml'),
        trim_blocks=True,
        lstrip_blocks=True)

    jinja_template = jinja_env.get_template(settings.SMTP_MESSAGE_TEMPLATE)

    # Get the list of individual webmaster to send the mail to
    webmasters = []
    for Jira_site_to_migrate in Jira_sites_to_migrate:
        for person_in_charge in Jira_site_to_migrate.persons_in_charge:
            if person_in_charge not in webmasters:
                webmasters.append(person_in_charge)

    # Send the mail
    for webmaster in webmasters:
        msgBody = jinja_template.render(sites=Jira_sites_to_migrate, webmaster=webmaster)
        send_message(webmaster, msgBody)


def update_WordPress_url_in_jira():
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    issues = jira.search_issues("project = WPFEEDBACK AND 'Url WordPress' is empty", maxResults=10000)
    for issue in issues:
        issue.update(customfield_10501="https://migration-wp.epfl.ch/{}".format(issue.fields.summary))


def process_wave_of_new_sites() -> None:
    # Retrieve the info from Jira
    Jira_sites_to_migrate = get_list_of_Jira_sites_to_migrate()

    # Send the notification to the webmasters
    notify_webmasters(Jira_sites_to_migrate)

    # Add the comment to Jira so we can keep track of what has been done
    for Jira_site_to_migrate in Jira_sites_to_migrate:
        comment = settings.JIRA_COMMENT.format(",".join(Jira_site_to_migrate.persons_in_charge))
        add_comment_to_Jira_item(Jira_site_to_migrate.jira_issue_key, comment)


def send_mailing_about_GoogleForm() -> list:
    notifications_to_send = list()

    with open('../mailing_data.csv', newline='') as csvfile:
        datareader = csv.reader(csvfile, delimiter=",")
        i = 0
        for row in datareader:
            if i > 0:
                notification_to_send = GoogleFormToSend()
                notification_to_send.site = row[0]
                notification_to_send.jahia_url = row[1]
                notification_to_send.associated_unit = row[2]
                notification_to_send.webmasters = ', '.join(row[3].split('|'))
                notification_to_send.google_form_url = row[4]
                notifications_to_send.append(notification_to_send)
            i += 1

    notify_of_Google_Form_Usage(notifications_to_send)



def notify_of_Google_Form_Usage(notifications: list) -> None:
    jinja_env = Environment(
        loader=FileSystemLoader("{}/templates/".format(os.path.dirname(os.path.dirname(__file__)))),
        autoescape=select_autoescape('html', 'xml'),
        trim_blocks=True,
        lstrip_blocks=True)

    jinja_template = jinja_env.get_template('20180430_WM_google_form.html')

    for notification in notifications:
        msgBody = jinja_template.render(notification_to_send=notification)

        me = settings.SMTP_FROM
        msg = MIMEMultipart('alternative')
        subject = '[WWP] [{}] Vérification des accréditations'.format(notification.site)
        msg['Subject'] = subject
        msg['From'] = me
        if settings.SMTP_DRYRUN:
            msg['To'] = me
            recipients = [me]
        else:
            msg['To'] = notification.webmasters
            recipients = []
            for webmaster in notification.webmasters.split(','):
                recipients.append(webmaster.strip())

            if me not in recipients:
                recipients.append(me)

        text = "Your mail client does not support HTML emails."

        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(msgBody, 'html')

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


if __name__ == "__main__":
    send_mailing_about_GoogleForm()

    # issue_key = get_Jira_issue_by_site_name('si-erp')
    # add_comment_to_Jira_item(issue_key,
    #                          "WM: corrigé, Association: NA. Accred: corrigé."
    #                          #'Correction des accreds pour Caroline Antonioli Pletscher'
    #                           )

    # process_wave_of_new_sites()

    # update_WordPress_url_in_jira()
