from jira import JIRA
import settings


def get_related_bugs(WordPress_url: str) -> list:
    return_value = list()

    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))

    bugs_related_to_this_site_jql = 'project = WWP AND resolution = Unresolved and text ~"{}/"'.format(WordPress_url)
    bugs_related_to_this_site = jira.search_issues(bugs_related_to_this_site_jql, maxResults=5000)
    for bug_related_to_this_site in bugs_related_to_this_site:
        return_value.append(bug_related_to_this_site.key)

    return return_value


def link_bug_to_site(bug_key: str, site_key: str) -> None:
    print("Linking bug '{}' with site '{}".format(bug_key, site_key))
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))

    jira.create_issue_link(
        type="blocks",
        inwardIssue=bug_key,
        outwardIssue=site_key,
        comment={
            "body": "Linking '%s' --&gt; '%s'" % (bug_key, site_key),
        }
    )


def issue_is_still_open(key: str) -> bool:
    print("Checking bug status for {}".format(key))
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    issue = jira.issue(key)
    current_status = str(issue.fields.status)
    return_value = (current_status != 'Done')
    return return_value


def transition_site(key: str, new_status: str) -> None:
    print("Transitioning {} with '{}'...".format(key, new_status), end='')
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    site = jira.issue(key)
    transitions = jira.transitions(site)
    for t in transitions:
        if t['name'] == new_status:
            jira.transition_issue(issue=site, transition=t['id'])
        print('done')


def link_bugs_with_sites():
    # Connect to the Jira instance
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))

    # Search for the issues wiating for feedback using JQL
    sites_awaiting_for_wm_feedback_jql = 'project = WPFEEDBACK AND issuetype = Story AND status != Done'
    sites_awaiting_for_wm_feedback = jira.search_issues(sites_awaiting_for_wm_feedback_jql, maxResults=5000)
    for site_awaiting_for_wm_feedback in sites_awaiting_for_wm_feedback:
        print('Checking links for {}'.format(site_awaiting_for_wm_feedback.key))
        related_bugs = get_related_bugs(site_awaiting_for_wm_feedback.fields.customfield_10501)

        # Make sure we do not duplicate work
        for related_bug in related_bugs:
            should_be_skipped = False

            for linked_issue in site_awaiting_for_wm_feedback.fields.issuelinks:
                if hasattr(linked_issue, 'inwardIssue') and linked_issue.inwardIssue.key == related_bug:
                    should_be_skipped = True
                    break
                if hasattr(linked_issue, 'outwardIssue') and linked_issue.outwardIssue.key == related_bug:
                    should_be_skipped = True
                    break

            if not should_be_skipped:
                link_bug_to_site(related_bug, site_awaiting_for_wm_feedback.key)


def transition_sites_having_open_bugs():
    # Connect to the Jira instance
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    # Search for the issues wiating for feedback using JQL
    sites_awaiting_for_wm_feedback_jql = 'project = WPFEEDBACK and status = "En attente de feedback" and issuetype = Story'
    sites_awaiting_for_wm_feedback = jira.search_issues(sites_awaiting_for_wm_feedback_jql, maxResults=5000)
    for site_awaiting_for_wm_feedback in sites_awaiting_for_wm_feedback:
        print("Checking transition for {}".format(site_awaiting_for_wm_feedback.key))
        should_be_transitioned = False

        for issue_link in site_awaiting_for_wm_feedback.fields.issuelinks:
            still_open = False
            if hasattr(issue_link, 'outwardIssue'):
                still_open = issue_is_still_open(issue_link.outwardIssue.key)
            else:
                still_open = issue_is_still_open(issue_link.inwardIssue.key)
            if still_open:
                should_be_transitioned = True
                break

        if should_be_transitioned:
            transition_site(site_awaiting_for_wm_feedback.key, 'Contient des bugs')


def transition_sites_waiting_for_fix() -> None:
    # Connect to the Jira instance
    jira = JIRA(settings.JIRA_URL, basic_auth=(settings.JIRA_USERNAME, settings.JIRA_PASSWORD))
    # Search for the issues wiating for feedback using JQL
    sites_having_bugs_jql = 'project = WPFEEDBACK and status = "En attente de correction de Bug" and issuetype = Story'
    sites_having_bugs = jira.search_issues(sites_having_bugs_jql, maxResults=5000)
    for site_having_bugs in sites_having_bugs:
        print("Checking transition for {}".format(site_having_bugs.key))
        should_be_transitioned = True

        for issue_link in site_having_bugs.fields.issuelinks:
            if hasattr(issue_link, 'outwardIssue'):
                still_open = issue_is_still_open(issue_link.outwardIssue.key)
            else:
                still_open = issue_is_still_open(issue_link.inwardIssue.key)
            if still_open:
                should_be_transitioned = False
                break

        if should_be_transitioned:
            transition_site(site_having_bugs.key, 'A redeployer en QA')


if __name__ == "__main__":
    # Make sure sure that sites are linked to their respective bugs
    link_bugs_with_sites()

    # Now that we know that all bugs and sites are linked correctly
    # it is time to find all the sites supposedly 'waiting for feedback' actually having open bugs attached
    # if it is the case, the site should be transitioned to 'waiting for bug fixing'

    transition_sites_having_open_bugs()

    # Now it's time to review all sites in 'En attente de correction de bug'
    # if they do not have linked bugs that are open, they can be transitioned back
    # to 'A migrer en QA'
    transition_sites_waiting_for_fix()
