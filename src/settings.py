import secrets


#JIRA_URL = "https://siexop-jirat.epfl.ch"
JIRA_URL = "https://epfl-jira-archive.atlassian.net"
JIRA_JQL = 'project = WPFEEDBACK AND status = "Accreds à vérifier" AND resolution = Unresolved'
#JIRA_JQL = 'project = WPFEEDBACK AND status = "En attente de feedback" AND resolution = Unresolved and (do_not_disturb_webmaster_before <= now() or do_not_disturb_webmaster_before is EMPTY)'
#JIRA_JQL = 'project = WPFEEDBACK AND status = "Déployé en QA"'


# Secrets to be excluded from git
JIRA_USERNAME = secrets.JIRA_USERNAME
JIRA_PASSWORD = secrets.JIRA_PASSWORD



SMTP_SERVER = "mail.epfl.ch"
SMTP_USERNAME = secrets.SMTP_USERNAME
SMTP_PASSWORD = secrets.SMTP_PASSWORD
SMTP_FROM = "wp-migration@epfl.ch"

SMTP_DRYRUN = False
SMTP_MESSAGE_SUBJECT = "[WWP] migration de Jahia à WordPress - Vérification des accréditations"
#SMTP_MESSAGE_SUBJECT = "[WWP] migration de Jahia à WordPress - Contrôle visuel des sites migrés de Jahia à WordPress"
SMTP_MESSAGE_TEMPLATE = '20180322_WM_Check_Accreds.html'
#SMTP_MESSAGE_TEMPLATE = '20180327_WM_check.html'
JIRA_COMMENT = "Mail envoyé à {} pour contrôler les accréditations"
#JIRA_COMMENT = "Mail envoyé à {} pour contrôler visuellement"

LDAP_SERVER = "ldap.epfl.ch"
LDAP_BASE_DN = "c=ch"
