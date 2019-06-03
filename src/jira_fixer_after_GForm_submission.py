from jira import JIRA
import settings
import csv


def get_separator(emails: str)->str:
    possible_separators = ["|", ",", ";", "/"]

    for separator in possible_separators:
        if emails.find(separator) > -1:
            return separator

    return ''


def normalize_emails(emails: str)->str:

    separator = get_separator(emails)

    if separator == '':
        return emails.strip()
    else:
        normalized_emails_list = list()
        mails = emails.split(separator)
        for mail in mails:
            normalized_emails_list.append(mail.strip())
        return '|'.join(normalized_emails_list)


def update_jira(site_name: str, unit_name: str, webmasters: str)->None:

    # cleanup
    unit_name = unit_name.upper()

    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    sites = jira.search_issues("project=WPFEEDBACK AND summary~'{}'".format(site_name), maxResults=1)
    assert len(sites) == 1

    site = sites[0]
    if site.fields.customfield_10404 != unit_name:
        comment = "{}: Updating unit name from '{}' to '{}'".format(site_name, site.fields.customfield_10404, unit_name)
        print(comment)
        jira.add_comment(site, comment)
        site.update(fields={'customfield_10404': unit_name})

    if site.fields.customfield_10403 != webmasters:
        comment = "{}: Updating webmasters from '{}' to '{}'".format(site_name, site.fields.customfield_10403, webmasters)
        print(comment)
        jira.add_comment(site, comment)
        site.update(fields={'customfield_10403': webmasters})


def transition_site(site_name: str, new_status: str) -> None:
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    sites = jira.search_issues("project=WPFEEDBACK AND summary~'{}'".format(site_name), maxResults=1)
    assert len(sites) == 1

    site = sites[0]

    transitions = jira.transitions(site)
    for t in transitions:
        if t['name'] == new_status:
            comment = "{}: Applied transition '{}'".format(site_name, new_status)
            print(comment)
            jira.transition_issue(issue=site, transition=t['id'])
            jira.add_comment(site, comment)


if __name__ == "__main__":
    with open('../loaded_rights_batch_2_results_clean.csv', 'r', newline='') as csvfile:
        spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')

        # Skip the header row
        next(spamreader, None)

        # Loop over the data
        for row in spamreader:
            site_name = row[1]
            unit_name = row[3]
            cleaned_emails = normalize_emails(row[4])
            update_jira(site_name, unit_name, cleaned_emails)
            transition_site(site_name, "Accred vérifiées")
