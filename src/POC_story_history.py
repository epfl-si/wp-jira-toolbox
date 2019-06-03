from jira import JIRA
import settings
import time
import datetime


def get_date_of_last_transition_to_status(key: str, status_name: str):
    dates = list()
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    site = jira.issue(key, expand='changelog')
    for history_item in site.changelog.histories:
        for item in history_item.items:
            print(item)
            if item.field == 'status' and item.toString.upper() == status_name.upper():
                timestamp = datetime.datetime.strptime(history_item.created, "%Y-%m-%dT%H:%M:%S.%f%z").timestamp()
                dates.append(timestamp)
    return max(dates)


if __name__ == "__main__":
    get_date_of_last_transition_to_status('WPFEEDBACK-3', 'EN ATTENTE DE FEEDBACK')
